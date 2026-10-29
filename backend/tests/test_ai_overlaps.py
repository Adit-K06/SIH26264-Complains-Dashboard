"""SQLite regression tests for the institution resolver and overlap scanner."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import app.ai.overlaps as overlap_module
from app.ai.overlaps import dismiss_flag, scan_overlaps, score_pair
from app.ai.resolver import resolve_institution
from app.db import Base
from app.models import (
    Bureau,
    Case,
    CaseAction,
    Category,
    Institution,
    OverlapFlag,
    Region,
    User,
)
from app.models.enums import CaseStatus, OverlapState, Priority, Role, SourceChannel


@pytest.fixture
def overlap_db(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(overlap_module, "_threshold", lambda: 0.45)
    with Session(engine) as db:
        region = Region(name="Synthetic Test Region")
        bureau_rb = Bureau(code="RB", name="Synthetic RB")
        bureau_pgrc = Bureau(code="PGRC", name="Synthetic PGRC")
        category = Category(name="Synthetic Faculty Category")
        other_category = Category(name="Synthetic Finance Category")
        db.add_all([region, bureau_rb, bureau_pgrc, category, other_category])
        db.flush()
        institution = Institution(
            aicte_permanent_id=f"SYN-{uuid.uuid4().hex[:12]}",
            name="Synthetic Engineering College",
            region_id=region.id,
            source="SYNTHETIC",
        )
        actor = User(
            name="Synthetic Admin",
            email=f"{uuid.uuid4().hex}@example.invalid",
            password_hash="not-a-login",
            role=Role.ADMIN.value,
            active=True,
        )
        db.add_all([institution, actor])
        db.flush()
        yield {
            "db": db,
            "region": region,
            "bureau_rb": bureau_rb,
            "bureau_pgrc": bureau_pgrc,
            "category": category,
            "other_category": other_category,
            "institution": institution,
            "actor": actor,
        }
    engine.dispose()


def _case(db, institution, bureau, category, case_no, summary, received_on=date(2026, 1, 1)):
    case = Case(
        case_no=case_no,
        institution_id=institution.id,
        bureau_id=bureau.id,
        category_id=category.id,
        status=CaseStatus.PENDING.value,
        received_on=received_on,
        last_action_on=datetime(2026, 1, 1, tzinfo=timezone.utc),
        priority=Priority.MEDIUM.value,
        summary=summary,
        complainant_ref=None,
        source_channel=SourceChannel.DIRECT.value,
        hard_deadline_type="NONE",
        source="SYNTHETIC",
    )
    db.add(case)
    db.flush()
    return case


def _planted_pair(ctx):
    db = ctx["db"]
    institution = ctx["institution"]
    category = ctx["category"]
    case_a = _case(
        db,
        institution,
        ctx["bureau_rb"],
        category,
        "RB-PLANTED-001",
        "The institute has not provided the required faculty details despite repeated requests for clarification.",
    )
    case_b = _case(
        db,
        institution,
        ctx["bureau_pgrc"],
        category,
        "PGRC-PLANTED-001",
        "Despite repeated requests for clarification, the college failed to provide its required faculty information.",
        date(2026, 1, 12),
    )
    return case_a, case_b


def test_planted_cross_bureau_pair_is_flagged(overlap_db):
    db = overlap_db["db"]
    case_a, case_b = _planted_pair(overlap_db)
    score, reasons = score_pair(case_a, case_b)
    result = scan_overlaps(db, overlap_db["institution"].id)
    db.commit()

    pair_flag = db.scalar(
        select(OverlapFlag).where(
            OverlapFlag.tier == "B",
            OverlapFlag.case_a.in_([case_a.id, case_b.id]),
            OverlapFlag.case_b.in_([case_a.id, case_b.id]),
        )
    )
    assert score >= 0.45
    assert "DIFFERENT_BUREAU" in reasons
    assert result["tier_b_created"] == 1
    assert pair_flag is not None


def test_hard_negative_is_not_flagged_as_tier_b(overlap_db):
    db = overlap_db["db"]
    institution = overlap_db["institution"]
    case_a = _case(
        db,
        institution,
        overlap_db["bureau_rb"],
        overlap_db["category"],
        "RB-NEGATIVE-001",
        "A request regarding faculty appointment records and submitted qualification certificates.",
        date(2025, 8, 1),
    )
    case_b = _case(
        db,
        institution,
        overlap_db["bureau_pgrc"],
        overlap_db["other_category"],
        "PGRC-NEGATIVE-001",
        "The complainant asks about delayed reimbursement of laboratory equipment invoices.",
        date(2026, 1, 1),
    )
    score, _ = score_pair(case_a, case_b)
    scan_overlaps(db, institution.id)
    db.commit()

    pair_flag = db.scalar(
        select(OverlapFlag).where(
            OverlapFlag.tier == "B",
            OverlapFlag.case_a.in_([case_a.id, case_b.id]),
            OverlapFlag.case_b.in_([case_a.id, case_b.id]),
        )
    )
    assert score < 0.45
    assert pair_flag is None


def test_tier_a_fires_for_rb_and_pgrc_open_cases(overlap_db):
    db = overlap_db["db"]
    _planted_pair(overlap_db)
    scan_overlaps(db, overlap_db["institution"].id)
    db.commit()

    tier_a = db.scalar(
        select(OverlapFlag).where(
            OverlapFlag.institution_id == overlap_db["institution"].id,
            OverlapFlag.tier == "A",
        )
    )
    assert tier_a is not None
    assert tier_a.state == OverlapState.OPEN.value


def test_dismissed_pair_stays_dismissed_until_source_changes(overlap_db):
    db = overlap_db["db"]
    case_a, case_b = _planted_pair(overlap_db)
    scan_overlaps(db, overlap_db["institution"].id)
    db.flush()
    flag = db.scalar(
        select(OverlapFlag).where(
            OverlapFlag.tier == "B",
            OverlapFlag.case_a.in_([case_a.id, case_b.id]),
            OverlapFlag.case_b.in_([case_a.id, case_b.id]),
        )
    )
    dismiss_flag(db, flag, overlap_db["actor"])
    db.commit()

    scan_overlaps(db, overlap_db["institution"].id)
    db.commit()
    db.refresh(flag)
    assert flag.state == OverlapState.DISMISSED.value


def test_scan_is_idempotent(overlap_db):
    db = overlap_db["db"]
    _planted_pair(overlap_db)
    first = scan_overlaps(db, overlap_db["institution"].id)
    db.commit()
    second = scan_overlaps(db, overlap_db["institution"].id)
    db.commit()

    assert first["tier_a_created"] == 1
    assert first["tier_b_created"] == 1
    assert second["tier_a_created"] == 0
    assert second["tier_b_created"] == 0
    assert db.scalar(select(CaseAction.id).limit(1)) is None
    assert len(db.scalars(select(OverlapFlag)).all()) == 2


def test_resolver_prefers_exact_id_and_normalizes_abbreviations(overlap_db):
    db = overlap_db["db"]
    institution = overlap_db["institution"]
    exact = resolve_institution(
        db,
        aicte_id=institution.aicte_permanent_id,
        name="Completely unrelated name",
    )
    fuzzy = resolve_institution(db, name="Synthetic Engg Tech Coll")

    assert exact["status"] == "AUTO_MATCH"
    assert exact["institution_id"] == institution.id
    assert fuzzy["status"] == "AUTO_MATCH"
    assert fuzzy["institution_id"] == institution.id



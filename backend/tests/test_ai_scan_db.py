"""scan_overlaps / resolve_institution / seed against the real SQLAlchemy models (SQLite in memory)."""
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.institution_resolver import resolve_institution
from app.ai.overlap import scan_overlaps
from app.models import Bureau, Case, CaseAction, Category, Institution, OverlapFlag, Region
from app.models.base import Base
from app.models.enums import OverlapStateEnum, OverlapTierEnum

T1 = "Students report that the institution has not returned their fees."
T2 = "A complaint alleges an unresolved delay in refunding student fees."


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def world(db):
    region = Region(name="Southern"); rb = Bureau(code="RB", name="RB"); pg = Bureau(code="PGRC", name="PGRC")
    cat = Category(name="fee refund"); db.add_all([region, rb, pg, cat]); db.flush()
    inst = Institution(aicte_permanent_id="A-1", name="Demo College of Engineering 1", region_id=region.id); db.add(inst); db.flush()
    def mk(no, bureau, text, received=date(2026, 1, 1), status="PENDING", inst_id=None):
        c = Case(case_no=no, institution_id=inst_id or inst.id, bureau_id=bureau.id, category_id=cat.id, status=status,
                 received_on=received, summary=text, last_action_on=datetime.combine(received, datetime.min.time(), tzinfo=timezone.utc))
        db.add(c); db.flush(); return c
    return {"inst": inst, "rb": rb, "pg": pg, "cat": cat, "mk": mk}


def test_scan_creates_tier_a_and_b_and_is_idempotent(db, world):
    a = world["mk"]("C1", world["rb"], T1); b = world["mk"]("C2", world["pg"], T2, received=date(2026, 1, 10))
    assert scan_overlaps(db) == 2
    flags = db.query(OverlapFlag).all()
    assert {f.tier for f in flags} == {OverlapTierEnum.A, OverlapTierEnum.B}
    pair = next(f for f in flags if f.tier == OverlapTierEnum.B)
    assert (pair.case_a, pair.case_b) == (a.id, b.id) and "DIFFERENT_BUREAU" in pair.reasons
    assert scan_overlaps(db) == 0
    assert db.query(OverlapFlag).count() == 2


def test_no_flags_for_same_bureau_or_closed_cases(db, world):
    world["mk"]("C1", world["rb"], T1); world["mk"]("C2", world["rb"], T2)
    world["mk"]("C3", world["pg"], T2, status="DISPOSED")
    assert scan_overlaps(db) == 0


def test_dismissed_pair_stays_dismissed_unless_case_changed_after_decision(db, world):
    a = world["mk"]("C1", world["rb"], T1); b = world["mk"]("C2", world["pg"], T2, received=date(2026, 1, 10))
    scan_overlaps(db)
    flag = db.query(OverlapFlag).filter(OverlapFlag.case_a.isnot(None)).one()
    flag.state = OverlapStateEnum.DISMISSED
    flag.decided_at = datetime(2026, 2, 1, tzinfo=timezone.utc); db.commit()
    assert scan_overlaps(db) == 0                      # nothing changed since decision (used to raise TypeError)
    db.refresh(flag); assert flag.state == OverlapStateEnum.DISMISSED
    b.last_action_on = datetime(2026, 3, 1, tzinfo=timezone.utc); db.commit()
    assert scan_overlaps(db) == 1                      # acted on after decided_at -> re-raised
    db.refresh(flag); assert flag.state == OverlapStateEnum.OPEN and flag.decided_at is None


def test_scan_can_be_limited_to_one_institution(db, world):
    other = Institution(aicte_permanent_id="A-2", name="Other Institute", region_id=world["inst"].region_id); db.add(other); db.flush()
    world["mk"]("C1", world["rb"], T1); world["mk"]("C2", world["pg"], T2)
    world["mk"]("C3", world["rb"], T1, inst_id=other.id); world["mk"]("C4", world["pg"], T2, inst_id=other.id)
    assert scan_overlaps(db, institution_id=other.id) == 2
    assert {f.institution_id for f in db.query(OverlapFlag)} == {other.id}


def test_resolver_against_database(db, world):
    r = resolve_institution(db, None, "A-1")
    assert r.method == "EXACT_ID" and r.institution_id == world["inst"].id
    r = resolve_institution(db, "demo coll. of engg 1")
    assert r.method == "FUZZY" and r.institution_id == world["inst"].id and not r.needs_review


def test_seed_is_idempotent_maps_regions_and_does_not_prelink(db, tmp_path, monkeypatch):
    from app.ai import seed as ai_seed
    pd.DataFrame([{"institution_id": "S1", "institution_name": "Demo A 1", "state": "Karnataka", "aicte_id": "SYN-AICTE-1"}]).to_csv(tmp_path / "institutions.csv", index=False)
    rows = [{"case_id": f"SYN-CASE-{i}", "case_no": f"SYN-CASE-{i}", "institution_id": "S1", "bureau": b, "category": "fee refund", "status": "PENDING",
             "summary": t, "complainant_ref": "", "created_at": "2026-01-01T10:00:00", "group_id": "OVERLAP-1"} for i, (b, t) in enumerate([("RB", T1), ("PGRC", T2)], 1)]
    pd.DataFrame(rows).to_csv(tmp_path / "complaints.csv", index=False)
    monkeypatch.setenv("AI_DATA_DIR", str(tmp_path))
    first = ai_seed.seed_database(db)
    assert first["cases_created"] == 2 and first["overlap_flags_created"] >= 1
    assert ai_seed.seed_database(db)["cases_created"] == 0
    inst = db.query(Institution).one()
    assert db.get(Region, inst.region_id).name == "South-Western"
    assert all(c.link_group_id is None for c in db.query(Case))
    assert db.query(CaseAction).count() == 2
    ai_seed.seed_database(db, reset=True)
    assert db.query(Case).count() == 2


def test_explain_flag_reads_flag_and_does_not_modify_it(db, world):
    """explain_flag is read-only and works without an LLM (template path)."""
    from app.ai.explain import explain_flag
    w = world
    a = w["mk"]("C1", w["rb"], T1); b = w["mk"]("C2", w["pg"], T2, received=date(2026, 1, 10))
    scan_overlaps(db)
    flag = db.query(OverlapFlag).filter(OverlapFlag.case_a.isnot(None)).first()
    assert flag is not None
    before = (flag.score, list(flag.reasons), flag.state)
    result = explain_flag(db, flag.id)
    assert result["method"] == "TEMPLATE" and result["advisory"] is True and set(result["sources"]) >= {a.id, b.id}
    db.refresh(flag)
    assert (flag.score, list(flag.reasons), flag.state) == before

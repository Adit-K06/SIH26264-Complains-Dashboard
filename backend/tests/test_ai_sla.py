"""Placeholder SLA boundary, daily dedupe, and escalation audit tests."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Alert, Bureau, Case, CaseAction, Category, Institution, Region, SlaRule
from app.models.enums import ActionType, AlertType, CaseStatus, Priority, SourceChannel
from app.sla import run_sla_check


@pytest.fixture
def sla_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        region = Region(name="Synthetic SLA Region")
        bureau = Bureau(code="RB", name="Synthetic SLA Bureau")
        category = Category(name="Synthetic SLA Category")
        db.add_all([region, bureau, category])
        db.flush()
        institution = Institution(
            aicte_permanent_id=f"SYN-SLA-{uuid.uuid4().hex[:8]}",
            name="Synthetic SLA Institution",
            region_id=region.id,
            source="SYNTHETIC",
        )
        db.add(institution)
        db.flush()
        yield db, bureau, category, institution
    engine.dispose()


def _case(db, bureau, category, institution, case_no, received_on, due_on):
    case = Case(
        case_no=case_no,
        institution_id=institution.id,
        bureau_id=bureau.id,
        category_id=category.id,
        status=CaseStatus.PENDING.value,
        received_on=received_on,
        last_action_on=datetime.now(timezone.utc),
        last_action_text="Synthetic action today",
        expected_disposal_on=due_on,
        priority=Priority.MEDIUM.value,
        summary="Synthetic SLA test case.",
        complainant_ref=None,
        source_channel=SourceChannel.DIRECT.value,
        hard_deadline_type="NONE",
        source="SYNTHETIC",
    )
    db.add(case)
    db.flush()
    return case


@freeze_time("2026-06-01")
def test_due_soon_alert_starts_at_the_75_percent_boundary(sla_db):
    db, bureau, category, institution = sla_db
    today = date.today()
    db.add(
        SlaRule(
            category_id=None,
            priority=Priority.MEDIUM.value,
            days_to_dispose=100,
            warn_at_pct=0.75,
            reminder_after_days=7,
            escalate_after_days=10,
        )
    )
    db.flush()
    received_74 = today - timedelta(days=74)
    received_75 = today - timedelta(days=75)
    case_74 = _case(db, bureau, category, institution, "SLA-74", received_74, received_74 + timedelta(days=100))
    case_75 = _case(db, bureau, category, institution, "SLA-75", received_75, received_75 + timedelta(days=100))

    result = run_sla_check(db, today)
    db.commit()

    due_soon_case_ids = set(
        db.scalars(select(Alert.case_id).where(Alert.type == AlertType.DUE_SOON.value)).all()
    )
    assert result["due_soon"] == 1
    assert case_74.id not in due_soon_case_ids
    assert case_75.id in due_soon_case_ids


@freeze_time("2026-06-01")
def test_escalation_alert_dedupes_and_appends_escalated_audit_row(sla_db):
    db, bureau, category, institution = sla_db
    today = date.today()
    received_on = today - timedelta(days=41)
    case = _case(
        db,
        bureau,
        category,
        institution,
        "SLA-ESCALATE",
        received_on,
        received_on + timedelta(days=30),
    )

    first = run_sla_check(db, today)
    db.commit()
    second = run_sla_check(db, today)
    db.commit()
    db.refresh(case)

    escalation_alerts = db.scalars(
        select(Alert).where(
            Alert.case_id == case.id,
            Alert.type == AlertType.ESCALATION.value,
        )
    ).all()
    audit = db.scalars(
        select(CaseAction).where(
            CaseAction.case_id == case.id,
            CaseAction.action_type == ActionType.ESCALATED.value,
            CaseAction.to_status == CaseStatus.ESCALATED.value,
        )
    ).all()

    assert first["escalations"] == 1
    assert second["escalations"] == 0
    assert len(escalation_alerts) == 1
    assert case.status == CaseStatus.ESCALATED.value
    assert len(audit) == 1

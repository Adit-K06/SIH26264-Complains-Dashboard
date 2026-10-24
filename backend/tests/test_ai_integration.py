from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.ai import resolve_institution, scan_overlaps
from app.models import (
    Base, Bureau, Case, CaseStatusEnum, Category, Institution,
    OverlapFlag, PriorityEnum,
)


def test_ai_integrates_with_backend_models_and_persists_tier_b():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        institution = Institution(aicte_permanent_id="AICTE-TEST-1", name="ABC Engineering College")
        bureau_a = Bureau(code="BUREAU-A", name="Bureau A")
        bureau_b = Bureau(code="BUREAU-B", name="Bureau B")
        category = Category(name="Admissions")
        db.add_all([institution, bureau_a, bureau_b, category])
        db.flush()
        db.add_all([
            Case(case_no="A-1", institution_id=institution.id, bureau_id=bureau_a.id,
                 category_id=category.id, status=CaseStatusEnum.PENDING,
                 received_on=date(2026, 1, 1), summary="Admission fee refund not processed",
                 priority=PriorityEnum.MEDIUM, complainant_ref="REF-123"),
            Case(case_no="B-1", institution_id=institution.id, bureau_id=bureau_b.id,
                 category_id=category.id, status=CaseStatusEnum.PENDING,
                 received_on=date(2026, 1, 4), summary="Admission fee refund not processed",
                 priority=PriorityEnum.MEDIUM, complainant_ref="REF-123"),
        ])
        db.commit()

        resolved = resolve_institution(db, name="ABC Engg College")
        assert resolved.institution_id == institution.id
        assert resolved.needs_review is False

        new_count = scan_overlaps(db)
        flags = db.query(OverlapFlag).all()
        assert new_count == 2
        assert any(flag.tier == "B" or getattr(flag.tier, "value", None) == "B" for flag in flags)
        assert any(flag.tier == "A" or getattr(flag.tier, "value", None) == "A" for flag in flags)

        # A repeated scan must not create duplicate flags.
        assert scan_overlaps(db) == 0

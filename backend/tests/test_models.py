"""Focused tests for SQLAlchemy models, metadata, constraints, and audit trail."""
import datetime
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateIndex

from app.database import get_db
from app.models import (
    ActionTypeEnum,
    Alert,
    AlertTypeEnum,
    ApiKey,
    Attachment,
    Base,
    Bureau,
    Case,
    CaseAction,
    CaseLink,
    CaseStatusEnum,
    Category,
    Institution,
    OverlapFlag,
    OverlapStateEnum,
    OverlapTierEnum,
    PriorityEnum,
    Region,
    RoleEnum,
    SlaRule,
    User,
)


@pytest.fixture
def db_session():
    """In-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_all_13_tables_registered_in_metadata():
    """Verify all 13 required tables are present in Base.metadata with exact names."""
    expected_tables = {
        "institutions",
        "regions",
        "bureaus",
        "categories",
        "users",
        "cases",
        "case_actions",
        "case_links",
        "overlap_flags",
        "alerts",
        "sla_rules",
        "attachments",
        "api_keys",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), (
        f"Missing tables: {expected_tables - actual_tables}"
    )
    assert len(expected_tables) == 13


def test_table_columns_exact_spec():
    """Verify key columns on all models match AGENTS.md."""
    inst_cols = {c.name for c in Base.metadata.tables["institutions"].columns}
    assert {
        "id",
        "aicte_permanent_id",
        "name",
        "address",
        "district",
        "state",
        "region_id",
        "type",
        "status",
    }.issubset(inst_cols)

    case_cols = {c.name for c in Base.metadata.tables["cases"].columns}
    assert {
        "id",
        "case_no",
        "institution_id",
        "bureau_id",
        "category_id",
        "status",
        "assigned_officer_id",
        "received_on",
        "last_action_on",
        "last_action_text",
        "next_action_text",
        "expected_disposal_on",
        "priority",
        "summary",
        "complainant_ref",
        "source",
        "link_group_id",
        "needs_institution_review",
        "text_vector",
    }.issubset(case_cols)

    action_cols = {c.name for c in Base.metadata.tables["case_actions"].columns}
    assert {
        "id",
        "case_id",
        "actor_id",
        "bureau_id",
        "action_type",
        "from_status",
        "to_status",
        "remarks",
        "attachment_id",
        "created_at",
    }.issubset(action_cols)

    overlap_cols = {c.name for c in Base.metadata.tables["overlap_flags"].columns}
    assert {
        "id",
        "institution_id",
        "case_a",
        "case_b",
        "tier",
        "score",
        "reasons",
        "state",
        "decided_by",
        "decided_at",
    }.issubset(overlap_cols)


def test_case_actions_append_only_orm_guard(db_session):
    """Verify that case_actions cannot be updated or deleted via ORM."""
    reg = Region(name="Northern")
    bur = Bureau(code="RB", name="Regulation Bureau")
    db_session.add_all([reg, bur])
    db_session.commit()

    usr = User(
        name="Officer A",
        email="officer.a@example.com",
        password_hash="hash123",
        role=RoleEnum.BUREAU_OFFICER,
        bureau_id=bur.id,
    )
    db_session.add(usr)
    db_session.commit()

    case = Case(
        case_no="RB-2026-0001",
        bureau_id=bur.id,
        status=CaseStatusEnum.PENDING,
        received_on=datetime.date(2026, 1, 15),
        priority=PriorityEnum.HIGH,
        summary="Test complaint summary",
        source="SYNTHETIC",
    )
    db_session.add(case)
    db_session.commit()

    action = CaseAction(
        case_id=case.id,
        actor_id=usr.id,
        bureau_id=bur.id,
        action_type=ActionTypeEnum.CREATED,
        to_status=CaseStatusEnum.PENDING,
        remarks="Case created initial action",
    )
    db_session.add(action)
    db_session.commit()
    action_id = action.id
    assert action_id is not None

    # Attempting to update must raise ValueError
    action.remarks = "Attempted unauthorized edit"
    with pytest.raises(ValueError, match="case_actions is append-only"):
        db_session.commit()
    db_session.rollback()

    # Attempting to delete must raise ValueError
    action = db_session.get(CaseAction, action_id)
    db_session.delete(action)
    with pytest.raises(ValueError, match="case_actions is append-only"):
        db_session.commit()
    db_session.rollback()


def test_tier_a_overlap_partial_unique_constraint(db_session):
    """Verify Tier A overlap partial unique index blocks duplicate Tier A for the same institution."""
    inst = Institution(
        aicte_permanent_id="1-00000001",
        name="Apex Engineering College",
        status="ACTIVE",
    )
    db_session.add(inst)
    db_session.commit()

    flag1 = OverlapFlag(
        institution_id=inst.id,
        case_a=None,
        case_b=None,
        tier=OverlapTierEnum.A,
        score=1.0,
        reasons=["DIFFERENT_BUREAU"],
        state=OverlapStateEnum.OPEN,
    )
    db_session.add(flag1)
    db_session.commit()

    # Second Tier A flag for the SAME institution (case_a=None, case_b=None) must fail
    flag2 = OverlapFlag(
        institution_id=inst.id,
        case_a=None,
        case_b=None,
        tier=OverlapTierEnum.A,
        score=0.9,
        reasons=["DIFFERENT_BUREAU"],
        state=OverlapStateEnum.OPEN,
    )
    db_session.add(flag2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_tier_b_overlap_partial_unique_pair(db_session):
    """Verify Tier B overlap unique index blocks duplicate (case_a, case_b) pair."""
    bur = Bureau(code="RB", name="Regulation Bureau")
    db_session.add(bur)
    db_session.commit()

    inst = Institution(
        aicte_permanent_id="1-00000002",
        name="Global Institute of Tech",
    )
    db_session.add(inst)
    db_session.commit()

    c1 = Case(
        case_no="RB-2026-0002",
        bureau_id=bur.id,
        institution_id=inst.id,
        status=CaseStatusEnum.PENDING,
        received_on=datetime.date(2026, 1, 10),
        priority=PriorityEnum.MEDIUM,
        summary="Case 1",
    )
    c2 = Case(
        case_no="RB-2026-0003",
        bureau_id=bur.id,
        institution_id=inst.id,
        status=CaseStatusEnum.PENDING,
        received_on=datetime.date(2026, 1, 12),
        priority=PriorityEnum.MEDIUM,
        summary="Case 2",
    )
    db_session.add_all([c1, c2])
    db_session.commit()

    flag1 = OverlapFlag(
        institution_id=inst.id,
        case_a=c1.id,
        case_b=c2.id,
        tier=OverlapTierEnum.B,
        score=0.85,
        reasons=["HIGH_TEXT_SIMILARITY"],
        state=OverlapStateEnum.OPEN,
    )
    db_session.add(flag1)
    db_session.commit()

    # Duplicate (c1.id, c2.id) must fail
    flag2 = OverlapFlag(
        institution_id=inst.id,
        case_a=c1.id,
        case_b=c2.id,
        tier=OverlapTierEnum.B,
        score=0.85,
        reasons=["HIGH_TEXT_SIMILARITY"],
        state=OverlapStateEnum.OPEN,
    )
    db_session.add(flag2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_case_unique_per_bureau(db_session):
    """Verify case_no is unique per bureau."""
    bur1 = Bureau(code="RB", name="Regulation")
    bur2 = Bureau(code="APPROVAL", name="Approval")
    db_session.add_all([bur1, bur2])
    db_session.commit()

    c1 = Case(
        case_no="CASE-100",
        bureau_id=bur1.id,
        received_on=datetime.date(2026, 1, 1),
        priority=PriorityEnum.LOW,
        summary="Summary 1",
    )
    db_session.add(c1)
    db_session.commit()

    # Same case_no in a different bureau is ALLOWED
    c2 = Case(
        case_no="CASE-100",
        bureau_id=bur2.id,
        received_on=datetime.date(2026, 1, 1),
        priority=PriorityEnum.LOW,
        summary="Summary 2",
    )
    db_session.add(c2)
    db_session.commit()

    # Same case_no in the SAME bureau must FAIL
    c3 = Case(
        case_no="CASE-100",
        bureau_id=bur1.id,
        received_on=datetime.date(2026, 1, 2),
        priority=PriorityEnum.LOW,
        summary="Duplicate",
    )
    db_session.add(c3)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_sla_rules_unique_category_priority(db_session):
    """Verify unique constraint on (category_id, priority) in sla_rules."""
    cat = Category(name="Infrastructure")
    db_session.add(cat)
    db_session.commit()

    r1 = SlaRule(
        category_id=cat.id,
        priority=PriorityEnum.HIGH,
        days_to_dispose=15,
        warn_at_pct=80,
        reminder_after_days=7,
        escalate_after_days=14,
    )
    db_session.add(r1)
    db_session.commit()

    r2 = SlaRule(
        category_id=cat.id,
        priority=PriorityEnum.HIGH,
        days_to_dispose=20,
        warn_at_pct=80,
        reminder_after_days=10,
        escalate_after_days=18,
    )
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_pg_trgm_gin_index_compilation():
    """Verify that institutions GIN trigram index compiles to valid PostgreSQL DDL with gin_trgm_ops."""
    inst_table = Base.metadata.tables["institutions"]
    trgm_index = None
    for idx in inst_table.indexes:
        if idx.name == "ix_institutions_name_trgm":
            trgm_index = idx
            break

    assert trgm_index is not None, "Trigram index ix_institutions_name_trgm not found"
    compiled_ddl = str(CreateIndex(trgm_index).compile(dialect=postgresql.dialect()))
    assert "USING gin" in compiled_ddl
    assert "gin_trgm_ops" in compiled_ddl


def test_jsonb_variant_compilation():
    """Verify text_vector and reasons compile to JSONB on PostgreSQL dialect."""
    case_table = Base.metadata.tables["cases"]
    text_vector_col = case_table.columns["text_vector"]
    compiled_type = text_vector_col.type.compile(dialect=postgresql.dialect())
    assert compiled_type == "JSONB"

    overlap_table = Base.metadata.tables["overlap_flags"]
    reasons_col = overlap_table.columns["reasons"]
    compiled_reasons = reasons_col.type.compile(dialect=postgresql.dialect())
    assert compiled_reasons == "JSONB"


def test_relationships_and_foreign_keys_across_all_models(db_session):
    """Verify full ORM relationship graph across all 13 models."""
    # 1. Region
    reg = Region(name="Western")
    db_session.add(reg)
    db_session.commit()

    # 2. Bureau
    bur = Bureau(code="PGRC", name="Public Grievance Redressal Cell")
    db_session.add(bur)
    db_session.commit()

    # 3. Category
    cat = Category(name="Faculty Issues")
    db_session.add(cat)
    db_session.commit()

    # 4. Institution
    inst = Institution(
        aicte_permanent_id="1-99990001",
        name="Western Institute of Technology",
        address="Sector 4",
        district="Pune",
        state="Maharashtra",
        region_id=reg.id,
        type="GOVERNMENT",
        status="ACTIVE",
    )
    db_session.add(inst)
    db_session.commit()

    # 5. User
    usr = User(
        name="Officer Rajesh",
        email="rajesh@aicte.gov.in",
        password_hash="hashedpass",
        role=RoleEnum.BUREAU_OFFICER,
        bureau_id=bur.id,
        region_id=reg.id,
        active=True,
    )
    db_session.add(usr)
    db_session.commit()

    # 6. ApiKey
    key = ApiKey(
        bureau_id=bur.id,
        key_hash="sha256_mock_hash",
        active=True,
    )
    db_session.add(key)
    db_session.commit()

    # 7. SlaRule
    sla = SlaRule(
        category_id=cat.id,
        priority=PriorityEnum.HIGH,
        days_to_dispose=30,
        warn_at_pct=75,
        reminder_after_days=10,
        escalate_after_days=25,
    )
    db_session.add(sla)
    db_session.commit()

    # 8. Case
    case = Case(
        case_no="PGRC-2026-001",
        institution_id=inst.id,
        bureau_id=bur.id,
        category_id=cat.id,
        status=CaseStatusEnum.PENDING,
        assigned_officer_id=usr.id,
        received_on=datetime.date(2026, 1, 10),
        priority=PriorityEnum.HIGH,
        summary="Delay in grievance response",
        source="SYNTHETIC",
        link_group_id="grp-123",
        needs_institution_review=False,
        text_vector={"token_weights": [0.1, 0.4]},
    )
    db_session.add(case)
    db_session.commit()

    # 9. Attachment
    att = Attachment(
        case_id=case.id,
        filename="complaint.pdf",
        mime="application/pdf",
        size=10240,
        sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        stored_path="/data/uploads/complaint.pdf",
        uploaded_by=usr.id,
    )
    db_session.add(att)
    db_session.commit()

    # 10. CaseAction
    act = CaseAction(
        case_id=case.id,
        actor_id=usr.id,
        bureau_id=bur.id,
        action_type=ActionTypeEnum.CREATED,
        to_status=CaseStatusEnum.PENDING,
        remarks="Created case from portal",
        attachment_id=att.id,
    )
    db_session.add(act)
    db_session.commit()

    # 11. CaseLink
    link = CaseLink(
        group_id="grp-123",
        case_id=case.id,
        linked_by=usr.id,
        lead_bureau_id=bur.id,
        note="Coordinated review needed",
    )
    db_session.add(link)
    db_session.commit()

    # 12. Alert
    alr = Alert(
        type=AlertTypeEnum.REMINDER,
        case_id=case.id,
        institution_id=inst.id,
        target_role=RoleEnum.BUREAU_OFFICER,
        target_bureau_id=bur.id,
        message="Case action reminder",
        due_on=datetime.date(2026, 1, 20),
    )
    db_session.add(alr)
    db_session.commit()

    # 13. OverlapFlag (OPEN overlap flag has no decision yet)
    flag = OverlapFlag(
        institution_id=inst.id,
        case_a=None,
        case_b=None,
        tier=OverlapTierEnum.A,
        score=0.95,
        reasons=["DIFFERENT_BUREAU"],
        state=OverlapStateEnum.OPEN,
        decided_by=None,
        decided_at=None,
    )
    db_session.add(flag)
    db_session.commit()

    # Verify bidirectional relationships
    assert case.institution.name == "Western Institute of Technology"
    assert case.bureau.code == "PGRC"
    assert case.category.name == "Faculty Issues"
    assert case.assigned_officer.email == "rajesh@aicte.gov.in"
    assert len(case.actions) == 1
    assert case.actions[0].remarks == "Created case from portal"
    assert len(case.attachments) == 1
    assert case.attachments[0].filename == "complaint.pdf"
    assert len(case.links) == 1
    assert len(case.alerts) == 1
    assert len(inst.overlap_flags) == 1
    assert bur.api_keys[0].key_hash == "sha256_mock_hash"
    assert cat.sla_rules[0].days_to_dispose == 30
    assert usr.region.name == "Western"


def test_get_db_session_lifecycle(monkeypatch):
    """Verify get_db dependency yields a valid session and closes it."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    test_sessionmaker = sessionmaker(bind=engine)
    monkeypatch.setattr("app.database.SessionLocal", test_sessionmaker)

    gen = get_db()
    session = next(gen)
    assert session is not None
    assert session.is_active
    with pytest.raises(StopIteration):
        next(gen)


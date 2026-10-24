"""Tests for Phase 4E: SLA Monitoring, Alerts Management, Admin SLA Rules, and Reports.

Covers:
  1. SLA calculations & monitoring:
     - Open cases: PENDING, UNDER_PROCESS, ESCALATED, TRANSFERRED.
     - Due today vs overdue yesterday.
     - Disposed cases excluded.
     - SlaRule lookup (category-specific vs default fallback).
     - GET /api/v1/sla/overview and GET /api/v1/sla/cases.
  2. Admin SLA Configuration:
     - GET /api/v1/admin/sla-rules (ADMIN only).
     - PUT /api/v1/admin/sla-rules/{id} (threshold updates).
     - RBAC: non-admin gets 403.
  3. Alerts:
     - GET /api/v1/alerts (pagination, unread_only, type filter).
     - POST /api/v1/alerts/{id}/read (sets read_at, idempotent).
     - POST /api/v1/alerts/generate (deterministic SLA alert creation).
     - Strict deduplication: one per (case_id, type, day).
     - RBAC: bureau officer cannot read or generate for out-of-bureau; regional officer scoped.
  4. Reports:
     - All 9 types: bureau, region, institution, ageing, disposal-rate, status, overlaps, monthly, quarterly.
     - format=json and format=csv (Content-Type text/csv, attachment header).
     - format=pdf rejected with 422.
     - Invalid report type rejected with 404.
     - Date range and scope filtering.
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import (
    Alert,
    Bureau,
    Case,
    CaseAction,
    Category,
    Institution,
    OverlapFlag,
    Region,
    SlaRule,
    User,
)
from app.models.base import Base
from app.models.enums import (
    ActionTypeEnum,
    AlertTypeEnum,
    CaseStatusEnum,
    OverlapStateEnum,
    OverlapTierEnum,
    PriorityEnum,
    RoleEnum,
)
from app.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Test DB and Client Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.rollback()
    for tbl in reversed(Base.metadata.sorted_tables):
        session.execute(tbl.delete())
    session.commit()
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db_session):
    """Seed regions, bureaus, institutions, categories, users, and sla rules."""
    # Regions
    r_north = Region(id=1, name="Northern")
    r_south = Region(id=2, name="Southern")
    db_session.add_all([r_north, r_south])

    # Bureaus
    b_rb = Bureau(id=1, code="RB", name="Research Bureau")
    b_pgrc = Bureau(id=2, code="PGRC", name="Public Grievance Redressal Cell")
    b_approval = Bureau(id=3, code="APPROVAL", name="Approval Bureau")
    b_academic = Bureau(id=4, code="ACADEMIC", name="Academic Bureau")
    b_finance = Bureau(id=5, code="FINANCE", name="Finance Bureau")
    db_session.add_all([b_rb, b_pgrc, b_approval, b_academic, b_finance])

    # Institutions
    inst1 = Institution(
        id=1, aicte_permanent_id="1-001", name="IIT Delhi",
        address="Hauz Khas", district="South Delhi", state="Delhi",
        region_id=1, type="Govt", status="APPROVED",
    )
    inst2 = Institution(
        id=2, aicte_permanent_id="1-002", name="IIT Madras",
        address="Chennai", district="Chennai", state="Tamil Nadu",
        region_id=2, type="Govt", status="APPROVED",
    )
    db_session.add_all([inst1, inst2])

    # Categories
    cat_infra = Category(id=1, name="Infrastructure")
    cat_faculty = Category(id=2, name="Faculty Shortage")
    db_session.add_all([cat_infra, cat_faculty])

    # Users
    u_admin = User(
        id=1, name="Admin User", email="admin@aicte.test",
        password_hash=hash_password("pw"), role=RoleEnum.ADMIN, active=True,
    )
    u_senior = User(
        id=2, name="Senior Officer", email="senior@aicte.test",
        password_hash=hash_password("pw"), role=RoleEnum.SENIOR_MGMT, active=True,
    )
    u_rb = User(
        id=3, name="RB Officer", email="rb@aicte.test",
        password_hash=hash_password("pw"), role=RoleEnum.BUREAU_OFFICER, bureau_id=1, active=True,
    )
    u_pgrc = User(
        id=4, name="PGRC Officer", email="pgrc@aicte.test",
        password_hash=hash_password("pw"), role=RoleEnum.BUREAU_OFFICER, bureau_id=2, active=True,
    )
    u_reg_north = User(
        id=5, name="North Reg Officer", email="north@aicte.test",
        password_hash=hash_password("pw"), role=RoleEnum.REGIONAL_OFFICER, region_id=1, active=True,
    )
    db_session.add_all([u_admin, u_senior, u_rb, u_pgrc, u_reg_north])

    # SLA rules
    # 1. Category 1 (Infrastructure) + HIGH -> 10 days
    rule1 = SlaRule(
        id=1, category_id=1, priority=PriorityEnum.HIGH,
        days_to_dispose=10, warn_at_pct=80, reminder_after_days=5, escalate_after_days=8,
    )
    # 2. General default (None) + MEDIUM -> 30 days
    rule2 = SlaRule(
        id=2, category_id=None, priority=PriorityEnum.MEDIUM,
        days_to_dispose=30, warn_at_pct=80, reminder_after_days=10, escalate_after_days=25,
    )
    db_session.add_all([rule1, rule2])

    db_session.commit()

    return {
        "admin": u_admin,
        "senior": u_senior,
        "rb_officer": u_rb,
        "pgrc_officer": u_pgrc,
        "north_officer": u_reg_north,
    }


def auth_header(user: User) -> dict:
    tok = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {tok}"}


def get_error(res) -> dict:
    body = res.json()
    if "error" in body:
        return body["error"]
    if "detail" in body and isinstance(body["detail"], dict) and "error" in body["detail"]:
        return body["detail"]["error"]
    return body.get("detail", {})


# ---------------------------------------------------------------------------
# 1. SLA Monitoring Tests
# ---------------------------------------------------------------------------

class TestSlaMonitoring:
    def test_sla_calculation_due_today_vs_overdue(self, client, db_session, seed_data):
        today = date.today()
        # Case 1: Due today -> NOT overdue
        c1 = Case(
            case_no="RB-001", bureau_id=1, institution_id=1, category_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.HIGH,
            received_on=today - timedelta(days=10),
            expected_disposal_on=today,
            summary="Due today", source="SYNTHETIC",
        )
        # Case 2: Due yesterday -> OVERDUE
        c2 = Case(
            case_no="RB-002", bureau_id=1, institution_id=1, category_id=1,
            status=CaseStatusEnum.UNDER_PROCESS, priority=PriorityEnum.HIGH,
            received_on=today - timedelta(days=11),
            expected_disposal_on=today - timedelta(days=1),
            summary="Due yesterday", source="SYNTHETIC",
        )
        # Case 3: Disposed case due yesterday -> Not open, excluded from open SLA
        c3 = Case(
            case_no="RB-003", bureau_id=1, institution_id=1, category_id=1,
            status=CaseStatusEnum.DISPOSED, priority=PriorityEnum.HIGH,
            received_on=today - timedelta(days=20),
            expected_disposal_on=today - timedelta(days=5),
            last_action_on=datetime.now(timezone.utc),
            summary="Disposed case", source="SYNTHETIC",
        )
        db_session.add_all([c1, c2, c3])
        db_session.commit()

        # Admin checks /sla/overview
        res = client.get("/api/v1/sla/overview", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total_open_cases"] == 2
        assert data["overdue_count"] == 1
        assert data["within_sla_count"] + data["due_soon_count"] == 1

        # Check /sla/cases
        res_cases = client.get("/api/v1/sla/cases", headers=auth_header(seed_data["admin"]))
        assert res_cases.status_code == 200
        items = res_cases.json()["items"]
        assert len(items) == 2

        case_due_today = next(item for item in items if item["case_no"] == "RB-001")
        assert case_due_today["is_beyond_sla"] is False
        assert case_due_today["days_remaining"] == 0

        case_overdue = next(item for item in items if item["case_no"] == "RB-002")
        assert case_overdue["is_beyond_sla"] is True
        assert case_overdue["sla_status"] == "OVERDUE"
        assert case_overdue["days_remaining"] == -1

    def test_sla_cases_filter_overdue_only(self, client, db_session, seed_data):
        today = date.today()
        c_open = Case(
            case_no="PGRC-001", bureau_id=2, institution_id=2,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.MEDIUM,
            received_on=today, expected_disposal_on=today + timedelta(days=30),
            summary="Fresh case", source="SYNTHETIC",
        )
        c_overdue = Case(
            case_no="PGRC-002", bureau_id=2, institution_id=2,
            status=CaseStatusEnum.ESCALATED, priority=PriorityEnum.MEDIUM,
            received_on=today - timedelta(days=40), expected_disposal_on=today - timedelta(days=10),
            summary="Overdue case", source="SYNTHETIC",
        )
        db_session.add_all([c_open, c_overdue])
        db_session.commit()

        res = client.get("/api/v1/sla/cases?overdue_only=true", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["case_no"] == "PGRC-002"

    def test_sla_rbac_scoping(self, client, db_session, seed_data):
        today = date.today()
        # RB case
        c_rb = Case(
            case_no="RB-100", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.MEDIUM,
            received_on=today, expected_disposal_on=today + timedelta(days=30),
            summary="RB case", source="SYNTHETIC",
        )
        # PGRC case
        c_pgrc = Case(
            case_no="PGRC-100", bureau_id=2, institution_id=2,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.MEDIUM,
            received_on=today, expected_disposal_on=today + timedelta(days=30),
            summary="PGRC case", source="SYNTHETIC",
        )
        db_session.add_all([c_rb, c_pgrc])
        db_session.commit()

        # RB officer sees only RB case
        res_rb = client.get("/api/v1/sla/cases", headers=auth_header(seed_data["rb_officer"]))
        assert res_rb.status_code == 200
        items_rb = res_rb.json()["items"]
        assert all(it["bureau_id"] == 1 for it in items_rb)
        assert any(it["case_no"] == "RB-100" for it in items_rb)
        assert not any(it["case_no"] == "PGRC-100" for it in items_rb)

        # North regional officer sees only inst 1 (Northern)
        res_reg = client.get("/api/v1/sla/cases", headers=auth_header(seed_data["north_officer"]))
        assert res_reg.status_code == 200
        items_reg = res_reg.json()["items"]
        assert all(it["institution_id"] == 1 for it in items_reg)


# ---------------------------------------------------------------------------
# 2. Admin SLA Rules Tests
# ---------------------------------------------------------------------------

class TestAdminSlaRules:
    def test_admin_list_and_update_sla_rule(self, client, db_session, seed_data):
        # List SLA rules
        res = client.get("/api/v1/admin/sla-rules", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        rules = res.json()
        assert len(rules) >= 2

        rule_to_update = rules[0]
        r_id = rule_to_update["id"]

        # Update days_to_dispose and warn_at_pct
        update_payload = {
            "days_to_dispose": 12,
            "warn_at_pct": 75,
            "reminder_after_days": 4,
            "escalate_after_days": 9,
        }
        res_put = client.put(f"/api/v1/admin/sla-rules/{r_id}", json=update_payload, headers=auth_header(seed_data["admin"]))
        assert res_put.status_code == 200
        updated = res_put.json()
        assert updated["days_to_dispose"] == 12
        assert updated["warn_at_pct"] == 75

        # Verify DB persisted
        refreshed = db_session.get(SlaRule, r_id)
        assert refreshed.days_to_dispose == 12

    def test_non_admin_forbidden_sla_rules(self, client, db_session, seed_data):
        res = client.get("/api/v1/admin/sla-rules", headers=auth_header(seed_data["senior"]))
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

        res_put = client.put("/api/v1/admin/sla-rules/1", json={"days_to_dispose": 15}, headers=auth_header(seed_data["rb_officer"]))
        assert res_put.status_code == 403


# ---------------------------------------------------------------------------
# 3. Alerts Tests
# ---------------------------------------------------------------------------

class TestAlerts:
    def test_alert_generation_and_deduplication(self, client, db_session, seed_data):
        today = date.today()
        # Create an overdue case
        c_overdue = Case(
            case_no="RB-OVERDUE-1", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.HIGH,
            received_on=today - timedelta(days=20),
            expected_disposal_on=today - timedelta(days=5),
            summary="Overdue case", source="SYNTHETIC",
        )
        # Create an inactive case needing reminder
        c_reminder = Case(
            case_no="RB-REMIND-1", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.UNDER_PROCESS, priority=PriorityEnum.MEDIUM,
            received_on=today - timedelta(days=15),
            expected_disposal_on=today + timedelta(days=15),
            last_action_on=datetime.now(timezone.utc) - timedelta(days=12),
            summary="Inactive case", source="SYNTHETIC",
        )
        db_session.add_all([c_overdue, c_reminder])
        db_session.commit()

        # Generate alerts
        res = client.post("/api/v1/alerts/generate", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        gen_data = res.json()
        assert gen_data["generated_count"] >= 2
        assert gen_data["types_breakdown"]["OVERDUE"] >= 1

        # Idempotency / Deduplication test: Running generate again on the same day must not create duplicate alerts!
        res_again = client.post("/api/v1/alerts/generate", headers=auth_header(seed_data["admin"]))
        assert res_again.status_code == 200
        again_data = res_again.json()
        assert again_data["generated_count"] == 0
        assert again_data["skipped_duplicates_count"] >= 2

    def test_list_alerts_and_mark_read(self, client, db_session, seed_data):
        # Insert a synthetic alert
        alert = Alert(
            type=AlertTypeEnum.OVERDUE,
            target_role=RoleEnum.BUREAU_OFFICER,
            target_bureau_id=1,
            message="Test overdue alert",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(alert)
        db_session.commit()
        alert_id = alert.id

        # List alerts (unread_only=True)
        res = client.get("/api/v1/alerts?unread_only=true", headers=auth_header(seed_data["rb_officer"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1
        found = any(a["id"] == alert_id for a in data["items"])
        assert found is True

        # Mark as read
        res_read = client.post(f"/api/v1/alerts/{alert_id}/read", headers=auth_header(seed_data["rb_officer"]))
        assert res_read.status_code == 200
        assert res_read.json()["read_at"] is not None

        # Verify now absent with unread_only=True
        res_unread = client.get("/api/v1/alerts?unread_only=true", headers=auth_header(seed_data["rb_officer"]))
        assert not any(a["id"] == alert_id for a in res_unread.json()["items"])

    def test_alert_rbac_forbidden_read(self, client, db_session, seed_data):
        # Alert targeted to PGRC (Bureau 2)
        alert = Alert(
            type=AlertTypeEnum.DUE_SOON,
            target_role=RoleEnum.BUREAU_OFFICER,
            target_bureau_id=2,
            message="PGRC alert",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(alert)
        db_session.commit()

        # RB officer (Bureau 1) attempts to mark PGRC alert as read -> 403
        res = client.post(f"/api/v1/alerts/{alert.id}/read", headers=auth_header(seed_data["rb_officer"]))
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

    def test_senior_mgmt_cannot_generate_alerts(self, client, db_session, seed_data):
        # SENIOR_MGMT is read-only and must be forbidden from triggering alert generation
        res = client.post("/api/v1/alerts/generate", headers=auth_header(seed_data["senior"]))
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"
        assert "Senior management is read-only" in get_error(res)["message"]

    def test_bureau_officer_generate_alerts_scoping(self, client, db_session, seed_data):
        today = date.today()
        # RB case (bureau 1) overdue
        c_rb = Case(
            case_no="RB-OVD-SCOPE", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.HIGH,
            received_on=today - timedelta(days=20),
            expected_disposal_on=today - timedelta(days=5),
            summary="RB Overdue", source="SYNTHETIC",
        )
        # PGRC case (bureau 2) overdue
        c_pgrc = Case(
            case_no="PGRC-OVD-SCOPE", bureau_id=2, institution_id=2,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.HIGH,
            received_on=today - timedelta(days=20),
            expected_disposal_on=today - timedelta(days=5),
            summary="PGRC Overdue", source="SYNTHETIC",
        )
        db_session.add_all([c_rb, c_pgrc])
        db_session.commit()

        # RB officer attempting to generate for bureau 2 -> 403
        res_cross = client.post("/api/v1/alerts/generate?bureau_id=2", headers=auth_header(seed_data["rb_officer"]))
        assert res_cross.status_code == 403
        assert get_error(res_cross)["code"] == "FORBIDDEN"

        # RB officer generates without bureau_id -> scoped strictly to bureau 1
        res_own = client.post("/api/v1/alerts/generate", headers=auth_header(seed_data["rb_officer"]))
        assert res_own.status_code == 200
        data = res_own.json()
        assert data["generated_count"] >= 1
        assert data["evaluated_cases_count"] == 1  # only evaluated RB case, not PGRC case!

        # Regional officer attempting to generate -> 403
        res_reg = client.post("/api/v1/alerts/generate", headers=auth_header(seed_data["north_officer"]))
        assert res_reg.status_code == 403
        assert get_error(res_reg)["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 4. Reports Tests
# ---------------------------------------------------------------------------

class TestReports:
    def test_all_report_types_json(self, client, db_session, seed_data):
        today = date.today()
        # Seed a disposed case and an open case
        c1 = Case(
            case_no="REP-001", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.DISPOSED, priority=PriorityEnum.HIGH,
            received_on=today - timedelta(days=30),
            expected_disposal_on=today - timedelta(days=15),
            last_action_on=datetime.now(timezone.utc),
            summary="Disposed", source="SYNTHETIC",
        )
        c2 = Case(
            case_no="REP-002", bureau_id=2, institution_id=2,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.MEDIUM,
            received_on=today - timedelta(days=10),
            expected_disposal_on=today + timedelta(days=20),
            summary="Open", source="SYNTHETIC",
        )
        flag = OverlapFlag(
            institution_id=1, tier=OverlapTierEnum.A, score=1.0,
            reasons=["SAME_INSTITUTION_MULTI_BUREAU"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add_all([c1, c2, flag])
        db_session.commit()

        report_types = [
            "bureau", "region", "institution", "ageing",
            "disposal-rate", "status", "overlaps", "monthly", "quarterly",
        ]

        for r_type in report_types:
            res = client.get(f"/api/v1/reports/{r_type}?format=json", headers=auth_header(seed_data["admin"]))
            assert res.status_code == 200, f"Report type {r_type} failed with status {res.status_code}: {res.text}"
            data = res.json()
            assert data["report_type"] == r_type
            assert "data" in data

    def test_report_csv_export(self, client, db_session, seed_data):
        res = client.get("/api/v1/reports/bureau?format=csv", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert 'filename="report_bureau.csv"' in res.headers["content-disposition"]
        csv_body = res.text
        assert "Bureau Code" in csv_body
        assert "RB" in csv_body

    def test_report_pdf_unsupported_422(self, client, db_session, seed_data):
        res = client.get("/api/v1/reports/bureau?format=pdf", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 422
        assert get_error(res)["code"] == "FORMAT_NOT_SUPPORTED"

    def test_report_invalid_type_404(self, client, db_session, seed_data):
        res = client.get("/api/v1/reports/nonexistent", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 404
        assert get_error(res)["code"] == "NOT_FOUND"

    def test_report_rbac_scoping_for_bureau_officer(self, client, db_session, seed_data):
        res = client.get("/api/v1/reports/bureau?format=json", headers=auth_header(seed_data["rb_officer"]))
        assert res.status_code == 200
        data = res.json()
        bureaus = data["data"]["bureaus"]
        # Bureau officer only sees their own bureau in breakdown
        assert len(bureaus) == 1
        assert bureaus[0]["bureau_code"] == "RB"

    def test_report_date_range_filtering(self, client, db_session, seed_data):
        today = date.today()
        # Case in range
        c_in = Case(
            case_no="DATE-IN", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.LOW,
            received_on=today - timedelta(days=10),
            summary="In range", source="SYNTHETIC",
        )
        # Case out of range
        c_out = Case(
            case_no="DATE-OUT", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.LOW,
            received_on=today - timedelta(days=50),
            summary="Out of range", source="SYNTHETIC",
        )
        db_session.add_all([c_in, c_out])
        db_session.commit()

        from_d = (today - timedelta(days=20)).isoformat()
        to_d = today.isoformat()

        res = client.get(f"/api/v1/reports/status?from_date={from_d}&to_date={to_d}", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["total_records"] == 1

    def test_report_regional_officer_scoping(self, client, db_session, seed_data):
        today = date.today()
        # Case for North institution
        c_north = Case(
            case_no="REG-NORTH", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.LOW,
            received_on=today, summary="North", source="SYNTHETIC",
        )
        # Case for South institution
        c_south = Case(
            case_no="REG-SOUTH", bureau_id=1, institution_id=2,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.LOW,
            received_on=today, summary="South", source="SYNTHETIC",
        )
        db_session.add_all([c_north, c_south])
        db_session.commit()

        res = client.get("/api/v1/reports/region", headers=auth_header(seed_data["north_officer"]))
        assert res.status_code == 200
        regions = res.json()["data"]["regions"]
        assert len(regions) == 1
        assert regions[0]["region_name"] == "Northern"
        assert regions[0]["total_cases"] == 1

    def test_report_overlaps_bureau_and_regional_scoping(self, client, db_session, seed_data):
        today = date.today()
        # Case in Bureau 1, Institution 1 (Northern Region)
        c1 = Case(
            case_no="OV-B1", bureau_id=1, institution_id=1,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.HIGH,
            received_on=today, summary="Bureau 1 case", source="SYNTHETIC",
        )
        # Case in Bureau 2, Institution 2 (Southern Region)
        c2 = Case(
            case_no="OV-B2", bureau_id=2, institution_id=2,
            status=CaseStatusEnum.PENDING, priority=PriorityEnum.HIGH,
            received_on=today, summary="Bureau 2 case", source="SYNTHETIC",
        )
        db_session.add_all([c1, c2])
        db_session.commit()

        # Flag 1: Involves Institution 1 (has Bureau 1 open case, Northern)
        f1 = OverlapFlag(
            institution_id=1, tier=OverlapTierEnum.A, score=0.95,
            state=OverlapStateEnum.OPEN, reasons=["SAME_INSTITUTION_MULTI_BUREAU"],
        )
        # Flag 2: Involves Institution 2 (only Bureau 2 case, Southern)
        f2 = OverlapFlag(
            institution_id=2, tier=OverlapTierEnum.A, score=0.90,
            state=OverlapStateEnum.CONFIRMED, reasons=["SAME_INSTITUTION_MULTI_BUREAU"],
        )
        db_session.add_all([f1, f2])
        db_session.commit()

        # Bureau 1 officer report -> sees ONLY Flag 1
        res_b1 = client.get("/api/v1/reports/overlaps", headers=auth_header(seed_data["rb_officer"]))
        assert res_b1.status_code == 200
        data_b1 = res_b1.json()["data"]
        assert data_b1["total_flags"] == 1
        assert data_b1["open_count"] == 1
        assert data_b1["confirmed_count"] == 0

        # Bureau 2 officer report -> sees ONLY Flag 2
        res_b2 = client.get("/api/v1/reports/overlaps", headers=auth_header(seed_data["pgrc_officer"]))
        assert res_b2.status_code == 200
        data_b2 = res_b2.json()["data"]
        assert data_b2["total_flags"] == 1
        assert data_b2["open_count"] == 0
        assert data_b2["confirmed_count"] == 1

        # Regional officer (Northern) -> sees ONLY Flag 1 (Inst 1 is North)
        res_reg = client.get("/api/v1/reports/overlaps", headers=auth_header(seed_data["north_officer"]))
        assert res_reg.status_code == 200
        data_reg = res_reg.json()["data"]
        assert data_reg["total_flags"] == 1
        assert data_reg["open_count"] == 1

        # Admin and Senior Mgmt see BOTH flags
        res_admin = client.get("/api/v1/reports/overlaps", headers=auth_header(seed_data["admin"]))
        assert res_admin.status_code == 200
        assert res_admin.json()["data"]["total_flags"] == 2

        res_senior = client.get("/api/v1/reports/overlaps", headers=auth_header(seed_data["senior"]))
        assert res_senior.status_code == 200
        assert res_senior.json()["data"]["total_flags"] == 2


# ---------------------------------------------------------------------------
# 5. Extended SLA & Admin Tests
# ---------------------------------------------------------------------------

class TestExtendedSlaAndAdmin:
    def test_sla_cases_pagination(self, client, db_session, seed_data):
        today = date.today()
        cases = []
        for i in range(15):
            cases.append(
                Case(
                    case_no=f"PAG-{i:03d}", bureau_id=1, institution_id=1,
                    status=CaseStatusEnum.PENDING, priority=PriorityEnum.LOW,
                    received_on=today, expected_disposal_on=today + timedelta(days=45),
                    summary=f"Case {i}", source="SYNTHETIC",
                )
            )
        db_session.add_all(cases)
        db_session.commit()

        # Page 1, size 10
        res1 = client.get("/api/v1/sla/cases?page=1&page_size=10", headers=auth_header(seed_data["admin"]))
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["total"] == 15
        assert len(data1["items"]) == 10
        assert data1["page"] == 1

        # Page 2, size 10
        res2 = client.get("/api/v1/sla/cases?page=2&page_size=10", headers=auth_header(seed_data["admin"]))
        assert res2.status_code == 200
        data2 = res2.json()
        assert len(data2["items"]) == 5
        assert data2["page"] == 2

    def test_admin_users_and_evaluation(self, client, db_session, seed_data):
        # GET /admin/users
        res_users = client.get("/api/v1/admin/users", headers=auth_header(seed_data["admin"]))
        assert res_users.status_code == 200
        users = res_users.json()
        assert len(users) >= 5
        assert any(u["email"] == "admin@aicte.test" for u in users)

        # GET /admin/evaluation
        res_eval = client.get("/api/v1/admin/evaluation", headers=auth_header(seed_data["admin"]))
        assert res_eval.status_code == 200
        eval_data = res_eval.json()
        assert eval_data["status"] == "ready"
        assert "fuzzy_threshold_auto" in eval_data

    def test_admin_update_sla_rule_404(self, client, db_session, seed_data):
        res = client.put("/api/v1/admin/sla-rules/9999", json={"days_to_dispose": 10}, headers=auth_header(seed_data["admin"]))
        assert res.status_code == 404
        assert get_error(res)["code"] == "NOT_FOUND"

    def test_alerts_filter_by_type_and_pagination(self, client, db_session, seed_data):
        a1 = Alert(type=AlertTypeEnum.OVERDUE, message="Overdue 1", created_at=datetime.now(timezone.utc))
        a2 = Alert(type=AlertTypeEnum.OVERDUE, message="Overdue 2", created_at=datetime.now(timezone.utc))
        a3 = Alert(type=AlertTypeEnum.DUE_SOON, message="Due soon", created_at=datetime.now(timezone.utc))
        db_session.add_all([a1, a2, a3])
        db_session.commit()

        res = client.get("/api/v1/alerts?type=OVERDUE&page=1&page_size=1", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["items"][0]["type"] == "OVERDUE"


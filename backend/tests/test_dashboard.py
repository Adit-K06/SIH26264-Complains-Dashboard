"""Tests for Phase 4B: Dashboard Aggregation APIs.

Covers:
  1. GET /dashboard/summary  – total, by_status, beyond_sla, overlap counts, monthly trend
  2. GET /dashboard/workload – per-bureau × status counts, all 5 bureaus
  3. GET /dashboard/ageing   – open-case bucket distribution, boundary conditions
  4. Authentication on all endpoints (401 without token)
  5. Empty-database edge cases
  6. Exact values from controlled fixtures (no magic numbers)

Metric definitions tested:
  - beyond_sla = open case AND expected_disposal_on < today
  - open_overlaps = overlap_flags WHERE state=OPEN
  - confirmed_groups = COUNT(DISTINCT institution_id) WHERE state=CONFIRMED
  - monthly received = received_on in month window
  - monthly disposed = DISPOSED cases with last_action_on in month window
  - ageing = today - received_on for open cases; boundaries 0-7,8-15,16-30,31-60,60+
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Bureau, Case, Category, Institution, OverlapFlag, Region, User
from app.models.base import Base
from app.models.enums import (
    CaseStatusEnum,
    OverlapStateEnum,
    OverlapTierEnum,
    PriorityEnum,
    RoleEnum,
)
from app.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Fixtures
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
def base_refs(db_session):
    """Seed the minimal reference rows needed by all dashboard tests."""
    r = Region(id=1, name="Northern")
    b_rb = Bureau(id=1, code="RB", name="Research Bureau")
    b_pgrc = Bureau(id=2, code="PGRC", name="Public Grievance Redressal Cell")
    b_approval = Bureau(id=3, code="APPROVAL", name="Approval Bureau")
    b_academic = Bureau(id=4, code="ACADEMIC", name="Academic Bureau")
    b_finance = Bureau(id=5, code="FINANCE", name="Finance Bureau")
    inst = Institution(
        id=1, aicte_permanent_id="1-001", name="Test Institute",
        address="Addr", district="D", state="S", region_id=1,
        type="College", status="APPROVED",
    )
    admin = User(
        id=1, name="Admin", email="admin@dash.local",
        password_hash=hash_password("x"),
        role=RoleEnum.ADMIN, active=True,
    )
    mgmt = User(
        id=2, name="Mgmt", email="mgmt@dash.local",
        password_hash=hash_password("x"),
        role=RoleEnum.SENIOR_MGMT, active=True,
    )
    officer = User(
        id=3, name="Officer", email="off@dash.local",
        password_hash=hash_password("x"),
        role=RoleEnum.BUREAU_OFFICER, bureau_id=1, active=True,
    )
    db_session.add_all([r, b_rb, b_pgrc, b_approval, b_academic, b_finance, inst, admin, mgmt, officer])
    db_session.commit()
    return {
        "admin": admin, "mgmt": mgmt, "officer": officer,
        "b_rb": b_rb, "b_pgrc": b_pgrc, "b_approval": b_approval,
        "b_academic": b_academic, "b_finance": b_finance,
        "inst": inst, "region": r,
    }


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def make_case(
    db_session, *, case_no: str, bureau_id: int, status: CaseStatusEnum,
    received_on: date, priority: PriorityEnum = PriorityEnum.MEDIUM,
    expected_disposal_on: date | None = None,
    last_action_on: datetime | None = None,
    institution_id: int | None = None,
) -> Case:
    c = Case(
        case_no=case_no,
        bureau_id=bureau_id,
        institution_id=institution_id,
        status=status,
        priority=priority,
        summary=f"Test case {case_no}",
        received_on=received_on,
        expected_disposal_on=expected_disposal_on,
        last_action_on=last_action_on,
        source="SYNTHETIC",
    )
    db_session.add(c)
    return c


TODAY = date.today()
NOW = datetime.now(timezone.utc)
THIS_MONTH = f"{TODAY.year:04d}-{TODAY.month:02d}"


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

class TestDashboardAuth:
    def test_summary_requires_auth(self, client):
        assert client.get("/api/v1/dashboard/summary").status_code == 401

    def test_workload_requires_auth(self, client):
        assert client.get("/api/v1/dashboard/workload").status_code == 401

    def test_ageing_requires_auth(self, client):
        assert client.get("/api/v1/dashboard/ageing").status_code == 401

    def test_all_roles_can_access_summary(self, client, base_refs):
        for key in ("admin", "mgmt", "officer"):
            res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs[key]))
            assert res.status_code == 200, f"{key} should access /dashboard/summary"

    def test_all_roles_can_access_workload(self, client, base_refs):
        for key in ("admin", "mgmt", "officer"):
            res = client.get("/api/v1/dashboard/workload", headers=auth(base_refs[key]))
            assert res.status_code == 200

    def test_all_roles_can_access_ageing(self, client, base_refs):
        for key in ("admin", "mgmt", "officer"):
            res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs[key]))
            assert res.status_code == 200


# ---------------------------------------------------------------------------
# Summary endpoint — empty database
# ---------------------------------------------------------------------------

class TestSummaryEmpty:
    def test_empty_db_returns_zeros(self, client, base_refs):
        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["by_status"] == {}
        assert data["beyond_sla"] == 0
        assert data["open_overlaps"] == 0
        assert data["confirmed_groups"] == 0

    def test_empty_db_monthly_has_12_entries(self, client, base_refs):
        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        monthly = res.json()["monthly"]
        assert len(monthly) == 12
        for entry in monthly:
            assert entry["received"] == 0
            assert entry["disposed"] == 0

    def test_monthly_last_entry_is_current_month(self, client, base_refs):
        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        monthly = res.json()["monthly"]
        assert monthly[-1]["month"] == THIS_MONTH

    def test_monthly_is_chronological(self, client, base_refs):
        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        months = [e["month"] for e in res.json()["monthly"]]
        assert months == sorted(months)


# ---------------------------------------------------------------------------
# Summary endpoint — controlled data
# ---------------------------------------------------------------------------

class TestSummaryMetrics:
    def test_total_counts_all_statuses(self, client, db_session, base_refs):
        make_case(db_session, case_no="RB/TOTAL/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY)
        make_case(db_session, case_no="RB/TOTAL/02", bureau_id=1,
                  status=CaseStatusEnum.DISPOSED, received_on=TODAY,
                  last_action_on=NOW)
        make_case(db_session, case_no="RB/TOTAL/03", bureau_id=1,
                  status=CaseStatusEnum.UNDER_PROCESS, received_on=TODAY)
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        data = res.json()
        assert data["total"] == 3
        assert data["by_status"]["PENDING"] == 1
        assert data["by_status"]["DISPOSED"] == 1
        assert data["by_status"]["UNDER_PROCESS"] == 1

    def test_by_status_only_contains_present_statuses(self, client, db_session, base_refs):
        make_case(db_session, case_no="RB/STAT/01", bureau_id=1,
                  status=CaseStatusEnum.ESCALATED, received_on=TODAY)
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        by_status = res.json()["by_status"]
        assert "ESCALATED" in by_status
        # TRANSFERRED not inserted, should not appear (or be 0)
        assert by_status.get("TRANSFERRED", 0) == 0

    def test_beyond_sla_counts_open_overdue_only(self, client, db_session, base_refs):
        past = TODAY - timedelta(days=5)
        future = TODAY + timedelta(days=5)

        # Open + overdue → counts
        make_case(db_session, case_no="RB/SLA/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=30),
                  expected_disposal_on=past)
        # Open + future SLA → does NOT count
        make_case(db_session, case_no="RB/SLA/02", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY,
                  expected_disposal_on=future)
        # Disposed + overdue → does NOT count (not open)
        make_case(db_session, case_no="RB/SLA/03", bureau_id=1,
                  status=CaseStatusEnum.DISPOSED, received_on=TODAY - timedelta(days=40),
                  expected_disposal_on=past, last_action_on=NOW)
        # Open + no expected_disposal_on → does NOT count
        make_case(db_session, case_no="RB/SLA/04", bureau_id=1,
                  status=CaseStatusEnum.UNDER_PROCESS, received_on=TODAY)
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        assert res.json()["beyond_sla"] == 1

    def test_beyond_sla_exact_today_not_counted(self, client, db_session, base_refs):
        """expected_disposal_on == today is NOT beyond SLA (must be strictly < today)."""
        make_case(db_session, case_no="RB/SLA/TODAY", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=10),
                  expected_disposal_on=TODAY)
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        assert res.json()["beyond_sla"] == 0

    def test_open_overlaps_counted(self, client, db_session, base_refs):
        db_session.add(OverlapFlag(
            institution_id=1, tier=OverlapTierEnum.A,
            score=0.0, reasons=[], state=OverlapStateEnum.OPEN,
        ))
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        assert res.json()["open_overlaps"] == 1

    def test_dismissed_overlap_not_counted_as_open(self, client, db_session, base_refs):
        # Create a Tier B overlap (needs case_a and case_b to satisfy unique constraint)
        c1 = make_case(db_session, case_no="RB/OVL/01", bureau_id=1,
                       status=CaseStatusEnum.PENDING, received_on=TODAY)
        c2 = make_case(db_session, case_no="RB/OVL/02", bureau_id=2,
                       status=CaseStatusEnum.PENDING, received_on=TODAY)
        db_session.flush()
        db_session.add(OverlapFlag(
            institution_id=1, case_a=c1.id, case_b=c2.id,
            tier=OverlapTierEnum.B, score=0.7, reasons=[],
            state=OverlapStateEnum.DISMISSED,
        ))
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        assert res.json()["open_overlaps"] == 0

    def test_confirmed_groups_counts_distinct_institutions(self, client, db_session, base_refs):
        # Two confirmed flags for the SAME institution → 1 group
        inst2 = Institution(
            id=2, aicte_permanent_id="1-002", name="Inst2",
            address="A", district="D", state="S", region_id=1,
            type="College", status="APPROVED",
        )
        db_session.add(inst2)
        db_session.flush()

        c1 = make_case(db_session, case_no="RB/CG/01", bureau_id=1,
                       status=CaseStatusEnum.PENDING, received_on=TODAY)
        c2 = make_case(db_session, case_no="RB/CG/02", bureau_id=2,
                       status=CaseStatusEnum.PENDING, received_on=TODAY)
        c3 = make_case(db_session, case_no="RB/CG/03", bureau_id=1,
                       status=CaseStatusEnum.PENDING, received_on=TODAY)
        c4 = make_case(db_session, case_no="RB/CG/04", bureau_id=2,
                       status=CaseStatusEnum.PENDING, received_on=TODAY)
        db_session.flush()

        # Institution 1: two confirmed Tier B flags
        db_session.add(OverlapFlag(
            institution_id=1, case_a=c1.id, case_b=c2.id,
            tier=OverlapTierEnum.B, score=0.8, reasons=[],
            state=OverlapStateEnum.CONFIRMED,
        ))
        # Institution 2: one confirmed Tier B flag
        db_session.add(OverlapFlag(
            institution_id=2, case_a=c3.id, case_b=c4.id,
            tier=OverlapTierEnum.B, score=0.9, reasons=[],
            state=OverlapStateEnum.CONFIRMED,
        ))
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        assert res.json()["confirmed_groups"] == 2

    def test_monthly_received_in_current_month(self, client, db_session, base_refs):
        make_case(db_session, case_no="RB/MON/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY)
        make_case(db_session, case_no="RB/MON/02", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY)
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        monthly = res.json()["monthly"]
        current = next(m for m in monthly if m["month"] == THIS_MONTH)
        assert current["received"] == 2

    def test_monthly_disposed_in_current_month(self, client, db_session, base_refs):
        make_case(db_session, case_no="RB/DIS/01", bureau_id=1,
                  status=CaseStatusEnum.DISPOSED,
                  received_on=TODAY - timedelta(days=10),
                  last_action_on=NOW)  # disposed this month
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        monthly = res.json()["monthly"]
        current = next(m for m in monthly if m["month"] == THIS_MONTH)
        assert current["disposed"] == 1

    def test_monthly_pending_not_counted_as_disposed(self, client, db_session, base_refs):
        make_case(db_session, case_no="RB/PEND/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING,
                  received_on=TODAY, last_action_on=NOW)
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        monthly = res.json()["monthly"]
        current = next(m for m in monthly if m["month"] == THIS_MONTH)
        assert current["disposed"] == 0

    def test_monthly_old_cases_outside_window_not_counted(self, client, db_session, base_refs):
        # Case received 13 months ago — outside 12-month window
        old_date = TODAY.replace(day=1) - timedelta(days=1)  # previous month's last day
        # Go back 12 more months
        y, m = old_date.year, old_date.month - 12
        while m <= 0:
            m += 12
            y -= 1
        old_received = date(y, m, 15)

        make_case(db_session, case_no="RB/OLD/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=old_received)
        db_session.commit()

        res = client.get("/api/v1/dashboard/summary", headers=auth(base_refs["admin"]))
        total_received = sum(e["received"] for e in res.json()["monthly"])
        assert total_received == 0


# ---------------------------------------------------------------------------
# Workload endpoint
# ---------------------------------------------------------------------------

class TestWorkload:
    def test_workload_returns_items_list(self, client, base_refs):
        res = client.get("/api/v1/dashboard/workload", headers=auth(base_refs["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert "items" in data

    def test_workload_includes_all_5_bureaus(self, client, base_refs):
        """All five AGENTS.md bureaus appear even when they have zero cases."""
        res = client.get("/api/v1/dashboard/workload", headers=auth(base_refs["admin"]))
        codes = {r["bureau"] for r in res.json()["items"]}
        assert codes == {"RB", "PGRC", "APPROVAL", "ACADEMIC", "FINANCE"}

    def test_workload_zero_bureau_has_empty_counts(self, client, base_refs):
        res = client.get("/api/v1/dashboard/workload", headers=auth(base_refs["admin"]))
        items = res.json()["items"]
        # With no cases seeded, all counts should be empty dicts
        for item in items:
            assert item["counts"] == {}

    def test_workload_counts_correct_per_bureau_status(self, client, db_session, base_refs):
        make_case(db_session, case_no="WL/RB/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY)
        make_case(db_session, case_no="WL/RB/02", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY)
        make_case(db_session, case_no="WL/RB/03", bureau_id=1,
                  status=CaseStatusEnum.DISPOSED, received_on=TODAY,
                  last_action_on=NOW)
        make_case(db_session, case_no="WL/PGRC/01", bureau_id=2,
                  status=CaseStatusEnum.UNDER_PROCESS, received_on=TODAY)
        db_session.commit()

        res = client.get("/api/v1/dashboard/workload", headers=auth(base_refs["admin"]))
        items = {r["bureau"]: r["counts"] for r in res.json()["items"]}

        assert items["RB"].get("PENDING") == 2
        assert items["RB"].get("DISPOSED") == 1
        assert items["PGRC"].get("UNDER_PROCESS") == 1
        # Bureaus with no cases
        assert items["APPROVAL"] == {}
        assert items["ACADEMIC"] == {}
        assert items["FINANCE"] == {}

    def test_workload_row_fields(self, client, base_refs):
        res = client.get("/api/v1/dashboard/workload", headers=auth(base_refs["admin"]))
        item = res.json()["items"][0]
        assert "bureau" in item
        assert "counts" in item


# ---------------------------------------------------------------------------
# Ageing endpoint
# ---------------------------------------------------------------------------

class TestAgeing:
    def test_ageing_returns_5_buckets(self, client, base_refs):
        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 5
        bucket_names = [b["bucket"] for b in items]
        assert set(bucket_names) == {"0-7", "8-15", "16-30", "31-60", "60+"}

    def test_ageing_empty_db_all_zero(self, client, base_refs):
        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        for bucket in res.json()["items"]:
            assert bucket["count"] == 0

    def test_ageing_open_case_in_0_7_bucket(self, client, db_session, base_refs):
        # Received today → age 0 → bucket 0-7
        make_case(db_session, case_no="AGE/07/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY)
        # Received 7 days ago → age 7 → still bucket 0-7 (boundary inclusive)
        make_case(db_session, case_no="AGE/07/02", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=7))
        db_session.commit()

        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        buckets = {b["bucket"]: b["count"] for b in res.json()["items"]}
        assert buckets["0-7"] == 2

    def test_ageing_8_falls_in_8_15(self, client, db_session, base_refs):
        make_case(db_session, case_no="AGE/815/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=8))
        make_case(db_session, case_no="AGE/815/02", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=15))
        db_session.commit()

        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        buckets = {b["bucket"]: b["count"] for b in res.json()["items"]}
        assert buckets["8-15"] == 2

    def test_ageing_16_and_30_fall_in_16_30(self, client, db_session, base_refs):
        make_case(db_session, case_no="AGE/1630/01", bureau_id=1,
                  status=CaseStatusEnum.UNDER_PROCESS, received_on=TODAY - timedelta(days=16))
        make_case(db_session, case_no="AGE/1630/02", bureau_id=1,
                  status=CaseStatusEnum.ESCALATED, received_on=TODAY - timedelta(days=30))
        db_session.commit()

        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        buckets = {b["bucket"]: b["count"] for b in res.json()["items"]}
        assert buckets["16-30"] == 2

    def test_ageing_31_and_60_fall_in_31_60(self, client, db_session, base_refs):
        make_case(db_session, case_no="AGE/3160/01", bureau_id=1,
                  status=CaseStatusEnum.TRANSFERRED, received_on=TODAY - timedelta(days=31))
        make_case(db_session, case_no="AGE/3160/02", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=60))
        db_session.commit()

        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        buckets = {b["bucket"]: b["count"] for b in res.json()["items"]}
        assert buckets["31-60"] == 2

    def test_ageing_61_falls_in_60_plus(self, client, db_session, base_refs):
        make_case(db_session, case_no="AGE/60P/01", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=61))
        make_case(db_session, case_no="AGE/60P/02", bureau_id=1,
                  status=CaseStatusEnum.PENDING, received_on=TODAY - timedelta(days=200))
        db_session.commit()

        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        buckets = {b["bucket"]: b["count"] for b in res.json()["items"]}
        assert buckets["60+"] == 2

    def test_ageing_disposed_case_not_counted(self, client, db_session, base_refs):
        """DISPOSED cases must not appear in ageing — only open cases count."""
        make_case(db_session, case_no="AGE/DIS/01", bureau_id=1,
                  status=CaseStatusEnum.DISPOSED,
                  received_on=TODAY - timedelta(days=10),
                  last_action_on=NOW)
        db_session.commit()

        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        total = sum(b["count"] for b in res.json()["items"])
        assert total == 0

    def test_ageing_multiple_open_statuses_all_counted(self, client, db_session, base_refs):
        """PENDING, UNDER_PROCESS, ESCALATED, TRANSFERRED all count in ageing."""
        for i, status in enumerate([
            CaseStatusEnum.PENDING,
            CaseStatusEnum.UNDER_PROCESS,
            CaseStatusEnum.ESCALATED,
            CaseStatusEnum.TRANSFERRED,
        ]):
            make_case(db_session, case_no=f"AGE/OPEN/0{i+1}", bureau_id=1,
                      status=status, received_on=TODAY - timedelta(days=5))
        db_session.commit()

        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        buckets = {b["bucket"]: b["count"] for b in res.json()["items"]}
        assert buckets["0-7"] == 4

    def test_ageing_bucket_order_preserved(self, client, base_refs):
        """Buckets should appear in logical order: 0-7, 8-15, 16-30, 31-60, 60+."""
        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        names = [b["bucket"] for b in res.json()["items"]]
        assert names == ["0-7", "8-15", "16-30", "31-60", "60+"]

    def test_ageing_response_fields(self, client, base_refs):
        res = client.get("/api/v1/dashboard/ageing", headers=auth(base_refs["admin"]))
        bucket = res.json()["items"][0]
        assert "bucket" in bucket
        assert "count" in bucket

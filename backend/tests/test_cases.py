"""Comprehensive tests for Phase 3 Complaint Management APIs.

Tests cover:
  1. Case listing, pagination, search (q), and all supported filters.
  2. Case detail success, 404, and actions history.
  3. Complainant reference masking across all roles and scopes.
  4. Complaint creation (auto-numbering, custom case_no, 409 duplicate).
  5. Foreign-key validation on create/update/assign (422).
  6. Status transitions (allowed: PENDING->UNDER_PROCESS->DISPOSED, any open->TRANSFERRED,
     any open->ESCALATED, DISPOSED->PENDING with remarks).
  7. Invalid transitions (409 Conflict, 422 on reopen without remarks).
  8. Dedicated endpoints: /transfer, /escalate, /dispose, /reopen.
  9. Role and scope enforcement (BUREAU_OFFICER, REGIONAL_OFFICER, SENIOR_MGMT, ADMIN).
  10. Assignment validation (matching bureau/region, inactive target -> 422).
  11. Append-only case_actions audit trail.
  12. Consistent error envelopes across all HTTP errors.
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
    Bureau,
    Case,
    CaseAction,
    Category,
    Institution,
    Region,
    SlaRule,
    User,
)
from app.models.base import Base
from app.models.enums import (
    ActionTypeEnum,
    CaseStatusEnum,
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
def seed_data(db_session):
    """Seed base regions, bureaus, categories, users for testing."""
    # Regions
    r_north = Region(id=1, name="Northern")
    r_south = Region(id=2, name="Southern")
    db_session.add_all([r_north, r_south])
    db_session.flush()

    # Bureaus
    b_rb = Bureau(id=1, code="RB", name="Research Bureau")
    b_pgrc = Bureau(id=2, code="PGRC", name="Public Grievance Redressal Cell")
    db_session.add_all([b_rb, b_pgrc])
    db_session.flush()

    # Categories
    c_adm = Category(id=1, name="Admission")
    c_fee = Category(id=2, name="Fee")
    db_session.add_all([c_adm, c_fee])
    db_session.flush()

    # Institutions
    inst_n = Institution(
        id=1,
        aicte_permanent_id="1-1001",
        name="Northern Institute of Tech",
        address="100 North Rd",
        district="Delhi",
        state="Delhi",
        region_id=r_north.id,
        type="College",
        status="APPROVED",
    )
    inst_s = Institution(
        id=2,
        aicte_permanent_id="1-2002",
        name="Southern Polytechnic",
        address="200 South Rd",
        district="Chennai",
        state="Tamil Nadu",
        region_id=r_south.id,
        type="Polytechnic",
        status="APPROVED",
    )
    db_session.add_all([inst_n, inst_s])
    db_session.flush()

    # Users
    admin = User(
        id=1,
        name="System Admin",
        email="admin@test.local",
        password_hash=hash_password("admin123"),
        role=RoleEnum.ADMIN,
        active=True,
    )
    mgmt = User(
        id=2,
        name="Senior Director",
        email="mgmt@test.local",
        password_hash=hash_password("mgmt123"),
        role=RoleEnum.SENIOR_MGMT,
        active=True,
    )
    officer_rb = User(
        id=3,
        name="RB Officer",
        email="rb.officer@test.local",
        password_hash=hash_password("officer123"),
        role=RoleEnum.BUREAU_OFFICER,
        bureau_id=b_rb.id,
        active=True,
    )
    officer_pgrc = User(
        id=4,
        name="PGRC Officer",
        email="pgrc.officer@test.local",
        password_hash=hash_password("officer123"),
        role=RoleEnum.BUREAU_OFFICER,
        bureau_id=b_pgrc.id,
        active=True,
    )
    reg_north = User(
        id=5,
        name="Northern Regional Officer",
        email="reg.north@test.local",
        password_hash=hash_password("officer123"),
        role=RoleEnum.REGIONAL_OFFICER,
        region_id=r_north.id,
        active=True,
    )
    reg_south = User(
        id=6,
        name="Southern Regional Officer",
        email="reg.south@test.local",
        password_hash=hash_password("officer123"),
        role=RoleEnum.REGIONAL_OFFICER,
        region_id=r_south.id,
        active=True,
    )
    inactive_officer = User(
        id=7,
        name="Inactive Officer",
        email="inactive@test.local",
        password_hash=hash_password("officer123"),
        role=RoleEnum.BUREAU_OFFICER,
        bureau_id=b_rb.id,
        active=False,
    )
    db_session.add_all([admin, mgmt, officer_rb, officer_pgrc, reg_north, reg_south, inactive_officer])

    # SLA rule
    sla = SlaRule(
        category_id=c_adm.id,
        priority=PriorityEnum.HIGH,
        days_to_dispose=15,
        warn_at_pct=80,
        reminder_after_days=10,
        escalate_after_days=16,
    )
    db_session.add(sla)
    db_session.commit()

    return {
        "admin": admin,
        "mgmt": mgmt,
        "officer_rb": officer_rb,
        "officer_pgrc": officer_pgrc,
        "reg_north": reg_north,
        "reg_south": reg_south,
        "inactive": inactive_officer,
        "b_rb": b_rb,
        "b_pgrc": b_pgrc,
        "r_north": r_north,
        "r_south": r_south,
        "c_adm": c_adm,
        "c_fee": c_fee,
        "inst_n": inst_n,
        "inst_s": inst_s,
    }


def auth_header(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


def get_error(res) -> dict:
    body = res.json()
    if "error" in body:
        return body["error"]
    if "detail" in body and isinstance(body["detail"], dict) and "error" in body["detail"]:
        return body["detail"]["error"]
    return body


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

class TestCaseListingAndFilters:
    def test_unauthenticated_request_rejected(self, client):
        # Without token -> 401
        res = client.get("/api/v1/cases")
        assert res.status_code == 401

        # With invalid token -> 401 with standard error envelope
        res2 = client.get("/api/v1/cases", headers={"Authorization": "Bearer invalid.token.value"})
        assert res2.status_code == 401
        assert get_error(res2)["code"] == "UNAUTHORIZED"

    def test_empty_list_matches_contract(self, client, seed_data):
        res = client.get("/api/v1/cases", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_pagination_and_sorting(self, client, db_session, seed_data):
        # Create 25 cases with dates
        base_date = date(2026, 1, 1)
        for i in range(25):
            c = Case(
                case_no=f"RB/2026/{str(i+1).zfill(6)}",
                bureau_id=seed_data["b_rb"].id,
                institution_id=seed_data["inst_n"].id,
                status=CaseStatusEnum.PENDING,
                priority=PriorityEnum.MEDIUM,
                summary=f"Summary {i+1}",
                received_on=base_date + timedelta(days=i),
                source="SYNTHETIC",
            )
            db_session.add(c)
        db_session.commit()

        # Page 1 (size 10)
        res1 = client.get("/api/v1/cases?page=1&page_size=10", headers=auth_header(seed_data["admin"]))
        assert res1.status_code == 200
        p1 = res1.json()
        assert p1["total"] == 25
        assert len(p1["items"]) == 10
        assert p1["page"] == 1
        # Most recent first
        assert p1["items"][0]["case_no"] == "RB/2026/000025"

        # Page 3 (size 10)
        res3 = client.get("/api/v1/cases?page=3&page_size=10", headers=auth_header(seed_data["admin"]))
        assert res3.status_code == 200
        p3 = res3.json()
        assert len(p3["items"]) == 5

    def test_filters(self, client, db_session, seed_data):
        today = date.today()
        c1 = Case(
            case_no="RB/2026/F00001",
            bureau_id=seed_data["b_rb"].id,
            institution_id=seed_data["inst_n"].id,
            category_id=seed_data["c_adm"].id,
            status=CaseStatusEnum.PENDING,
            priority=PriorityEnum.HIGH,
            summary="Admission irregularities reported",
            received_on=today - timedelta(days=20),
            expected_disposal_on=today - timedelta(days=5),  # beyond SLA
            last_action_on=datetime.now(timezone.utc) - timedelta(days=15),
            link_group_id="grp-123",
            source="SYNTHETIC",
        )
        c2 = Case(
            case_no="PGRC/2026/F00002",
            bureau_id=seed_data["b_pgrc"].id,
            institution_id=seed_data["inst_s"].id,
            category_id=seed_data["c_fee"].id,
            status=CaseStatusEnum.DISPOSED,
            priority=PriorityEnum.LOW,
            summary="Excess fee refund inquiry",
            received_on=today - timedelta(days=5),
            expected_disposal_on=today + timedelta(days=40),
            last_action_on=datetime.now(timezone.utc) - timedelta(days=1),
            link_group_id=None,
            source="SYNTHETIC",
        )
        db_session.add_all([c1, c2])
        db_session.commit()

        headers = auth_header(seed_data["admin"])

        # Filter q (case_no, summary, inst name)
        res = client.get("/api/v1/cases?q=Admission", headers=headers)
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["case_no"] == "RB/2026/F00001"

        res = client.get("/api/v1/cases?q=Southern", headers=headers)
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["case_no"] == "PGRC/2026/F00002"

        # Filter status
        res = client.get("/api/v1/cases?status=PENDING", headers=headers)
        assert any(c["case_no"] == "RB/2026/F00001" for c in res.json()["items"])

        # Filter priority
        res = client.get("/api/v1/cases?priority=HIGH", headers=headers)
        assert all(c["priority"] == "HIGH" for c in res.json()["items"])

        # Filter bureau_id
        res = client.get(f"/api/v1/cases?bureau_id={seed_data['b_pgrc'].id}", headers=headers)
        assert all(c["bureau_id"] == seed_data["b_pgrc"].id for c in res.json()["items"])

        # Filter region_id
        res = client.get(f"/api/v1/cases?region_id={seed_data['r_south'].id}", headers=headers)
        assert all(c["region_id"] == seed_data["r_south"].id for c in res.json()["items"])

        # Filter category_id
        res = client.get(f"/api/v1/cases?category_id={seed_data['c_fee'].id}", headers=headers)
        assert all(c["category_id"] == seed_data["c_fee"].id for c in res.json()["items"])

        # Filter aicte_id
        res = client.get("/api/v1/cases?aicte_id=1-1001", headers=headers)
        assert any(c["case_no"] == "RB/2026/F00001" for c in res.json()["items"])

        # Filter beyond_sla: c1 is open and expected_disposal_on < today
        res = client.get("/api/v1/cases?beyond_sla=true", headers=headers)
        items = res.json()["items"]
        assert any(c["case_no"] == "RB/2026/F00001" for c in items)
        assert not any(c["case_no"] == "PGRC/2026/F00002" for c in items)

        # Filter linked
        res = client.get("/api/v1/cases?linked=true", headers=headers)
        assert any(c["case_no"] == "RB/2026/F00001" for c in res.json()["items"])
        assert not any(c["case_no"] == "PGRC/2026/F00002" for c in res.json()["items"])

        # Filter no_recent_action_days (c1 last action was 15 days ago)
        res = client.get("/api/v1/cases?no_recent_action_days=10", headers=headers)
        assert any(c["case_no"] == "RB/2026/F00001" for c in res.json()["items"])

        # Complainant ref must NOT be in CaseRowOut
        assert "complainant_ref" not in res.json()["items"][0]


class TestCaseDetailAndMasking:
    def test_case_detail_not_found_returns_404(self, client, seed_data):
        res = client.get("/api/v1/cases/99999", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 404
        assert get_error(res)["code"] == "NOT_FOUND"

    def test_complainant_ref_masking_matrix(self, client, db_session, seed_data):
        """Verify complainant_ref masking rules:
        - ADMIN sees full reference
        - BUREAU_OFFICER sees full ref for own bureau, '***' for other bureau
        - REGIONAL_OFFICER sees full ref for own region, '***' for other region
        - SENIOR_MGMT always sees '***'
        """
        # Case in RB bureau and Northern region
        c_rb_north = Case(
            case_no="RB/2026/MASK01",
            bureau_id=seed_data["b_rb"].id,
            institution_id=seed_data["inst_n"].id,  # Northern region
            status=CaseStatusEnum.PENDING,
            priority=PriorityEnum.MEDIUM,
            summary="Testing masking",
            received_on=date(2026, 1, 1),
            complainant_ref="REF-SECRET-999",
            source="SYNTHETIC",
        )
        db_session.add(c_rb_north)
        db_session.commit()
        cid = c_rb_north.id

        # 1. ADMIN
        res = client.get(f"/api/v1/cases/{cid}", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["complainant_ref"] == "REF-SECRET-999"

        # 2. RB Officer (own bureau)
        res = client.get(f"/api/v1/cases/{cid}", headers=auth_header(seed_data["officer_rb"]))
        assert res.json()["complainant_ref"] == "REF-SECRET-999"

        # 3. PGRC Officer (different bureau) -> masked
        res = client.get(f"/api/v1/cases/{cid}", headers=auth_header(seed_data["officer_pgrc"]))
        assert res.json()["complainant_ref"] == "***"

        # 4. Northern Regional Officer (own region)
        res = client.get(f"/api/v1/cases/{cid}", headers=auth_header(seed_data["reg_north"]))
        assert res.json()["complainant_ref"] == "REF-SECRET-999"

        # 5. Southern Regional Officer (different region) -> masked
        res = client.get(f"/api/v1/cases/{cid}", headers=auth_header(seed_data["reg_south"]))
        assert res.json()["complainant_ref"] == "***"

        # 6. SENIOR_MGMT -> always masked
        res = client.get(f"/api/v1/cases/{cid}", headers=auth_header(seed_data["mgmt"]))
        assert res.json()["complainant_ref"] == "***"


class TestCaseCreation:
    def test_create_case_auto_numbering(self, client, seed_data):
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "category_id": seed_data["c_adm"].id,
            "priority": "HIGH",
            "summary": "Auto case number test",
            "complainant_ref": "COMP-1234",
        }
        res = client.post("/api/v1/cases", json=payload, headers=auth_header(seed_data["admin"]))
        assert res.status_code == 201
        data = res.json()
        assert data["case_no"].startswith("RB/")
        assert data["status"] == "PENDING"
        assert data["priority"] == "HIGH"
        # SlaRule for Admission HIGH is 15 days
        rec_on = date.fromisoformat(data["received_on"])
        exp_on = date.fromisoformat(data["expected_disposal_on"])
        assert (exp_on - rec_on).days == 15
        # Creation audit action recorded
        assert len(data["actions"]) == 1
        assert data["actions"][0]["action_type"] == "CREATED"
        assert data["actions"][0]["to_status"] == "PENDING"

    def test_create_duplicate_case_no_same_bureau_fails_409(self, client, seed_data):
        payload = {
            "case_no": "RB/2026/CUSTOM01",
            "bureau_id": seed_data["b_rb"].id,
            "summary": "Custom case no test",
        }
        res1 = client.post("/api/v1/cases", json=payload, headers=auth_header(seed_data["admin"]))
        assert res1.status_code == 201

        # Second create with same bureau & case_no -> 409
        res2 = client.post("/api/v1/cases", json=payload, headers=auth_header(seed_data["admin"]))
        assert res2.status_code == 409
        assert get_error(res2)["code"] == "CONFLICT"

    def test_create_same_case_no_different_bureau_allowed(self, client, seed_data):
        payload1 = {
            "case_no": "SHARED/2026/01",
            "bureau_id": seed_data["b_rb"].id,
            "summary": "Shared number test bureau 1",
        }
        payload2 = {
            "case_no": "SHARED/2026/01",
            "bureau_id": seed_data["b_pgrc"].id,
            "summary": "Shared number test bureau 2",
        }
        res1 = client.post("/api/v1/cases", json=payload1, headers=auth_header(seed_data["admin"]))
        res2 = client.post("/api/v1/cases", json=payload2, headers=auth_header(seed_data["admin"]))
        assert res1.status_code == 201
        assert res2.status_code == 201

    def test_create_invalid_foreign_keys_return_422(self, client, seed_data):
        headers = auth_header(seed_data["admin"])
        # Invalid bureau
        res = client.post("/api/v1/cases", json={"bureau_id": 9999, "summary": "test"}, headers=headers)
        assert res.status_code == 422

        # Invalid institution
        res = client.post("/api/v1/cases", json={"bureau_id": seed_data["b_rb"].id, "institution_id": 9999, "summary": "test"}, headers=headers)
        assert res.status_code == 422

        # Invalid category
        res = client.post("/api/v1/cases", json={"bureau_id": seed_data["b_rb"].id, "category_id": 9999, "summary": "test"}, headers=headers)
        assert res.status_code == 422

    def test_create_rbac_enforcement(self, client, seed_data):
        # 1. SENIOR_MGMT cannot create complaints
        res = client.post(
            "/api/v1/cases",
            json={"bureau_id": seed_data["b_rb"].id, "summary": "test"},
            headers=auth_header(seed_data["mgmt"]),
        )
        assert res.status_code == 403

        # 2. Bureau officer creating for different bureau -> 403
        res = client.post(
            "/api/v1/cases",
            json={"bureau_id": seed_data["b_pgrc"].id, "summary": "test"},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 403

        # 3. Bureau officer creating for own bureau -> 201
        res = client.post(
            "/api/v1/cases",
            json={"bureau_id": seed_data["b_rb"].id, "summary": "own bureau test"},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 201

        # 4. Regional officer creating for different region -> 403
        res = client.post(
            "/api/v1/cases",
            json={
                "bureau_id": seed_data["b_rb"].id,
                "institution_id": seed_data["inst_s"].id,  # Southern
                "summary": "test",
            },
            headers=auth_header(seed_data["reg_north"]),
        )
        assert res.status_code == 403

        # 5. Regional officer creating for own region -> 201
        res = client.post(
            "/api/v1/cases",
            json={
                "bureau_id": seed_data["b_rb"].id,
                "institution_id": seed_data["inst_n"].id,  # Northern
                "summary": "regional own test",
            },
            headers=auth_header(seed_data["reg_north"]),
        )
        assert res.status_code == 201


class TestCaseUpdatesAndTransitions:
    def _create_test_case(self, client, seed_data, init_status=CaseStatusEnum.PENDING):
        headers = auth_header(seed_data["admin"])
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "summary": "Transition test case",
        }
        res = client.post("/api/v1/cases", json=payload, headers=headers)
        assert res.status_code == 201
        cid = res.json()["id"]

        if init_status != CaseStatusEnum.PENDING:
            # Advance as admin
            if init_status == CaseStatusEnum.UNDER_PROCESS:
                client.patch(f"/api/v1/cases/{cid}", json={"status": "UNDER_PROCESS", "remarks": "advance"}, headers=headers)
            elif init_status == CaseStatusEnum.DISPOSED:
                client.patch(f"/api/v1/cases/{cid}", json={"status": "UNDER_PROCESS", "remarks": "proc"}, headers=headers)
                client.post(f"/api/v1/cases/{cid}/dispose", json={"remarks": "done"}, headers=headers)
        return cid

    def test_permitted_updates_via_patch(self, client, seed_data):
        cid = self._create_test_case(client, seed_data)
        headers = auth_header(seed_data["officer_rb"])

        res = client.patch(
            f"/api/v1/cases/{cid}",
            json={"priority": "HIGH", "summary": "Updated summary text", "next_action_text": "Call complainant"},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["priority"] == "HIGH"
        assert data["summary"] == "Updated summary text"
        assert data["next_action_text"] == "Call complainant"

    def test_status_transitions_rules(self, client, seed_data):
        """Test transitions per AGENTS.md:
        PENDING -> UNDER_PROCESS -> DISPOSED
        DISPOSED -> PENDING (requires remarks, else 422)
        Invalid transitions return 409 CONFLICT.
        """
        cid = self._create_test_case(client, seed_data, init_status=CaseStatusEnum.PENDING)
        headers = auth_header(seed_data["officer_rb"])

        # PENDING -> DISPOSED directly is forbidden -> 409
        res = client.post(f"/api/v1/cases/{cid}/dispose", json={"remarks": "skip"}, headers=headers)
        assert res.status_code == 409
        assert get_error(res)["code"] == "CONFLICT"

        # PENDING -> UNDER_PROCESS -> 200
        res = client.patch(f"/api/v1/cases/{cid}", json={"status": "UNDER_PROCESS", "remarks": "Started review"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "UNDER_PROCESS"

        # UNDER_PROCESS -> DISPOSED -> 200
        res = client.post(f"/api/v1/cases/{cid}/dispose", json={"remarks": "Resolution completed"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "DISPOSED"

        # DISPOSED -> ESCALATED is forbidden -> 409
        res = client.post(f"/api/v1/cases/{cid}/escalate", json={"remarks": "try escalate"}, headers=headers)
        assert res.status_code == 409

        # DISPOSED -> TRANSFERRED is forbidden -> 409
        res = client.post(f"/api/v1/cases/{cid}/transfer", json={"remarks": "try transfer"}, headers=headers)
        assert res.status_code == 409

        # DISPOSED -> PENDING without remarks -> 422
        res = client.post(f"/api/v1/cases/{cid}/reopen", json={"remarks": ""}, headers=headers)
        assert res.status_code == 422

        # DISPOSED -> PENDING with valid remarks -> 200
        res = client.post(f"/api/v1/cases/{cid}/reopen", json={"remarks": "New evidence presented"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "PENDING"

    def test_transfer_and_escalate_endpoints(self, client, seed_data):
        cid = self._create_test_case(client, seed_data, init_status=CaseStatusEnum.PENDING)
        headers = auth_header(seed_data["officer_rb"])

        # Transfer to another bureau
        res = client.post(
            f"/api/v1/cases/{cid}/transfer",
            json={"to_bureau_id": seed_data["b_pgrc"].id, "remarks": "Transferred to PGRC"},
            headers=headers,
        )
        assert res.status_code == 200
        assert res.json()["status"] == "TRANSFERRED"
        assert res.json()["bureau_id"] == seed_data["b_pgrc"].id

        # Escalate an open case
        # Note: case is now in PGRC bureau! Senior mgmt can escalate any open case
        res = client.post(
            f"/api/v1/cases/{cid}/escalate",
            json={"remarks": "Overdue for coordination"},
            headers=auth_header(seed_data["mgmt"]),
        )
        assert res.status_code == 200
        assert res.json()["status"] == "ESCALATED"

    def test_senior_mgmt_restricted_operations(self, client, seed_data):
        cid = self._create_test_case(client, seed_data, init_status=CaseStatusEnum.PENDING)
        headers = auth_header(seed_data["mgmt"])

        # Cannot patch
        res = client.patch(f"/api/v1/cases/{cid}", json={"summary": "new"}, headers=headers)
        assert res.status_code == 403

        # Cannot dispose
        res = client.post(f"/api/v1/cases/{cid}/dispose", json={"remarks": "done"}, headers=headers)
        assert res.status_code == 403

        # Cannot transfer
        res = client.post(f"/api/v1/cases/{cid}/transfer", json={"remarks": "move"}, headers=headers)
        assert res.status_code == 403

        # Cannot reopen
        res = client.post(f"/api/v1/cases/{cid}/reopen", json={"remarks": "open"}, headers=headers)
        assert res.status_code == 403

        # CAN escalate open case
        res = client.post(f"/api/v1/cases/{cid}/escalate", json={"remarks": "Urgent escalation"}, headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "ESCALATED"

    def test_bureau_officer_cannot_transfer_other_bureau_case(self, client, db_session, seed_data):
        """BUREAU_OFFICER cannot transfer a case belonging to another bureau (403).
        Verify: status, bureau, and audit trail are unchanged after rejection.
        """
        # Create a case in PGRC bureau
        cid = self._create_test_case(client, seed_data, init_status=CaseStatusEnum.PENDING)
        # The helper creates cases in RB; get the case detail to confirm
        admin_h = auth_header(seed_data["admin"])
        pre = client.get(f"/api/v1/cases/{cid}", headers=admin_h).json()
        assert pre["bureau_id"] == seed_data["b_rb"].id

        # Count existing actions before the rejected transfer attempt
        actions_before = client.get(f"/api/v1/cases/{cid}/actions", headers=admin_h).json()

        # PGRC officer attempts transfer of RB case -> 403
        res = client.post(
            f"/api/v1/cases/{cid}/transfer",
            json={"to_bureau_id": seed_data["b_pgrc"].id, "remarks": "Hijack attempt"},
            headers=auth_header(seed_data["officer_pgrc"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

        # Verify case is unchanged
        post = client.get(f"/api/v1/cases/{cid}", headers=admin_h).json()
        assert post["bureau_id"] == seed_data["b_rb"].id
        assert post["status"] == "PENDING"

        # No new audit action was added
        actions_after = client.get(f"/api/v1/cases/{cid}/actions", headers=admin_h).json()
        assert len(actions_after) == len(actions_before)

    def test_regional_officer_cannot_transfer_other_region_case(self, client, db_session, seed_data):
        """REGIONAL_OFFICER cannot transfer a case for an institution outside their region (403).
        Verify: status, bureau, and audit trail are unchanged after rejection.
        """
        # Create a case linked to a Northern institution (inst_n, region_id=1)
        admin_h = auth_header(seed_data["admin"])
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "summary": "Cross-region transfer test",
        }
        res = client.post("/api/v1/cases", json=payload, headers=admin_h)
        assert res.status_code == 201
        cid = res.json()["id"]

        actions_before = client.get(f"/api/v1/cases/{cid}/actions", headers=admin_h).json()

        # Southern regional officer attempts transfer of Northern case -> 403
        res = client.post(
            f"/api/v1/cases/{cid}/transfer",
            json={"to_bureau_id": seed_data["b_pgrc"].id, "remarks": "Cross-region attempt"},
            headers=auth_header(seed_data["reg_south"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

        # Verify case is unchanged
        post = client.get(f"/api/v1/cases/{cid}", headers=admin_h).json()
        assert post["bureau_id"] == seed_data["b_rb"].id
        assert post["status"] == "PENDING"

        # No new audit action was added
        actions_after = client.get(f"/api/v1/cases/{cid}/actions", headers=admin_h).json()
        assert len(actions_after) == len(actions_before)

    def test_transfer_to_nonexistent_bureau_returns_422(self, client, seed_data):
        """Transfer to a nonexistent destination bureau returns 422.
        Verify: status, bureau, and audit trail are unchanged after rejection.
        """
        cid = self._create_test_case(client, seed_data, init_status=CaseStatusEnum.PENDING)
        admin_h = auth_header(seed_data["admin"])
        actions_before = client.get(f"/api/v1/cases/{cid}/actions", headers=admin_h).json()

        # RB officer transfers to bureau ID 99999 (does not exist) -> 422
        res = client.post(
            f"/api/v1/cases/{cid}/transfer",
            json={"to_bureau_id": 99999, "remarks": "Transfer to ghost bureau"},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "UNPROCESSABLE_ENTITY"

        # Verify case is unchanged
        post = client.get(f"/api/v1/cases/{cid}", headers=admin_h).json()
        assert post["bureau_id"] == seed_data["b_rb"].id
        assert post["status"] == "PENDING"

        # No new audit action was added
        actions_after = client.get(f"/api/v1/cases/{cid}/actions", headers=admin_h).json()
        assert len(actions_after) == len(actions_before)

    def test_transfer_audit_history_records_origin_and_destination(self, client, db_session, seed_data):
        """Verify the transfer CaseAction reliably records:
        - Origin bureau (CaseAction.bureau_id = source bureau before mutation)
        - Destination bureau (Case.bureau_id after transfer = destination)
        - Acting user (CaseAction.actor_id)
        - Transfer reason (CaseAction.remarks)
        - Previous and resulting status (from_status / to_status)
        """
        cid = self._create_test_case(client, seed_data, init_status=CaseStatusEnum.PENDING)
        admin_h = auth_header(seed_data["admin"])

        origin_bureau_id = seed_data["b_rb"].id
        dest_bureau_id = seed_data["b_pgrc"].id

        # Perform the transfer
        res = client.post(
            f"/api/v1/cases/{cid}/transfer",
            json={"to_bureau_id": dest_bureau_id, "remarks": "Reassigning to PGRC for grievance handling"},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        data = res.json()

        # Case now belongs to destination bureau
        assert data["bureau_id"] == dest_bureau_id
        assert data["status"] == "TRANSFERRED"

        # Inspect the TRANSFERRED action in audit trail
        actions = client.get(f"/api/v1/cases/{cid}/actions", headers=admin_h).json()
        transfer_actions = [a for a in actions if a["action_type"] == "TRANSFERRED"]
        assert len(transfer_actions) == 1

        t_act = transfer_actions[0]
        # Origin bureau is recorded in action.bureau_id
        assert t_act["bureau_id"] == origin_bureau_id
        # Destination is the updated case.bureau_id (verified above)
        # Acting user
        assert t_act["actor_id"] == seed_data["officer_rb"].id
        # Transfer reason
        assert t_act["remarks"] == "Reassigning to PGRC for grievance handling"
        # Status transition
        assert t_act["from_status"] == "PENDING"
        assert t_act["to_status"] == "TRANSFERRED"


class TestCaseAssignmentAndAudit:
    def test_assignment_to_matching_officer(self, client, seed_data):
        headers = auth_header(seed_data["admin"])
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "summary": "Assignment test",
        }
        res = client.post("/api/v1/cases", json=payload, headers=headers)
        cid = res.json()["id"]

        # Assign to RB officer (matching bureau)
        res_assign = client.patch(
            f"/api/v1/cases/{cid}",
            json={"assigned_officer_id": seed_data["officer_rb"].id, "remarks": "Assigned for review"},
            headers=headers,
        )
        assert res_assign.status_code == 200
        assert res_assign.json()["assigned_officer_id"] == seed_data["officer_rb"].id
        assert res_assign.json()["assigned_officer_name"] == "RB Officer"

    def test_assignment_to_mismatched_officer_fails_422(self, client, seed_data):
        headers = auth_header(seed_data["admin"])
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "summary": "Mismatched assignment test",
        }
        res = client.post("/api/v1/cases", json=payload, headers=headers)
        cid = res.json()["id"]

        # Assign RB case to PGRC officer -> 422
        res_assign = client.patch(
            f"/api/v1/cases/{cid}",
            json={"assigned_officer_id": seed_data["officer_pgrc"].id},
            headers=headers,
        )
        assert res_assign.status_code == 422
        assert get_error(res_assign)["code"] == "UNPROCESSABLE_ENTITY"

    def test_assignment_to_inactive_officer_fails_422(self, client, seed_data):
        headers = auth_header(seed_data["admin"])
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "summary": "Inactive assignment test",
        }
        res = client.post("/api/v1/cases", json=payload, headers=headers)
        cid = res.json()["id"]

        res_assign = client.patch(
            f"/api/v1/cases/{cid}",
            json={"assigned_officer_id": seed_data["inactive"].id},
            headers=headers,
        )
        assert res_assign.status_code == 422

    def test_case_actions_audit_trail_and_append_only(self, client, db_session, seed_data):
        headers = auth_header(seed_data["admin"])
        res = client.post(
            "/api/v1/cases",
            json={"bureau_id": seed_data["b_rb"].id, "summary": "Audit log test"},
            headers=headers,
        )
        cid = res.json()["id"]

        # Add manual note action
        client.post(
            f"/api/v1/cases/{cid}/actions",
            json={"action_type": "NOTE", "remarks": "Complainant contacted via phone"},
            headers=headers,
        )

        # Get actions
        res_acts = client.get(f"/api/v1/cases/{cid}/actions", headers=headers)
        assert res_acts.status_code == 200
        actions = res_acts.json()
        assert len(actions) == 2
        assert actions[0]["action_type"] == "CREATED"
        assert actions[1]["action_type"] == "NOTE"
        assert actions[1]["remarks"] == "Complainant contacted via phone"

        # Verify append-only enforcement: attempting to update or delete action in ORM throws ValueError
        act_obj = db_session.query(CaseAction).filter(CaseAction.id == actions[0]["id"]).first()
        act_obj.remarks = "Tampered remark"
        with pytest.raises(ValueError, match="append-only"):
            db_session.commit()
        db_session.rollback()

        with pytest.raises(ValueError, match="append-only"):
            db_session.delete(act_obj)
            db_session.commit()
        db_session.rollback()

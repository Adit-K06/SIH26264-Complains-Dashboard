"""Tests for Phase 4D: Overlap Detection and Case Linking.

Covers:
  1.  Listing overlap flags and verifying response fields.
  2.  Filtering by state, institution, and tier.
  3.  Pagination and invalid parameters.
  4.  Creating overlap candidates through the scan workflow.
  5.  Repeated scans without duplicate flags.
  6.  Missing or insufficient institution data.
  7.  Confirming and dismissing eligible flags.
  8.  Invalid and repeated decisions.
  9.  Case-link creation and retrieval.
  10. Rejection of self-links, duplicate links, and nonexistent cases.
  11. Unauthorized users and cross-bureau/cross-region attempts.
  12. SENIOR_MGMT mutation restrictions.
  13. Transaction rollback and consistency after failures.
  14. Preservation of all existing Phase 1-4C behavior.
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
    CaseLink,
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
    CaseStatusEnum,
    OPEN_CASE_STATUSES,
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
def seed_data(db_session):
    """Seed regions, bureaus, categories, institutions, and users."""
    # Regions
    r_north = Region(id=1, name="Northern")
    r_south = Region(id=2, name="Southern")
    db_session.add_all([r_north, r_south])
    db_session.flush()

    # Bureaus
    b_rb = Bureau(id=1, code="RB", name="Research Bureau")
    b_pgrc = Bureau(id=2, code="PGRC", name="Public Grievance Redressal Cell")
    b_approval = Bureau(id=3, code="APPROVAL", name="Approval Bureau")
    db_session.add_all([b_rb, b_pgrc, b_approval])
    db_session.flush()

    # Categories
    c_adm = Category(id=1, name="Admission irregularity")
    c_fee = Category(id=2, name="Fee refund")
    db_session.add_all([c_adm, c_fee])
    db_session.flush()

    # Institutions
    inst_n = Institution(
        id=1,
        aicte_permanent_id="1-1001",
        name="Northern Tech Institute",
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
        name="Admin User",
        email="admin@test.local",
        password_hash=hash_password("admin123"),
        role=RoleEnum.ADMIN,
        active=True,
    )
    officer_rb = User(
        id=2,
        name="RB Officer",
        email="rb.officer@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.BUREAU_OFFICER,
        bureau_id=b_rb.id,
        active=True,
    )
    officer_pgrc = User(
        id=3,
        name="PGRC Officer",
        email="pgrc.officer@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.BUREAU_OFFICER,
        bureau_id=b_pgrc.id,
        active=True,
    )
    reg_north = User(
        id=4,
        name="North Regional Officer",
        email="north.officer@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.REGIONAL_OFFICER,
        region_id=r_north.id,
        active=True,
    )
    reg_south = User(
        id=5,
        name="South Regional Officer",
        email="south.officer@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.REGIONAL_OFFICER,
        region_id=r_south.id,
        active=True,
    )
    mgmt = User(
        id=6,
        name="Senior Director",
        email="mgmt@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.SENIOR_MGMT,
        active=True,
    )
    db_session.add_all([admin, officer_rb, officer_pgrc, reg_north, reg_south, mgmt])
    db_session.flush()

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
        "officer_rb": officer_rb,
        "officer_pgrc": officer_pgrc,
        "reg_north": reg_north,
        "reg_south": reg_south,
        "mgmt": mgmt,
        "b_rb": b_rb,
        "b_pgrc": b_pgrc,
        "b_approval": b_approval,
        "c_adm": c_adm,
        "c_fee": c_fee,
        "inst_n": inst_n,
        "inst_s": inst_s,
        "r_north": r_north,
        "r_south": r_south,
    }


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def get_error(res) -> dict:
    body = res.json()
    if "error" in body:
        return body["error"]
    if "detail" in body and isinstance(body["detail"], dict) and "error" in body["detail"]:
        return body["detail"]["error"]
    return body.get("detail", {})


# ---------------------------------------------------------------------------
# Helper to create test cases in the DB
# ---------------------------------------------------------------------------

def _create_case(
    db_session, bureau_id, institution_id=None, case_no="TEST-001",
    status=CaseStatusEnum.PENDING, category_id=None, summary="Test case",
) -> Case:
    case = Case(
        case_no=case_no,
        bureau_id=bureau_id,
        institution_id=institution_id,
        category_id=category_id,
        status=status,
        received_on=date.today(),
        last_action_on=datetime.now(timezone.utc),
        last_action_text="Created for test",
        expected_disposal_on=date.today() + timedelta(days=30),
        priority=PriorityEnum.MEDIUM,
        summary=summary,
        source="SYNTHETIC",
    )
    db_session.add(case)
    db_session.flush()

    action = CaseAction(
        case_id=case.id,
        actor_id=None,
        bureau_id=bureau_id,
        action_type=ActionTypeEnum.CREATED,
        from_status=None,
        to_status=status,
        remarks="Created for test",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(action)
    db_session.flush()
    return case


# ---------------------------------------------------------------------------
# Test class: Listing and Filtering
# ---------------------------------------------------------------------------

class TestOverlapListing:
    def test_list_overlaps_empty(self, client, seed_data):
        res = client.get("/api/v1/overlaps", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["page_size"] == 5

    def test_list_overlaps_returns_expected_fields(self, client, seed_data, db_session):
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            case_a=None,
            case_b=None,
            tier=OverlapTierEnum.A,
            score=0.0,
            reasons=["DIFFERENT_BUREAU"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.get("/api/v1/overlaps", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["id"] == flag.id
        assert item["institution_id"] == seed_data["inst_n"].id
        assert item["institution_name"] == "Northern Tech Institute"
        assert item["tier"] == "A"
        assert item["score"] == 0.0
        assert item["reasons"] == ["DIFFERENT_BUREAU"]
        assert item["state"] == "OPEN"
        assert item["case_a_id"] is None
        assert item["case_b_id"] is None

    def test_filter_by_state_confirmed(self, client, seed_data, db_session):
        flag_open = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[], state=OverlapStateEnum.OPEN,
        )
        flag_confirmed = OverlapFlag(
            institution_id=seed_data["inst_s"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[], state=OverlapStateEnum.CONFIRMED,
        )
        db_session.add_all([flag_open, flag_confirmed])
        db_session.commit()

        # Default state=OPEN
        res = client.get("/api/v1/overlaps", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["state"] == "OPEN"

        # Explicit CONFIRMED
        res = client.get("/api/v1/overlaps?state=CONFIRMED", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["state"] == "CONFIRMED"

    def test_filter_by_institution(self, client, seed_data, db_session):
        flag1 = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[], state=OverlapStateEnum.OPEN,
        )
        flag2 = OverlapFlag(
            institution_id=seed_data["inst_s"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[], state=OverlapStateEnum.OPEN,
        )
        db_session.add_all([flag1, flag2])
        db_session.commit()

        res = client.get(
            f"/api/v1/overlaps?institution_id={seed_data['inst_n'].id}",
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["institution_id"] == seed_data["inst_n"].id

    def test_filter_by_tier(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "TIER-B-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "TIER-B-2")
        db_session.flush()

        flag_a = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[], state=OverlapStateEnum.OPEN,
        )
        flag_b = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            case_a=c1.id, case_b=c2.id,
            tier=OverlapTierEnum.B, score=0.65, reasons=["HIGH_TEXT_SIMILARITY"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add_all([flag_a, flag_b])
        db_session.commit()

        res = client.get("/api/v1/overlaps?tier=B", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["tier"] == "B"

        res = client.get("/api/v1/overlaps?tier=A", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["tier"] == "A"

    def test_invalid_state_filter(self, client, seed_data):
        res = client.get("/api/v1/overlaps?state=INVALID", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 422
        assert get_error(res)["code"] == "UNPROCESSABLE_ENTITY"

    def test_invalid_tier_filter(self, client, seed_data):
        res = client.get("/api/v1/overlaps?tier=X", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 422
        assert get_error(res)["code"] == "UNPROCESSABLE_ENTITY"

    def test_invalid_institution_id(self, client, seed_data):
        res = client.get("/api/v1/overlaps?institution_id=9999", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 422

    def test_pagination(self, client, seed_data, db_session):
        # Create 7 distinct institutions to respect the unique constraint on (institution_id, Tier A)
        for i in range(7):
            inst = Institution(
                id=100 + i,
                aicte_permanent_id=f"1-PAGE-{i}",
                name=f"Pagination Tech {i}",
                region_id=seed_data["r_north"].id,
                status="APPROVED",
            )
            db_session.add(inst)
            db_session.flush()

            flag = OverlapFlag(
                institution_id=inst.id,
                case_a=None,
                case_b=None,
                tier=OverlapTierEnum.A,
                score=0.0,
                reasons=[],
                state=OverlapStateEnum.OPEN,
            )
            db_session.add(flag)
        db_session.commit()

        # Default page_size=5
        res = client.get("/api/v1/overlaps", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 5
        assert data["total"] == 7
        assert data["page"] == 1

        # Page 2
        res = client.get("/api/v1/overlaps?page=2", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 2
        assert data["total"] == 7
        assert data["page"] == 2

    def test_unauthenticated_request_401(self, client, seed_data):
        res = client.get("/api/v1/overlaps")
        assert res.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Test class: Overlap Scan
# ---------------------------------------------------------------------------

class TestOverlapScan:
    def test_scan_no_overlaps(self, client, seed_data, db_session):
        # One case in one bureau — no overlap
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "SCAN-001")
        db_session.commit()

        res = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["new_flags"] == 0

    def test_scan_detects_tier_a_overlap(self, client, seed_data, db_session):
        # Same institution, two different bureaus with open cases
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "SCAN-A1")
        _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "SCAN-A2")
        db_session.commit()

        res = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["new_flags"] >= 1

        # Verify flag exists in DB
        flags = db_session.query(OverlapFlag).filter(
            OverlapFlag.institution_id == seed_data["inst_n"].id,
            OverlapFlag.tier == OverlapTierEnum.A,
        ).all()
        assert len(flags) == 1
        assert flags[0].state == OverlapStateEnum.OPEN

    def test_scan_specific_institution(self, client, seed_data, db_session):
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "SCAN-SI1")
        _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "SCAN-SI2")
        # Southern institution has only one bureau
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_s"].id, "SCAN-SI3")
        db_session.commit()

        # Scan only northern institution
        res = client.post(
            f"/api/v1/overlaps/scan?institution_id={seed_data['inst_n'].id}",
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        assert res.json()["new_flags"] >= 1

        # No flag for southern institution
        flags_s = db_session.query(OverlapFlag).filter(
            OverlapFlag.institution_id == seed_data["inst_s"].id,
        ).all()
        assert len(flags_s) == 0

    def test_repeated_scan_no_duplicate_flags(self, client, seed_data, db_session):
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "DEDUP-1")
        _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "DEDUP-2")
        db_session.commit()

        # First scan
        res1 = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["admin"]))
        assert res1.status_code == 200
        first_count = res1.json()["new_flags"]
        assert first_count >= 1

        # Second scan — should not create duplicates
        res2 = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["admin"]))
        assert res2.status_code == 200
        assert res2.json()["new_flags"] == 0

        # Total flags remains the same
        total = db_session.query(OverlapFlag).filter(
            OverlapFlag.institution_id == seed_data["inst_n"].id,
        ).count()
        assert total == first_count

    def test_scan_ignores_disposed_cases(self, client, seed_data, db_session):
        # One open, one disposed — not 2 distinct bureaus with open cases
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "DISP-1",
                      status=CaseStatusEnum.PENDING)
        _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "DISP-2",
                      status=CaseStatusEnum.DISPOSED)
        db_session.commit()

        res = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["new_flags"] == 0

    def test_scan_invalid_institution_id(self, client, seed_data):
        res = client.post(
            "/api/v1/overlaps/scan?institution_id=9999",
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422

    def test_scan_senior_mgmt_forbidden(self, client, seed_data):
        res = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["mgmt"]))
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

    def test_scan_bureau_officer_allowed(self, client, seed_data, db_session):
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "BO-SCAN-1")
        _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "BO-SCAN-2")
        db_session.commit()

        res = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["officer_rb"]))
        assert res.status_code == 200
        assert res.json()["new_flags"] >= 1

    def test_scan_regional_officer_scope_enforcement(self, client, seed_data, db_session):
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_s"].id, "REG-S1")
        _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_s"].id, "REG-S2")
        db_session.commit()

        # North regional officer scanning south institution -> 403
        res = client.post(
            f"/api/v1/overlaps/scan?institution_id={seed_data['inst_s'].id}",
            headers=auth_header(seed_data["reg_north"]),
        )
        assert res.status_code == 403

    def test_scan_no_institution_cases(self, client, seed_data, db_session):
        """Cases without institution_id should not trigger overlaps."""
        _create_case(db_session, seed_data["b_rb"].id, None, "NO-INST-1")
        _create_case(db_session, seed_data["b_pgrc"].id, None, "NO-INST-2")
        db_session.commit()

        res = client.post("/api/v1/overlaps/scan", headers=auth_header(seed_data["admin"]))
        assert res.status_code == 200
        assert res.json()["new_flags"] == 0


# ---------------------------------------------------------------------------
# Test class: Confirm (Link) and Dismiss
# ---------------------------------------------------------------------------

class TestOverlapDecisions:
    def test_confirm_and_link_tier_a(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "LINK-A1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "LINK-A2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=["DIFFERENT_BUREAU"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id, "note": "Confirmed overlap"},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "CONFIRMED"
        assert data["decided_by"] == seed_data["admin"].id

        # Verify CaseLink records
        links = db_session.query(CaseLink).all()
        assert len(links) == 2
        group_ids = set(link.group_id for link in links)
        assert len(group_ids) == 1  # Same group
        case_ids = set(link.case_id for link in links)
        assert c1.id in case_ids
        assert c2.id in case_ids

        # Verify LINKED audit actions
        linked_actions = db_session.query(CaseAction).filter(
            CaseAction.action_type == ActionTypeEnum.LINKED,
        ).all()
        assert len(linked_actions) == 2

        # Verify cases have link_group_id set
        db_session.refresh(c1)
        db_session.refresh(c2)
        assert c1.link_group_id is not None
        assert c1.link_group_id == c2.link_group_id

    def test_confirm_and_link_tier_b(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "LINK-B1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "LINK-B2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            case_a=c1.id, case_b=c2.id,
            tier=OverlapTierEnum.B, score=0.72,
            reasons=["HIGH_TEXT_SIMILARITY", "SAME_CATEGORY"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "CONFIRMED"

        # Exactly 2 case links for the pair
        links = db_session.query(CaseLink).all()
        assert len(links) == 2

    def test_dismiss_overlap(self, client, seed_data, db_session):
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[], state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/dismiss",
            json={},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "DISMISSED"
        assert data["decided_by"] == seed_data["admin"].id

    def test_link_nonexistent_flag_404(self, client, seed_data):
        res = client.post(
            "/api/v1/overlaps/9999/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 404

    def test_dismiss_nonexistent_flag_404(self, client, seed_data):
        res = client.post(
            "/api/v1/overlaps/9999/dismiss",
            json={},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 404

    def test_link_already_confirmed_409(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "DUP-C1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "DUP-C2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.CONFIRMED,
            decided_by=seed_data["admin"].id,
            decided_at=datetime.now(timezone.utc),
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 409
        assert get_error(res)["code"] == "CONFLICT"

    def test_dismiss_already_dismissed_409(self, client, seed_data, db_session):
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.DISMISSED,
            decided_by=seed_data["admin"].id,
            decided_at=datetime.now(timezone.utc),
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/dismiss",
            json={},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 409
        assert get_error(res)["code"] == "CONFLICT"

    def test_link_invalid_lead_bureau_422(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "INV-LEAD-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "INV-LEAD-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": 9999},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422

    def test_link_insufficient_cases_422(self, client, seed_data, db_session):
        """Tier A flag where institution has only 1 open case — cannot link."""
        _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "INSUF-1")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# Test class: RBAC for Overlap Decisions
# ---------------------------------------------------------------------------

class TestOverlapRBAC:
    def test_senior_mgmt_cannot_link(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "MGMT-L1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "MGMT-L2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["mgmt"]),
        )
        assert res.status_code == 403

        # Flag remains OPEN
        db_session.refresh(flag)
        assert flag.state == OverlapStateEnum.OPEN

    def test_senior_mgmt_cannot_dismiss(self, client, seed_data, db_session):
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/dismiss",
            json={},
            headers=auth_header(seed_data["mgmt"]),
        )
        assert res.status_code == 403

    def test_bureau_officer_cannot_link_cross_bureau_tier_a(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "BO-XA-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "BO-XA-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # RB officer attempts to link cross-bureau Tier A overlap
        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

        # Verify flag, cases, links, and audit history are completely unchanged
        db_session.refresh(flag)
        assert flag.state == OverlapStateEnum.OPEN
        assert flag.decided_by is None
        assert flag.decided_at is None

        db_session.refresh(c1)
        db_session.refresh(c2)
        assert c1.link_group_id is None
        assert c2.link_group_id is None

        assert db_session.query(CaseLink).count() == 0
        assert db_session.query(CaseAction).filter(CaseAction.action_type == ActionTypeEnum.LINKED).count() == 0

    def test_admin_can_link_cross_bureau_tier_a(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "ADM-XA-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "ADM-XA-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "CONFIRMED"
        assert db_session.query(CaseLink).count() == 2

    def test_bureau_officer_cannot_link_cross_bureau_tier_b(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "BO-XB-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "BO-XB-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            case_a=c1.id, case_b=c2.id,
            tier=OverlapTierEnum.B, score=0.75, reasons=["HIGH_TEXT_SIMILARITY"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # RB officer attempts to link pair containing PGRC case
        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

        db_session.refresh(flag)
        assert flag.state == OverlapStateEnum.OPEN
        assert db_session.query(CaseLink).count() == 0

    def test_bureau_officer_can_link_same_bureau_tier_b(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "BO-SB-1")
        c2 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "BO-SB-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            case_a=c1.id, case_b=c2.id,
            tier=OverlapTierEnum.B, score=0.82, reasons=["HIGH_TEXT_SIMILARITY"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # RB officer links pair where both cases belong to RB
        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["state"] == "CONFIRMED"
        assert db_session.query(CaseLink).count() == 2

    def test_bureau_officer_can_dismiss_own_bureau_overlap(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "BO-DISM-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "BO-DISM-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # RB officer can dismiss an overlap involving RB
        res = client.post(
            f"/api/v1/overlaps/{flag.id}/dismiss",
            json={},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        assert res.json()["state"] == "DISMISSED"

    def test_tier_b_self_link_rejected_422(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "SELF-1")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            case_a=c1.id, case_b=c1.id,
            tier=OverlapTierEnum.B, score=1.0, reasons=["SELF"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "UNPROCESSABLE_ENTITY"

    def test_link_transaction_rollback_on_commit_failure(self, client, seed_data, db_session, monkeypatch):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "ROLL-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "ROLL-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=["DIFFERENT_BUREAU"],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        from sqlalchemy.orm import Session
        orig_commit = Session.commit

        def failing_commit(self):
            raise RuntimeError("Simulated DB failure during commit")

        monkeypatch.setattr(Session, "commit", failing_commit)

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 400
        assert get_error(res)["code"] == "BAD_REQUEST"

        monkeypatch.undo()

        # Verify state is completely preserved
        db_session.rollback()
        db_session.refresh(flag)
        assert flag.state == OverlapStateEnum.OPEN
        assert flag.decided_by is None
        assert db_session.query(CaseLink).count() == 0
        assert db_session.query(CaseAction).filter(CaseAction.action_type == ActionTypeEnum.LINKED).count() == 0

    def test_bureau_officer_cannot_link_other_bureau_overlap(self, client, seed_data, db_session):
        # Only institution with PGRC cases, no RB cases
        c1 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_s"].id, "BO-OTHER-1")
        c2 = _create_case(db_session, seed_data["b_approval"].id, seed_data["inst_s"].id, "BO-OTHER-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_s"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # RB officer has NO cases for inst_s
        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_pgrc"].id},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 403

    def test_regional_officer_can_act_own_region(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "REG-OWN-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "REG-OWN-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # North officer for northern institution
        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["reg_north"]),
        )
        assert res.status_code == 200

    def test_regional_officer_cannot_act_other_region(self, client, seed_data, db_session):
        flag = OverlapFlag(
            institution_id=seed_data["inst_s"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # North officer for southern institution -> 403
        res = client.post(
            f"/api/v1/overlaps/{flag.id}/dismiss",
            json={},
            headers=auth_header(seed_data["reg_north"]),
        )
        assert res.status_code == 403

    def test_senior_mgmt_can_read_overlaps(self, client, seed_data, db_session):
        """SENIOR_MGMT is read-only but can list overlaps."""
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[], state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.get("/api/v1/overlaps", headers=auth_header(seed_data["mgmt"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1


# ---------------------------------------------------------------------------
# Test class: Case Linking Details
# ---------------------------------------------------------------------------

class TestCaseLinking:
    def test_link_creates_audit_actions(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "AUDIT-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "AUDIT-2")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id, "note": "Linking for audit"},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200

        # Each case should have a LINKED action
        for c in [c1, c2]:
            actions = db_session.query(CaseAction).filter(
                CaseAction.case_id == c.id,
                CaseAction.action_type == ActionTypeEnum.LINKED,
            ).all()
            assert len(actions) == 1
            assert actions[0].actor_id == seed_data["admin"].id
            assert actions[0].from_status == c.status
            assert actions[0].to_status == c.status  # Status doesn't change

    def test_link_preserves_case_status(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "STATUS-1",
                          status=CaseStatusEnum.UNDER_PROCESS)
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "STATUS-2",
                          status=CaseStatusEnum.PENDING)
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200

        # Statuses unchanged
        db_session.refresh(c1)
        db_session.refresh(c2)
        assert c1.status == CaseStatusEnum.UNDER_PROCESS
        assert c2.status == CaseStatusEnum.PENDING

    def test_link_group_id_consistency(self, client, seed_data, db_session):
        c1 = _create_case(db_session, seed_data["b_rb"].id, seed_data["inst_n"].id, "GROUP-1")
        c2 = _create_case(db_session, seed_data["b_pgrc"].id, seed_data["inst_n"].id, "GROUP-2")
        c3 = _create_case(db_session, seed_data["b_approval"].id, seed_data["inst_n"].id, "GROUP-3")
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/link",
            json={"lead_bureau_id": seed_data["b_rb"].id},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200

        # All 3 cases should have the same link_group_id
        db_session.refresh(c1)
        db_session.refresh(c2)
        db_session.refresh(c3)
        assert c1.link_group_id is not None
        assert c1.link_group_id == c2.link_group_id == c3.link_group_id

        # 3 CaseLink records
        links = db_session.query(CaseLink).filter(
            CaseLink.group_id == c1.link_group_id,
        ).all()
        assert len(links) == 3

    def test_dismiss_does_not_create_links(self, client, seed_data, db_session):
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/dismiss",
            json={},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200

        links = db_session.query(CaseLink).all()
        assert len(links) == 0

    def test_dismiss_does_not_create_audit_actions(self, client, seed_data, db_session):
        flag = OverlapFlag(
            institution_id=seed_data["inst_n"].id,
            tier=OverlapTierEnum.A, score=0.0, reasons=[],
            state=OverlapStateEnum.OPEN,
        )
        db_session.add(flag)
        db_session.commit()

        # Count existing actions
        before_count = db_session.query(CaseAction).count()

        res = client.post(
            f"/api/v1/overlaps/{flag.id}/dismiss",
            json={},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200

        after_count = db_session.query(CaseAction).count()
        assert after_count == before_count  # No new audit actions for dismiss

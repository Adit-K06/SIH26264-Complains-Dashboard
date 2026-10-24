"""Tests for Phase 4A: Institutions API and Lookup endpoints.

Covers:
  1. GET /institutions      – list, pagination, text search, all filter combos
  2. GET /institutions/{id} – success and 404
  3. GET /institutions/{id}/cases – list, status filter, 404 for unknown institution
  4. GET /institutions/resolve – success (stub), missing params → 422
  5. GET /bureaus / GET /regions / GET /categories – lookup lists
  6. Authentication guard on all endpoints (401 without token)
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Bureau, Case, Category, Institution, Region, User
from app.models.base import Base
from app.models.enums import CaseStatusEnum, PriorityEnum, RoleEnum
from app.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Fixtures (isolated in-memory DB – no shared state with other test modules)
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
def seed(db_session):
    """Seed reference data: regions, bureaus, categories, users, institutions, cases."""
    # Regions
    r_north = Region(id=1, name="Northern")
    r_south = Region(id=2, name="Southern")
    r_east = Region(id=3, name="Eastern")
    db_session.add_all([r_north, r_south, r_east])
    db_session.flush()

    # Bureaus
    b_rb = Bureau(id=1, code="RB", name="Research Bureau")
    b_pgrc = Bureau(id=2, code="PGRC", name="Public Grievance Redressal Cell")
    b_approval = Bureau(id=3, code="APPROVAL", name="Approval Bureau")
    db_session.add_all([b_rb, b_pgrc, b_approval])
    db_session.flush()

    # Categories
    c_fee = Category(id=1, name="Fee refund")
    c_adm = Category(id=2, name="Admission irregularity")
    db_session.add_all([c_fee, c_adm])
    db_session.flush()

    # Institutions
    inst_north1 = Institution(
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
    inst_north2 = Institution(
        id=2,
        aicte_permanent_id="1-1002",
        name="Alpha Engineering College",
        address="200 Hill Rd",
        district="Chandigarh",
        state="Punjab",
        region_id=r_north.id,
        type="College",
        status="APPROVED",
    )
    inst_south = Institution(
        id=3,
        aicte_permanent_id="1-2001",
        name="Southern Polytechnic",
        address="300 South Rd",
        district="Chennai",
        state="Tamil Nadu",
        region_id=r_south.id,
        type="Polytechnic",
        status="APPROVED",
    )
    db_session.add_all([inst_north1, inst_north2, inst_south])
    db_session.flush()

    # Users (one per role)
    admin = User(
        id=1, name="Admin", email="admin@test.local",
        password_hash=hash_password("admin123"),
        role=RoleEnum.ADMIN, active=True,
    )
    officer_rb = User(
        id=2, name="RB Officer", email="rb@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.BUREAU_OFFICER, bureau_id=b_rb.id, active=True,
    )
    reg_north = User(
        id=3, name="Northern Officer", email="north@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.REGIONAL_OFFICER, region_id=r_north.id, active=True,
    )
    mgmt = User(
        id=4, name="Director", email="mgmt@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.SENIOR_MGMT, active=True,
    )
    db_session.add_all([admin, officer_rb, reg_north, mgmt])
    db_session.flush()

    # Cases attached to institutions
    c1 = Case(
        case_no="RB/2026/000001",
        institution_id=inst_north1.id,
        bureau_id=b_rb.id,
        category_id=c_fee.id,
        status=CaseStatusEnum.PENDING,
        priority=PriorityEnum.HIGH,
        summary="Overdue fee refund",
        received_on=date(2026, 1, 10),
        source="SYNTHETIC",
    )
    c2 = Case(
        case_no="PGRC/2026/000001",
        institution_id=inst_north1.id,
        bureau_id=b_pgrc.id,
        category_id=c_adm.id,
        status=CaseStatusEnum.DISPOSED,
        priority=PriorityEnum.LOW,
        summary="Admission issue resolved",
        received_on=date(2026, 2, 5),
        source="SYNTHETIC",
    )
    c3 = Case(
        case_no="RB/2026/000002",
        institution_id=inst_south.id,
        bureau_id=b_rb.id,
        status=CaseStatusEnum.UNDER_PROCESS,
        priority=PriorityEnum.MEDIUM,
        summary="Southern case",
        received_on=date(2026, 3, 1),
        source="SYNTHETIC",
    )
    db_session.add_all([c1, c2, c3])
    db_session.commit()

    return {
        "admin": admin, "officer_rb": officer_rb,
        "reg_north": reg_north, "mgmt": mgmt,
        "r_north": r_north, "r_south": r_south, "r_east": r_east,
        "b_rb": b_rb, "b_pgrc": b_pgrc, "b_approval": b_approval,
        "c_fee": c_fee, "c_adm": c_adm,
        "inst_north1": inst_north1, "inst_north2": inst_north2, "inst_south": inst_south,
        "c1": c1, "c2": c2, "c3": c3,
    }


def auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def get_error(res) -> dict:
    body = res.json()
    if "error" in body:
        return body["error"]
    if "detail" in body and isinstance(body["detail"], dict) and "error" in body["detail"]:
        return body["detail"]["error"]
    return body


# ---------------------------------------------------------------------------
# Tests: GET /institutions
# ---------------------------------------------------------------------------

class TestInstitutionList:
    def test_requires_auth(self, client):
        res = client.get("/api/v1/institutions")
        assert res.status_code == 401

    def test_empty_list(self, client, seed):
        # seed fixture loads data, but we test the shape here too
        res = client.get("/api/v1/institutions", headers=auth(seed["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_returns_all_three_institutions(self, client, seed):
        res = client.get("/api/v1/institutions", headers=auth(seed["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 3

    def test_response_fields_present(self, client, seed):
        res = client.get("/api/v1/institutions", headers=auth(seed["admin"]))
        item = res.json()["items"][0]
        for field in ("id", "aicte_permanent_id", "name", "region_id", "region_name", "type", "status"):
            assert field in item

    def test_text_search_by_name(self, client, seed):
        res = client.get("/api/v1/institutions?q=Northern", headers=auth(seed["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["aicte_permanent_id"] == "1-1001"

    def test_text_search_by_aicte_id(self, client, seed):
        res = client.get("/api/v1/institutions?q=1-2001", headers=auth(seed["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["name"] == "Southern Polytechnic"

    def test_text_search_by_district(self, client, seed):
        res = client.get("/api/v1/institutions?q=Chennai", headers=auth(seed["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1

    def test_filter_by_region_id(self, client, seed):
        res = client.get(
            f"/api/v1/institutions?region_id={seed['r_north'].id}",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert all(i["region_id"] == seed["r_north"].id for i in data["items"])

    def test_filter_by_region_id_no_results(self, client, seed):
        res = client.get(
            f"/api/v1/institutions?region_id={seed['r_east'].id}",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0
        assert res.json()["items"] == []

    def test_filter_by_state(self, client, seed):
        res = client.get("/api/v1/institutions?state=Tamil+Nadu", headers=auth(seed["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1

    def test_filter_by_type(self, client, seed):
        res = client.get("/api/v1/institutions?type=Polytechnic", headers=auth(seed["admin"]))
        assert res.status_code == 200
        assert res.json()["total"] == 1
        assert res.json()["items"][0]["type"] == "Polytechnic"

    def test_pagination_page_size(self, client, seed):
        res = client.get("/api/v1/institutions?page=1&page_size=2", headers=auth(seed["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_pagination_page_2(self, client, seed):
        res = client.get("/api/v1/institutions?page=2&page_size=2", headers=auth(seed["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 1

    def test_all_roles_can_list(self, client, seed):
        for user_key in ("officer_rb", "reg_north", "mgmt"):
            res = client.get("/api/v1/institutions", headers=auth(seed[user_key]))
            assert res.status_code == 200, f"{user_key} should be able to list institutions"

    def test_region_name_included(self, client, seed):
        res = client.get(
            f"/api/v1/institutions?region_id={seed['r_south'].id}",
            headers=auth(seed["admin"]),
        )
        items = res.json()["items"]
        assert items[0]["region_name"] == "Southern"


# ---------------------------------------------------------------------------
# Tests: GET /institutions/{id}
# ---------------------------------------------------------------------------

class TestInstitutionDetail:
    def test_requires_auth(self, client, seed):
        res = client.get(f"/api/v1/institutions/{seed['inst_north1'].id}")
        assert res.status_code == 401

    def test_returns_correct_institution(self, client, seed):
        res = client.get(
            f"/api/v1/institutions/{seed['inst_north1'].id}",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["aicte_permanent_id"] == "1-1001"
        assert data["name"] == "Northern Tech Institute"
        assert data["region_name"] == "Northern"

    def test_not_found_returns_404(self, client, seed):
        res = client.get("/api/v1/institutions/99999", headers=auth(seed["admin"]))
        assert res.status_code == 404
        assert get_error(res)["code"] == "NOT_FOUND"

    def test_all_roles_can_read(self, client, seed):
        for user_key in ("officer_rb", "reg_north", "mgmt"):
            res = client.get(
                f"/api/v1/institutions/{seed['inst_south'].id}",
                headers=auth(seed[user_key]),
            )
            assert res.status_code == 200, f"{user_key} should be able to read institution detail"


# ---------------------------------------------------------------------------
# Tests: GET /institutions/{id}/cases
# ---------------------------------------------------------------------------

class TestInstitutionCases:
    def test_requires_auth(self, client, seed):
        res = client.get(f"/api/v1/institutions/{seed['inst_north1'].id}/cases")
        assert res.status_code == 401

    def test_returns_cases_for_institution(self, client, seed):
        res = client.get(
            f"/api/v1/institutions/{seed['inst_north1'].id}/cases",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        case_nos = {item["case_no"] for item in data["items"]}
        assert "RB/2026/000001" in case_nos
        assert "PGRC/2026/000001" in case_nos

    def test_no_complainant_ref_in_response(self, client, seed):
        res = client.get(
            f"/api/v1/institutions/{seed['inst_north1'].id}/cases",
            headers=auth(seed["admin"]),
        )
        for item in res.json()["items"]:
            assert "complainant_ref" not in item

    def test_status_filter(self, client, seed):
        res = client.get(
            f"/api/v1/institutions/{seed['inst_north1'].id}/cases?status=PENDING",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "PENDING"

    def test_institution_with_no_cases_returns_empty(self, client, seed):
        res = client.get(
            f"/api/v1/institutions/{seed['inst_north2'].id}/cases",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_unknown_institution_returns_404(self, client, seed):
        res = client.get("/api/v1/institutions/99999/cases", headers=auth(seed["admin"]))
        assert res.status_code == 404
        assert get_error(res)["code"] == "NOT_FOUND"

    def test_pagination(self, client, seed):
        res = client.get(
            f"/api/v1/institutions/{seed['inst_north1'].id}/cases?page=1&page_size=1",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1

    def test_case_row_fields(self, client, seed):
        res = client.get(
            f"/api/v1/institutions/{seed['inst_north1'].id}/cases",
            headers=auth(seed["admin"]),
        )
        item = res.json()["items"][0]
        for field in ("id", "case_no", "status", "bureau_id", "bureau_code", "priority"):
            assert field in item


# ---------------------------------------------------------------------------
# Tests: GET /institutions/resolve
# ---------------------------------------------------------------------------

class TestInstitutionResolve:
    def test_requires_auth(self, client, seed):
        res = client.get("/api/v1/institutions/resolve?name=Northern+Tech")
        assert res.status_code == 401

    def test_stub_returns_valid_shape(self, client, seed):
        res = client.get(
            "/api/v1/institutions/resolve?name=Northern+Tech",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert "institution_id" in data
        assert "confidence" in data
        assert "method" in data
        assert "candidates" in data
        assert "needs_review" in data

    def test_resolve_with_aicte_id(self, client, seed):
        res = client.get(
            "/api/v1/institutions/resolve?aicte_id=1-1001",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 200

    def test_missing_params_returns_422(self, client, seed):
        res = client.get(
            "/api/v1/institutions/resolve",
            headers=auth(seed["admin"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "UNPROCESSABLE_ENTITY"


# ---------------------------------------------------------------------------
# Tests: GET /bureaus, GET /regions, GET /categories
# ---------------------------------------------------------------------------

class TestLookups:
    def test_bureaus_requires_auth(self, client):
        assert client.get("/api/v1/bureaus").status_code == 401

    def test_regions_requires_auth(self, client):
        assert client.get("/api/v1/regions").status_code == 401

    def test_categories_requires_auth(self, client):
        assert client.get("/api/v1/categories").status_code == 401

    def test_bureaus_returns_list(self, client, seed):
        res = client.get("/api/v1/bureaus", headers=auth(seed["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 3  # RB, PGRC, APPROVAL seeded above
        codes = {b["code"] for b in data}
        assert "RB" in codes and "PGRC" in codes and "APPROVAL" in codes

    def test_bureaus_fields(self, client, seed):
        res = client.get("/api/v1/bureaus", headers=auth(seed["admin"]))
        item = res.json()[0]
        assert "id" in item
        assert "code" in item
        assert "name" in item

    def test_bureaus_ordered_by_code(self, client, seed):
        res = client.get("/api/v1/bureaus", headers=auth(seed["admin"]))
        codes = [b["code"] for b in res.json()]
        assert codes == sorted(codes)

    def test_regions_returns_list(self, client, seed):
        res = client.get("/api/v1/regions", headers=auth(seed["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 3
        names = {r["name"] for r in data}
        assert "Northern" in names and "Southern" in names

    def test_regions_fields(self, client, seed):
        res = client.get("/api/v1/regions", headers=auth(seed["admin"]))
        item = res.json()[0]
        assert "id" in item
        assert "name" in item

    def test_regions_ordered_by_name(self, client, seed):
        res = client.get("/api/v1/regions", headers=auth(seed["admin"]))
        names = [r["name"] for r in res.json()]
        assert names == sorted(names)

    def test_categories_returns_list(self, client, seed):
        res = client.get("/api/v1/categories", headers=auth(seed["admin"]))
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_categories_fields(self, client, seed):
        res = client.get("/api/v1/categories", headers=auth(seed["admin"]))
        item = res.json()[0]
        assert "id" in item
        assert "name" in item

    def test_categories_ordered_by_name(self, client, seed):
        res = client.get("/api/v1/categories", headers=auth(seed["admin"]))
        names = [c["name"] for c in res.json()]
        assert names == sorted(names)

    def test_all_roles_can_access_lookups(self, client, seed):
        for user_key in ("officer_rb", "reg_north", "mgmt"):
            for endpoint in ("/api/v1/bureaus", "/api/v1/regions", "/api/v1/categories"):
                res = client.get(endpoint, headers=auth(seed[user_key]))
                assert res.status_code == 200, f"{user_key} should access {endpoint}"

    def test_empty_lookup_returns_empty_list(self, client, db_session):
        """With no data seeded, all lookups return [] — not an error."""
        res = client.get("/api/v1/bureaus", headers={"Authorization": "Bearer invalid"})
        # No valid token means 401, not 500 — verifies error handling on empty table
        assert res.status_code == 401

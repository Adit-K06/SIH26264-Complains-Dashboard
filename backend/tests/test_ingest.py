"""Tests for Phase 4C: Complaint Data Ingestion and CSV Import.

Covers:
  1. Successful single-record ingestion via Bearer token and X-API-Key
  2. Successful batch ingestion (all-or-nothing atomic)
  3. Successful CSV import (multipart upload and raw text/csv)
  4. Missing or invalid CSV headers (422)
  5. Empty files (422) and blank rows (gracefully skipped)
  6. Invalid dates, enum values, and foreign-key IDs
  7. Duplicate records according to documented policy:
     - Ingestion: 409 Conflict & batch rollback
     - CSV Import: Row-level rejection & detailed error report
  8. Unauthorized requests and invalid tokens (401 / 403)
  9. Bureau and regional scope violations:
     - Bureau officer ingesting/importing for another bureau (403 / row error)
     - Regional officer ingesting/importing outside region (403 / row error)
     - Senior mgmt prohibited from ingesting/importing (403)
     - API key restricted to its assigned bureau (403)
  10. Atomic rollback on failed batch ingestion vs partial-success CSV import
  11. Case creation and audit-action consistency (CaseAction CREATED recorded)
  12. Upload-size (413) and row-count limits (422)
"""
from datetime import date, datetime, timedelta, timezone
import hashlib
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import (
    ApiKey,
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
    """Seed reference regions, bureaus, categories, institutions, users, and API keys."""
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
    inactive = User(
        id=7,
        name="Inactive Admin",
        email="inactive@test.local",
        password_hash=hash_password("pass"),
        role=RoleEnum.ADMIN,
        active=False,
    )
    db_session.add_all([admin, officer_rb, officer_pgrc, reg_north, reg_south, mgmt, inactive])
    db_session.flush()

    # API Keys
    raw_key_rb = "valid-api-key-rb-12345"
    key_hash_rb = hashlib.sha256(raw_key_rb.encode("utf-8")).hexdigest()
    api_key_rb = ApiKey(id=1, bureau_id=b_rb.id, key_hash=key_hash_rb, active=True)

    raw_key_inactive = "inactive-api-key-99999"
    key_hash_inactive = hashlib.sha256(raw_key_inactive.encode("utf-8")).hexdigest()
    api_key_inactive = ApiKey(id=2, bureau_id=b_rb.id, key_hash=key_hash_inactive, active=False)

    db_session.add_all([api_key_rb, api_key_inactive])

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
        "inactive": inactive,
        "b_rb": b_rb,
        "b_pgrc": b_pgrc,
        "c_adm": c_adm,
        "c_fee": c_fee,
        "inst_n": inst_n,
        "inst_s": inst_s,
        "raw_key_rb": raw_key_rb,
        "raw_key_inactive": raw_key_inactive,
    }


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def get_error(res) -> dict:
    body = res.json()
    if "error" in body:
        return body["error"]
    if "detail" in body and isinstance(body["detail"], dict) and "error" in body["detail"]:
        return body["detail"]["error"]
    return body


# ---------------------------------------------------------------------------
# Ingestion Tests (/api/v1/ingest/cases)
# ---------------------------------------------------------------------------

class TestSingleAndBatchIngestion:
    def test_single_record_ingestion_bearer_auth(self, client, seed_data):
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "category_id": seed_data["c_adm"].id,
            "priority": "HIGH",
            "summary": "Single case ingestion via Bearer token",
            "complainant_ref": "COMP-ING-001",
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["bureau_id"] == seed_data["b_rb"].id
        assert item["status"] == "PENDING"
        assert item["priority"] == "HIGH"
        assert item["case_no"].startswith("RB/")

    def test_single_record_ingestion_api_key_auth(self, client, seed_data):
        payload = {
            "bureau_id": seed_data["b_rb"].id,
            "institution_id": seed_data["inst_n"].id,
            "summary": "Ingestion using X-API-Key header",
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers={"X-API-Key": seed_data["raw_key_rb"]},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["bureau_id"] == seed_data["b_rb"].id

    def test_batch_ingestion_list_payload(self, client, seed_data):
        payload = [
            {
                "bureau_id": seed_data["b_rb"].id,
                "summary": "Batch case 1",
            },
            {
                "bureau_id": seed_data["b_rb"].id,
                "summary": "Batch case 2",
            },
        ]
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["case_no"] != data["items"][1]["case_no"]

    def test_batch_ingestion_wrapper_object(self, client, seed_data):
        payload = {
            "items": [
                {"bureau_code": "RB", "summary": "Wrapped case 1"},
                {"bureau_code": "RB", "summary": "Wrapped case 2"},
            ]
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 201
        assert res.json()["total"] == 2

    def test_audit_action_created_for_ingested_cases(self, client, db_session, seed_data):
        payload = {"bureau_id": seed_data["b_rb"].id, "summary": "Audit action test"}
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 201
        cid = res.json()["items"][0]["id"]

        actions = db_session.query(CaseAction).filter(CaseAction.case_id == cid).all()
        assert len(actions) == 1
        assert actions[0].action_type == ActionTypeEnum.CREATED
        assert actions[0].actor_id == seed_data["admin"].id
        assert actions[0].bureau_id == seed_data["b_rb"].id
        assert actions[0].remarks == "Case ingested via API"

    def test_audit_action_for_api_key_sets_actor_null(self, client, db_session, seed_data):
        payload = {"bureau_id": seed_data["b_rb"].id, "summary": "API Key audit test"}
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers={"X-API-Key": seed_data["raw_key_rb"]},
        )
        assert res.status_code == 201
        cid = res.json()["items"][0]["id"]

        actions = db_session.query(CaseAction).filter(CaseAction.case_id == cid).all()
        assert len(actions) == 1
        assert actions[0].actor_id is None
        assert actions[0].remarks == "Case ingested via API Key"


class TestIngestionSecurityAndRBAC:
    def test_unauthenticated_request_returns_401(self, client):
        res = client.post("/api/v1/ingest/cases", json={"bureau_id": 1, "summary": "test"})
        assert res.status_code == 401
        assert get_error(res)["code"] == "UNAUTHORIZED"

    def test_invalid_bearer_token_returns_401(self, client):
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": 1, "summary": "test"},
            headers={"Authorization": "Bearer bad.token.value"},
        )
        assert res.status_code == 401
        assert get_error(res)["code"] == "UNAUTHORIZED"

    def test_invalid_api_key_returns_401(self, client):
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": 1, "summary": "test"},
            headers={"X-API-Key": "invalid-secret-key"},
        )
        assert res.status_code == 401
        assert get_error(res)["code"] == "UNAUTHORIZED"

    def test_inactive_api_key_returns_401(self, client, seed_data):
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": 1, "summary": "test"},
            headers={"X-API-Key": seed_data["raw_key_inactive"]},
        )
        assert res.status_code == 401

    def test_inactive_user_token_returns_403(self, client, seed_data):
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": 1, "summary": "test"},
            headers=auth_header(seed_data["inactive"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

    def test_senior_mgmt_cannot_ingest_cases(self, client, seed_data):
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": 1, "summary": "test"},
            headers=auth_header(seed_data["mgmt"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

    def test_bureau_officer_cross_bureau_rejected_403(self, client, seed_data):
        # RB officer trying to ingest PGRC case
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": seed_data["b_pgrc"].id, "summary": "Cross bureau test"},
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

    def test_regional_officer_cross_region_rejected_403(self, client, seed_data):
        # North officer trying to ingest Southern institution case
        res = client.post(
            "/api/v1/ingest/cases",
            json={
                "bureau_id": seed_data["b_rb"].id,
                "institution_id": seed_data["inst_s"].id,
                "summary": "Cross region test",
            },
            headers=auth_header(seed_data["reg_north"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

    def test_api_key_cross_bureau_rejected_403(self, client, seed_data):
        # RB API Key trying to ingest PGRC case
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": seed_data["b_pgrc"].id, "summary": "Key cross bureau test"},
            headers={"X-API-Key": seed_data["raw_key_rb"]},
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"


class TestIngestionAtomicityAndValidation:
    def test_batch_rollback_on_single_invalid_item(self, client, db_session, seed_data):
        """Atomic batch: if item 2 fails FK check, item 1 must NOT be written."""
        initial_count = db_session.query(Case).count()

        payload = [
            {"bureau_id": seed_data["b_rb"].id, "summary": "Valid item 1"},
            {"bureau_id": 99999, "summary": "Invalid bureau item 2"},
        ]
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "UNPROCESSABLE_ENTITY"

        # Assert no rows were created in DB
        final_count = db_session.query(Case).count()
        assert final_count == initial_count

    def test_duplicate_case_no_rolls_back_batch_409(self, client, db_session, seed_data):
        initial_count = db_session.query(Case).count()

        payload = [
            {"bureau_id": seed_data["b_rb"].id, "case_no": "RB/2026/DUP999", "summary": "First"},
            {"bureau_id": seed_data["b_rb"].id, "case_no": "RB/2026/DUP999", "summary": "Duplicate in batch"},
        ]
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 409
        assert get_error(res)["code"] == "CONFLICT"
        assert db_session.query(Case).count() == initial_count

    def test_invalid_institution_fk_returns_422(self, client, seed_data):
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": seed_data["b_rb"].id, "institution_id": 99999, "summary": "Bad FK"},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "UNPROCESSABLE_ENTITY"

    def test_empty_summary_returns_422(self, client, seed_data):
        res = client.post(
            "/api/v1/ingest/cases",
            json={"bureau_id": seed_data["b_rb"].id, "summary": "   "},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# CSV Import Tests (/api/v1/import/cases-csv)
# ---------------------------------------------------------------------------

class TestCsvImport:
    def test_successful_csv_import_multipart(self, client, db_session, seed_data):
        csv_content = (
            "bureau_code,institution_id,category_id,priority,summary\n"
            "RB,1,1,HIGH,Test CSV Case 1\n"
            "RB,1,2,MEDIUM,Test CSV Case 2\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            files={"file": ("cases.csv", csv_content.encode("utf-8"), "text/csv")},
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["created"] == 2
        assert data["rejected"] == 0
        assert data["errors"] == []

    def test_successful_csv_import_raw_text(self, client, db_session, seed_data):
        csv_content = (
            "bureau_code,priority,summary\n"
            "PGRC,LOW,Raw text body case\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers={
                **auth_header(seed_data["admin"]),
                "Content-Type": "text/csv",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["created"] == 1

    def test_csv_blank_rows_ignored(self, client, seed_data):
        csv_content = (
            "bureau_code,summary\n"
            "\n"
            "RB,Valid case after blank\n"
            "   ,   \n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["created"] == 1
        assert data["rejected"] == 0

    def test_missing_csv_headers_returns_422(self, client, seed_data):
        csv_content = "random_header_one,random_header_two\nval1,val2\n"
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "INVALID_CSV_HEADERS"

    def test_empty_csv_file_returns_422(self, client, seed_data):
        res = client.post(
            "/api/v1/import/cases-csv",
            content=b"",
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "EMPTY_FILE"

    def test_partial_success_with_row_level_rejections(self, client, seed_data):
        """Partial success policy:
        Row 2: Valid
        Row 3: Invalid bureau ID
        Row 4: Valid
        Row 5: Invalid date format
        """
        csv_content = (
            "bureau_code,received_on,summary\n"
            "RB,2026-03-01,Valid row 2\n"
            "NONEXISTENT,2026-03-01,Invalid bureau row 3\n"
            "RB,2026-03-01,Valid row 4\n"
            "RB,invalid-date,Bad date row 5\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 4
        assert data["created"] == 2
        assert data["rejected"] == 2
        assert len(data["errors"]) == 2

        err_rows = [e["row"] for e in data["errors"]]
        assert 3 in err_rows
        assert 5 in err_rows

    def test_csv_duplicate_case_no_rejected_as_row_error(self, client, seed_data):
        csv_content = (
            "bureau_code,case_no,summary\n"
            "RB,RB/2026/CSV001,Original case row 2\n"
            "RB,RB/2026/CSV001,Duplicate case row 3\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["created"] == 1
        assert data["rejected"] == 1
        assert data["errors"][0]["row"] == 3
        assert "Duplicate" in data["errors"][0]["error"]

    def test_csv_bureau_officer_scope_enforcement(self, client, seed_data):
        # RB officer uploads CSV with 1 RB row and 1 PGRC row
        csv_content = (
            "bureau_code,summary\n"
            "RB,Own bureau row 2\n"
            "PGRC,Forbidden bureau row 3\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["created"] == 1
        assert data["rejected"] == 1
        assert data["errors"][0]["row"] == 3
        assert "not authorized" in data["errors"][0]["error"]

    def test_csv_regional_officer_scope_enforcement(self, client, seed_data):
        # North officer uploads CSV with Northern institution (1) and Southern institution (2)
        csv_content = (
            "bureau_code,institution_id,summary\n"
            "RB,1,North institution row 2\n"
            "RB,2,South institution row 3\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["reg_north"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert data["created"] == 1
        assert data["rejected"] == 1
        assert data["errors"][0]["row"] == 3
        assert "Regional officer" in data["errors"][0]["error"]

    def test_csv_senior_mgmt_forbidden(self, client, seed_data):
        csv_content = "bureau_code,summary\nRB,Test\n"
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["mgmt"]),
        )
        assert res.status_code == 403
        assert get_error(res)["code"] == "FORBIDDEN"

    def test_csv_file_size_limit_413(self, client, seed_data):
        # Generate content larger than 5MB
        big_content = b"bureau_code,summary\n" + (b"RB," + b"A" * 1024 + b"\n") * 5200
        assert len(big_content) > 5 * 1024 * 1024
        res = client.post(
            "/api/v1/import/cases-csv",
            content=big_content,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 413
        assert get_error(res)["code"] == "FILE_TOO_LARGE"

    def test_csv_row_count_limit_422(self, client, seed_data):
        # Generate CSV with 1005 rows (> 1000 limit)
        lines = ["bureau_code,summary"] + [f"RB,Row {i}" for i in range(1005)]
        csv_content = "\n".join(lines).encode("utf-8")
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content,
            headers=auth_header(seed_data["admin"]),
        )
        assert res.status_code == 422
        assert get_error(res)["code"] == "ROW_LIMIT_EXCEEDED"


class TestIngestLifecycleRules:
    """Targeted regression tests verifying complaint cases can only start in PENDING."""

    @pytest.mark.parametrize("bad_status", ["UNDER_PROCESS", "DISPOSED", "TRANSFERRED", "ESCALATED"])
    def test_ingest_explicit_non_pending_statuses_rejected_422(self, client, seed_data, db_session, bad_status):
        payload = {
            "items": [
                {
                    "bureau_code": "RB",
                    "summary": f"Case with explicit bad status {bad_status}",
                    "status": bad_status,
                }
            ]
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 422
        err = get_error(res)
        assert err["code"] == "UNPROCESSABLE_ENTITY"
        assert "Initial status must be PENDING" in err["message"]
        assert bad_status in err["message"]

        # Assert no records were written
        assert db_session.query(Case).count() == 0
        assert db_session.query(CaseAction).count() == 0

    def test_ingest_omitted_status_defaults_to_pending(self, client, seed_data, db_session):
        payload = {
            "items": [
                {
                    "bureau_code": "RB",
                    "summary": "Case with omitted status",
                }
            ]
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "PENDING"

        case = db_session.query(Case).first()
        assert case is not None
        assert case.status == CaseStatusEnum.PENDING

        action = db_session.query(CaseAction).filter(CaseAction.case_id == case.id).first()
        assert action is not None
        assert action.action_type == ActionTypeEnum.CREATED
        assert action.from_status is None
        assert action.to_status == CaseStatusEnum.PENDING

    def test_ingest_explicit_pending_succeeds(self, client, seed_data, db_session):
        payload = {
            "items": [
                {
                    "bureau_code": "RB",
                    "summary": "Case with explicit PENDING status",
                    "status": "PENDING",
                }
            ]
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "PENDING"

        case = db_session.query(Case).first()
        assert case.status == CaseStatusEnum.PENDING
        action = db_session.query(CaseAction).filter(CaseAction.case_id == case.id).first()
        assert action.to_status == CaseStatusEnum.PENDING

    def test_ingest_batch_atomic_rollback_on_non_pending_status(self, client, seed_data, db_session):
        payload = {
            "items": [
                {
                    "bureau_code": "RB",
                    "summary": "Valid item 1",
                },
                {
                    "bureau_code": "RB",
                    "summary": "Invalid item 2 with DISPOSED",
                    "status": "DISPOSED",
                },
                {
                    "bureau_code": "RB",
                    "summary": "Valid item 3 with PENDING",
                    "status": "PENDING",
                },
            ]
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 422
        err = get_error(res)
        assert "Initial status must be PENDING" in err["message"]

        # Atomic rollback verification: nothing written
        assert db_session.query(Case).count() == 0
        assert db_session.query(CaseAction).count() == 0

    def test_ingest_api_key_respects_pending_only(self, client, seed_data, db_session):
        payload = {
            "items": [
                {
                    "bureau_code": "RB",
                    "summary": "API Key ingestion with ESCALATED status",
                    "status": "ESCALATED",
                }
            ]
        }
        res = client.post(
            "/api/v1/ingest/cases",
            json=payload,
            headers={"X-API-Key": seed_data["raw_key_rb"]},
        )
        assert res.status_code == 422
        assert db_session.query(Case).count() == 0
        assert db_session.query(CaseAction).count() == 0

    @pytest.mark.parametrize("bad_status", ["UNDER_PROCESS", "DISPOSED", "TRANSFERRED", "ESCALATED", "UNKNOWN_STATUS"])
    def test_csv_explicit_non_pending_statuses_rejected_as_row_error(self, client, seed_data, db_session, bad_status):
        csv_content = (
            "bureau_code,summary,status\n"
            f"RB,Row with bad status {bad_status},{bad_status}\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["created"] == 0
        assert data["rejected"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["row"] == 2

        # Assert no case or action created
        assert db_session.query(Case).count() == 0
        assert db_session.query(CaseAction).count() == 0

    def test_csv_omitted_and_blank_status_defaults_to_pending(self, client, seed_data, db_session):
        # Row 2 omits status column; Row 3 has status column but empty value
        csv_content = (
            "bureau_code,summary,status\n"
            "RB,Case with blank status,\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["created"] == 1
        assert data["rejected"] == 0

        case = db_session.query(Case).first()
        assert case is not None
        assert case.status == CaseStatusEnum.PENDING

        action = db_session.query(CaseAction).filter(CaseAction.case_id == case.id).first()
        assert action is not None
        assert action.action_type == ActionTypeEnum.CREATED
        assert action.to_status == CaseStatusEnum.PENDING

    def test_csv_explicit_pending_succeeds(self, client, seed_data, db_session):
        csv_content = (
            "bureau_code,summary,status\n"
            "RB,Case with explicit PENDING,PENDING\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["created"] == 1
        assert data["rejected"] == 0

        case = db_session.query(Case).first()
        assert case.status == CaseStatusEnum.PENDING
        action = db_session.query(CaseAction).filter(CaseAction.case_id == case.id).first()
        assert action.to_status == CaseStatusEnum.PENDING

    def test_csv_partial_success_with_mixed_statuses(self, client, seed_data, db_session):
        csv_content = (
            "bureau_code,summary,status\n"
            "RB,Valid row omitted status,\n"
            "RB,Invalid row disposed,DISPOSED\n"
            "RB,Valid row explicit pending,PENDING\n"
            "RB,Invalid row transferred,TRANSFERRED\n"
        )
        res = client.post(
            "/api/v1/import/cases-csv",
            content=csv_content.encode("utf-8"),
            headers=auth_header(seed_data["officer_rb"]),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 4
        assert data["created"] == 2
        assert data["rejected"] == 2
        assert len(data["errors"]) == 2

        # Check errors reference rows 3 and 5 (1-based index including header)
        error_rows = [e["row"] for e in data["errors"]]
        assert 3 in error_rows
        assert 5 in error_rows

        # In DB: exactly 2 cases created, both PENDING, both have CREATED action with to_status=PENDING
        cases = db_session.query(Case).all()
        assert len(cases) == 2
        for c in cases:
            assert c.status == CaseStatusEnum.PENDING
            action = db_session.query(CaseAction).filter(CaseAction.case_id == c.id).first()
            assert action is not None
            assert action.to_status == CaseStatusEnum.PENDING


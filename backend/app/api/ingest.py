"""Complaint Data Ingestion and CSV Import router.

Endpoints per AGENTS.md:
  POST /api/v1/ingest/cases       – Single / batch machine ingestion (Bearer token or X-API-Key)
  POST /api/v1/import/cases-csv   – Bulk CSV import with row-level validation & duplicate detection

Ownership: P1 Backend.

Security & Ingestion Policies:
------------------------------
1. Authentication:
   - Ingest API (/ingest/cases): Supports BOTH Header X-API-Key (hashed with SHA-256 and verified
     against api_keys table for bureau machine-to-machine integration) AND standard Bearer token (JWT).
   - CSV Import (/import/cases-csv): Requires authenticated user via Bearer token (ADMIN, BUREAU_OFFICER,
     or REGIONAL_OFFICER). SENIOR_MGMT is strictly prohibited from creating/importing cases (HTTP 403).
2. Processing Behavior:
   - /ingest/cases is ATOMIC (all-or-nothing). If any record in the batch fails validation, FK lookup,
     duplicate check, or authorization, the entire batch transaction is aborted and rolled back.
   - /import/cases-csv is PARTIAL SUCCESS. Valid rows are committed transactionally with an append-only
     CaseAction audit entry; invalid or duplicate rows are recorded with specific row numbers and error
     reasons in the import summary.
3. Duplicate Policy:
   - Case numbers are unique per bureau (uq_cases_case_no_bureau_id constraint).
   - In /ingest/cases, duplicate case_no in the bureau raises HTTP 409 CONFLICT and rolls back the batch.
   - In /import/cases-csv, duplicate case_no is flagged as row error, rejected, and not silently overwritten.
4. Limits:
   - Max file size: 5 MB (5,242,880 bytes). Exceeding yields HTTP 413.
   - Max CSV rows: 1000 rows. Exceeding yields HTTP 422.
"""
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
from typing import Any, Union

from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.cases import _DEFAULT_SLA_DAYS, CaseRowOut
from app.auth import get_current_user
from app.database import get_db
from app.models import ApiKey, Bureau, Case, CaseAction, Category, Institution, SlaRule, User
from app.models.enums import ActionTypeEnum, CaseStatusEnum, PriorityEnum, RoleEnum
from app.security import TokenError, decode_token

router = APIRouter(tags=["ingest"])

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_ROW_COUNT = 1000


# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}},
    )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CaseIngestItem(BaseModel):
    case_no: str | None = None
    bureau_id: int | None = None
    bureau_code: str | None = None
    institution_id: int | None = None
    aicte_id: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    priority: PriorityEnum = PriorityEnum.MEDIUM
    status: CaseStatusEnum | None = None
    summary: str
    received_on: date | None = None
    expected_disposal_on: date | None = None
    complainant_ref: str | None = None
    assigned_officer_id: int | None = None
    next_action_text: str | None = None
    source: str = "SYNTHETIC"
    needs_institution_review: bool = False


class BatchIngestRequest(BaseModel):
    items: list[CaseIngestItem]


class BatchIngestResponse(BaseModel):
    items: list[CaseRowOut]
    total: int


class CsvRowError(BaseModel):
    row: int
    case_no: str | None = None
    error: str


class CsvImportSummary(BaseModel):
    total: int
    created: int
    rejected: int
    errors: list[CsvRowError]


# ---------------------------------------------------------------------------
# Ingestion Auth Helper
# ---------------------------------------------------------------------------

class IngestAuth:
    def __init__(self, is_api_key: bool, bureau_id: int | None = None, user: User | None = None):
        self.is_api_key = is_api_key
        self.bureau_id = bureau_id
        self.user = user


def get_ingest_auth(
    request: Request,
    db: Session = Depends(get_db),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> IngestAuth:
    """Authenticate via X-API-Key header OR Bearer JWT."""
    # 1. Check API Key
    if x_api_key and x_api_key.strip():
        key_hash = hashlib.sha256(x_api_key.strip().encode("utf-8")).hexdigest()
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.active == True)  # noqa: E712
            .first()
        )
        if not api_key:
            raise _err(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Invalid or inactive API key")
        return IngestAuth(is_api_key=True, bureau_id=api_key.bureau_id, user=None)

    # 2. Check Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        try:
            payload = decode_token(token, expected_type="access")
            user_id = int(payload["sub"])
        except (TokenError, KeyError, ValueError) as exc:
            msg = str(exc) if isinstance(exc, TokenError) else "Invalid token"
            raise _err(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", msg)

        user = db.get(User, user_id)
        if not user:
            raise _err(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "User not found")
        if not user.active:
            raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Account is inactive")
        return IngestAuth(is_api_key=False, bureau_id=user.bureau_id, user=user)

    raise _err(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", "Authentication required via Bearer token or X-API-Key")


# ---------------------------------------------------------------------------
# Case helper functions
# ---------------------------------------------------------------------------

def _generate_case_no(db: Session, bureau: Bureau, rec_date: date, seen_in_batch: set[tuple[str, int]]) -> str:
    year = rec_date.year
    seq = db.query(Case).filter(Case.bureau_id == bureau.id).count() + 1
    case_no = f"{bureau.code}/{year}/{str(seq).zfill(6)}"
    while (case_no, bureau.id) in seen_in_batch or (
        db.query(Case).filter(Case.bureau_id == bureau.id, Case.case_no == case_no).first() is not None
    ):
        seq += 1
        case_no = f"{bureau.code}/{year}/{str(seq).zfill(6)}"
    return case_no


def _calculate_expected_disposal(db: Session, category_id: int | None, priority: PriorityEnum, rec_date: date) -> date:
    rule = None
    if category_id:
        rule = db.query(SlaRule).filter(
            SlaRule.category_id == category_id,
            SlaRule.priority == priority,
        ).first()
    if rule is None:
        rule = db.query(SlaRule).filter(
            SlaRule.category_id.is_(None),
            SlaRule.priority == priority,
        ).first()
    default_days = {PriorityEnum.HIGH: 15, PriorityEnum.MEDIUM: 30, PriorityEnum.LOW: 45}
    days = rule.days_to_dispose if rule else default_days.get(priority, 30)
    return rec_date + timedelta(days=days)


def _row_to_case_out(c: Case) -> CaseRowOut:
    return CaseRowOut(
        id=c.id,
        case_no=c.case_no,
        status=c.status,
        institution_id=c.institution_id,
        institution_name=c.institution.name if c.institution else None,
        bureau_id=c.bureau_id,
        bureau_code=c.bureau.code if c.bureau else None,
        region_id=c.institution.region_id if c.institution else None,
        category_id=c.category_id,
        category_name=c.category.name if c.category else None,
        priority=c.priority,
        received_on=c.received_on,
        last_action_on=c.last_action_on,
        expected_disposal_on=c.expected_disposal_on,
        link_group_id=c.link_group_id,
    )


# ---------------------------------------------------------------------------
# POST /ingest/cases
# ---------------------------------------------------------------------------

@router.post("/ingest/cases", response_model=BatchIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_cases(
    payload: Union[BatchIngestRequest, list[CaseIngestItem], CaseIngestItem],
    auth: IngestAuth = Depends(get_ingest_auth),
    db: Session = Depends(get_db),
):
    """Atomic machine / API case ingestion.

    Accepts a single case, a list of cases, or a batch object.
    Supports Bearer token authentication (User RBAC) or X-API-Key header.
    Atomic: if any record fails validation, FK resolution, RBAC scope, or duplicate
    check, the entire batch is rolled back and an error is raised.
    """
    if isinstance(payload, BatchIngestRequest):
        items = payload.items
    elif isinstance(payload, list):
        items = payload
    else:
        items = [payload]

    if not items:
        return BatchIngestResponse(items=[], total=0)

    # Pre-check: Senior mgmt cannot create cases
    if not auth.is_api_key and auth.user and auth.user.role == RoleEnum.SENIOR_MGMT:
        raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Senior management cannot create complaint cases")

    now = datetime.now(timezone.utc)
    seen_in_batch: set[tuple[str, int]] = set()
    created_cases: list[Case] = []

    try:
        for idx, item in enumerate(items):
            # 1. Summary validation
            if not item.summary or not item.summary.strip():
                raise _err(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "UNPROCESSABLE_ENTITY",
                    f"Item {idx}: Summary is required and cannot be empty",
                )

            # 1b. Initial status validation
            if item.status is not None and item.status != CaseStatusEnum.PENDING:
                raise _err(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "UNPROCESSABLE_ENTITY",
                    f"Item {idx}: Initial status must be PENDING. Cannot ingest cases with status '{item.status.value}'",
                )

            # 2. Bureau resolution
            bureau = None
            if item.bureau_id is not None:
                bureau = db.get(Bureau, item.bureau_id)
            elif item.bureau_code and item.bureau_code.strip():
                bureau = db.query(Bureau).filter(func.upper(Bureau.code) == item.bureau_code.strip().upper()).first()

            if not bureau:
                raise _err(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "UNPROCESSABLE_ENTITY",
                    f"Item {idx}: Bureau not found",
                )

            # 3. RBAC / Scope validation
            if auth.is_api_key:
                if auth.bureau_id != bureau.id:
                    raise _err(
                        status.HTTP_403_FORBIDDEN,
                        "FORBIDDEN",
                        f"Item {idx}: API key is restricted to bureau ID {auth.bureau_id}, cannot ingest for bureau ID {bureau.id}",
                    )
            else:
                user = auth.user
                if user.role == RoleEnum.BUREAU_OFFICER and user.bureau_id != bureau.id:
                    raise _err(
                        status.HTTP_403_FORBIDDEN,
                        "FORBIDDEN",
                        f"Item {idx}: Bureau officers may only ingest cases in their own bureau",
                    )

            # 4. Institution resolution
            institution = None
            if item.institution_id is not None:
                institution = db.get(Institution, item.institution_id)
                if not institution:
                    raise _err(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "UNPROCESSABLE_ENTITY",
                        f"Item {idx}: Institution ID {item.institution_id} not found",
                    )
            elif item.aicte_id and item.aicte_id.strip():
                institution = db.query(Institution).filter(
                    Institution.aicte_permanent_id == item.aicte_id.strip()
                ).first()
                if not institution:
                    raise _err(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "UNPROCESSABLE_ENTITY",
                        f"Item {idx}: Institution with AICTE ID '{item.aicte_id}' not found",
                    )

            # Regional officer scope check
            if not auth.is_api_key and auth.user and auth.user.role == RoleEnum.REGIONAL_OFFICER:
                if not institution or institution.region_id != auth.user.region_id:
                    raise _err(
                        status.HTTP_403_FORBIDDEN,
                        "FORBIDDEN",
                        f"Item {idx}: Regional officers may only ingest cases for institutions in their own region",
                    )

            # 5. Category resolution
            category = None
            if item.category_id is not None:
                category = db.get(Category, item.category_id)
                if not category:
                    raise _err(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "UNPROCESSABLE_ENTITY",
                        f"Item {idx}: Category ID {item.category_id} not found",
                    )
            elif item.category_name and item.category_name.strip():
                category = db.query(Category).filter(
                    func.lower(Category.name) == item.category_name.strip().lower()
                ).first()
                if not category:
                    raise _err(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "UNPROCESSABLE_ENTITY",
                        f"Item {idx}: Category '{item.category_name}' not found",
                    )

            # 6. Assigned officer validation
            if item.assigned_officer_id is not None:
                officer = db.get(User, item.assigned_officer_id)
                if not officer or not officer.active:
                    raise _err(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "UNPROCESSABLE_ENTITY",
                        f"Item {idx}: Assigned officer not found or inactive",
                    )
                if officer.role == RoleEnum.BUREAU_OFFICER and officer.bureau_id != bureau.id:
                    raise _err(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "UNPROCESSABLE_ENTITY",
                        f"Item {idx}: Assigned officer belongs to a different bureau",
                    )
                inst_reg = institution.region_id if institution else None
                if officer.role == RoleEnum.REGIONAL_OFFICER and officer.region_id != inst_reg:
                    raise _err(
                        status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "UNPROCESSABLE_ENTITY",
                        f"Item {idx}: Assigned officer belongs to a different region",
                    )

            # 7. Dates & case_no
            rec_date = item.received_on or date.today()
            if item.case_no and item.case_no.strip():
                c_no = item.case_no.strip()
                if len(c_no) > 100:
                    raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "case_no exceeds 100 characters")
                existing = db.query(Case).filter(Case.bureau_id == bureau.id, Case.case_no == c_no).first()
                if existing or (c_no, bureau.id) in seen_in_batch:
                    raise _err(
                        status.HTTP_409_CONFLICT,
                        "CONFLICT",
                        f"Case number '{c_no}' already exists in bureau '{bureau.code}'",
                    )
                seen_in_batch.add((c_no, bureau.id))
            else:
                c_no = _generate_case_no(db, bureau, rec_date, seen_in_batch)
                seen_in_batch.add((c_no, bureau.id))

            expected_disposal = item.expected_disposal_on or _calculate_expected_disposal(
                db, category.id if category else None, item.priority, rec_date
            )

            # 8. Create Case and Action
            new_case = Case(
                case_no=c_no,
                bureau_id=bureau.id,
                institution_id=institution.id if institution else None,
                category_id=category.id if category else None,
                status=CaseStatusEnum.PENDING,
                assigned_officer_id=item.assigned_officer_id,
                received_on=rec_date,
                last_action_on=now,
                last_action_text="Case ingested via API",
                next_action_text=item.next_action_text,
                expected_disposal_on=expected_disposal,
                priority=item.priority,
                summary=item.summary.strip(),
                complainant_ref=item.complainant_ref,
                source=item.source or "SYNTHETIC",
                needs_institution_review=item.needs_institution_review,
            )
            db.add(new_case)
            db.flush()

            action = CaseAction(
                case_id=new_case.id,
                actor_id=auth.user.id if auth.user else None,
                bureau_id=bureau.id,
                action_type=ActionTypeEnum.CREATED,
                from_status=None,
                to_status=new_case.status,
                remarks="Case ingested via API Key" if auth.is_api_key else "Case ingested via API",
                created_at=now,
            )
            db.add(action)
            created_cases.append(new_case)

        db.commit()
        for c in created_cases:
            db.refresh(c)

        return BatchIngestResponse(
            items=[_row_to_case_out(c) for c in created_cases],
            total=len(created_cases),
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _err(status.HTTP_400_BAD_REQUEST, "BAD_REQUEST", str(exc))


# ---------------------------------------------------------------------------
# POST /import/cases-csv
# ---------------------------------------------------------------------------

@router.post("/import/cases-csv", response_model=CsvImportSummary)
async def import_cases_csv(
    request: Request,
    file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk import cases from CSV with row-level validation and partial success.

    Accepts multipart/form-data upload or raw text/csv body.
    Requires Bearer token authentication.
    Duplicate handling: Rows with duplicate case_no in the bureau are rejected and
    reported in errors with row number and reason. Valid rows are successfully imported.
    """
    if current_user.role == RoleEnum.SENIOR_MGMT:
        raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Senior management cannot create complaint cases")

    # Read uploaded content
    if file:
        content = await file.read()
    else:
        content = await request.body()

    if not content or not content.strip():
        raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "EMPTY_FILE", "Uploaded CSV file is empty")

    if len(content) > MAX_UPLOAD_SIZE:
        raise _err(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "FILE_TOO_LARGE",
            f"File size ({len(content)} bytes) exceeds the maximum allowed limit of {MAX_UPLOAD_SIZE} bytes (5MB)",
        )

    # Decode UTF-8 (handling BOM)
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "INVALID_ENCODING", "File encoding must be valid UTF-8")

    # Parse CSV
    stream = io.StringIO(decoded)
    reader = csv.DictReader(stream)

    if not reader.fieldnames:
        raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "EMPTY_FILE", "Uploaded CSV file is empty")

    # Map headers to canonical names
    header_map: dict[str, str] = {}
    for h in reader.fieldnames:
        if not h:
            continue
        cleaned = h.strip().lower()
        if cleaned in ("summary", "description"):
            header_map["summary"] = h
        elif cleaned in ("bureau_code", "bureau", "bureau_id"):
            header_map["bureau"] = h
        elif cleaned in ("institution_id", "aicte_id", "aicte_permanent_id"):
            header_map["institution"] = h
        elif cleaned in ("category_id", "category_name", "category"):
            header_map["category"] = h
        elif cleaned == "priority":
            header_map["priority"] = h
        elif cleaned == "status":
            header_map["status"] = h
        elif cleaned in ("received_on", "date_received"):
            header_map["received_on"] = h
        elif cleaned in ("expected_disposal_on", "due_date"):
            header_map["expected_disposal_on"] = h
        elif cleaned in ("case_no", "case_number"):
            header_map["case_no"] = h
        elif cleaned in ("complainant_ref", "complainant_reference"):
            header_map["complainant_ref"] = h
        elif cleaned == "source":
            header_map["source"] = h

    if "summary" not in header_map or "bureau" not in header_map:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "INVALID_CSV_HEADERS",
            "CSV must contain at least 'summary' and bureau identifier ('bureau_code' or 'bureau_id')",
        )

    total_rows = 0
    created_count = 0
    rejected_count = 0
    errors: list[CsvRowError] = []
    seen_in_batch: set[tuple[str, int]] = set()
    now = datetime.now(timezone.utc)

    rows = list(reader)
    if len(rows) > MAX_ROW_COUNT:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "ROW_LIMIT_EXCEEDED",
            f"CSV contains {len(rows)} rows, exceeding the maximum allowed limit of {MAX_ROW_COUNT} rows",
        )

    for row_idx, raw_row in enumerate(rows, start=2):  # line 1 is header
        # Check blank row
        if not any(v and v.strip() for v in raw_row.values()):
            continue

        total_rows += 1
        summary_val = raw_row.get(header_map["summary"], "").strip()
        if not summary_val:
            errors.append(CsvRowError(row=row_idx, error="Summary is required and cannot be empty"))
            rejected_count += 1
            continue

        # Bureau resolution
        bureau_val = raw_row.get(header_map["bureau"], "").strip()
        if not bureau_val:
            errors.append(CsvRowError(row=row_idx, error="Bureau identifier is required"))
            rejected_count += 1
            continue

        bureau = None
        if bureau_val.isdigit():
            bureau = db.get(Bureau, int(bureau_val))
        if not bureau:
            bureau = db.query(Bureau).filter(func.upper(Bureau.code) == bureau_val.upper()).first()

        if not bureau:
            errors.append(CsvRowError(row=row_idx, error=f"Bureau '{bureau_val}' not found"))
            rejected_count += 1
            continue

        # RBAC check on bureau
        if current_user.role == RoleEnum.BUREAU_OFFICER and bureau.id != current_user.bureau_id:
            errors.append(
                CsvRowError(
                    row=row_idx,
                    error=f"Bureau officer not authorized to import for bureau '{bureau.code}'",
                )
            )
            rejected_count += 1
            continue

        # Institution resolution
        institution = None
        if "institution" in header_map:
            inst_val = raw_row.get(header_map["institution"], "").strip()
            if inst_val:
                if inst_val.isdigit():
                    institution = db.get(Institution, int(inst_val))
                if not institution:
                    institution = db.query(Institution).filter(
                        Institution.aicte_permanent_id == inst_val
                    ).first()
                if not institution:
                    errors.append(CsvRowError(row=row_idx, error=f"Institution '{inst_val}' not found"))
                    rejected_count += 1
                    continue

        # Regional officer scope check
        if current_user.role == RoleEnum.REGIONAL_OFFICER:
            if not institution or institution.region_id != current_user.region_id:
                errors.append(
                    CsvRowError(
                        row=row_idx,
                        error="Regional officer may only import cases for institutions in their own region",
                    )
                )
                rejected_count += 1
                continue

        # Category resolution
        category = None
        if "category" in header_map:
            cat_val = raw_row.get(header_map["category"], "").strip()
            if cat_val:
                if cat_val.isdigit():
                    category = db.get(Category, int(cat_val))
                if not category:
                    category = db.query(Category).filter(
                        func.lower(Category.name) == cat_val.lower()
                    ).first()
                if not category:
                    errors.append(CsvRowError(row=row_idx, error=f"Category '{cat_val}' not found"))
                    rejected_count += 1
                    continue

        # Priority
        priority = PriorityEnum.MEDIUM
        if "priority" in header_map:
            p_val = raw_row.get(header_map["priority"], "").strip().upper()
            if p_val:
                try:
                    priority = PriorityEnum(p_val)
                except ValueError:
                    errors.append(CsvRowError(row=row_idx, error=f"Invalid priority '{p_val}'. Must be LOW, MEDIUM, or HIGH"))
                    rejected_count += 1
                    continue

        # Status
        case_status = CaseStatusEnum.PENDING
        if "status" in header_map:
            s_val = raw_row.get(header_map["status"], "").strip().upper()
            if s_val:
                try:
                    parsed_status = CaseStatusEnum(s_val)
                except ValueError:
                    errors.append(CsvRowError(row=row_idx, error=f"Invalid status '{s_val}'. Must be a valid case status"))
                    rejected_count += 1
                    continue
                if parsed_status != CaseStatusEnum.PENDING:
                    errors.append(
                        CsvRowError(
                            row=row_idx,
                            error=f"Initial status must be PENDING. Cannot import cases with status '{s_val}'",
                        )
                    )
                    rejected_count += 1
                    continue
                case_status = CaseStatusEnum.PENDING

        # Dates
        rec_date = date.today()
        if "received_on" in header_map:
            r_val = raw_row.get(header_map["received_on"], "").strip()
            if r_val:
                try:
                    rec_date = date.fromisoformat(r_val)
                except ValueError:
                    errors.append(CsvRowError(row=row_idx, error=f"Invalid date format for received_on: '{r_val}'. Expected YYYY-MM-DD"))
                    rejected_count += 1
                    continue

        expected_disposal = None
        if "expected_disposal_on" in header_map:
            e_val = raw_row.get(header_map["expected_disposal_on"], "").strip()
            if e_val:
                try:
                    expected_disposal = date.fromisoformat(e_val)
                except ValueError:
                    errors.append(CsvRowError(row=row_idx, error=f"Invalid date format for expected_disposal_on: '{e_val}'. Expected YYYY-MM-DD"))
                    rejected_count += 1
                    continue

        if expected_disposal is None:
            expected_disposal = _calculate_expected_disposal(
                db, category.id if category else None, priority, rec_date
            )

        # Case No and duplicate check
        c_no = None
        if "case_no" in header_map:
            c_val = raw_row.get(header_map["case_no"], "").strip()
            if c_val:
                c_no = c_val

        if c_no:
            if (c_no, bureau.id) in seen_in_batch or (
                db.query(Case).filter(Case.bureau_id == bureau.id, Case.case_no == c_no).first() is not None
            ):
                errors.append(
                    CsvRowError(
                        row=row_idx,
                        case_no=c_no,
                        error=f"Duplicate case number '{c_no}' in bureau '{bureau.code}'",
                    )
                )
                rejected_count += 1
                continue
            seen_in_batch.add((c_no, bureau.id))
        else:
            c_no = _generate_case_no(db, bureau, rec_date, seen_in_batch)
            seen_in_batch.add((c_no, bureau.id))

        complainant_ref = None
        if "complainant_ref" in header_map:
            cr_val = raw_row.get(header_map["complainant_ref"], "").strip()
            if cr_val:
                complainant_ref = cr_val

        source_val = "SYNTHETIC"
        if "source" in header_map:
            s_val = raw_row.get(header_map["source"], "").strip()
            if s_val:
                source_val = s_val

        # Create Case & CaseAction
        try:
            new_case = Case(
                case_no=c_no,
                bureau_id=bureau.id,
                institution_id=institution.id if institution else None,
                category_id=category.id if category else None,
                status=case_status,
                received_on=rec_date,
                last_action_on=now,
                last_action_text="Case imported via CSV",
                expected_disposal_on=expected_disposal,
                priority=priority,
                summary=summary_val,
                complainant_ref=complainant_ref,
                source=source_val,
            )
            db.add(new_case)
            db.flush()

            action = CaseAction(
                case_id=new_case.id,
                actor_id=current_user.id,
                bureau_id=bureau.id,
                action_type=ActionTypeEnum.CREATED,
                from_status=None,
                to_status=new_case.status,
                remarks="Case imported via CSV",
                created_at=now,
            )
            db.add(action)
            db.commit()
            created_count += 1
        except Exception as exc:
            db.rollback()
            errors.append(CsvRowError(row=row_idx, case_no=c_no, error=f"Database error: {str(exc)}"))
            rejected_count += 1

    return CsvImportSummary(
        total=total_rows,
        created=created_count,
        rejected=rejected_count,
        errors=errors,
    )

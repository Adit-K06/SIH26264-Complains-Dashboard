"""Institutions API router.

Endpoints per AGENTS.md:
  GET /institutions                   – paginated list with optional filters
  GET /institutions/{id}              – institution detail
  GET /institutions/{id}/cases        – cases linked to an institution
  GET /institutions/resolve?name=     – fuzzy name-to-institution resolution (AI stub)

All endpoints require authentication (any active role). No institution write
endpoints exist in Phase 4A; those belong to the ingest/import subphase.

RBAC: all authenticated roles may read institution data. No complainant_ref
or other sensitive case data is exposed here; case details follow case RBAC.
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.ai import resolve_institution
from app.auth import get_current_user
from app.database import get_db
from app.models import Bureau, Case, Category, Institution, Region, User
from app.models.enums import CaseStatusEnum, PriorityEnum

router = APIRouter(prefix="/institutions", tags=["institutions"])


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

from fastapi import HTTPException, status as http_status


def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}},
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class InstitutionOut(BaseModel):
    id: int
    aicte_permanent_id: str
    name: str
    address: str | None = None
    district: str | None = None
    state: str | None = None
    region_id: int | None = None
    region_name: str | None = None
    type: str | None = None
    status: str | None = None

    model_config = {"from_attributes": True}


class PagedInstitutionResponse(BaseModel):
    items: list[InstitutionOut]
    total: int
    page: int
    page_size: int


class InstitutionCaseRow(BaseModel):
    """Compact case row within an institution's case list."""
    id: int
    case_no: str
    status: CaseStatusEnum
    bureau_id: int
    bureau_code: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    priority: PriorityEnum
    received_on: str | None = None  # YYYY-MM-DD
    expected_disposal_on: str | None = None
    link_group_id: str | None = None

    model_config = {"from_attributes": True}


class PagedCaseResponse(BaseModel):
    items: list[InstitutionCaseRow]
    total: int
    page: int
    page_size: int


class ResolveOut(BaseModel):
    institution_id: int | None = None
    confidence: float
    method: str
    candidates: list
    needs_review: bool


# ---------------------------------------------------------------------------
# GET /institutions
# ---------------------------------------------------------------------------

@router.get("", response_model=PagedInstitutionResponse)
@router.get("/", response_model=PagedInstitutionResponse, include_in_schema=False)
def list_institutions(
    q: str | None = None,
    region_id: int | None = None,
    state: str | None = None,
    type: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List institutions with optional text search and filters.

    Filters:
      q         – case-insensitive substring match against name, aicte_permanent_id, district, state
      region_id – exact region filter
      state     – exact state filter (case-insensitive)
      type      – exact institution type filter
      status    – institution status filter
    """
    query = db.query(Institution).outerjoin(Region, Institution.region_id == Region.id)

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Institution.name.ilike(term),
                Institution.aicte_permanent_id.ilike(term),
                Institution.district.ilike(term),
                Institution.state.ilike(term),
            )
        )

    if region_id is not None:
        query = query.filter(Institution.region_id == region_id)

    if state and state.strip():
        query = query.filter(Institution.state.ilike(state.strip()))

    if type and type.strip():
        query = query.filter(Institution.type.ilike(type.strip()))

    if status and status.strip():
        query = query.filter(Institution.status.ilike(status.strip()))

    total = query.count()
    offset = (page - 1) * page_size
    institutions = (
        query.options(joinedload(Institution.region))
        .order_by(Institution.name.asc(), Institution.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [
        InstitutionOut(
            id=inst.id,
            aicte_permanent_id=inst.aicte_permanent_id,
            name=inst.name,
            address=inst.address,
            district=inst.district,
            state=inst.state,
            region_id=inst.region_id,
            region_name=inst.region.name if inst.region else None,
            type=inst.type,
            status=inst.status,
        )
        for inst in institutions
    ]

    return PagedInstitutionResponse(items=items, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# GET /institutions/resolve  — must be declared BEFORE /{id} to avoid clash
# ---------------------------------------------------------------------------

@router.get("/resolve", response_model=ResolveOut)
def resolve(
    name: str | None = None,
    aicte_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resolve a free-text institution name or AICTE ID to a known institution.

    Delegates to the frozen AI contract (app.ai.resolve_institution).
    Returns the stub response until P2 provides the real implementation.
    """
    if not name and not aicte_id:
        raise _err(
            http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            "UNPROCESSABLE_ENTITY",
            "At least one of 'name' or 'aicte_id' is required",
        )

    result = resolve_institution(db, name=name or None, aicte_id=aicte_id or None)
    return ResolveOut(
        institution_id=result.institution_id,
        confidence=result.confidence,
        method=result.method,
        candidates=result.candidates,
        needs_review=result.needs_review,
    )


# ---------------------------------------------------------------------------
# GET /institutions/{id}
# ---------------------------------------------------------------------------

@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(
    institution_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a single institution by its internal ID."""
    inst = (
        db.query(Institution)
        .options(joinedload(Institution.region))
        .filter(Institution.id == institution_id)
        .first()
    )
    if inst is None:
        raise _err(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Institution {institution_id} not found")

    return InstitutionOut(
        id=inst.id,
        aicte_permanent_id=inst.aicte_permanent_id,
        name=inst.name,
        address=inst.address,
        district=inst.district,
        state=inst.state,
        region_id=inst.region_id,
        region_name=inst.region.name if inst.region else None,
        type=inst.type,
        status=inst.status,
    )


# ---------------------------------------------------------------------------
# GET /institutions/{id}/cases
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/cases", response_model=PagedCaseResponse)
def get_institution_cases(
    institution_id: int,
    status: CaseStatusEnum | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List cases associated with an institution.

    Optional status filter; results are ordered by received_on descending.
    No complainant_ref is returned here — full case detail follows case RBAC.
    """
    inst = db.get(Institution, institution_id)
    if inst is None:
        raise _err(http_status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Institution {institution_id} not found")

    query = (
        db.query(Case)
        .outerjoin(Bureau, Case.bureau_id == Bureau.id)
        .outerjoin(Category, Case.category_id == Category.id)
        .filter(Case.institution_id == institution_id)
    )

    if status is not None:
        query = query.filter(Case.status == status)

    total = query.count()
    offset = (page - 1) * page_size
    cases = (
        query.order_by(Case.received_on.desc(), Case.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [
        InstitutionCaseRow(
            id=c.id,
            case_no=c.case_no,
            status=c.status,
            bureau_id=c.bureau_id,
            bureau_code=c.bureau.code if c.bureau else None,
            category_id=c.category_id,
            category_name=c.category.name if c.category else None,
            priority=c.priority,
            received_on=c.received_on.isoformat() if c.received_on else None,
            expected_disposal_on=c.expected_disposal_on.isoformat() if c.expected_disposal_on else None,
            link_group_id=c.link_group_id,
        )
        for c in cases
    ]

    return PagedCaseResponse(items=items, total=total, page=page, page_size=page_size)

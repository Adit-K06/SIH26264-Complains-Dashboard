"""Overlap detection and case-linking API router.

Endpoints per AGENTS.md:
  GET    /overlaps              – List/filter overlap flags
  POST   /overlaps/scan         – Run overlap detection scan
  POST   /overlaps/{id}/link    – Confirm overlap and link cases
  POST   /overlaps/{id}/dismiss – Dismiss overlap flag

Ownership: P4 Platform/QA.

Tier A: institution with open cases in >=2 distinct bureaus.
         -> OverlapFlag with case_a=NULL, case_b=NULL, tier=A.
Tier B: pair-wise overlap score >= configured threshold.
         -> OverlapFlag with case_a, case_b set, tier=B.

Case linking: POST /overlaps/{id}/link creates CaseLink entries for cases
in the same overlap group, records LINKED audit actions, and confirms the flag.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    assert_bureau_scope,
    assert_region_scope,
    get_current_user,
)
from app.database import get_db
from app.models import (
    Bureau,
    Case,
    CaseAction,
    CaseLink,
    Institution,
    OverlapFlag,
    User,
)
from app.models.enums import (
    ActionTypeEnum,
    CaseStatusEnum,
    OPEN_CASE_STATUSES,
    OverlapStateEnum,
    OverlapTierEnum,
    RoleEnum,
)
from app.ai import scan_overlaps as ai_scan_overlaps

router = APIRouter(prefix="/overlaps", tags=["overlaps"])


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}},
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class OverlapItemOut(BaseModel):
    id: int
    institution_id: int
    institution_name: str | None = None
    case_a_id: int | None = None
    case_b_id: int | None = None
    tier: str
    score: float | None = None
    reasons: list[str] = []
    state: str
    decided_by: int | None = None
    decided_at: datetime | None = None

    model_config = {"from_attributes": True}


class OverlapListResponse(BaseModel):
    items: list[OverlapItemOut]
    total: int
    page: int
    page_size: int


class ScanResponse(BaseModel):
    new_flags: int


class LinkRequest(BaseModel):
    lead_bureau_id: int
    note: str | None = None


class DismissRequest(BaseModel):
    note: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _flag_to_out(flag: OverlapFlag) -> OverlapItemOut:
    inst_name = flag.institution.name if flag.institution else None
    return OverlapItemOut(
        id=flag.id,
        institution_id=flag.institution_id,
        institution_name=inst_name,
        case_a_id=flag.case_a,
        case_b_id=flag.case_b,
        tier=flag.tier.value if flag.tier else "A",
        score=flag.score,
        reasons=flag.reasons if isinstance(flag.reasons, list) else [],
        state=flag.state.value if flag.state else "OPEN",
        decided_by=flag.decided_by,
        decided_at=flag.decided_at,
    )


def _check_overlap_dismiss_permission(user: User, flag: OverlapFlag, db: Session) -> None:
    """Raise 403 if user cannot dismiss this overlap flag.

    ADMIN: unrestricted.
    BUREAU_OFFICER: can dismiss only if an involved case/institution is in their bureau scope.
    REGIONAL_OFFICER: can act only if the institution is in their region.
    SENIOR_MGMT: read-only; cannot dismiss.
    """
    if user.role == RoleEnum.ADMIN:
        return

    if user.role == RoleEnum.SENIOR_MGMT:
        raise _err(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN",
            "Senior management cannot dismiss overlap flags",
        )

    if user.role == RoleEnum.BUREAU_OFFICER:
        has_scope = False
        if flag.case_a:
            case_a = db.get(Case, flag.case_a)
            if case_a and case_a.bureau_id == user.bureau_id:
                has_scope = True
        if not has_scope and flag.case_b:
            case_b = db.get(Case, flag.case_b)
            if case_b and case_b.bureau_id == user.bureau_id:
                has_scope = True
        if not has_scope:
            # For Tier A flags (no specific cases), check if institution has open cases in user's bureau
            inst_cases = db.query(Case).filter(
                Case.institution_id == flag.institution_id,
                Case.bureau_id == user.bureau_id,
                Case.status.in_(list(OPEN_CASE_STATUSES)),
            ).first()
            if inst_cases:
                has_scope = True
        if not has_scope:
            raise _err(
                status.HTTP_403_FORBIDDEN,
                "FORBIDDEN",
                "Bureau officers may only act on overlaps involving their own bureau",
            )

    if user.role == RoleEnum.REGIONAL_OFFICER:
        institution = flag.institution or db.get(Institution, flag.institution_id)
        if not institution or institution.region_id != user.region_id:
            raise _err(
                status.HTTP_403_FORBIDDEN,
                "FORBIDDEN",
                "Regional officers may only act on overlaps for institutions in their own region",
            )


def _check_link_cases_permission(user: User, flag: OverlapFlag, cases: list[Case], db: Session) -> None:
    """Raise 403 if user lacks permission over every affected case in the linking workflow.

    - ADMIN: unrestricted; authorized for cross-bureau and cross-region linking.
    - SENIOR_MGMT: read-only; cannot link cases (HTTP 403).
    - BUREAU_OFFICER: may only mutate cases belonging to their own bureau.
      If any affected case belongs to another bureau, reject with HTTP 403.
    - REGIONAL_OFFICER: restricted to institutions and cases within their permitted region.
      If any affected case or the flagged institution is outside their region, reject with HTTP 403.
    """
    if user.role == RoleEnum.ADMIN:
        return

    if user.role == RoleEnum.SENIOR_MGMT:
        raise _err(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN",
            "Senior management cannot confirm or link overlap flags",
        )

    if user.role == RoleEnum.BUREAU_OFFICER:
        for case in cases:
            if case.bureau_id != user.bureau_id:
                raise _err(
                    status.HTTP_403_FORBIDDEN,
                    "FORBIDDEN",
                    "Bureau officers may only link cases belonging to their own bureau",
                )

    if user.role == RoleEnum.REGIONAL_OFFICER:
        flag_inst = flag.institution or db.get(Institution, flag.institution_id)
        if not flag_inst or flag_inst.region_id != user.region_id:
            raise _err(
                status.HTTP_403_FORBIDDEN,
                "FORBIDDEN",
                "Regional officers may only act on overlaps for institutions in their own region",
            )
        for case in cases:
            case_inst = case.institution or (db.get(Institution, case.institution_id) if case.institution_id else None)
            if not case_inst or case_inst.region_id != user.region_id:
                raise _err(
                    status.HTTP_403_FORBIDDEN,
                    "FORBIDDEN",
                    "Regional officers may only link cases for institutions in their own region",
                )


# ---------------------------------------------------------------------------
# GET /overlaps
# ---------------------------------------------------------------------------

@router.get("", response_model=OverlapListResponse)
def list_overlaps(
    state: str | None = Query("OPEN", description="Filter by overlap state"),
    institution_id: int | None = Query(None, description="Filter by institution"),
    tier: str | None = Query(None, description="Filter by tier (A or B)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(5, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List overlap flags with filtering and pagination."""
    query = db.query(OverlapFlag).options(joinedload(OverlapFlag.institution))

    # State filter
    if state is not None and state.strip():
        try:
            state_enum = OverlapStateEnum(state.strip().upper())
        except ValueError:
            raise _err(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "UNPROCESSABLE_ENTITY",
                f"Invalid state '{state}'. Must be OPEN, CONFIRMED, or DISMISSED",
            )
        query = query.filter(OverlapFlag.state == state_enum)

    # Institution filter
    if institution_id is not None:
        inst = db.get(Institution, institution_id)
        if not inst:
            raise _err(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "UNPROCESSABLE_ENTITY",
                f"Institution {institution_id} not found",
            )
        query = query.filter(OverlapFlag.institution_id == institution_id)

    # Tier filter
    if tier is not None and tier.strip():
        try:
            tier_enum = OverlapTierEnum(tier.strip().upper())
        except ValueError:
            raise _err(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "UNPROCESSABLE_ENTITY",
                f"Invalid tier '{tier}'. Must be A or B",
            )
        query = query.filter(OverlapFlag.tier == tier_enum)

    total = query.count()
    offset = (page - 1) * page_size
    flags = query.order_by(OverlapFlag.id.desc()).offset(offset).limit(page_size).all()

    return OverlapListResponse(
        items=[_flag_to_out(f) for f in flags],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# POST /overlaps/scan
# ---------------------------------------------------------------------------

@router.post("/scan", response_model=ScanResponse)
def run_overlap_scan(
    institution_id: int | None = Query(None, description="Scan specific institution"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run overlap detection scan. Creates new OverlapFlag records for
    detected overlaps that don't already have an active flag.

    Uses the AI contract to create Tier A and Tier B overlap flags.
    The API-level Tier A check below is retained as a defensive idempotency
    check and does not duplicate flags already created by the AI scan.
    """
    # Only ADMIN and BUREAU_OFFICER can trigger scans
    if current_user.role == RoleEnum.SENIOR_MGMT:
        raise _err(
            status.HTTP_403_FORBIDDEN,
            "FORBIDDEN",
            "Senior management cannot trigger overlap scans",
        )

    # Validate institution_id if provided
    if institution_id is not None:
        inst = db.get(Institution, institution_id)
        if not inst:
            raise _err(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "UNPROCESSABLE_ENTITY",
                f"Institution {institution_id} not found",
            )

    # Regional officer scope check
    if current_user.role == RoleEnum.REGIONAL_OFFICER:
        if institution_id is not None:
            inst = db.get(Institution, institution_id)
            if inst and inst.region_id != current_user.region_id:
                raise _err(
                    status.HTTP_403_FORBIDDEN,
                    "FORBIDDEN",
                    "Regional officers may only scan institutions in their own region",
                )

    new_flags = 0

    # Run the integrated AI overlap detector.
    try:
        ai_result = ai_scan_overlaps(db, institution_id=institution_id)
        new_flags += ai_result
    except Exception:
        # AI module failure should not break the scan
        pass

    # Run our own Tier A detection:
    # "institution with open cases in >=2 distinct bureaus"
    # This detects institutions that have open complaints across multiple bureaus.
    open_statuses = list(OPEN_CASE_STATUSES)

    if institution_id is not None:
        # Scan single institution
        institutions_to_check = [institution_id]
    else:
        # Find all institutions with open cases
        inst_ids_query = (
            db.query(Case.institution_id)
            .filter(
                Case.institution_id.isnot(None),
                Case.status.in_(open_statuses),
            )
            .distinct()
        )
        institutions_to_check = [row[0] for row in inst_ids_query.all()]

    for inst_id in institutions_to_check:
        # Count distinct bureaus with open cases for this institution
        distinct_bureaus = (
            db.query(func.count(func.distinct(Case.bureau_id)))
            .filter(
                Case.institution_id == inst_id,
                Case.status.in_(open_statuses),
            )
            .scalar()
        )

        if distinct_bureaus is not None and distinct_bureaus >= 2:
            # Check if Tier A flag already exists for this institution
            existing = (
                db.query(OverlapFlag)
                .filter(
                    OverlapFlag.institution_id == inst_id,
                    OverlapFlag.case_a.is_(None),
                    OverlapFlag.case_b.is_(None),
                )
                .first()
            )

            if existing is None:
                # Create new Tier A flag
                reasons = ["DIFFERENT_BUREAU"]
                flag = OverlapFlag(
                    institution_id=inst_id,
                    case_a=None,
                    case_b=None,
                    tier=OverlapTierEnum.A,
                    score=0.0,
                    reasons=reasons,
                    state=OverlapStateEnum.OPEN,
                )
                db.add(flag)
                new_flags += 1
            elif existing.state == OverlapStateEnum.DISMISSED:
                # Re-check: if conditions still hold and state was dismissed,
                # do not re-raise per AGENTS.md: "dismissed pairs not re-raised
                # unless summary/status changed after decided_at"
                # For Tier A, we skip re-raising dismissed flags.
                pass

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise _err(
            status.HTTP_400_BAD_REQUEST,
            "BAD_REQUEST",
            "Overlap scan failed due to a database error",
        )

    return ScanResponse(new_flags=new_flags)


# ---------------------------------------------------------------------------
# POST /overlaps/{id}/link
# ---------------------------------------------------------------------------

@router.post("/{overlap_id}/link", response_model=OverlapItemOut)
def link_overlap(
    overlap_id: int,
    body: LinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm an overlap flag and link the related cases.

    Per AGENTS.md: POST /overlaps/{id}/link (lead_bureau_id, note)
    Creates case_links entries and records LINKED audit actions.
    """
    flag = db.query(OverlapFlag).options(
        joinedload(OverlapFlag.institution)
    ).filter(OverlapFlag.id == overlap_id).first()

    if not flag:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Overlap flag {overlap_id} not found")

    # Only OPEN flags can be confirmed/linked
    if flag.state != OverlapStateEnum.OPEN:
        raise _err(
            status.HTTP_409_CONFLICT,
            "CONFLICT",
            f"Overlap flag is already {flag.state.value}; only OPEN flags can be linked",
        )

    # Validate lead bureau
    lead_bureau = db.get(Bureau, body.lead_bureau_id)
    if not lead_bureau:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "UNPROCESSABLE_ENTITY",
            f"Lead bureau {body.lead_bureau_id} not found",
        )

    now = datetime.now(timezone.utc)
    group_id = str(uuid.uuid4())

    # Determine cases to link
    cases_to_link: list[Case] = []

    if flag.tier == OverlapTierEnum.B:
        # Tier B: link the specific case pair
        if flag.case_a:
            case_a = db.get(Case, flag.case_a)
            if case_a:
                cases_to_link.append(case_a)
        if flag.case_b:
            case_b = db.get(Case, flag.case_b)
            if case_b:
                cases_to_link.append(case_b)
    else:
        # Tier A: link all open cases for this institution across bureaus
        cases_to_link = (
            db.query(Case)
            .filter(
                Case.institution_id == flag.institution_id,
                Case.status.in_(list(OPEN_CASE_STATUSES)),
            )
            .all()
        )

    if len(cases_to_link) < 2:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "UNPROCESSABLE_ENTITY",
            "Cannot link: fewer than 2 eligible cases found for this overlap",
        )

    if flag.tier == OverlapTierEnum.B and len(cases_to_link) == 2 and cases_to_link[0].id == cases_to_link[1].id:
        raise _err(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "UNPROCESSABLE_ENTITY",
            "Cannot link: case cannot be linked to itself",
        )

    # RBAC check: verify actor is authorized to modify every affected case BEFORE any mutation
    _check_link_cases_permission(current_user, flag, cases_to_link, db)

    # Create case links and audit actions
    for case in cases_to_link:
        # Check if case already has a link in this group
        existing_link = db.query(CaseLink).filter(
            CaseLink.group_id == group_id,
            CaseLink.case_id == case.id,
        ).first()

        if existing_link is None:
            link = CaseLink(
                group_id=group_id,
                case_id=case.id,
                linked_by=current_user.id,
                lead_bureau_id=body.lead_bureau_id,
                note=body.note,
                created_at=now,
            )
            db.add(link)

            # Update case link_group_id
            case.link_group_id = group_id

            # Record LINKED audit action
            action = CaseAction(
                case_id=case.id,
                actor_id=current_user.id,
                bureau_id=case.bureau_id,
                action_type=ActionTypeEnum.LINKED,
                from_status=case.status,
                to_status=case.status,
                remarks=body.note or f"Case linked via overlap flag #{overlap_id}",
                created_at=now,
            )
            db.add(action)

    # Confirm the flag
    flag.state = OverlapStateEnum.CONFIRMED
    flag.decided_by = current_user.id
    flag.decided_at = now

    try:
        db.commit()
        db.refresh(flag)
    except Exception:
        db.rollback()
        raise _err(
            status.HTTP_400_BAD_REQUEST,
            "BAD_REQUEST",
            "Failed to link cases due to a database error",
        )

    return _flag_to_out(flag)


# ---------------------------------------------------------------------------
# POST /overlaps/{id}/dismiss
# ---------------------------------------------------------------------------

@router.post("/{overlap_id}/dismiss", response_model=OverlapItemOut)
def dismiss_overlap(
    overlap_id: int,
    body: DismissRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dismiss an overlap flag.

    Per AGENTS.md: POST /overlaps/{id}/dismiss
    Marks the flag as DISMISSED and records who dismissed it.
    """
    flag = db.query(OverlapFlag).options(
        joinedload(OverlapFlag.institution)
    ).filter(OverlapFlag.id == overlap_id).first()

    if not flag:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Overlap flag {overlap_id} not found")

    # Only OPEN flags can be dismissed
    if flag.state != OverlapStateEnum.OPEN:
        raise _err(
            status.HTTP_409_CONFLICT,
            "CONFLICT",
            f"Overlap flag is already {flag.state.value}; only OPEN flags can be dismissed",
        )

    # RBAC check
    _check_overlap_dismiss_permission(current_user, flag, db)

    now = datetime.now(timezone.utc)

    flag.state = OverlapStateEnum.DISMISSED
    flag.decided_by = current_user.id
    flag.decided_at = now

    try:
        db.commit()
        db.refresh(flag)
    except Exception:
        db.rollback()
        raise _err(
            status.HTTP_400_BAD_REQUEST,
            "BAD_REQUEST",
            "Failed to dismiss overlap flag due to a database error",
        )

    return _flag_to_out(flag)

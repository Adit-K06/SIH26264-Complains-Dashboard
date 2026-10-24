"""Case management API router.

Endpoints per AGENTS.md:
  GET    /cases
  GET    /cases/{id}
  POST   /cases
  PATCH  /cases/{id}
  POST   /cases/{id}/actions
  POST   /cases/{id}/transfer
  POST   /cases/{id}/escalate
  POST   /cases/{id}/dispose
  POST   /cases/{id}/reopen
  GET    /cases/{id}/actions

Enforces RBAC, allowed status transitions, append-only case_actions audit trail,
and complainant_ref masking strictly as defined in AGENTS.md.
"""
from datetime import date, datetime, timedelta, timezone
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    assert_bureau_scope,
    assert_region_scope,
    get_current_user,
    should_mask_complainant_ref,
)
from app.database import get_db
from app.models import Bureau, Case, CaseAction, Category, Institution, Region, SlaRule, User
from app.models.enums import ActionTypeEnum, CaseStatusEnum, PriorityEnum, RoleEnum

router = APIRouter(prefix="/cases", tags=["cases"])

OPEN_STATUSES = {
    CaseStatusEnum.PENDING,
    CaseStatusEnum.UNDER_PROCESS,
    CaseStatusEnum.TRANSFERRED,
    CaseStatusEnum.ESCALATED,
}

# Default SLA placeholder days if no SlaRule is configured in DB
_DEFAULT_SLA_DAYS: dict[PriorityEnum, int] = {
    PriorityEnum.HIGH: 15,
    PriorityEnum.MEDIUM: 30,
    PriorityEnum.LOW: 45,
}


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _err(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message}},
    )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CaseRowOut(BaseModel):
    id: int
    case_no: str
    status: CaseStatusEnum
    institution_id: int | None = None
    institution_name: str | None = None
    bureau_id: int
    bureau_code: str | None = None
    region_id: int | None = None
    category_id: int | None = None
    category_name: str | None = None
    priority: PriorityEnum
    received_on: date | None = None
    last_action_on: datetime | None = None
    expected_disposal_on: date | None = None
    link_group_id: str | None = None

    model_config = {"from_attributes": True}


class PagedCaseResponse(BaseModel):
    items: list[CaseRowOut]
    total: int
    page: int
    page_size: int


class CaseActionOut(BaseModel):
    id: int
    case_id: int
    actor_id: int | None = None
    actor_name: str | None = None
    bureau_id: int | None = None
    action_type: ActionTypeEnum
    from_status: CaseStatusEnum | None = None
    to_status: CaseStatusEnum | None = None
    remarks: str | None = None
    attachment_id: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CaseDetailOut(BaseModel):
    id: int
    case_no: str
    status: CaseStatusEnum
    priority: PriorityEnum
    institution_id: int | None = None
    institution_name: str | None = None
    institution_aicte_id: str | None = None
    bureau_id: int
    bureau_code: str | None = None
    bureau_name: str | None = None
    region_id: int | None = None
    region_name: str | None = None
    category_id: int | None = None
    category_name: str | None = None
    assigned_officer_id: int | None = None
    assigned_officer_name: str | None = None
    received_on: date
    last_action_on: datetime | None = None
    last_action_text: str | None = None
    next_action_text: str | None = None
    expected_disposal_on: date | None = None
    summary: str
    complainant_ref: str | None = None
    source: str
    link_group_id: str | None = None
    needs_institution_review: bool
    actions: list[CaseActionOut] = []

    model_config = {"from_attributes": True}


class CaseCreate(BaseModel):
    case_no: str | None = None
    bureau_id: int
    institution_id: int | None = None
    category_id: int | None = None
    priority: PriorityEnum = PriorityEnum.MEDIUM
    summary: str
    received_on: date | None = None
    expected_disposal_on: date | None = None
    complainant_ref: str | None = None
    assigned_officer_id: int | None = None
    next_action_text: str | None = None
    source: str = "SYNTHETIC"
    needs_institution_review: bool = False


class CaseUpdate(BaseModel):
    priority: PriorityEnum | None = None
    category_id: int | None = None
    assigned_officer_id: int | None = None
    next_action_text: str | None = None
    summary: str | None = None
    needs_institution_review: bool | None = None
    expected_disposal_on: date | None = None
    status: CaseStatusEnum | None = None
    remarks: str | None = None


class ActionCreate(BaseModel):
    action_type: ActionTypeEnum = ActionTypeEnum.ACTION
    to_status: CaseStatusEnum | None = None
    remarks: str | None = None
    assigned_officer_id: int | None = None
    attachment_id: int | None = None


class TransferRequest(BaseModel):
    to_bureau_id: int | None = None
    bureau_id: int | None = None
    remarks: str | None = None


class EscalateRequest(BaseModel):
    remarks: str | None = None


class DisposeRequest(BaseModel):
    remarks: str | None = None


class ReopenRequest(BaseModel):
    remarks: str


# ---------------------------------------------------------------------------
# Transition and Permission Helpers
# ---------------------------------------------------------------------------

def _validate_transition(
    from_status: CaseStatusEnum,
    to_status: CaseStatusEnum,
    remarks: str | None = None,
) -> ActionTypeEnum:
    """Validate status transition per AGENTS.md:
    PENDING -> UNDER_PROCESS | UNDER_PROCESS -> DISPOSED | any open -> TRANSFERRED | any open -> ESCALATED
    DISPOSED -> PENDING (REOPEN; remarks required, else 422)
    Any other transition -> HTTP 409 Conflict.
    """
    if from_status == to_status:
        return ActionTypeEnum.ACTION

    # PENDING -> UNDER_PROCESS
    if from_status == CaseStatusEnum.PENDING and to_status == CaseStatusEnum.UNDER_PROCESS:
        return ActionTypeEnum.ACTION

    # UNDER_PROCESS -> DISPOSED
    if from_status == CaseStatusEnum.UNDER_PROCESS and to_status == CaseStatusEnum.DISPOSED:
        return ActionTypeEnum.DISPOSED

    # any open -> TRANSFERRED
    if from_status in OPEN_STATUSES and to_status == CaseStatusEnum.TRANSFERRED:
        return ActionTypeEnum.TRANSFERRED

    # any open -> ESCALATED
    if from_status in OPEN_STATUSES and to_status == CaseStatusEnum.ESCALATED:
        return ActionTypeEnum.ESCALATED

    # DISPOSED -> PENDING (REOPEN; remarks required, else 422)
    if from_status == CaseStatusEnum.DISPOSED and to_status == CaseStatusEnum.PENDING:
        if not remarks or not remarks.strip():
            raise _err(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "UNPROCESSABLE_ENTITY",
                "Remarks are required to reopen a disposed case",
            )
        return ActionTypeEnum.REOPENED

    raise _err(
        status.HTTP_409_CONFLICT,
        "CONFLICT",
        f"Invalid status transition from {from_status.value} to {to_status.value}",
    )


def _check_create_permission(user: User, bureau_id: int, institution_region_id: int | None) -> None:
    if user.role == RoleEnum.SENIOR_MGMT:
        raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Senior management cannot create complaint cases")
    if user.role == RoleEnum.BUREAU_OFFICER:
        if user.bureau_id != bureau_id:
            raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Bureau officers may only create cases in their own bureau")
    elif user.role == RoleEnum.REGIONAL_OFFICER:
        if institution_region_id is None or user.region_id != institution_region_id:
            raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Regional officers may only create cases for institutions in their own region")


def _check_update_permission(user: User, case_bureau_id: int, case_region_id: int | None) -> None:
    if user.role == RoleEnum.SENIOR_MGMT:
        raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Senior management has read-only access and cannot update cases")
    if user.role == RoleEnum.BUREAU_OFFICER:
        if user.bureau_id != case_bureau_id:
            raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Bureau officers may only update cases in their own bureau")
    elif user.role == RoleEnum.REGIONAL_OFFICER:
        if case_region_id is None or user.region_id != case_region_id:
            raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Regional officers may only update cases for institutions in their own region")


def _check_act_permission(user: User, case_bureau_id: int, case_region_id: int | None, is_escalation: bool = False) -> None:
    if is_escalation:
        if user.role == RoleEnum.SENIOR_MGMT or user.role == RoleEnum.ADMIN:
            return
        if user.role == RoleEnum.BUREAU_OFFICER and user.bureau_id == case_bureau_id:
            return
        if user.role == RoleEnum.REGIONAL_OFFICER and case_region_id is not None and user.region_id == case_region_id:
            return
        raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Insufficient permissions to escalate this case")

    if user.role == RoleEnum.SENIOR_MGMT:
        raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Senior management may only perform escalation actions")
    if user.role == RoleEnum.BUREAU_OFFICER:
        if user.bureau_id != case_bureau_id:
            raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Bureau officers may only act on cases in their own bureau")
    elif user.role == RoleEnum.REGIONAL_OFFICER:
        if case_region_id is None or user.region_id != case_region_id:
            raise _err(status.HTTP_403_FORBIDDEN, "FORBIDDEN", "Regional officers may only act on cases for institutions in their own region")


def _format_case_detail(case: Case, user: User) -> CaseDetailOut:
    region_id = case.institution.region_id if case.institution else None
    region_name = case.institution.region.name if (case.institution and case.institution.region) else None

    # Apply complainant ref masking strictly
    if should_mask_complainant_ref(user, case.bureau_id, region_id):
        ref = "***" if case.complainant_ref else None
    else:
        ref = case.complainant_ref

    actions = [
        CaseActionOut(
            id=act.id,
            case_id=act.case_id,
            actor_id=act.actor_id,
            actor_name=act.actor.name if act.actor else None,
            bureau_id=act.bureau_id,
            action_type=act.action_type,
            from_status=act.from_status,
            to_status=act.to_status,
            remarks=act.remarks,
            attachment_id=act.attachment_id,
            created_at=act.created_at,
        )
        for act in case.actions
    ]

    return CaseDetailOut(
        id=case.id,
        case_no=case.case_no,
        status=case.status,
        priority=case.priority,
        institution_id=case.institution_id,
        institution_name=case.institution.name if case.institution else None,
        institution_aicte_id=case.institution.aicte_permanent_id if case.institution else None,
        bureau_id=case.bureau_id,
        bureau_code=case.bureau.code if case.bureau else None,
        bureau_name=case.bureau.name if case.bureau else None,
        region_id=region_id,
        region_name=region_name,
        category_id=case.category_id,
        category_name=case.category.name if case.category else None,
        assigned_officer_id=case.assigned_officer_id,
        assigned_officer_name=case.assigned_officer.name if case.assigned_officer else None,
        received_on=case.received_on,
        last_action_on=case.last_action_on,
        last_action_text=case.last_action_text,
        next_action_text=case.next_action_text,
        expected_disposal_on=case.expected_disposal_on,
        summary=case.summary,
        complainant_ref=ref,
        source=case.source,
        link_group_id=case.link_group_id,
        needs_institution_review=case.needs_institution_review,
        actions=actions,
    )


# ---------------------------------------------------------------------------
# GET /cases
# ---------------------------------------------------------------------------

@router.get("", response_model=PagedCaseResponse)
@router.get("/", response_model=PagedCaseResponse, include_in_schema=False)
def list_cases(
    q: str | None = None,
    status: CaseStatusEnum | None = None,
    priority: PriorityEnum | None = None,
    bureau_id: int | None = None,
    region_id: int | None = None,
    category_id: int | None = None,
    institution_id: int | None = None,
    aicte_id: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    beyond_sla: bool | None = None,
    linked: bool | None = None,
    no_recent_action_days: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List and search cases with supported filters and validated pagination."""
    query = (
        db.query(Case)
        .outerjoin(Institution, Case.institution_id == Institution.id)
        .outerjoin(Bureau, Case.bureau_id == Bureau.id)
        .outerjoin(Category, Case.category_id == Category.id)
    )

    if q and q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Case.case_no.ilike(term),
                Institution.name.ilike(term),
                Case.summary.ilike(term),
            )
        )

    if status:
        query = query.filter(Case.status == status)

    if priority:
        query = query.filter(Case.priority == priority)

    if bureau_id:
        query = query.filter(Case.bureau_id == bureau_id)

    if region_id:
        query = query.filter(Institution.region_id == region_id)

    if category_id:
        query = query.filter(Case.category_id == category_id)

    if institution_id:
        query = query.filter(Case.institution_id == institution_id)

    if aicte_id and aicte_id.strip():
        query = query.filter(Institution.aicte_permanent_id.ilike(aicte_id.strip()))

    if from_date:
        query = query.filter(Case.received_on >= from_date)

    if to_date:
        query = query.filter(Case.received_on <= to_date)

    today = date.today()
    if beyond_sla is True:
        # beyond_sla = expected_disposal_on < today AND case is open
        query = query.filter(
            Case.status.in_(OPEN_STATUSES),
            Case.expected_disposal_on.isnot(None),
            Case.expected_disposal_on < today,
        )
    elif beyond_sla is False:
        query = query.filter(
            or_(
                ~Case.status.in_(OPEN_STATUSES),
                Case.expected_disposal_on.is_(None),
                Case.expected_disposal_on >= today,
            )
        )

    if linked is True:
        query = query.filter(Case.link_group_id.isnot(None))
    elif linked is False:
        query = query.filter(Case.link_group_id.is_(None))

    if no_recent_action_days is not None and no_recent_action_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=no_recent_action_days)
        query = query.filter(
            Case.status.in_(OPEN_STATUSES),
            or_(Case.last_action_on.is_(None), Case.last_action_on <= cutoff),
        )

    total = query.count()
    offset = (page - 1) * page_size
    cases = (
        query.order_by(Case.received_on.desc(), Case.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [
        CaseRowOut(
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
        for c in cases
    ]

    return PagedCaseResponse(items=items, total=total, page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# POST /cases
# ---------------------------------------------------------------------------

@router.post("", response_model=CaseDetailOut, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=CaseDetailOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_case(
    body: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new case with initial append-only action log and permission validation."""
    bureau = db.get(Bureau, body.bureau_id)
    if bureau is None:
        raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Bureau not found")

    institution = None
    if body.institution_id is not None:
        institution = db.get(Institution, body.institution_id)
        if institution is None:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Institution not found")

    if body.category_id is not None:
        category = db.get(Category, body.category_id)
        if category is None:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Category not found")

    assigned_officer = None
    if body.assigned_officer_id is not None:
        assigned_officer = db.get(User, body.assigned_officer_id)
        if assigned_officer is None or not assigned_officer.active:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer not found or inactive")

    # RBAC check
    inst_region_id = institution.region_id if institution else None
    _check_create_permission(current_user, body.bureau_id, inst_region_id)

    # Validate assignment scope if assigned_officer given
    if assigned_officer:
        if assigned_officer.role == RoleEnum.BUREAU_OFFICER and assigned_officer.bureau_id != body.bureau_id:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer belongs to a different bureau")
        if assigned_officer.role == RoleEnum.REGIONAL_OFFICER and assigned_officer.region_id != inst_region_id:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer belongs to a different region")

    rec_date = body.received_on or date.today()

    # Determine or generate case_no
    if body.case_no and body.case_no.strip():
        case_no = body.case_no.strip()
        existing = db.query(Case).filter(Case.bureau_id == body.bureau_id, Case.case_no == case_no).first()
        if existing:
            raise _err(status.HTTP_409_CONFLICT, "CONFLICT", f"Case number '{case_no}' already exists in this bureau")
    else:
        year = rec_date.year
        seq = db.query(Case).filter(Case.bureau_id == body.bureau_id).count() + 1
        case_no = f"{bureau.code}/{year}/{str(seq).zfill(6)}"
        while db.query(Case).filter(Case.bureau_id == body.bureau_id, Case.case_no == case_no).first() is not None:
            seq += 1
            case_no = f"{bureau.code}/{year}/{str(seq).zfill(6)}"

    # Compute expected_disposal_on if not supplied
    expected_disposal = body.expected_disposal_on
    if expected_disposal is None:
        rule = None
        if body.category_id:
            rule = db.query(SlaRule).filter(
                SlaRule.category_id == body.category_id,
                SlaRule.priority == body.priority,
            ).first()
        if rule is None:
            rule = db.query(SlaRule).filter(
                SlaRule.category_id.is_(None),
                SlaRule.priority == body.priority,
            ).first()
        days = rule.days_to_dispose if rule else _DEFAULT_SLA_DAYS.get(body.priority, 30)
        expected_disposal = rec_date + timedelta(days=days)

    now = datetime.now(timezone.utc)
    new_case = Case(
        case_no=case_no,
        institution_id=body.institution_id,
        bureau_id=body.bureau_id,
        category_id=body.category_id,
        status=CaseStatusEnum.PENDING,
        assigned_officer_id=body.assigned_officer_id,
        received_on=rec_date,
        last_action_on=now,
        last_action_text="Case created",
        next_action_text=body.next_action_text,
        expected_disposal_on=expected_disposal,
        priority=body.priority,
        summary=body.summary.strip(),
        complainant_ref=body.complainant_ref,
        source=body.source,
        needs_institution_review=body.needs_institution_review,
    )
    db.add(new_case)
    db.flush()

    # Append-only creation action
    action = CaseAction(
        case_id=new_case.id,
        actor_id=current_user.id,
        bureau_id=new_case.bureau_id,
        action_type=ActionTypeEnum.CREATED,
        from_status=None,
        to_status=CaseStatusEnum.PENDING,
        remarks="Case created",
        created_at=now,
    )
    db.add(action)
    db.commit()
    db.refresh(new_case)

    return _format_case_detail(new_case, current_user)


# ---------------------------------------------------------------------------
# GET /cases/{id}
# ---------------------------------------------------------------------------

@router.get("/{case_id}", response_model=CaseDetailOut)
def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve an individual case with action history and complainant_ref masking."""
    case = (
        db.query(Case)
        .options(
            joinedload(Case.institution).joinedload(Institution.region),
            joinedload(Case.bureau),
            joinedload(Case.category),
            joinedload(Case.assigned_officer),
            joinedload(Case.actions).joinedload(CaseAction.actor),
        )
        .filter(Case.id == case_id)
        .first()
    )
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    return _format_case_detail(case, current_user)


# ---------------------------------------------------------------------------
# PATCH /cases/{id}
# ---------------------------------------------------------------------------

@router.patch("/{case_id}", response_model=CaseDetailOut)
def update_case(
    case_id: int,
    body: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update permitted case fields and validate status transitions if changed."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    case_region_id = case.institution.region_id if case.institution else None
    _check_update_permission(current_user, case.bureau_id, case_region_id)

    now = datetime.now(timezone.utc)
    updated_fields = False

    if body.priority is not None and body.priority != case.priority:
        case.priority = body.priority
        updated_fields = True

    if body.category_id is not None and body.category_id != case.category_id:
        if db.get(Category, body.category_id) is None:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Category not found")
        case.category_id = body.category_id
        updated_fields = True

    if body.summary is not None and body.summary.strip() != case.summary:
        case.summary = body.summary.strip()
        updated_fields = True

    if body.next_action_text is not None:
        case.next_action_text = body.next_action_text
        updated_fields = True

    if body.needs_institution_review is not None:
        case.needs_institution_review = body.needs_institution_review
        updated_fields = True

    if body.expected_disposal_on is not None:
        case.expected_disposal_on = body.expected_disposal_on
        updated_fields = True

    # Assignment change
    if body.assigned_officer_id is not None and body.assigned_officer_id != case.assigned_officer_id:
        officer = db.get(User, body.assigned_officer_id)
        if officer is None or not officer.active:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer not found or inactive")
        if officer.role == RoleEnum.BUREAU_OFFICER and officer.bureau_id != case.bureau_id:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer belongs to a different bureau")
        if officer.role == RoleEnum.REGIONAL_OFFICER and officer.region_id != case_region_id:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer belongs to a different region")

        case.assigned_officer_id = officer.id
        action = CaseAction(
            case_id=case.id,
            actor_id=current_user.id,
            bureau_id=current_user.bureau_id or case.bureau_id,
            action_type=ActionTypeEnum.ASSIGNED,
            from_status=case.status,
            to_status=case.status,
            remarks=body.remarks or f"Assigned to {officer.name}",
            created_at=now,
        )
        db.add(action)
        case.last_action_on = now
        case.last_action_text = action.remarks
        updated_fields = True

    # Status change
    if body.status is not None and body.status != case.status:
        action_type = _validate_transition(case.status, body.status, remarks=body.remarks)
        old_status = case.status
        case.status = body.status
        action = CaseAction(
            case_id=case.id,
            actor_id=current_user.id,
            bureau_id=current_user.bureau_id or case.bureau_id,
            action_type=action_type,
            from_status=old_status,
            to_status=body.status,
            remarks=body.remarks,
            created_at=now,
        )
        db.add(action)
        case.last_action_on = now
        if body.remarks:
            case.last_action_text = body.remarks
        updated_fields = True
    elif updated_fields and not (body.assigned_officer_id and body.assigned_officer_id != case.assigned_officer_id):
        # Record a general update action if fields changed without status/assignment action
        action = CaseAction(
            case_id=case.id,
            actor_id=current_user.id,
            bureau_id=current_user.bureau_id or case.bureau_id,
            action_type=ActionTypeEnum.ACTION,
            from_status=case.status,
            to_status=case.status,
            remarks=body.remarks or "Case fields updated",
            created_at=now,
        )
        db.add(action)
        case.last_action_on = now
        case.last_action_text = action.remarks

    db.commit()
    db.refresh(case)
    return _format_case_detail(case, current_user)


# ---------------------------------------------------------------------------
# POST /cases/{id}/actions
# ---------------------------------------------------------------------------

@router.post("/{case_id}/actions", response_model=CaseActionOut, status_code=status.HTTP_201_CREATED)
def record_case_action(
    case_id: int,
    body: ActionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a case action to the append-only log with transition validation."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    case_region_id = case.institution.region_id if case.institution else None
    is_escalate = (
        body.action_type == ActionTypeEnum.ESCALATED
        or body.to_status == CaseStatusEnum.ESCALATED
    )
    _check_act_permission(current_user, case.bureau_id, case_region_id, is_escalation=is_escalate)

    now = datetime.now(timezone.utc)
    from_status = case.status
    to_status = case.status
    action_type = body.action_type

    if body.to_status is not None and body.to_status != case.status:
        action_type = _validate_transition(case.status, body.to_status, remarks=body.remarks)
        to_status = body.to_status
        case.status = body.to_status

    if body.assigned_officer_id is not None:
        officer = db.get(User, body.assigned_officer_id)
        if officer is None or not officer.active:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer not found or inactive")
        if officer.role == RoleEnum.BUREAU_OFFICER and officer.bureau_id != case.bureau_id:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer belongs to a different bureau")
        if officer.role == RoleEnum.REGIONAL_OFFICER and officer.region_id != case_region_id:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Assigned officer belongs to a different region")
        case.assigned_officer_id = officer.id
        if action_type == ActionTypeEnum.ACTION:
            action_type = ActionTypeEnum.ASSIGNED

    case.last_action_on = now
    if body.remarks:
        case.last_action_text = body.remarks

    action = CaseAction(
        case_id=case.id,
        actor_id=current_user.id,
        bureau_id=current_user.bureau_id or case.bureau_id,
        action_type=action_type,
        from_status=from_status,
        to_status=to_status,
        remarks=body.remarks,
        attachment_id=body.attachment_id,
        created_at=now,
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    return CaseActionOut(
        id=action.id,
        case_id=action.case_id,
        actor_id=action.actor_id,
        actor_name=current_user.name,
        bureau_id=action.bureau_id,
        action_type=action.action_type,
        from_status=action.from_status,
        to_status=action.to_status,
        remarks=action.remarks,
        attachment_id=action.attachment_id,
        created_at=action.created_at,
    )


# ---------------------------------------------------------------------------
# GET /cases/{id}/actions
# ---------------------------------------------------------------------------

@router.get("/{case_id}/actions", response_model=list[CaseActionOut])
def get_case_actions(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve audit action history for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    actions = (
        db.query(CaseAction)
        .options(joinedload(CaseAction.actor))
        .filter(CaseAction.case_id == case_id)
        .order_by(CaseAction.created_at.asc())
        .all()
    )
    return [
        CaseActionOut(
            id=act.id,
            case_id=act.case_id,
            actor_id=act.actor_id,
            actor_name=act.actor.name if act.actor else None,
            bureau_id=act.bureau_id,
            action_type=act.action_type,
            from_status=act.from_status,
            to_status=act.to_status,
            remarks=act.remarks,
            attachment_id=act.attachment_id,
            created_at=act.created_at,
        )
        for act in actions
    ]


# ---------------------------------------------------------------------------
# POST /cases/{id}/transfer
# ---------------------------------------------------------------------------

@router.post("/{case_id}/transfer", response_model=CaseDetailOut)
def transfer_case(
    case_id: int,
    body: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Transfer an open case to TRANSFERRED status and optionally reassign bureau."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    case_region_id = case.institution.region_id if case.institution else None
    _check_act_permission(current_user, case.bureau_id, case_region_id, is_escalation=False)

    # Allowed: any open -> TRANSFERRED
    _validate_transition(case.status, CaseStatusEnum.TRANSFERRED, remarks=body.remarks)

    target_bureau_id = body.to_bureau_id or body.bureau_id
    if target_bureau_id is not None:
        target_bureau = db.get(Bureau, target_bureau_id)
        if target_bureau is None:
            raise _err(status.HTTP_422_UNPROCESSABLE_ENTITY, "UNPROCESSABLE_ENTITY", "Target bureau not found")

    # Capture origin bureau before mutation so audit trail preserves both ends
    origin_bureau_id = case.bureau_id

    if target_bureau_id is not None:
        case.bureau_id = target_bureau_id

    now = datetime.now(timezone.utc)
    old_status = case.status
    case.status = CaseStatusEnum.TRANSFERRED
    case.last_action_on = now
    case.last_action_text = body.remarks or "Case transferred"

    action = CaseAction(
        case_id=case.id,
        actor_id=current_user.id,
        bureau_id=origin_bureau_id,
        action_type=ActionTypeEnum.TRANSFERRED,
        from_status=old_status,
        to_status=CaseStatusEnum.TRANSFERRED,
        remarks=body.remarks or "Case transferred",
        created_at=now,
    )
    db.add(action)
    db.commit()
    db.refresh(case)
    return _format_case_detail(case, current_user)


# ---------------------------------------------------------------------------
# POST /cases/{id}/escalate
# ---------------------------------------------------------------------------

@router.post("/{case_id}/escalate", response_model=CaseDetailOut)
def escalate_case(
    case_id: int,
    body: EscalateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Escalate an open case. Allowed for SENIOR_MGMT, ADMIN, and authorized officers."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    case_region_id = case.institution.region_id if case.institution else None
    _check_act_permission(current_user, case.bureau_id, case_region_id, is_escalation=True)

    # Allowed: any open -> ESCALATED
    _validate_transition(case.status, CaseStatusEnum.ESCALATED, remarks=body.remarks)

    now = datetime.now(timezone.utc)
    old_status = case.status
    case.status = CaseStatusEnum.ESCALATED
    case.last_action_on = now
    case.last_action_text = body.remarks or "Case escalated"

    action = CaseAction(
        case_id=case.id,
        actor_id=current_user.id,
        bureau_id=current_user.bureau_id or case.bureau_id,
        action_type=ActionTypeEnum.ESCALATED,
        from_status=old_status,
        to_status=CaseStatusEnum.ESCALATED,
        remarks=body.remarks or "Case escalated",
        created_at=now,
    )
    db.add(action)
    db.commit()
    db.refresh(case)
    return _format_case_detail(case, current_user)


# ---------------------------------------------------------------------------
# POST /cases/{id}/dispose
# ---------------------------------------------------------------------------

@router.post("/{case_id}/dispose", response_model=CaseDetailOut)
def dispose_case(
    case_id: int,
    body: DisposeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dispose a case. Case must be UNDER_PROCESS per AGENTS.md."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    case_region_id = case.institution.region_id if case.institution else None
    _check_act_permission(current_user, case.bureau_id, case_region_id, is_escalation=False)

    # Allowed: UNDER_PROCESS -> DISPOSED
    _validate_transition(case.status, CaseStatusEnum.DISPOSED, remarks=body.remarks)

    now = datetime.now(timezone.utc)
    old_status = case.status
    case.status = CaseStatusEnum.DISPOSED
    case.last_action_on = now
    case.last_action_text = body.remarks or "Case disposed"

    action = CaseAction(
        case_id=case.id,
        actor_id=current_user.id,
        bureau_id=current_user.bureau_id or case.bureau_id,
        action_type=ActionTypeEnum.DISPOSED,
        from_status=old_status,
        to_status=CaseStatusEnum.DISPOSED,
        remarks=body.remarks or "Case disposed",
        created_at=now,
    )
    db.add(action)
    db.commit()
    db.refresh(case)
    return _format_case_detail(case, current_user)


# ---------------------------------------------------------------------------
# POST /cases/{id}/reopen
# ---------------------------------------------------------------------------

@router.post("/{case_id}/reopen", response_model=CaseDetailOut)
def reopen_case(
    case_id: int,
    body: ReopenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reopen a DISPOSED case to PENDING. Remarks are required, else 422."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if case is None:
        raise _err(status.HTTP_404_NOT_FOUND, "NOT_FOUND", f"Case {case_id} not found")

    case_region_id = case.institution.region_id if case.institution else None
    _check_act_permission(current_user, case.bureau_id, case_region_id, is_escalation=False)

    # Allowed: DISPOSED -> PENDING with mandatory remarks
    _validate_transition(case.status, CaseStatusEnum.PENDING, remarks=body.remarks)

    now = datetime.now(timezone.utc)
    old_status = case.status
    case.status = CaseStatusEnum.PENDING
    case.last_action_on = now
    case.last_action_text = body.remarks.strip()

    action = CaseAction(
        case_id=case.id,
        actor_id=current_user.id,
        bureau_id=current_user.bureau_id or case.bureau_id,
        action_type=ActionTypeEnum.REOPENED,
        from_status=old_status,
        to_status=CaseStatusEnum.PENDING,
        remarks=body.remarks.strip(),
        created_at=now,
    )
    db.add(action)
    db.commit()
    db.refresh(case)
    return _format_case_detail(case, current_user)

"""Case creation and scan scheduling endpoints."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.overlaps import scan_overlaps
from app.api.deps import ensure_can_act_on_institution
from app.db import SessionLocal, get_db
from app.models import Bureau, Case, CaseAction, Category, Institution, Region, SlaRule, User
from app.models.enums import ActionType, CaseStatus, HardDeadlineType, Priority, SourceChannel
from app.security import get_current_user
from app.workflow import InvalidTransition, apply_transition

router = APIRouter()


class CaseCreate(BaseModel):
    case_no: str = Field(min_length=1, max_length=128)
    institution_id: UUID | None = None
    bureau_id: UUID
    category_id: UUID
    received_on: date
    summary: str = Field(min_length=1)
    priority: Priority = Priority.MEDIUM
    source_channel: SourceChannel = SourceChannel.DIRECT
    complainant_ref: str | None = Field(default=None, max_length=256)


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _days_to_dispose(db: Session, category_id: UUID, priority: str) -> int:
    specific = db.scalar(
        select(SlaRule).where(
            SlaRule.category_id == category_id,
            SlaRule.priority == priority,
        )
    )
    rule = specific or db.scalar(
        select(SlaRule).where(SlaRule.category_id.is_(None), SlaRule.priority == priority)
    )
    return rule.days_to_dispose if rule else 30


def _scan_created_institution(institution_id: str | None) -> None:
    with SessionLocal() as task_db:
        parsed_id = UUID(institution_id) if institution_id else None
        scan_overlaps(task_db, institution_id=parsed_id)
        task_db.commit()


def _case_response(case: Case) -> dict:
    return {
        "id": str(case.id),
        "case_no": case.case_no,
        "institution_id": str(case.institution_id) if case.institution_id else None,
        "bureau_id": str(case.bureau_id),
        "category_id": str(case.category_id),
        "status": _enum_value(case.status),
        "received_on": case.received_on.isoformat(),
        "expected_disposal_on": case.expected_disposal_on.isoformat() if case.expected_disposal_on else None,
        "priority": _enum_value(case.priority),
        "summary": case.summary,
        "complainant_ref": case.complainant_ref,
        "source_channel": _enum_value(case.source_channel),
        "source": case.source,
    }


def _can_read_complainant_ref(db: Session, user: User, case: Case) -> bool:
    role = _enum_value(user.role)
    if role == "ADMIN":
        return True
    if role == "BUREAU_OFFICER":
        return user.bureau_id == case.bureau_id
    if role == "REGIONAL_OFFICER" and case.institution_id is not None:
        institution = db.get(Institution, case.institution_id)
        return institution is not None and institution.region_id == user.region_id
    return False


def _case_read_payload(db: Session, case: Case, user: User, include_actions: bool = False) -> dict:
    bureau = db.get(Bureau, case.bureau_id)
    category = db.get(Category, case.category_id)
    institution = db.get(Institution, case.institution_id) if case.institution_id else None
    region = db.get(Region, institution.region_id) if institution and institution.region_id else None
    assigned = db.get(User, case.assigned_officer_id) if case.assigned_officer_id else None
    payload = {
        "id": str(case.id),
        "case_no": case.case_no,
        "institution_id": str(case.institution_id) if case.institution_id else None,
        "institution_name": institution.name if institution else None,
        "aicte_permanent_id": institution.aicte_permanent_id if institution else None,
        "bureau_id": str(case.bureau_id),
        "bureau_code": bureau.code if bureau else None,
        "bureau_name": bureau.name if bureau else None,
        "category_id": str(case.category_id),
        "category_name": category.name if category else None,
        "region_id": str(institution.region_id) if institution and institution.region_id else None,
        "status": _enum_value(case.status),
        "received_on": case.received_on.isoformat(),
        "last_action_on": case.last_action_on.isoformat() if case.last_action_on else None,
        "last_action_text": case.last_action_text,
        "next_action_text": case.next_action_text,
        "expected_disposal_on": case.expected_disposal_on.isoformat() if case.expected_disposal_on else None,
        "priority": _enum_value(case.priority),
        "summary": case.summary,
        "complainant_ref": case.complainant_ref if _can_read_complainant_ref(db, user, case) else None,
        "source_channel": _enum_value(case.source_channel),
        "source": case.source,
        "hard_deadline_on": case.hard_deadline_on.isoformat() if case.hard_deadline_on else None,
        "hard_deadline_type": _enum_value(case.hard_deadline_type),
        "link_group_id": str(case.link_group_id) if case.link_group_id else None,
        "needs_institution_review": bool(case.needs_institution_review),
        "assigned_officer_id": str(case.assigned_officer_id) if case.assigned_officer_id else None,
        "assigned_officer_name": assigned.name if assigned else None,
        "institution": ({
            "id": str(institution.id),
            "aicte_permanent_id": institution.aicte_permanent_id,
            "name": institution.name,
            "address": institution.address,
            "district": institution.district,
            "state": institution.state,
            "region_id": str(institution.region_id) if institution.region_id else None,
            "region_name": region.name if region else None,
            "type": institution.type,
            "status": institution.status,
            "source": institution.source,
        } if institution else None),
    }
    if include_actions:
        actions = db.scalars(
            select(CaseAction)
            .where(CaseAction.case_id == case.id)
            .order_by(CaseAction.created_at, CaseAction.id)
        ).all()
        payload["actions"] = []
        for action in actions:
            actor = db.get(User, action.actor_id) if action.actor_id else None
            action_bureau = db.get(Bureau, action.bureau_id) if action.bureau_id else None
            payload["actions"].append({
                "id": str(action.id),
                "case_id": str(action.case_id),
                "action_type": _enum_value(action.action_type),
                "action_tag": action.action_tag,
                "from_status": _enum_value(action.from_status) if action.from_status else None,
                "to_status": _enum_value(action.to_status) if action.to_status else None,
                "remarks": action.remarks,
                "created_at": action.created_at.isoformat() if action.created_at else None,
                "actor_name": actor.name if actor else None,
                "bureau_code": action_bureau.code if action_bureau else None,
            })
    return payload


@router.get("/cases")
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    q: str | None = None,
    institution_id: UUID | None = None,
    aicte_id: str | None = None,
    bureau_id: UUID | None = None,
    region_id: UUID | None = None,
    category_id: UUID | None = None,
    case_status: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    beyond_sla: bool | None = None,
    no_recent_action_days: int | None = Query(default=None, ge=0),
    linked: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
):
    statement = select(Case).outerjoin(Institution, Case.institution_id == Institution.id)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(or_(
            Case.case_no.ilike(pattern),
            Case.summary.ilike(pattern),
            Institution.name.ilike(pattern),
            Institution.aicte_permanent_id.ilike(pattern),
        ))
    if institution_id is not None:
        statement = statement.where(Case.institution_id == institution_id)
    if aicte_id:
        statement = statement.where(Institution.aicte_permanent_id == aicte_id)
    if bureau_id is not None:
        statement = statement.where(Case.bureau_id == bureau_id)
    if region_id is not None:
        statement = statement.where(Institution.region_id == region_id)
    if category_id is not None:
        statement = statement.where(Case.category_id == category_id)
    if case_status:
        statement = statement.where(Case.status == case_status)
    if priority:
        statement = statement.where(Case.priority == priority)
    if from_date is not None:
        statement = statement.where(Case.received_on >= from_date)
    if to_date is not None:
        statement = statement.where(Case.received_on <= to_date)
    if beyond_sla is True:
        statement = statement.where(
            Case.status != CaseStatus.DISPOSED.value,
            Case.expected_disposal_on.is_not(None),
            Case.expected_disposal_on < date.today(),
        )
    elif beyond_sla is False:
        statement = statement.where(or_(
            Case.status == CaseStatus.DISPOSED.value,
            Case.expected_disposal_on.is_(None),
            Case.expected_disposal_on >= date.today(),
        ))
    if no_recent_action_days is not None:
        cutoff = date.today() - timedelta(days=no_recent_action_days)
        statement = statement.where(
            func.coalesce(func.date(Case.last_action_on), Case.received_on) <= cutoff.isoformat()
        )
    if linked is True:
        statement = statement.where(Case.link_group_id.is_not(None))
    elif linked is False:
        statement = statement.where(Case.link_group_id.is_(None))

    total = db.scalar(select(func.count()).select_from(
        statement.with_only_columns(Case.id).order_by(None).subquery()
    )) or 0
    cases = db.scalars(
        statement.order_by(Case.received_on.desc(), Case.case_no)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_case_read_payload(db, case, user) for case in cases],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/cases/{case_id}")
def get_case(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "CASE_NOT_FOUND", "message": "Case was not found."},
        )
    return _case_read_payload(db, case, user, include_actions=True)


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    bureau = db.get(Bureau, payload.bureau_id)
    category = db.get(Category, payload.category_id)
    institution = db.get(Institution, payload.institution_id) if payload.institution_id else None
    if bureau is None or category is None or (payload.institution_id and institution is None):
        raise HTTPException(
            status_code=404,
            detail={"code": "REFERENCE_NOT_FOUND", "message": "Bureau, category, or institution was not found."},
        )
    ensure_can_act_on_institution(db, user, bureau.id, institution.id if institution else None)
    priority = _enum_value(payload.priority)
    days = _days_to_dispose(db, category.id, priority)
    case = Case(
        case_no=payload.case_no,
        institution_id=institution.id if institution else None,
        bureau_id=bureau.id,
        category_id=category.id,
        status=CaseStatus.PENDING.value,
        assigned_officer_id=user.id,
        received_on=payload.received_on,
        last_action_text="Synthetic case created.",
        next_action_text="Review submissions and coordinate next steps.",
        expected_disposal_on=payload.received_on + timedelta(days=days),
        priority=priority,
        summary=payload.summary,
        complainant_ref=payload.complainant_ref,
        source_channel=_enum_value(payload.source_channel),
        hard_deadline_type=HardDeadlineType.NONE.value,
        source="SYNTHETIC",
    )
    db.add(case)
    try:
        db.flush()
        db.add(
            CaseAction(
                case_id=case.id,
                actor_id=user.id,
                bureau_id=bureau.id,
                action_type=ActionType.CREATED.value,
                from_status=None,
                to_status=CaseStatus.PENDING.value,
                remarks="Synthetic case created.",
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={"code": "CASE_CONFLICT", "message": "That case number is already used in this bureau."},
        )
    db.refresh(case)
    background_tasks.add_task(
        _scan_created_institution,
        str(institution.id) if institution else None,
    )
    return _case_response(case)


def _check_case_permission(db: Session, user: User, case: Case, is_escalate: bool = False):
    role = _enum_value(user.role)
    if role == "ADMIN":
        return
    if is_escalate and role == "SENIOR_MGMT":
        return
    if role == "BUREAU_OFFICER":
        if user.bureau_id != case.bureau_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Bureau officers can only act on cases in their own bureau."},
            )
        return
    if role == "REGIONAL_OFFICER":
        inst = db.get(Institution, case.institution_id) if case.institution_id else None
        if not inst or inst.region_id != user.region_id:
            raise HTTPException(
                status_code=403,
                detail={"code": "FORBIDDEN", "message": "Regional officers can only act on cases in their region."},
            )
        return
    raise HTTPException(
        status_code=403,
        detail={"code": "FORBIDDEN", "message": "Action not permitted for this role."},
    )


class CaseActionRequest(BaseModel):
    action_type: str = "ACTION"
    to_status: str | None = None
    remarks: str | None = None


class TransferRequest(BaseModel):
    to_bureau_id: UUID | None = None
    remarks: str | None = None


class SimpleRemarksRequest(BaseModel):
    remarks: str | None = None


@router.post("/cases/{case_id}/actions")
def perform_case_action(
    case_id: UUID,
    payload: CaseActionRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case was not found."})
    _check_case_permission(db, user, case)

    to_status = payload.to_status
    if not to_status:
        current_status = _enum_value(case.status)
        if current_status == CaseStatus.PENDING.value:
            to_status = CaseStatus.UNDER_PROCESS.value
        else:
            to_status = current_status

    try:
        apply_transition(db, case, user, payload.action_type, to_status, payload.remarks)
        db.commit()
    except InvalidTransition as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": str(e)})

    db.refresh(case)
    return _case_read_payload(db, case, user, include_actions=True)


@router.post("/cases/{case_id}/transfer")
def transfer_case(
    case_id: UUID,
    payload: TransferRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case was not found."})
    _check_case_permission(db, user, case)

    try:
        apply_transition(db, case, user, ActionType.TRANSFERRED.value, CaseStatus.TRANSFERRED.value, payload.remarks)
        if payload.to_bureau_id:
            case.bureau_id = payload.to_bureau_id
        db.commit()
    except InvalidTransition as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": str(e)})

    db.refresh(case)
    return _case_read_payload(db, case, user, include_actions=True)


@router.post("/cases/{case_id}/escalate")
def escalate_case(
    case_id: UUID,
    payload: SimpleRemarksRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case was not found."})
    _check_case_permission(db, user, case, is_escalate=True)

    try:
        apply_transition(db, case, user, ActionType.ESCALATED.value, CaseStatus.ESCALATED.value, payload.remarks)
        db.commit()
    except InvalidTransition as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": str(e)})

    db.refresh(case)
    return _case_read_payload(db, case, user, include_actions=True)


@router.post("/cases/{case_id}/dispose")
def dispose_case(
    case_id: UUID,
    payload: SimpleRemarksRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case was not found."})
    _check_case_permission(db, user, case)

    try:
        apply_transition(db, case, user, ActionType.DISPOSED.value, CaseStatus.DISPOSED.value, payload.remarks)
        db.commit()
    except InvalidTransition as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": str(e)})

    db.refresh(case)
    return _case_read_payload(db, case, user, include_actions=True)


@router.post("/cases/{case_id}/reopen")
def reopen_case(
    case_id: UUID,
    payload: SimpleRemarksRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail={"code": "CASE_NOT_FOUND", "message": "Case was not found."})
    _check_case_permission(db, user, case)

    if not payload.remarks or not payload.remarks.strip():
        raise HTTPException(
            status_code=422,
            detail={"code": "VALIDATION_ERROR", "message": "Reopening a case requires remarks."},
        )

    try:
        apply_transition(db, case, user, ActionType.REOPENED.value, CaseStatus.PENDING.value, payload.remarks)
        db.commit()
    except InvalidTransition as e:
        db.rollback()
        raise HTTPException(status_code=409, detail={"code": "CONFLICT", "message": str(e)})

    db.refresh(case)
    return _case_read_payload(db, case, user, include_actions=True)

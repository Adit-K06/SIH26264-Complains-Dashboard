"""Overlap review and coordination endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.overlaps import dismiss_flag, scan_overlaps
from app.api.deps import ensure_can_act_on_cases, require_admin
from app.db import get_db
from app.models import Bureau, Case, CaseAction, CaseLink, Institution, OverlapFlag, User
from app.models.enums import ActionType, LinkType, OverlapState, OverlapTier, Role
from app.security import get_current_user

router = APIRouter()


class LinkRequest(BaseModel):
    lead_bureau_id: UUID
    note: str = Field(default="", max_length=4000)


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _case_payload(db: Session, case: Case, user: User) -> dict:
    bureau = db.get(Bureau, case.bureau_id)
    user_role = _value(user.role)
    can_view_complainant_ref = user_role == Role.ADMIN.value
    if user_role == Role.BUREAU_OFFICER.value:
        can_view_complainant_ref = user.bureau_id == case.bureau_id
    elif user_role == Role.REGIONAL_OFFICER.value and case.institution_id is not None:
        institution = db.get(Institution, case.institution_id)
        can_view_complainant_ref = (
            institution is not None and institution.region_id == user.region_id
        )
    return {
        "id": str(case.id),
        "case_no": case.case_no,
        "bureau_id": str(case.bureau_id),
        "bureau_code": bureau.code if bureau else None,
        "category_id": str(case.category_id),
        "status": _value(case.status),
        "received_on": case.received_on.isoformat(),
        "summary": case.summary,
        "complainant_ref": case.complainant_ref if can_view_complainant_ref else None,
    }


def _flag_payload(db: Session, flag: OverlapFlag, user: User) -> dict:
    institution = db.get(Institution, flag.institution_id)
    if _value(flag.tier) == OverlapTier.B.value:
        cases = [
            db.get(Case, case_id)
            for case_id in (flag.case_a, flag.case_b)
            if case_id is not None
        ]
    else:
        cases = db.scalars(
            select(Case).where(
                Case.institution_id == flag.institution_id,
                Case.status != "DISPOSED",
            ).order_by(Case.received_on, Case.case_no)
        ).all()
    return {
        "id": str(flag.id),
        "institution_id": str(flag.institution_id),
        "institution_name": institution.name if institution else None,
        "tier": _value(flag.tier),
        "score": flag.score,
        "reasons": flag.reasons,
        "state": _value(flag.state),
        "created_at": flag.created_at.isoformat() if flag.created_at else None,
        "decided_at": flag.decided_at.isoformat() if flag.decided_at else None,
        "cases": [_case_payload(db, case, user) for case in cases if case is not None],
    }


@router.get("/overlaps")
def list_overlaps(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    tier: str | None = None,
    state: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    statement = select(OverlapFlag)
    if tier is not None:
        if tier not in {item.value for item in OverlapTier}:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_TIER", "message": "Tier must be A or B."},
            )
        statement = statement.where(OverlapFlag.tier == tier)
    if state is not None:
        if state not in {item.value for item in OverlapState}:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_STATE", "message": "Unknown overlap state."},
            )
        statement = statement.where(OverlapFlag.state == state)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    flags = db.scalars(
        statement.order_by(OverlapFlag.created_at.desc(), OverlapFlag.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_flag_payload(db, flag, user) for flag in flags],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/overlaps/scan")
def scan_endpoint(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    require_admin(user)
    result = scan_overlaps(db)
    db.commit()
    return result


@router.post("/overlaps/{overlap_id}/link")
def link_overlap(
    overlap_id: UUID,
    payload: LinkRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    flag = db.get(OverlapFlag, overlap_id)
    if flag is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "OVERLAP_NOT_FOUND", "message": "Overlap flag was not found."},
        )
    if _value(flag.tier) != OverlapTier.B.value or flag.case_a is None or flag.case_b is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "PAIR_REQUIRED", "message": "Only a Tier B case pair can be linked."},
        )
    case_a, case_b = db.get(Case, flag.case_a), db.get(Case, flag.case_b)
    if case_a is None or case_b is None:
        raise HTTPException(
            status_code=409,
            detail={"code": "CASES_MISSING", "message": "The cases for this overlap are no longer available."},
        )
    ensure_can_act_on_cases(db, user, [case_a, case_b])
    lead_bureau = db.get(Bureau, payload.lead_bureau_id)
    if lead_bureau is None or lead_bureau.id not in {case_a.bureau_id, case_b.bureau_id}:
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_LEAD_BUREAU", "message": "Lead bureau must own one of the linked cases."},
        )
    if _value(flag.state) == OverlapState.DISMISSED.value:
        raise HTTPException(
            status_code=409,
            detail={"code": "OVERLAP_DISMISSED", "message": "A dismissed overlap must be re-scanned after its source changes."},
        )
    if _value(flag.state) == OverlapState.CONFIRMED.value:
        group_id = db.scalar(
            select(CaseLink.group_id)
            .where(CaseLink.case_id.in_([case_a.id, case_b.id]))
            .limit(1)
        )
        return {"id": str(flag.id), "state": "CONFIRMED", "group_id": str(group_id) if group_id else None}

    group_id = uuid4()
    now = datetime.now(timezone.utc)
    note = payload.note.strip()
    for case in (case_a, case_b):
        case.link_group_id = group_id
        db.add(
            CaseLink(
                group_id=group_id,
                case_id=case.id,
                linked_by=user.id,
                lead_bureau_id=lead_bureau.id,
                link_type=LinkType.CROSS_BUREAU.value,
                note=note,
                created_at=now,
            )
        )
        db.add(
            CaseAction(
                case_id=case.id,
                actor_id=user.id,
                bureau_id=case.bureau_id,
                action_type=ActionType.LINKED.value,
                from_status=None,
                to_status=None,
                remarks=note or f"Linked as group {group_id}.",
                created_at=now,
            )
        )
    flag.state = OverlapState.CONFIRMED.value
    flag.decided_by = user.id
    flag.decided_at = now
    db.commit()
    return {"id": str(flag.id), "state": "CONFIRMED", "group_id": str(group_id)}


@router.post("/overlaps/{overlap_id}/dismiss")
def dismiss_overlap(
    overlap_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    flag = db.get(OverlapFlag, overlap_id)
    if flag is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "OVERLAP_NOT_FOUND", "message": "Overlap flag was not found."},
        )
    if _value(flag.state) == OverlapState.CONFIRMED.value:
        raise HTTPException(
            status_code=409,
            detail={"code": "OVERLAP_CONFIRMED", "message": "A confirmed overlap cannot be dismissed."},
        )
    if _value(flag.tier) == OverlapTier.B.value:
        cases = [db.get(Case, case_id) for case_id in (flag.case_a, flag.case_b) if case_id]
    else:
        cases = db.scalars(
            select(Case).where(
                Case.institution_id == flag.institution_id,
                Case.status != "DISPOSED",
            )
        ).all()
    ensure_can_act_on_cases(db, user, [case for case in cases if case is not None])
    dismiss_flag(db, flag, user)
    db.commit()
    return {"id": str(flag.id), "state": _value(flag.state), "decided_at": flag.decided_at.isoformat() if flag.decided_at else None}

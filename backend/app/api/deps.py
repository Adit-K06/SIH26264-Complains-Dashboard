"""Shared authorization helpers for API routes."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Case, Institution, User
from app.models.enums import Role


def role_value(user: User) -> str:
    return user.role.value if hasattr(user.role, "value") else str(user.role)


def require_admin(user: User) -> User:
    if role_value(user) != Role.ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "Administrator access is required."},
        )
    return user


def ensure_can_act_on_institution(
    db: Session,
    user: User,
    bureau_id,
    institution_id,
) -> None:
    role = role_value(user)
    if role == Role.ADMIN.value:
        return
    if role == Role.BUREAU_OFFICER.value and user.bureau_id == bureau_id:
        return
    if role == Role.REGIONAL_OFFICER.value and institution_id is not None:
        institution = db.get(Institution, institution_id)
        if institution is not None and institution.region_id == user.region_id:
            return
    raise HTTPException(
        status_code=403,
        detail={"code": "FORBIDDEN", "message": "You cannot act outside your bureau or region."},
    )


def ensure_can_act_on_cases(db: Session, user: User, cases: list[Case]) -> None:
    if role_value(user) == Role.ADMIN.value:
        return
    if not cases:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "No cases are available for this action."},
        )
    if role_value(user) == Role.BUREAU_OFFICER.value:
        allowed = all(case.bureau_id == user.bureau_id for case in cases)
    elif role_value(user) == Role.REGIONAL_OFFICER.value:
        institutions = {
            case.institution_id: db.get(Institution, case.institution_id)
            for case in cases
            if case.institution_id is not None
        }
        allowed = all(
            institution is not None and institution.region_id == user.region_id
            for institution in institutions.values()
        )
    else:
        allowed = False
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail={"code": "FORBIDDEN", "message": "You cannot act outside your bureau or region."},
        )
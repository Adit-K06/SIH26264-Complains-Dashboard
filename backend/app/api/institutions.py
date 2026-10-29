"""Institution listing and detail endpoints."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.cases import _case_read_payload
from app.db import get_db
from app.models import Case, Institution, Region, User
from app.security import get_current_user

router = APIRouter()


def _institution_payload(db: Session, inst: Institution) -> dict:
    region = db.get(Region, inst.region_id) if inst.region_id else None
    return {
        "id": str(inst.id),
        "aicte_permanent_id": inst.aicte_permanent_id,
        "name": inst.name,
        "address": inst.address,
        "district": inst.district,
        "state": inst.state,
        "region_id": str(inst.region_id) if inst.region_id else None,
        "region_name": region.name if region else None,
        "type": inst.type,
        "status": inst.status,
        "source": inst.source,
    }


@router.get("/institutions")
def list_institutions(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    q: str | None = None,
    region_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
):
    stmt = select(Institution)
    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Institution.name.ilike(term),
                Institution.aicte_permanent_id.ilike(term),
                Institution.address.ilike(term),
            )
        )
    if region_id is not None:
        stmt = stmt.where(Institution.region_id == region_id)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(
        stmt.order_by(Institution.aicte_permanent_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [_institution_payload(db, inst) for inst in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/institutions/{institution_id}")
def get_institution(
    institution_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    inst = db.get(Institution, institution_id)
    if inst is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "INSTITUTION_NOT_FOUND", "message": "Institution was not found."},
        )
    return _institution_payload(db, inst)


@router.get("/institutions/{institution_id}/cases")
def get_institution_cases(
    institution_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
):
    inst = db.get(Institution, institution_id)
    if inst is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "INSTITUTION_NOT_FOUND", "message": "Institution was not found."},
        )

    stmt = select(Case).where(Case.institution_id == institution_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    cases = db.scalars(
        stmt.order_by(Case.received_on.desc(), Case.case_no)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [_case_read_payload(db, case, user) for case in cases],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


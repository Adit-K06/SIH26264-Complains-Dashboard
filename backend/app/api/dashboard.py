"""Dashboard summary endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics import ageing_rows, dashboard_summary, monthly_rows, workload_rows
from app.db import get_db
from app.models import User
from app.security import get_current_user

router = APIRouter()


@router.get("/dashboard/summary")
def summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    return dashboard_summary(db)


@router.get("/dashboard/workload")
def workload(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    items = workload_rows(db)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items)}


@router.get("/dashboard/ageing")
def ageing(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    items = ageing_rows(db)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items)}


@router.get("/dashboard/trend")
def trend(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    items = monthly_rows(db)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items)}
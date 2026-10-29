"""Alert list and acknowledgement endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Alert, User
from app.security import get_current_user

router = APIRouter()


def _value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _alert_payload(alert: Alert) -> dict:
    return {
        "id": str(alert.id),
        "type": _value(alert.type),
        "case_id": str(alert.case_id) if alert.case_id else None,
        "institution_id": str(alert.institution_id) if alert.institution_id else None,
        "target_role": _value(alert.target_role) if alert.target_role else None,
        "target_bureau_id": str(alert.target_bureau_id) if alert.target_bureau_id else None,
        "message": alert.message,
        "due_on": alert.due_on.isoformat() if alert.due_on else None,
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "read_at": alert.read_at.isoformat() if alert.read_at else None,
    }


@router.get("/alerts")
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    unread_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    statement = select(Alert)
    if unread_only:
        statement = statement.where(Alert.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    alerts = db.scalars(
        statement.order_by(Alert.created_at.desc(), Alert.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_alert_payload(alert) for alert in alerts],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "ALERT_NOT_FOUND", "message": "Alert was not found."},
        )
    if alert.read_at is None:
        alert.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)
    return _alert_payload(alert)
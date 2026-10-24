"""Alerts API router.

Endpoints per AGENTS.md:
  GET /alerts           – list alerts with pagination, read/unread filters, and RBAC scoping
  POST /alerts/{id}/read – mark an alert as read
  POST /alerts/generate – deterministic evaluation and generation of SLA alerts with deduplication

Deduplication rule per AGENTS.md:
  "Dedupe: one per (case_id, type, day)."
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Alert, Bureau, Case, Institution, SlaRule, User
from app.models.enums import AlertTypeEnum, CaseStatusEnum, OPEN_CASE_STATUSES, PriorityEnum, RoleEnum

router = APIRouter(prefix="/alerts", tags=["alerts"])

_DEFAULT_SLA_DAYS: dict[PriorityEnum, int] = {
    PriorityEnum.HIGH: 15,
    PriorityEnum.MEDIUM: 30,
    PriorityEnum.LOW: 45,
}


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: AlertTypeEnum
    case_id: Optional[int] = None
    case_no: Optional[str] = None
    institution_id: Optional[int] = None
    institution_name: Optional[str] = None
    target_role: Optional[RoleEnum] = None
    target_bureau_id: Optional[int] = None
    target_bureau_code: Optional[str] = None
    message: str
    due_on: Optional[date] = None
    created_at: datetime
    read_at: Optional[datetime] = None


class AlertList(BaseModel):
    items: list[AlertOut]
    total: int
    page: int
    page_size: int


class GenerateAlertsResult(BaseModel):
    generated_count: int
    evaluated_cases_count: int
    skipped_duplicates_count: int
    types_breakdown: dict[str, int]


def _alert_exists_today(db: Session, case_id: int, alert_type: AlertTypeEnum, today: date) -> bool:
    """Check if an alert for (case_id, type) was already created today."""
    start_of_day = datetime.combine(today, time.min).replace(tzinfo=timezone.utc)
    end_of_day = datetime.combine(today, time.max).replace(tzinfo=timezone.utc)
    existing = db.query(Alert.id).filter(
        Alert.case_id == case_id,
        Alert.type == alert_type,
        Alert.created_at >= start_of_day,
        Alert.created_at <= end_of_day,
    ).first()
    return existing is not None


def _check_alert_scope(user: User, alert: Alert, db: Session) -> bool:
    """Check if user has permission to view/act on the given alert."""
    if user.role in {RoleEnum.ADMIN, RoleEnum.SENIOR_MGMT}:
        return True

    if user.role == RoleEnum.BUREAU_OFFICER:
        if alert.target_bureau_id is not None:
            return alert.target_bureau_id == user.bureau_id
        if alert.case_id is not None:
            c = db.get(Case, alert.case_id)
            return c is not None and c.bureau_id == user.bureau_id
        return False

    if user.role == RoleEnum.REGIONAL_OFFICER:
        inst_id = alert.institution_id
        if inst_id is None and alert.case_id is not None:
            c = db.get(Case, alert.case_id)
            if c:
                inst_id = c.institution_id
        if inst_id is not None:
            inst = db.get(Institution, inst_id)
            return inst is not None and inst.region_id == user.region_id
        return False

    return False


@router.get("", response_model=AlertList)
def list_alerts(
    unread_only: bool = Query(False),
    type: Optional[AlertTypeEnum] = Query(None),
    case_id: Optional[int] = Query(None),
    institution_id: Optional[int] = Query(None),
    target_bureau_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve alerts with role-based scoping and filtering."""
    query = db.query(Alert)

    # Scoping by role
    if current_user.role == RoleEnum.BUREAU_OFFICER:
        # Bureau officer sees alerts matching target_bureau_id OR cases in their bureau
        query = query.outerjoin(Case, Alert.case_id == Case.id).filter(
            or_(
                Alert.target_bureau_id == current_user.bureau_id,
                and_(Alert.case_id.isnot(None), Case.bureau_id == current_user.bureau_id),
            )
        )
    elif current_user.role == RoleEnum.REGIONAL_OFFICER:
        # Regional officer sees alerts where institution is in their region
        query = query.outerjoin(Case, Alert.case_id == Case.id).outerjoin(
            Institution,
            or_(
                Alert.institution_id == Institution.id,
                Case.institution_id == Institution.id,
            ),
        ).filter(
            Institution.region_id == current_user.region_id
        )

    # Specific filters
    if unread_only:
        query = query.filter(Alert.read_at.is_(None))
    if type is not None:
        query = query.filter(Alert.type == type)
    if case_id is not None:
        query = query.filter(Alert.case_id == case_id)
    if institution_id is not None:
        query = query.filter(Alert.institution_id == institution_id)
    if target_bureau_id is not None:
        if current_user.role == RoleEnum.BUREAU_OFFICER and target_bureau_id != current_user.bureau_id:
            # Query will result in empty
            query = query.filter(Alert.target_bureau_id == target_bureau_id)
        else:
            query = query.filter(Alert.target_bureau_id == target_bureau_id)

    total = query.count()
    alerts = (
        query.order_by(Alert.read_at.asc().nulls_first(), Alert.created_at.desc(), Alert.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for a in alerts:
        case_obj = a.case
        inst_obj = a.institution or (case_obj.institution if case_obj else None)
        bureau_obj = a.target_bureau or (case_obj.bureau if case_obj else None)

        items.append(
            AlertOut(
                id=a.id,
                type=a.type,
                case_id=a.case_id,
                case_no=case_obj.case_no if case_obj else None,
                institution_id=a.institution_id or (inst_obj.id if inst_obj else None),
                institution_name=inst_obj.name if inst_obj else None,
                target_role=a.target_role,
                target_bureau_id=a.target_bureau_id or (bureau_obj.id if bureau_obj else None),
                target_bureau_code=bureau_obj.code if bureau_obj else None,
                message=a.message,
                due_on=a.due_on,
                created_at=a.created_at,
                read_at=a.read_at,
            )
        )

    return AlertList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{id}/read", response_model=AlertOut)
def mark_alert_read(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark an alert as read."""
    alert = db.get(Alert, id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"Alert {id} not found"}},
        )

    if not _check_alert_scope(current_user, alert, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Cannot mark out-of-scope alert as read"}},
        )

    if alert.read_at is None:
        alert.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(alert)

    case_obj = alert.case
    inst_obj = alert.institution or (case_obj.institution if case_obj else None)
    bureau_obj = alert.target_bureau or (case_obj.bureau if case_obj else None)

    return AlertOut(
        id=alert.id,
        type=alert.type,
        case_id=alert.case_id,
        case_no=case_obj.case_no if case_obj else None,
        institution_id=alert.institution_id or (inst_obj.id if inst_obj else None),
        institution_name=inst_obj.name if inst_obj else None,
        target_role=alert.target_role,
        target_bureau_id=alert.target_bureau_id or (bureau_obj.id if bureau_obj else None),
        target_bureau_code=bureau_obj.code if bureau_obj else None,
        message=alert.message,
        due_on=alert.due_on,
        created_at=alert.created_at,
        read_at=alert.read_at,
    )


@router.post("/generate", response_model=GenerateAlertsResult)
def generate_alerts(
    bureau_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deterministically evaluate open cases against SLA rules and generate alerts.

    Adheres strictly to the deduplication constraint:
      "Dedupe: one per (case_id, type, day)."
    """
    if current_user.role == RoleEnum.SENIOR_MGMT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Senior management is read-only and cannot generate alerts"}},
        )
    elif current_user.role == RoleEnum.REGIONAL_OFFICER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Regional officers cannot trigger alert generation"}},
        )
    elif current_user.role == RoleEnum.BUREAU_OFFICER:
        if bureau_id is not None and bureau_id != current_user.bureau_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": {"code": "FORBIDDEN", "message": "Bureau officers may only generate alerts for their own bureau"}},
            )
        bureau_id = current_user.bureau_id
    elif current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "FORBIDDEN", "message": "Insufficient permissions to generate alerts"}},
        )

    today = date.today()
    query = db.query(Case).filter(Case.status.in_(OPEN_CASE_STATUSES))
    if bureau_id is not None:
        query = query.filter(Case.bureau_id == bureau_id)

    cases = query.all()

    rules = db.query(SlaRule).all()
    rule_map = {(r.category_id, r.priority): r for r in rules}

    generated_count = 0
    skipped_duplicates_count = 0
    type_counts: dict[str, int] = {
        "OVERDUE": 0,
        "DUE_SOON": 0,
        "REMINDER": 0,
        "ESCALATION": 0,
    }

    alerts_to_add: list[Alert] = []

    for c in cases:
        rule = rule_map.get((c.category_id, c.priority)) or rule_map.get((None, c.priority))
        days_to_dispose = rule.days_to_dispose if rule else _DEFAULT_SLA_DAYS.get(c.priority, 30)
        warn_pct = rule.warn_at_pct if rule else 80
        reminder_days = rule.reminder_after_days if rule else 7
        escalate_days = rule.escalate_after_days if rule else 30

        exp_date = c.expected_disposal_on or (c.received_on + timedelta(days=days_to_dispose))
        elapsed_days = (today - c.received_on).days
        remaining_days = (exp_date - today).days

        # Determine days since last recorded action
        if c.last_action_on:
            last_action_date = c.last_action_on.date() if isinstance(c.last_action_on, datetime) else c.last_action_on
            days_since_action = (today - last_action_date).days
        else:
            days_since_action = elapsed_days

        # 1. OVERDUE
        if exp_date < today:
            overdue_by = abs(remaining_days)
            if _alert_exists_today(db, c.id, AlertTypeEnum.OVERDUE, today):
                skipped_duplicates_count += 1
            else:
                alert = Alert(
                    type=AlertTypeEnum.OVERDUE,
                    case_id=c.id,
                    institution_id=c.institution_id,
                    target_role=RoleEnum.BUREAU_OFFICER,
                    target_bureau_id=c.bureau_id,
                    message=f"Case {c.case_no} is overdue by {overdue_by} day(s) (was due on {exp_date}).",
                    due_on=exp_date,
                    created_at=datetime.now(timezone.utc),
                )
                alerts_to_add.append(alert)
                generated_count += 1
                type_counts["OVERDUE"] += 1
        else:
            # 2. DUE_SOON (only if not overdue)
            is_due_soon = False
            total_window = (exp_date - c.received_on).days
            if total_window > 0 and (elapsed_days / total_window * 100 >= warn_pct or remaining_days <= 3):
                is_due_soon = True

            if is_due_soon:
                if _alert_exists_today(db, c.id, AlertTypeEnum.DUE_SOON, today):
                    skipped_duplicates_count += 1
                else:
                    alert = Alert(
                        type=AlertTypeEnum.DUE_SOON,
                        case_id=c.id,
                        institution_id=c.institution_id,
                        target_role=RoleEnum.BUREAU_OFFICER,
                        target_bureau_id=c.bureau_id,
                        message=f"Case {c.case_no} is due soon on {exp_date} ({remaining_days} day(s) remaining).",
                        due_on=exp_date,
                        created_at=datetime.now(timezone.utc),
                    )
                    alerts_to_add.append(alert)
                    generated_count += 1
                    type_counts["DUE_SOON"] += 1

        # 3. REMINDER (inactivity)
        if days_since_action >= reminder_days:
            if _alert_exists_today(db, c.id, AlertTypeEnum.REMINDER, today):
                skipped_duplicates_count += 1
            else:
                alert = Alert(
                    type=AlertTypeEnum.REMINDER,
                    case_id=c.id,
                    institution_id=c.institution_id,
                    target_role=RoleEnum.BUREAU_OFFICER,
                    target_bureau_id=c.bureau_id,
                    message=f"Case {c.case_no} has had no action recorded for {days_since_action} day(s).",
                    due_on=exp_date,
                    created_at=datetime.now(timezone.utc),
                )
                alerts_to_add.append(alert)
                generated_count += 1
                type_counts["REMINDER"] += 1

        # 4. ESCALATION (elapsed beyond threshold or escalated status)
        if elapsed_days >= escalate_days or c.status == CaseStatusEnum.ESCALATED:
            if _alert_exists_today(db, c.id, AlertTypeEnum.ESCALATION, today):
                skipped_duplicates_count += 1
            else:
                alert = Alert(
                    type=AlertTypeEnum.ESCALATION,
                    case_id=c.id,
                    institution_id=c.institution_id,
                    target_role=RoleEnum.SENIOR_MGMT,
                    target_bureau_id=c.bureau_id,
                    message=f"Case {c.case_no} requires escalation: open for {elapsed_days} day(s).",
                    due_on=exp_date,
                    created_at=datetime.now(timezone.utc),
                )
                alerts_to_add.append(alert)
                generated_count += 1
                type_counts["ESCALATION"] += 1

    if alerts_to_add:
        db.add_all(alerts_to_add)
        db.commit()

    return GenerateAlertsResult(
        generated_count=generated_count,
        evaluated_cases_count=len(cases),
        skipped_duplicates_count=skipped_duplicates_count,
        types_breakdown=type_counts,
    )

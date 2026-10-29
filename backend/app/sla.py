"""Placeholder SLA checks and deduplicated alert creation."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Alert, Case, SlaRule, User
from app.models.enums import AlertType, CaseStatus, Priority, Role, ActionType
from app.workflow import apply_transition

SYSTEM_EMAIL = "system@aicte.invalid"


def _value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _sla_rule(db: Session, case: Case) -> tuple[int, float, int, int]:
    specific = db.scalar(
        select(SlaRule).where(
            SlaRule.category_id == case.category_id,
            SlaRule.priority == _value(case.priority),
        )
    )
    rule = specific or db.scalar(
        select(SlaRule).where(
            SlaRule.category_id.is_(None),
            SlaRule.priority == _value(case.priority),
        )
    )
    if rule is None:
        return 30, 0.75, 7, 10
    return (
        rule.days_to_dispose,
        rule.warn_at_pct,
        rule.reminder_after_days,
        rule.escalate_after_days,
    )


def _alert_exists_today(db: Session, case_id, alert_type: str, today: date) -> bool:
    found = db.scalar(
        select(Alert.id)
        .where(
            Alert.case_id == case_id,
            Alert.type == alert_type,
            func.date(Alert.created_at) == today.isoformat(),
        )
        .limit(1)
    )
    return found is not None


def _add_alert(
    db: Session,
    case: Case,
    alert_type: str,
    message: str,
    due_on: date,
    today: date,
) -> bool:
    if _alert_exists_today(db, case.id, alert_type, today):
        return False
    db.add(
        Alert(
            type=alert_type,
            case_id=case.id,
            institution_id=case.institution_id,
            target_bureau_id=case.bureau_id,
            message=message,
            due_on=due_on,
            created_at=datetime.combine(today, time(hour=12), tzinfo=timezone.utc),
        )
    )
    return True


def _system_user(db: Session) -> User:
    user = db.scalar(select(User).where(User.email == SYSTEM_EMAIL))
    if user is None:
        user = User(
            name="System Automation",
            email=SYSTEM_EMAIL,
            password_hash="!",
            role=Role.ADMIN.value,
            active=False,
        )
        db.add(user)
        db.flush()
    return user


def run_sla_check(db: Session, today: date) -> dict[str, int]:
    """Create DUE_SOON, OVERDUE, REMINDER, and ESCALATION alerts for open cases."""
    cases = db.scalars(
        select(Case).where(Case.status != CaseStatus.DISPOSED.value).order_by(Case.id)
    ).all()
    result = {
        "checked": len(cases),
        "due_soon": 0,
        "overdue": 0,
        "reminders": 0,
        "escalations": 0,
    }
    system_user = None
    for case in cases:
        days_to_dispose, warn_at_pct, reminder_after_days, escalate_after_days = _sla_rule(db, case)
        days_to_dispose = max(1, days_to_dispose)
        due_on = case.expected_disposal_on or (case.received_on + timedelta(days=days_to_dispose))
        elapsed_days = max(0, (today - case.received_on).days)
        idle_from = case.last_action_on.date() if case.last_action_on else case.received_on
        idle_days = max(0, (today - idle_from).days)

        if today > due_on:
            if _add_alert(
                db,
                case,
                AlertType.OVERDUE.value,
                "SLA placeholder: this case is past its expected disposal date.",
                due_on,
                today,
            ):
                result["overdue"] += 1
        elif elapsed_days / days_to_dispose >= warn_at_pct:
            if _add_alert(
                db,
                case,
                AlertType.DUE_SOON.value,
                "SLA placeholder: this case is approaching its expected disposal date.",
                due_on,
                today,
            ):
                result["due_soon"] += 1

        if idle_days >= reminder_after_days:
            if _add_alert(
                db,
                case,
                AlertType.REMINDER.value,
                "SLA placeholder: no recent case action has been recorded.",
                due_on,
                today,
            ):
                result["reminders"] += 1

        overdue_days = (today - due_on).days if today > due_on else 0
        if overdue_days >= escalate_after_days:
            if _add_alert(
                db,
                case,
                AlertType.ESCALATION.value,
                "SLA placeholder: this overdue case has reached its escalation point.",
                due_on,
                today,
            ):
                result["escalations"] += 1
            current_status = _value(case.status)
            if current_status != CaseStatus.ESCALATED.value:
                if system_user is None:
                    system_user = _system_user(db)
                apply_transition(
                    db,
                    case,
                    system_user,
                    ActionType.ESCALATED.value,
                    CaseStatus.ESCALATED.value,
                    "System escalation after the placeholder SLA overdue period.",
                )
    db.flush()
    return result
"""The only application helper that changes a case status."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import Case, CaseAction
from app.models.enums import ActionType, CaseStatus


class InvalidTransition(ValueError):
    pass


def apply_transition(
    db: Session,
    case: Case,
    user: Any,
    action_type: str,
    to_status: str,
    remarks: str | None,
) -> CaseAction:
    """Apply an allowed status change and append its audit row in this transaction."""
    current = case.status.value if hasattr(case.status, "value") else str(case.status)
    target = to_status.value if hasattr(to_status, "value") else str(to_status)
    is_open = current != CaseStatus.DISPOSED.value
    allowed = (
        (current == CaseStatus.PENDING.value and target == CaseStatus.UNDER_PROCESS.value)
        or (current == CaseStatus.UNDER_PROCESS.value and target == CaseStatus.DISPOSED.value)
        or (is_open and target in {CaseStatus.TRANSFERRED.value, CaseStatus.ESCALATED.value})
        or (current == CaseStatus.DISPOSED.value and target == CaseStatus.PENDING.value and bool(remarks and remarks.strip()))
    )
    if not allowed:
        raise InvalidTransition(f"Transition {current} -> {target} is not allowed.")
    if target == CaseStatus.PENDING.value and not (remarks and remarks.strip()):
        raise InvalidTransition("Reopening a case requires remarks.")

    now = datetime.now(timezone.utc)
    action = CaseAction(
        case_id=case.id,
        actor_id=user.id,
        bureau_id=case.bureau_id,
        action_type=action_type,
        from_status=current,
        to_status=target,
        remarks=remarks,
        created_at=now,
    )
    case.status = target
    case.last_action_on = now
    case.last_action_text = remarks
    db.add(action)
    db.flush()
    return action
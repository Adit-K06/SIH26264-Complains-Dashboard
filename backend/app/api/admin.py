"""Admin API router for SLA configuration and system administration.

Endpoints per AGENTS.md:
  GET /admin/sla-rules       – list all configured SLA rules
  PUT /admin/sla-rules/{id}  – update an existing SLA rule
  GET /admin/users           – list system users
  GET /admin/evaluation      – system AI / evaluation summary

All routes require ADMIN role.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import Category, SlaRule, User
from app.models.enums import PriorityEnum, RoleEnum

router = APIRouter(prefix="/admin", tags=["admin"])


class SlaRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    priority: PriorityEnum
    days_to_dispose: int
    warn_at_pct: int
    reminder_after_days: int
    escalate_after_days: int


class SlaRuleUpdate(BaseModel):
    days_to_dispose: Optional[int] = Field(None, ge=1, le=365)
    warn_at_pct: Optional[int] = Field(None, ge=1, le=100)
    reminder_after_days: Optional[int] = Field(None, ge=1, le=365)
    escalate_after_days: Optional[int] = Field(None, ge=1, le=365)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: RoleEnum
    bureau_id: Optional[int] = None
    region_id: Optional[int] = None
    active: bool


@router.get("/sla-rules", response_model=list[SlaRuleOut])
def list_sla_rules(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all SLA rules configured in the database."""
    rules = db.query(SlaRule).order_by(SlaRule.priority.asc(), SlaRule.category_id.asc().nulls_first()).all()
    out = []
    for r in rules:
        out.append(
            SlaRuleOut(
                id=r.id,
                category_id=r.category_id,
                category_name=r.category.name if r.category else None,
                priority=r.priority,
                days_to_dispose=r.days_to_dispose,
                warn_at_pct=r.warn_at_pct,
                reminder_after_days=r.reminder_after_days,
                escalate_after_days=r.escalate_after_days,
            )
        )
    return out


@router.put("/sla-rules/{id}", response_model=SlaRuleOut)
def update_sla_rule(
    id: int,
    payload: SlaRuleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update SLA rule thresholds and durations."""
    rule = db.get(SlaRule, id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": f"SLA rule {id} not found"}},
        )

    if payload.days_to_dispose is not None:
        rule.days_to_dispose = payload.days_to_dispose
    if payload.warn_at_pct is not None:
        rule.warn_at_pct = payload.warn_at_pct
    if payload.reminder_after_days is not None:
        rule.reminder_after_days = payload.reminder_after_days
    if payload.escalate_after_days is not None:
        rule.escalate_after_days = payload.escalate_after_days

    db.commit()
    db.refresh(rule)

    return SlaRuleOut(
        id=rule.id,
        category_id=rule.category_id,
        category_name=rule.category.name if rule.category else None,
        priority=rule.priority,
        days_to_dispose=rule.days_to_dispose,
        warn_at_pct=rule.warn_at_pct,
        reminder_after_days=rule.reminder_after_days,
        escalate_after_days=rule.escalate_after_days,
    )


@router.get("/users", response_model=list[UserOut])
def list_admin_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all registered system users (ADMIN only)."""
    users = db.query(User).order_by(User.id.asc()).all()
    return users


@router.get("/evaluation")
def get_admin_evaluation(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """System evaluation and model performance metrics.

    Returns metrics from docs/evaluation.json when available (produced by
    `python -m app.ai.evaluate`), falling back to config constants.
    """
    import json
    import os

    base = {
        "status": "ready",
        "fuzzy_threshold_auto": 0.92,
        "fuzzy_threshold_review": 0.75,
        "overlap_threshold": float(os.getenv("OVERLAP_THRESHOLD", "0.40")),
        "similarity_mode": os.getenv("SIMILARITY_MODE", "tfidf"),
        "tier_b_weights": {
            "text_similarity": 0.45,
            "category_match": 0.30,
            "time_proximity": 0.15,
            "reference_overlap": 0.10,
        },
        "synthetic_source": "SYNTHETIC",
    }
    # Try to load real evaluation metrics from docs/evaluation.json
    try:
        from app.ai.paths import docs_dir
        eval_path = docs_dir() / "evaluation.json"
        if eval_path.exists():
            with open(eval_path, "r", encoding="utf-8") as fh:
                eval_data = json.load(fh)
            base["evaluation"] = eval_data
            base["status"] = "evaluated"
    except Exception:
        pass  # evaluation.json missing or malformed — return base config only
    return base

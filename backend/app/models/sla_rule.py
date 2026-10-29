"""SlaRule model.

PLACEHOLDER values — days_to_dispose, warn_at_pct, reminder_after_days,
escalate_after_days are NOT official AICTE norms.
Seeded with placeholder values in migration 0003.
"""
from __future__ import annotations

import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import priority_col


class SlaRule(Base):
    __tablename__ = "sla_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    # nullable → catch-all rule when category_id is NULL
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("categories.id"), nullable=True
    )
    priority: Mapped[str] = mapped_column(priority_col, nullable=False)
    days_to_dispose: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    warn_at_pct: Mapped[float] = mapped_column(sa.Float, nullable=False)
    reminder_after_days: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    escalate_after_days: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("category_id", "priority", name="uq_sla_rules_cat_prio"),
    )

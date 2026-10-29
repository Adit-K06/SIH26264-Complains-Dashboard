"""OverlapFlag model.

Tier A: institution-level flag — case_a AND case_b are both NULL.
Tier B: case-pair flag — case_a AND case_b are both NOT NULL.

The CHECK constraint enforces this invariant at the DB level.
unique(case_a, case_b): PostgreSQL treats NULL != NULL so multiple Tier A
rows (both NULL) are allowed by the constraint, which is correct.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import overlap_state_col, overlap_tier_col


class OverlapFlag(Base):
    __tablename__ = "overlap_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("institutions.id"), nullable=False
    )
    # Tier A: both NULL. Tier B: both NOT NULL.
    case_a: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("cases.id"), nullable=True
    )
    case_b: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("cases.id"), nullable=True
    )
    tier: Mapped[str] = mapped_column(overlap_tier_col, nullable=False)
    score: Mapped[Optional[float]] = mapped_column(sa.Float, nullable=True)
    # JSON list of reason codes (e.g. ["HIGH_TEXT_SIMILARITY","SAME_CATEGORY"])
    reasons: Mapped[dict] = mapped_column(JSON, nullable=False, server_default="[]")
    state: Mapped[str] = mapped_column(
        overlap_state_col,
        nullable=False,
        server_default="OPEN",
    )
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        # Prevents re-detecting the same case pair (NULL != NULL in PG → Tier A safe)
        sa.UniqueConstraint("case_a", "case_b", name="uq_overlap_flags_case_pair"),
        # Tier A rows have case_a=NULL and case_b=NULL; Tier B have both NOT NULL
        sa.CheckConstraint(
            "(tier = 'A' AND case_a IS NULL AND case_b IS NULL)"
            " OR (tier = 'B' AND case_a IS NOT NULL AND case_b IS NOT NULL)",
            name="chk_overlap_tier_case_nullity",
        ),
    )

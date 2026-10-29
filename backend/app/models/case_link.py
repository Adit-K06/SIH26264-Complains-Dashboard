"""CaseLink model.

Groups related cases (cross-bureau overlaps or same-bureau duplicates).
link_type = CROSS_BUREAU: cases from different bureaus linked by the overlap engine.
link_type = SAME_BUREAU_DUPLICATE: mass-complaint clustering (feature 15).
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import link_type_col


class CaseLink(Base):
    __tablename__ = "case_links"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    # Shared group UUID across all cases in the same link group
    group_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid, nullable=False, index=True)
    case_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("cases.id"), nullable=False
    )
    linked_by: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=False
    )
    lead_bureau_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("bureaus.id"), nullable=False
    )
    link_type: Mapped[str] = mapped_column(link_type_col, nullable=False)
    note: Mapped[str] = mapped_column(sa.Text, nullable=False, server_default="")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

"""CaseAction model. app.db rejects ORM and SQL updates and deletes."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import action_tag_col, action_type_col, case_status_col


class CaseAction(Base):
    __tablename__ = "case_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("cases.id"), nullable=False
    )
    # NULL means system-generated (worker / automation)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=True
    )
    bureau_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("bureaus.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(action_type_col, nullable=False)
    action_tag: Mapped[Optional[str]] = mapped_column(
        action_tag_col, nullable=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(
        case_status_col, nullable=True
    )
    to_status: Mapped[Optional[str]] = mapped_column(
        case_status_col, nullable=True
    )
    remarks: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    attachment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("attachments.id"), nullable=True
    )
    # Required when Conflict Guard warning was overridden (P10)
    override_reason: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.Index("ix_case_actions_case_created", "case_id", "created_at"),
    )

"""Alert model.

Deduplication: unique functional index on (case_id, type, created_at::date)
WHERE case_id IS NOT NULL — created in migration 0001 via op.execute() because
SQLAlchemy autogenerate cannot emit functional/partial indexes.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import alert_type_col, role_col


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(alert_type_col, nullable=False)
    case_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("cases.id"), nullable=True
    )
    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("institutions.id"), nullable=True
    )
    target_role: Mapped[Optional[str]] = mapped_column(role_col, nullable=True)
    target_bureau_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("bureaus.id"), nullable=True
    )
    message: Mapped[str] = mapped_column(sa.Text, nullable=False)
    due_on: Mapped[Optional[date]] = mapped_column(sa.Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Note: the functional dedupe index (case_id, type, created_at::date)
    # is NOT declared here — it lives in migration 0001 via op.execute().

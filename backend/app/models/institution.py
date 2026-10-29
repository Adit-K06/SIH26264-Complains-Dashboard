"""Institution model; demo institution records are synthetic."""
from __future__ import annotations

import uuid
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    # Permanent AICTE ID — never changes; assigned at registration
    aicte_permanent_id: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(sa.Text, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    district: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True)
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("regions.id"), nullable=True, index=True
    )
    type: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(sa.String(64), nullable=True)
    # All records are synthetic
    source: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default="SYNTHETIC"
    )

"""Attachment model.

Magic-bytes validation and SHA-256 deduplication handled at the API layer (P5).
"""
from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("cases.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    mime: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    stored_path: Mapped[str] = mapped_column(sa.String(1024), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=False
    )

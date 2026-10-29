"""ApiKey model. Keys stored as bcrypt hash — raw key never persisted."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    bureau_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("bureaus.id"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(sa.String(256), nullable=False)
    active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.true()
    )

"""Bureau model. Bureau names are ASSUMPTIONS (see AGENTS.md rule 8)."""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Bureau(Base):
    __tablename__ = "bureaus"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(sa.String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(sa.String(256), nullable=False)

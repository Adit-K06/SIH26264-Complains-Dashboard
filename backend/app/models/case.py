"""Case model.

text_vector is stored as JSON to hold preprocessed TF-IDF token weights
used by the overlap engine (P7). Never contains PII.
complainant_ref is masked at the API layer based on role scope (P2/P4).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import (
    CaseStatus,
    HardDeadlineType,
    Priority,
    SourceChannel,
    case_status_col,
    hard_deadline_type_col,
    priority_col,
    source_channel_col,
)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4
    )
    # Bureau-specific case number; unique per bureau enforced via UniqueConstraint
    case_no: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    institution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("institutions.id"), nullable=True
    )
    bureau_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("bureaus.id"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("categories.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        case_status_col,
        nullable=False,
        server_default=CaseStatus.PENDING.value,
    )
    assigned_officer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=True
    )
    received_on: Mapped[date] = mapped_column(sa.Date, nullable=False)
    last_action_on: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_action_text: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    next_action_text: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    expected_disposal_on: Mapped[Optional[date]] = mapped_column(
        sa.Date, nullable=True
    )
    priority: Mapped[str] = mapped_column(
        priority_col, nullable=False, server_default=Priority.MEDIUM.value
    )
    summary: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    # Masked at the API layer for roles outside the case's bureau/region scope
    complainant_ref: Mapped[Optional[str]] = mapped_column(
        sa.String(256), nullable=True
    )
    source_channel: Mapped[str] = mapped_column(source_channel_col, nullable=False)
    hard_deadline_on: Mapped[Optional[date]] = mapped_column(sa.Date, nullable=True)
    hard_deadline_type: Mapped[str] = mapped_column(
        hard_deadline_type_col,
        nullable=False,
        server_default=HardDeadlineType.NONE.value,
    )
    # Groups linked cases (set by overlap engine / officer)
    link_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid, nullable=True
    )
    needs_institution_review: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.false()
    )
    # Preprocessed TF-IDF weights for overlap engine; never contains PII
    text_vector: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(
        sa.String(32), nullable=False, server_default="SYNTHETIC"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (
        # Unique case number per bureau
        sa.UniqueConstraint("bureau_id", "case_no", name="uq_cases_bureau_case_no"),
        # Indexes per AGENTS.md
        sa.Index("ix_cases_institution_status", "institution_id", "status"),
        sa.Index("ix_cases_bureau_status", "bureau_id", "status"),
        sa.Index("ix_cases_received_on", "received_on"),
        sa.Index("ix_cases_expected_disposal_on", "expected_disposal_on"),
        sa.Index("ix_cases_hard_deadline_on", "hard_deadline_on"),
    )

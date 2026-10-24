"""Case model."""
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import CaseStatusEnum, PriorityEnum


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_no = Column(String(100), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="SET NULL"), nullable=True, index=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(
        Enum(CaseStatusEnum, native_enum=False, length=50),
        nullable=False,
        default=CaseStatusEnum.PENDING,
        index=True,
    )
    assigned_officer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    received_on = Column(Date, nullable=False)
    last_action_on = Column(DateTime(timezone=True), nullable=True)
    last_action_text = Column(Text, nullable=True)
    next_action_text = Column(Text, nullable=True)
    expected_disposal_on = Column(Date, nullable=True)
    priority = Column(
        Enum(PriorityEnum, native_enum=False, length=50),
        nullable=False,
        default=PriorityEnum.MEDIUM,
        index=True,
    )
    summary = Column(Text, nullable=False)
    complainant_ref = Column(String(255), nullable=True)
    source = Column(String(50), nullable=False, default="SYNTHETIC")
    link_group_id = Column(String(36), nullable=True, index=True)
    needs_institution_review = Column(Boolean, nullable=False, default=False)
    text_vector = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    __table_args__ = (
        UniqueConstraint("case_no", "bureau_id", name="uq_cases_case_no_bureau_id"),
        Index("ix_cases_institution_id_status", "institution_id", "status"),
        Index("ix_cases_bureau_id_status", "bureau_id", "status"),
        Index("ix_cases_received_on", "received_on"),
        Index("ix_cases_expected_disposal_on", "expected_disposal_on"),
    )

    # Relationships
    institution = relationship("Institution", back_populates="cases")
    bureau = relationship("Bureau", back_populates="cases")
    category = relationship("Category", back_populates="cases")
    assigned_officer = relationship("User", back_populates="assigned_cases")
    actions = relationship("CaseAction", back_populates="case", cascade="all, delete-orphan", order_by="CaseAction.created_at")
    attachments = relationship("Attachment", back_populates="case", cascade="all, delete-orphan")
    links = relationship("CaseLink", back_populates="case", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="case", cascade="all, delete-orphan")
    overlap_flags_as_a = relationship("OverlapFlag", foreign_keys="[OverlapFlag.case_a]", back_populates="first_case", cascade="all, delete-orphan")
    overlap_flags_as_b = relationship("OverlapFlag", foreign_keys="[OverlapFlag.case_b]", back_populates="second_case", cascade="all, delete-orphan")

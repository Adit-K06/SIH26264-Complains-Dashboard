"""OverlapFlag model."""
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import OverlapStateEnum, OverlapTierEnum


class OverlapFlag(Base):
    __tablename__ = "overlap_flags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    case_a = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    case_b = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    tier = Column(Enum(OverlapTierEnum, native_enum=False, length=10), nullable=False, index=True)
    score = Column(Float, nullable=False, default=0.0)
    reasons = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    state = Column(
        Enum(OverlapStateEnum, native_enum=False, length=50),
        nullable=False,
        default=OverlapStateEnum.OPEN,
        index=True,
    )
    decided_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        # Tier B unique pair
        Index(
            "uq_overlap_flags_case_a_case_b",
            "case_a",
            "case_b",
            unique=True,
            postgresql_where=text("case_a IS NOT NULL AND case_b IS NOT NULL"),
            sqlite_where=text("case_a IS NOT NULL AND case_b IS NOT NULL"),
        ),
        # Tier A partial unique per institution where case_a and case_b are both NULL
        Index(
            "uq_overlap_flags_tier_a_institution",
            "institution_id",
            unique=True,
            postgresql_where=text("case_a IS NULL AND case_b IS NULL"),
            sqlite_where=text("case_a IS NULL AND case_b IS NULL"),
        ),
    )

    # Relationships
    institution = relationship("Institution", back_populates="overlap_flags")
    first_case = relationship("Case", foreign_keys=[case_a], back_populates="overlap_flags_as_a")
    second_case = relationship("Case", foreign_keys=[case_b], back_populates="overlap_flags_as_b")
    decided_by_user = relationship("User", back_populates="decided_overlaps")

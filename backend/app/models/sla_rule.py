"""SlaRule model."""
from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import PriorityEnum


class SlaRule(Base):
    __tablename__ = "sla_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True)
    priority = Column(Enum(PriorityEnum, native_enum=False, length=50), nullable=False, index=True)
    days_to_dispose = Column(Integer, nullable=False)
    warn_at_pct = Column(Integer, nullable=False, default=80)
    reminder_after_days = Column(Integer, nullable=False)
    escalate_after_days = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("category_id", "priority", name="uq_sla_rules_category_priority"),
    )

    # Relationships
    category = relationship("Category", back_populates="sla_rules")

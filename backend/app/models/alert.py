"""Alert model."""
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import AlertTypeEnum, RoleEnum


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(Enum(AlertTypeEnum, native_enum=False, length=50), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=True)
    target_role = Column(Enum(RoleEnum, native_enum=False, length=50), nullable=True, index=True)
    target_bureau_id = Column(Integer, ForeignKey("bureaus.id", ondelete="SET NULL"), nullable=True, index=True)
    message = Column(Text, nullable=False)
    due_on = Column(Date, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    read_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        Index("ix_alerts_case_id_type_created_at", "case_id", "type", "created_at"),
        Index("ix_alerts_institution_id", "institution_id"),
    )

    # Relationships
    case = relationship("Case", back_populates="alerts")
    institution = relationship("Institution", back_populates="alerts")
    target_bureau = relationship("Bureau")

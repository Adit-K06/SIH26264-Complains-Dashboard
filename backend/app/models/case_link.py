"""CaseLink model."""
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class CaseLink(Base):
    __tablename__ = "case_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(String(36), nullable=False)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    linked_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    lead_bureau_id = Column(Integer, ForeignKey("bureaus.id", ondelete="RESTRICT"), nullable=False, index=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_case_links_group_id", "group_id"),
        Index("ix_case_links_case_id", "case_id"),
    )

    # Relationships
    case = relationship("Case", back_populates="links")
    linked_by_user = relationship("User")
    lead_bureau = relationship("Bureau", back_populates="lead_links")

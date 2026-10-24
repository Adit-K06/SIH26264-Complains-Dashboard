"""Institution model."""
from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aicte_permanent_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    address = Column(Text, nullable=True)
    district = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True)
    type = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True, default="ACTIVE")

    __table_args__ = (
        Index(
            "ix_institutions_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_institutions_region_id", "region_id"),
    )

    # Relationships
    region = relationship("Region", back_populates="institutions")
    cases = relationship("Case", back_populates="institution")
    overlap_flags = relationship("OverlapFlag", back_populates="institution")
    alerts = relationship("Alert", back_populates="institution")

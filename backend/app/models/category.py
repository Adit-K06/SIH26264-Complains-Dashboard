"""Category model."""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    # Relationships
    cases = relationship("Case", back_populates="category")
    sla_rules = relationship("SlaRule", back_populates="category")

"""Region model."""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)

    # Relationships
    institutions = relationship("Institution", back_populates="region")
    users = relationship("User", back_populates="region")

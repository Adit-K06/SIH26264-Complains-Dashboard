"""ApiKey model."""
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id", ondelete="CASCADE"), nullable=False, index=True)
    key_hash = Column(String(255), unique=True, nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)

    # Relationships
    bureau = relationship("Bureau", back_populates="api_keys")

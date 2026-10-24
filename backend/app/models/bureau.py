"""Bureau model."""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Bureau(Base):
    __tablename__ = "bureaus"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)

    # Relationships
    users = relationship("User", back_populates="bureau")
    cases = relationship("Case", back_populates="bureau")
    api_keys = relationship("ApiKey", back_populates="bureau")
    case_actions = relationship("CaseAction", back_populates="bureau")
    lead_links = relationship("CaseLink", back_populates="lead_bureau")

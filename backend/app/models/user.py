"""User model."""
from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base
from app.models.enums import RoleEnum


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum, native_enum=False, length=50), nullable=False, index=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id", ondelete="SET NULL"), nullable=True, index=True)
    region_id = Column(Integer, ForeignKey("regions.id", ondelete="SET NULL"), nullable=True, index=True)
    active = Column(Boolean, default=True, nullable=False)

    # Relationships
    bureau = relationship("Bureau", back_populates="users")
    region = relationship("Region", back_populates="users")
    assigned_cases = relationship("Case", back_populates="assigned_officer")
    case_actions = relationship("CaseAction", back_populates="actor")
    attachments = relationship("Attachment", back_populates="uploader")
    decided_overlaps = relationship("OverlapFlag", back_populates="decided_by_user")

"""Attachment model."""
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    mime = Column(String(100), nullable=False)
    size = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    stored_path = Column(String(500), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Relationships
    case = relationship("Case", back_populates="attachments")
    uploader = relationship("User", back_populates="attachments")

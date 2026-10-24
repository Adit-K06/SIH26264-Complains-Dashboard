"""CaseAction model (append-only audit trail)."""
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
    event,
    func,
)
from sqlalchemy.orm import Session, relationship

from app.models.base import Base
from app.models.enums import ActionTypeEnum, CaseStatusEnum


class CaseAction(Base):
    __tablename__ = "case_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    bureau_id = Column(Integer, ForeignKey("bureaus.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type = Column(
        Enum(ActionTypeEnum, native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    from_status = Column(Enum(CaseStatusEnum, native_enum=False, length=50), nullable=True)
    to_status = Column(Enum(CaseStatusEnum, native_enum=False, length=50), nullable=True)
    remarks = Column(Text, nullable=True)
    attachment_id = Column(Integer, ForeignKey("attachments.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    # Relationships
    case = relationship("Case", back_populates="actions")
    actor = relationship("User", back_populates="case_actions")
    bureau = relationship("Bureau", back_populates="case_actions")
    attachment = relationship("Attachment")


# Append-only enforcement at ORM level
@event.listens_for(CaseAction, "before_update")
def _prevent_case_action_update(mapper, connection, target):
    raise ValueError("case_actions is append-only: updates are prohibited")


@event.listens_for(CaseAction, "before_delete")
def _prevent_case_action_delete(mapper, connection, target):
    raise ValueError("case_actions is append-only: deletes are prohibited")


@event.listens_for(Session, "before_flush")
def _check_case_actions_flush(session, flush_context, instances):
    for obj in session.dirty:
        if isinstance(obj, CaseAction) and session.is_modified(obj, include_collections=False):
            raise ValueError("case_actions is append-only: updates are prohibited")
    for obj in session.deleted:
        if isinstance(obj, CaseAction):
            raise ValueError("case_actions is append-only: deletes are prohibited")

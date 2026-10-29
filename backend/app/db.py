"""Shared SQLAlchemy engine, metadata, session factory, and startup helpers."""
from __future__ import annotations

from typing import Any, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Single declarative base shared by all models."""


def _engine_options(database_url: str) -> dict[str, Any]:
    options: dict[str, Any] = {"pool_pre_ping": True}
    if database_url.lower().startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options.update(pool_size=10, max_overflow=20)
    return options


engine = create_engine(settings.DATABASE_URL, **_engine_options(settings.DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _mutation_targets_case_actions(statement: str) -> bool:
    tokens = statement.strip().split()
    if not tokens:
        return False
    command = tokens[0].upper()
    if command == "UPDATE" and len(tokens) > 1:
        table_token = tokens[1]
    elif command == "DELETE" and len(tokens) > 2 and tokens[1].upper() == "FROM":
        table_token = tokens[2]
    else:
        return False
    table_name = table_token.rsplit(".", 1)[-1].strip('"[];').lower()
    return table_name == "case_actions"


@event.listens_for(Engine, "before_cursor_execute")
def _reject_case_action_sql_mutations(
    connection: Any,
    cursor: Any,
    statement: str,
    parameters: Any,
    context: Any,
    executemany: bool,
) -> None:
    if _mutation_targets_case_actions(statement):
        raise ValueError("case_actions is append-only; updates and deletes are forbidden")


@event.listens_for(Session, "before_flush")
def _reject_case_action_object_mutations(
    session: Session, flush_context: Any, instances: Any
) -> None:
    from app.models.case_action import CaseAction

    changed = any(
        isinstance(instance, CaseAction)
        and session.is_modified(instance, include_collections=False)
        for instance in session.dirty
    )
    deleted = any(isinstance(instance, CaseAction) for instance in session.deleted)
    if changed or deleted:
        raise ValueError("case_actions is append-only; updates and deletes are forbidden")


def create_tables() -> None:
    """Import all models, then create any missing tables from their metadata."""
    import app.models  # noqa: F401 — registers every mapped table

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
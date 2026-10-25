"""Database engine, sessionmaker, and dependency helpers."""
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.base import Base

DEFAULT_DATABASE_URL = "postgresql+psycopg://sih:sihpass@localhost:5432/sih"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def normalize_db_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine supporting both SQLite and PostgreSQL."""
    raw_url = url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    target_url = normalize_db_url(raw_url)
    if target_url.startswith("sqlite"):
        return create_engine(
            target_url,
            connect_args={"check_same_thread": False},
        )
    return create_engine(target_url, pool_pre_ping=True)


# Initialize global engine gracefully
engine: Engine | None = None
try:
    engine = get_engine(DATABASE_URL)
except Exception:
    # Allows offline model usage and environments where DB driver is not yet installed
    engine = None

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency."""
    global engine
    if SessionLocal.kw.get("bind") is None:
        if engine is None:
            engine = get_engine()
        SessionLocal.configure(bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = ["Base", "DATABASE_URL", "get_engine", "engine", "SessionLocal", "get_db"]

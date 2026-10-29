"""Re-exports Base from app.db so model files have a stable import path."""
from app.db import Base  # noqa: F401

__all__ = ["Base"]

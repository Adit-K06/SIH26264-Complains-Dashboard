"""Application configuration — loaded from environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "sqlite:///./aicte.db"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-32-char-random-string"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # Optional AI
    LLM_ENABLED: bool = False
    OPENAI_API_KEY: str = ""

    # File uploads
    MAX_ATTACHMENT_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Overlap
    OVERLAP_THRESHOLD: float = 0.45


settings = Settings()

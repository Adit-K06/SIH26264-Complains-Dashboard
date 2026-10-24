"""Application configuration loaded from environment variables.

Secrets (JWT_SECRET, DATABASE_URL) must never be hardcoded.
All values have development-safe defaults; override via .env or environment.
In production, insecure or missing JWT_SECRET values fail closed immediately.
"""
from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("environment", "app_env", "env"),
    )
    database_url: str = "postgresql+psycopg://sih:sihpass@localhost:5432/sih"
    jwt_secret: str = "change-me"            # MUST be overridden in production
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 7
    storage_dir: str = "/data/uploads"
    cors_origins: str = "http://localhost,http://localhost:5173"
    demo_clock_offset_days: int = 0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in ("production", "prod")

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.is_production:
            if not self.jwt_secret or not self.jwt_secret.strip():
                raise ValueError("In production, JWT_SECRET must be set and non-empty.")
            if self.jwt_secret.strip() == "change-me":
                raise ValueError("In production, JWT_SECRET cannot use the default 'change-me' value.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Validate settings on module load
get_settings()

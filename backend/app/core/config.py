"""Application settings.

All configuration is loaded from environment variables (or a ``.env``
file). Values can be overridden per-environment.
"""

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = Field(default="Shift Roster", description="Display name")
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=True)
    app_timezone: str = Field(default="UTC")

    # --- Backend server ---
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)

    # --- Security ---
    secret_key: str = Field(default="change-me")
    backend_cors_origins: List[str] = Field(default_factory=list)

    # --- JWT ---
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=480)  # 8 hours

    # --- Database ---
    postgres_user: str = Field(default="shiftroster")
    postgres_password: str = Field(default="shiftroster")
    postgres_db: str = Field(default="shiftroster")
    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    database_url: Optional[str] = Field(default=None)

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value):  # type: ignore[override]
        if value is None or value == "":
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("secret_key", mode="after")
    @classmethod
    def _reject_default_secret_in_production(cls, value: str, info) -> str:
        """Fail loudly in production if the placeholder secret is still in use.

        Development environments (and the test suite) are allowed to keep
        the placeholder so first-run local workflows still work.
        """
        env = (info.data.get("app_env") or "development").lower()
        if env == "production" and value == "change-me":
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in production"
            )
        return value

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Build the SQLAlchemy DSN from components or return override."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()

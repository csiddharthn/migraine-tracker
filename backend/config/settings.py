from __future__ import annotations

"""Purpose: Application settings and environment configuration.

Usage: Defines Settings (BaseSettings) for database URLs, API keys,
log levels, and config paths. Used across backend services.

Functions available:
- None (class-based module)

Classes available:
- Settings

Call hierarchy:
- settings.py -> pydantic.BaseSettings, Field, SecretStr
- settings.py -> pydantic_settings.SettingsConfigDict
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str = Field(alias="MIGRAINE_DATABASE_URL")
    test_database_url: str | None = Field(default=None, alias="MIGRAINE_TEST_DATABASE_URL")
    log_level: str = Field(default="INFO", alias="MIGRAINE_LOG_LEVEL")
    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")
    openrouter_api_key: SecretStr | None = Field(default=None, alias="OPENROUTER_API_KEY")
    config_path: Path = PROJECT_ROOT / "backend" / "config" / "app.yaml"

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    def app_config(self) -> dict[str, Any]:
        with self.config_path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

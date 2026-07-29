"""Settings, read from the environment.

One setting matters: ``DATABASE_URL``. The app, the migrations and the tests
all read it from here, so there is a single source of truth for where the data
lives.

It defaults to a local SQLite file so the service runs straight after a clone
with nothing else installed. Docker Compose points it at PostgreSQL, which is
what it is meant to run on.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Medication Request Service"
    database_url: str = "sqlite+pysqlite:///./medication_requests.db"
    sql_echo: bool = False
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return the settings, built once and reused."""
    return Settings()

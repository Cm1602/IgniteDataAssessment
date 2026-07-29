"""Shared test fixtures.

The suite runs against a throwaway SQLite database built by the real Alembic
migrations, so every run also proves the migrations apply. Set DATABASE_URL
before running pytest to point it at PostgreSQL instead.

Each test runs inside a transaction that gets rolled back afterwards. That
keeps tests independent while still letting the code under test call commit()
exactly as it does in production, so the tests exercise the real path rather
than a special one.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

# This has to happen before anything imports app.config, which caches settings
# on first use. Respect DATABASE_URL if the caller already set one.
_TEMP_DIR = Path(tempfile.mkdtemp(prefix="medication-requests-tests-"))
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{(_TEMP_DIR / 'test.db').as_posix()}")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import engine as app_engine  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """Alembic config pointed at this project, for the drift check."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return config


@pytest.fixture(scope="session", autouse=True)
def migrated_database(alembic_config: Config) -> Iterator[Engine]:
    """Build the schema once for the whole run, then clean up after."""
    command.upgrade(alembic_config, "head")

    yield app_engine

    app_engine.dispose()
    shutil.rmtree(_TEMP_DIR, ignore_errors=True)


@pytest.fixture
def db_session(migrated_database: Engine) -> Iterator[Session]:
    """A session whose work is thrown away at the end of the test.

    ``join_transaction_mode="create_savepoint"`` means a commit() inside the
    code under test releases a savepoint rather than ending the outer
    transaction, so the rollback below can still undo everything.
    """
    connection = migrated_database.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

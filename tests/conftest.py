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
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

# This has to happen before anything imports app.config, which caches settings
# on first use. Respect DATABASE_URL if the caller already set one.
_TEMP_DIR = Path(tempfile.mkdtemp(prefix="medication-requests-tests-"))
os.environ.setdefault("DATABASE_URL", f"sqlite+pysqlite:///{(_TEMP_DIR / 'test.db').as_posix()}")

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import engine as app_engine  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed import load_reference_data  # noqa: E402
from app.seed_data import CLINICIANS, MEDICATIONS, PATIENTS  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Handy names for seeded rows, so tests read as sentences rather than UUIDs.
PATIENT = str(PATIENTS[0]["id"])
OTHER_PATIENT = str(PATIENTS[1]["id"])
CLINICIAN = str(CLINICIANS[0]["id"])
MEDICATION = str(MEDICATIONS[0]["id"])
OTHER_MEDICATION = str(MEDICATIONS[1]["id"])


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


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """An API client wired to the test's session, with reference data loaded.

    Overriding get_session is what keeps the request handlers inside the
    transaction this test will roll back.
    """
    load_reference_data(db_session)
    db_session.flush()

    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def new_request() -> Callable[..., dict[str, Any]]:
    """Build a valid POST body, overriding whichever fields a test cares about."""

    def build(**overrides: Any) -> dict[str, Any]:
        body: dict[str, Any] = {
            "clinician_id": CLINICIAN,
            "medication_id": MEDICATION,
            "reason_text": "Schistosomiasis treatment",
            "prescribed_date": "2026-01-05",
            "start_date": "2026-01-06",
            "end_date": "2026-01-20",
            "frequency": "3 times/day",
        }
        body.update(overrides)
        return body

    return build

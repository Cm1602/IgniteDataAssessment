"""Engine and session setup."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()


def _connect_args(url: str) -> dict[str, Any]:
    if url.startswith("sqlite"):
        # FastAPI runs plain `def` endpoints in a worker thread, and SQLite
        # objects to being used from a thread other than the one that created it
        # unless told otherwise.
        return {"connect_args": {"check_same_thread": False}}
    # Idle pooled connections can be dropped by the database or a proxy.
    # pre_ping checks one is alive before handing it out.
    return {"pool_pre_ping": True}


def _make_sqlite_behave(target: Engine) -> None:
    """Switch off two SQLite defaults that would otherwise cause quiet trouble.

    Foreign keys are disabled per connection for backwards compatibility, so
    without the pragma a bad reference is accepted instead of rejected.

    Separately, the pysqlite driver manages transactions itself in a way that
    stops SAVEPOINT nesting inside a real transaction, which breaks the usual
    "roll each test back" pattern. Taking over BEGIN, as the SQLAlchemy pysqlite
    notes recommend, fixes it.

    Neither applies to PostgreSQL. Both matter here because the test suite runs
    on SQLite.
    """

    @event.listens_for(target, "connect")
    def _on_connect(dbapi_connection: Any, _record: Any) -> None:
        dbapi_connection.isolation_level = None
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    @event.listens_for(target, "begin")
    def _on_begin(connection: Connection) -> None:
        connection.exec_driver_sql("BEGIN")


def build_engine(url: str, *, echo: bool = False) -> Engine:
    """Create an engine set up for whichever backend the URL points at."""
    new_engine = create_engine(url, echo=echo, future=True, **_connect_args(url))
    if new_engine.dialect.name == "sqlite":
        _make_sqlite_behave(new_engine)
    return new_engine


engine: Engine = build_engine(_settings.database_url, echo=_settings.sql_echo)

SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency giving each request its own session."""
    session = SessionFactory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """A session with a transaction wrapped around it, for scripts rather than requests."""
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

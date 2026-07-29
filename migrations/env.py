"""Alembic environment.

The database URL comes from the app settings rather than alembic.ini, so there
is one place that decides which database everything talks to.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db.base import Base
from app.models import (  # noqa: F401  imported so the tables register on Base.metadata
    Clinician,
    Medication,
    MedicationRequest,
    Patient,
)

config = context.config
if config.config_file_name is not None:
    # disable_existing_loggers defaults to True, which switches off every logger
    # that already exists and is not named in alembic.ini. Running migrations in
    # the same process as the app would then silently stop the app logging
    # anything.
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Percent signs are special in ini files, so escape any that appear in a
# password before handing the URL over.
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Print the SQL instead of running it (``alembic upgrade head --sql``)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run the migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite cannot ALTER most things, so Alembic has to rebuild the
            # table instead. Harmless on PostgreSQL, which is why it is
            # switched on only where it is needed.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

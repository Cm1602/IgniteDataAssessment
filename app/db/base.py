"""The declarative base and the bits every table shares."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Without this, SQLAlchemy generates anonymous names for indexes and
# constraints, which are painful to drop in a later migration because you do not
# know what they are called. Setting a convention once makes every name
# predictable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Parent class for every table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKey:
    """A UUID primary key.

    Sequential integer keys leak how many records exist and roughly when each
    one was created, and make neighbouring records easy to guess. ``Uuid``
    renders as a native uuid column on PostgreSQL and CHAR(32) on SQLite, so the
    same model works on both.
    """

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)


class Timestamps:
    """Created and updated audit columns.

    Each has a server default so rows inserted outside the ORM still get one,
    and a Python default so rows inserted through the ORM get a timezone aware
    value without a round trip.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

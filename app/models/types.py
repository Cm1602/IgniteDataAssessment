"""Column types shared by the models."""

from __future__ import annotations

import enum

import sqlalchemy as sa


def enum_column(enum_cls: type[enum.Enum], name: str) -> sa.Enum:
    """Store an enum as text with a CHECK constraint rather than a native type.

    PostgreSQL has real enum types, but adding a value to one needs an ALTER
    TYPE migration, and SQLite has no equivalent at all. Text plus a check
    behaves the same on both.

    ``values_callable`` stores the value rather than the member name, so the
    column holds "on-hold" rather than "ON_HOLD".
    """
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )

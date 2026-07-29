"""Errors raised when a business rule is broken.

These carry no HTTP status codes on purpose. Translating them into responses is
the API layer's job, which keeps the rules usable from anywhere else too, for
example a bulk import script.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for every business rule violation."""


class InvalidDateRangeError(DomainError):
    """End date is earlier than start date."""


class InvalidStatusTransitionError(DomainError):
    """The requested status change is not allowed."""

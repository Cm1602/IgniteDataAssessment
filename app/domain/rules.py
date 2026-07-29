"""The business rules, as plain functions."""

from __future__ import annotations

from datetime import date

from app.domain.enums import TERMINAL_STATUSES, MedicationRequestStatus
from app.domain.errors import InvalidDateRangeError, InvalidStatusTransitionError


def periods_overlap(
    first_start: date,
    first_end: date | None,
    second_start: date,
    second_end: date | None,
) -> bool:
    """Return True if two effective periods share at least one day.

    Two periods overlap when each one starts before the other one finishes. A
    missing end date means the period is open ended, in which case "starts
    before it finishes" is always true and the check falls away by itself.

    Both endpoints are inclusive, so periods that share a single day overlap.
    """
    first_starts_before_second_ends = second_end is None or first_start <= second_end
    first_ends_after_second_starts = first_end is None or first_end >= second_start

    return first_starts_before_second_ends and first_ends_after_second_starts


def validate_effective_period(start_date: date, end_date: date | None) -> None:
    """Raise if the end date is before the start date."""
    if end_date is not None and end_date < start_date:
        raise InvalidDateRangeError(
            f"end_date {end_date.isoformat()} is before start_date {start_date.isoformat()}."
        )


def validate_status_transition(
    current: MedicationRequestStatus, requested: MedicationRequestStatus
) -> None:
    """Raise if a finished request is being made active again.

    That is the only move the brief forbids. Everything else, including setting
    a status to the value it already has, is allowed.
    """
    if current in TERMINAL_STATUSES and requested is MedicationRequestStatus.ACTIVE:
        raise InvalidStatusTransitionError(
            f"A {current.value} medication request cannot be set back to {requested.value}."
        )

"""The business rules, specified as tests.

Three of the four rules in the brief are decisions about values, so they live
in the domain layer as plain functions and are covered here. The fourth,
restricting which fields PATCH accepts, is enforced at the schema boundary and
is covered in ``test_schemas.py``.

Assumptions about open ended and single day periods are written up in the
README.
"""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.enums import MedicationRequestStatus as Status
from app.domain.errors import InvalidDateRangeError, InvalidStatusTransitionError
from app.domain.rules import (
    periods_overlap,
    validate_effective_period,
    validate_status_transition,
)


def jan(day: int) -> date:
    """Shorthand for a day in January 2026, to keep the tables below readable."""
    return date(2026, 1, day)


class TestPeriodsOverlap:
    """Do two effective periods touch at any point?"""

    @pytest.mark.parametrize(
        ("first", "second", "expected"),
        [
            ((jan(1), jan(10)), (jan(1), jan(10)), True),
            ((jan(1), jan(10)), (jan(5), jan(15)), True),
            ((jan(5), jan(15)), (jan(1), jan(10)), True),
            ((jan(1), jan(31)), (jan(10), jan(12)), True),
            # Sharing a single day counts: inclusive endpoints.
            ((jan(1), jan(10)), (jan(10), jan(20)), True),
            ((jan(1), jan(10)), (jan(12), jan(20)), False),
            ((jan(12), jan(20)), (jan(1), jan(10)), False),
            ((jan(1), jan(10)), (jan(11), jan(20)), False),
            # No end date means open ended, so it blocks anything starting later.
            ((jan(1), None), (jan(20), jan(25)), True),
            ((jan(1), None), (jan(20), None), True),
            ((jan(1), jan(10)), (jan(20), None), False),
            ((jan(20), jan(25)), (jan(1), None), True),
        ],
    )
    def test_overlap_cases(
        self,
        first: tuple[date, date | None],
        second: tuple[date, date | None],
        expected: bool,
    ) -> None:
        assert periods_overlap(first[0], first[1], second[0], second[1]) is expected

    def test_argument_order_does_not_matter(self) -> None:
        forwards = periods_overlap(jan(1), jan(10), jan(5), None)
        backwards = periods_overlap(jan(5), None, jan(1), jan(10))

        assert forwards == backwards


class TestValidateEffectivePeriod:
    """End date may not be earlier than start date."""

    def test_allows_end_after_start(self) -> None:
        validate_effective_period(jan(1), jan(2))

    def test_allows_a_single_day_request(self) -> None:
        validate_effective_period(jan(1), jan(1))

    def test_allows_no_end_date(self) -> None:
        validate_effective_period(jan(1), None)

    def test_rejects_end_before_start(self) -> None:
        with pytest.raises(InvalidDateRangeError) as caught:
            validate_effective_period(jan(10), jan(9))

        assert "2026-01-10" in str(caught.value)
        assert "2026-01-09" in str(caught.value)


class TestValidateStatusTransition:
    """Completed and cancelled requests are final. They never go back to active."""

    @pytest.mark.parametrize("final_status", [Status.COMPLETED, Status.CANCELLED])
    def test_rejects_reviving_a_finished_request(self, final_status: Status) -> None:
        with pytest.raises(InvalidStatusTransitionError):
            validate_status_transition(final_status, Status.ACTIVE)

    @pytest.mark.parametrize(
        ("current", "requested"),
        [
            (Status.ACTIVE, Status.ON_HOLD),
            (Status.ACTIVE, Status.COMPLETED),
            (Status.ACTIVE, Status.CANCELLED),
            (Status.ON_HOLD, Status.ACTIVE),
            (Status.ON_HOLD, Status.COMPLETED),
            (Status.ON_HOLD, Status.CANCELLED),
            # Only the move back to active is forbidden.
            (Status.COMPLETED, Status.CANCELLED),
        ],
    )
    def test_allows_everything_else(self, current: Status, requested: Status) -> None:
        validate_status_transition(current, requested)

    @pytest.mark.parametrize("status", list(Status))
    def test_setting_the_same_status_is_always_fine(self, status: Status) -> None:
        validate_status_transition(status, status)

    def test_error_names_both_statuses(self) -> None:
        with pytest.raises(InvalidStatusTransitionError) as caught:
            validate_status_transition(Status.CANCELLED, Status.ACTIVE)

        assert "cancelled" in str(caught.value)
        assert "active" in str(caught.value)

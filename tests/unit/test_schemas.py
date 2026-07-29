"""What the API will and will not accept.

These schemas describe request *bodies*. The patient reference is required on a
medication request, but it arrives as the ``{patient_id}`` path segment of
``POST /patients/{patient_id}/medication-requests``, so it is not part of the
body and is rejected if sent there.

This is also where business rule 4 lives: PATCH may only touch end date,
frequency and status. We reject anything else rather than ignoring it, so a
client never gets a 200 back for a change that did not happen.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.enums import MedicationRequestStatus as Status
from app.schemas.medication_request import (
    MedicationRequestCreate,
    MedicationRequestQuery,
    MedicationRequestUpdate,
)


def create_body(**overrides: Any) -> dict[str, Any]:
    """A valid POST body, with room to break one field at a time.

    No patient_id: that comes from the path.
    """
    body: dict[str, Any] = {
        "clinician_id": str(uuid.uuid4()),
        "medication_id": str(uuid.uuid4()),
        "prescribed_date": "2026-01-05",
        "start_date": "2026-01-06",
    }
    body.update(overrides)
    return body


class TestCreate:
    """POST /patients/{patient_id}/medication-requests."""

    def test_accepts_the_minimum_required_fields(self) -> None:
        model = MedicationRequestCreate.model_validate(create_body())

        assert model.prescribed_date == date(2026, 1, 5)
        assert model.start_date == date(2026, 1, 6)

    def test_optional_fields_default_to_empty(self) -> None:
        model = MedicationRequestCreate.model_validate(create_body())

        assert model.end_date is None
        assert model.frequency is None
        assert model.reason_text is None

    def test_status_defaults_to_active(self) -> None:
        """A brand new prescription is active unless told otherwise."""
        model = MedicationRequestCreate.model_validate(create_body())

        assert model.status is Status.ACTIVE

    @pytest.mark.parametrize(
        "missing", ["clinician_id", "medication_id", "prescribed_date", "start_date"]
    )
    def test_rejects_missing_required_field(self, missing: str) -> None:
        body = create_body()
        del body[missing]

        with pytest.raises(ValidationError):
            MedicationRequestCreate.model_validate(body)

    def test_rejects_patient_id_in_the_body(self) -> None:
        """The patient comes from the path. Taking it here too would be ambiguous."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            MedicationRequestCreate.model_validate(create_body(patient_id=str(uuid.uuid4())))

    def test_rejects_any_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            MedicationRequestCreate.model_validate(create_body(dosage="2 tablets"))

    def test_rejects_a_status_outside_the_allowed_set(self) -> None:
        with pytest.raises(ValidationError):
            MedicationRequestCreate.model_validate(create_body(status="paused"))

    def test_rejects_a_clinician_id_that_is_not_a_uuid(self) -> None:
        with pytest.raises(ValidationError):
            MedicationRequestCreate.model_validate(create_body(clinician_id="not-a-uuid"))

    def test_rejects_blank_free_text(self) -> None:
        """An empty string is almost always a client bug, not a deliberate value."""
        with pytest.raises(ValidationError):
            MedicationRequestCreate.model_validate(create_body(reason_text=""))


class TestUpdate:
    """PATCH /medication-requests/{id}, and business rule 4."""

    @pytest.mark.parametrize(
        ("field", "value"),
        [("end_date", "2026-02-01"), ("frequency", "twice/day"), ("status", "on-hold")],
    )
    def test_accepts_each_permitted_field(self, field: str, value: str) -> None:
        model = MedicationRequestUpdate.model_validate({field: value})

        assert field in model.model_fields_set

    @pytest.mark.parametrize(
        "field",
        [
            "patient_id",
            "clinician_id",
            "medication_id",
            "start_date",
            "prescribed_date",
            "reason_text",
        ],
    )
    def test_rejects_every_field_outside_the_permitted_set(self, field: str) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            MedicationRequestUpdate.model_validate({field: "2026-01-01"})

    def test_rejects_an_empty_patch(self) -> None:
        """Nothing to do is more likely a client bug than an intention."""
        with pytest.raises(ValidationError):
            MedicationRequestUpdate.model_validate({})

    def test_rejects_a_null_status(self) -> None:
        """Clearing the end date makes sense. Clearing the status does not."""
        with pytest.raises(ValidationError):
            MedicationRequestUpdate.model_validate({"status": None})

    def test_tells_omitted_apart_from_explicitly_null(self) -> None:
        """Sending null clears a field. Leaving the key out leaves it alone."""
        left_alone = MedicationRequestUpdate.model_validate({"frequency": "once/day"})
        cleared = MedicationRequestUpdate.model_validate({"end_date": None})

        assert left_alone.model_dump(exclude_unset=True) == {"frequency": "once/day"}
        assert cleared.model_dump(exclude_unset=True) == {"end_date": None}


class TestQuery:
    """Filters and paging on the list endpoint."""

    def test_defaults_to_no_filters_and_a_bounded_page(self) -> None:
        query = MedicationRequestQuery()

        assert query.status is None
        assert query.prescribed_date_from is None
        assert query.prescribed_date_to is None
        assert query.limit == 50
        assert query.offset == 0

    def test_accepts_several_statuses(self) -> None:
        """So a caller can ask for active and on-hold in one go."""
        query = MedicationRequestQuery.model_validate({"status": ["active", "on-hold"]})

        assert query.status == [Status.ACTIVE, Status.ON_HOLD]

    def test_accepts_a_prescribed_date_range(self) -> None:
        query = MedicationRequestQuery.model_validate(
            {"prescribed_date_from": "2026-01-01", "prescribed_date_to": "2026-03-01"}
        )

        assert query.prescribed_date_from == date(2026, 1, 1)
        assert query.prescribed_date_to == date(2026, 3, 1)

    def test_rejects_a_backwards_date_range(self) -> None:
        with pytest.raises(ValidationError):
            MedicationRequestQuery.model_validate(
                {"prescribed_date_from": "2026-03-01", "prescribed_date_to": "2026-01-01"}
            )

    def test_allows_a_range_of_a_single_day(self) -> None:
        query = MedicationRequestQuery.model_validate(
            {"prescribed_date_from": "2026-01-01", "prescribed_date_to": "2026-01-01"}
        )

        assert query.prescribed_date_from == query.prescribed_date_to

    @pytest.mark.parametrize(("field", "value"), [("limit", 0), ("limit", 201), ("offset", -1)])
    def test_rejects_paging_outside_sensible_bounds(self, field: str, value: int) -> None:
        with pytest.raises(ValidationError):
            MedicationRequestQuery.model_validate({field: value})

    @pytest.mark.parametrize("limit", [1, 200])
    def test_accepts_paging_at_the_bounds(self, limit: int) -> None:
        assert MedicationRequestQuery.model_validate({"limit": limit}).limit == limit

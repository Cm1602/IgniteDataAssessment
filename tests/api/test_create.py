"""POST /patients/{patient_id}/medication-requests."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import CLINICIAN, MEDICATION, OTHER_MEDICATION, OTHER_PATIENT, PATIENT

Body = Callable[..., dict[str, Any]]


def test_returns_201_and_the_new_request(client: TestClient, new_request: Body) -> None:
    response = client.post(f"/patients/{PATIENT}/medication-requests", json=new_request())

    assert response.status_code == 201
    body = response.json()
    assert uuid.UUID(body["id"])
    assert body["patient_id"] == PATIENT
    assert body["clinician_id"] == CLINICIAN
    assert body["medication_id"] == MEDICATION
    assert body["status"] == "active"
    assert body["frequency"] == "3 times/day"
    assert body["reason_text"] == "Schistosomiasis treatment"


def test_includes_the_medication_and_clinician_names(client: TestClient, new_request: Body) -> None:
    """The brief asks for the code name and the clinician's name in responses."""
    body = client.post(f"/patients/{PATIENT}/medication-requests", json=new_request()).json()

    assert body["medication"]["code_name"] == "Oxamniquine"
    assert body["clinician"]["first_name"] == "Elinor"
    assert body["clinician"]["last_name"] == "Ostrom"


def test_allows_an_open_ended_request(client: TestClient, new_request: Body) -> None:
    response = client.post(
        f"/patients/{PATIENT}/medication-requests", json=new_request(end_date=None)
    )

    assert response.status_code == 201
    assert response.json()["end_date"] is None


def test_what_you_get_back_is_what_was_saved(client: TestClient, new_request: Body) -> None:
    """The POST response and a later GET should not disagree about anything."""
    created = client.post(f"/patients/{PATIENT}/medication-requests", json=new_request()).json()

    listed = client.get(f"/patients/{PATIENT}/medication-requests").json()

    assert listed == [created]


class TestMissingReferences:
    """Creating a request fails if anything it points at is not there."""

    def test_unknown_patient_is_404(self, client: TestClient, new_request: Body) -> None:
        """The patient is in the URL, so a missing one means the URL is wrong."""
        response = client.post(f"/patients/{uuid.uuid4()}/medication-requests", json=new_request())

        assert response.status_code == 404

    def test_unknown_clinician_is_400(self, client: TestClient, new_request: Body) -> None:
        """The body parsed fine, the value in it just does not point at anything."""
        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(clinician_id=str(uuid.uuid4())),
        )

        assert response.status_code == 400
        assert "clinician" in response.json()["detail"].lower()

    def test_unknown_medication_is_400(self, client: TestClient, new_request: Body) -> None:
        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(medication_id=str(uuid.uuid4())),
        )

        assert response.status_code == 400
        assert "medication" in response.json()["detail"].lower()

    def test_nothing_is_written_when_a_reference_is_missing(
        self, client: TestClient, new_request: Body
    ) -> None:
        client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(clinician_id=str(uuid.uuid4())),
        )

        assert client.get(f"/patients/{PATIENT}/medication-requests").json() == []


class TestValidation:
    """Bad payloads never reach the business logic."""

    def test_missing_prescribed_date_is_422(self, client: TestClient, new_request: Body) -> None:
        body = new_request()
        del body["prescribed_date"]

        response = client.post(f"/patients/{PATIENT}/medication-requests", json=body)

        assert response.status_code == 422

    def test_unknown_field_is_422(self, client: TestClient, new_request: Body) -> None:
        response = client.post(
            f"/patients/{PATIENT}/medication-requests", json=new_request(dosage="2 tablets")
        )

        assert response.status_code == 422

    def test_patient_id_in_the_body_is_422(self, client: TestClient, new_request: Body) -> None:
        response = client.post(
            f"/patients/{PATIENT}/medication-requests", json=new_request(patient_id=PATIENT)
        )

        assert response.status_code == 422

    def test_end_date_before_start_date_is_400(self, client: TestClient, new_request: Body) -> None:
        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-01-10", end_date="2026-01-09"),
        )

        assert response.status_code == 400

    def test_a_patient_id_that_is_not_a_uuid_is_422(
        self, client: TestClient, new_request: Body
    ) -> None:
        response = client.post("/patients/not-a-uuid/medication-requests", json=new_request())

        assert response.status_code == 422


class TestOverlapRule:
    """No two active requests for the same patient and medication may overlap."""

    def test_an_overlapping_active_request_is_409(
        self, client: TestClient, new_request: Body
    ) -> None:
        client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-01-01", end_date="2026-01-31"),
        )

        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-01-15", end_date="2026-02-15"),
        )

        assert response.status_code == 409

    def test_sharing_a_single_day_is_an_overlap(
        self, client: TestClient, new_request: Body
    ) -> None:
        client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-01-01", end_date="2026-01-31"),
        )

        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-01-31", end_date="2026-02-15"),
        )

        assert response.status_code == 409

    def test_an_open_ended_request_blocks_everything_after_it(
        self, client: TestClient, new_request: Body
    ) -> None:
        client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-01-01", end_date=None),
        )

        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2027-06-01", end_date="2027-06-30"),
        )

        assert response.status_code == 409

    def test_periods_that_do_not_touch_are_fine(
        self, client: TestClient, new_request: Body
    ) -> None:
        client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-01-01", end_date="2026-01-31"),
        )

        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(start_date="2026-02-01", end_date="2026-02-28"),
        )

        assert response.status_code == 201

    def test_a_different_medication_is_fine(self, client: TestClient, new_request: Body) -> None:
        client.post(f"/patients/{PATIENT}/medication-requests", json=new_request())

        response = client.post(
            f"/patients/{PATIENT}/medication-requests",
            json=new_request(medication_id=OTHER_MEDICATION),
        )

        assert response.status_code == 201

    def test_a_different_patient_is_fine(self, client: TestClient, new_request: Body) -> None:
        client.post(f"/patients/{PATIENT}/medication-requests", json=new_request())

        response = client.post(f"/patients/{OTHER_PATIENT}/medication-requests", json=new_request())

        assert response.status_code == 201

    def test_only_active_requests_block(self, client: TestClient, new_request: Body) -> None:
        """A cancelled request is not a live prescription, so it blocks nothing."""
        client.post(
            f"/patients/{PATIENT}/medication-requests", json=new_request(status="cancelled")
        )

        response = client.post(f"/patients/{PATIENT}/medication-requests", json=new_request())

        assert response.status_code == 201

    def test_a_new_non_active_request_may_overlap_an_active_one(
        self, client: TestClient, new_request: Body
    ) -> None:
        client.post(f"/patients/{PATIENT}/medication-requests", json=new_request())

        response = client.post(
            f"/patients/{PATIENT}/medication-requests", json=new_request(status="on-hold")
        )

        assert response.status_code == 201

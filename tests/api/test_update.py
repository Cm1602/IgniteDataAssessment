"""PATCH /medication-requests/{id}."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import PATIENT

Body = Callable[..., dict[str, Any]]
Create = Callable[..., dict[str, Any]]


@pytest.fixture
def create(client: TestClient, new_request: Body) -> Create:
    """Create a request and hand back the response body."""

    def make(**overrides: Any) -> dict[str, Any]:
        response = client.post(
            f"/patients/{PATIENT}/medication-requests", json=new_request(**overrides)
        )
        assert response.status_code == 201, response.text
        return dict(response.json())

    return make


class TestThePermittedFields:
    def test_change_the_end_date(self, client: TestClient, create: Create) -> None:
        existing = create()

        response = client.patch(
            f"/medication-requests/{existing['id']}", json={"end_date": "2026-02-28"}
        )

        assert response.status_code == 200
        assert response.json()["end_date"] == "2026-02-28"

    def test_change_the_frequency(self, client: TestClient, create: Create) -> None:
        existing = create()

        response = client.patch(
            f"/medication-requests/{existing['id']}", json={"frequency": "twice/day"}
        )

        assert response.status_code == 200
        assert response.json()["frequency"] == "twice/day"

    def test_change_the_status(self, client: TestClient, create: Create) -> None:
        existing = create()

        response = client.patch(
            f"/medication-requests/{existing['id']}", json={"status": "on-hold"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "on-hold"

    def test_change_all_three_at_once(self, client: TestClient, create: Create) -> None:
        existing = create()

        response = client.patch(
            f"/medication-requests/{existing['id']}",
            json={"end_date": "2026-03-01", "frequency": "once/day", "status": "completed"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["end_date"] == "2026-03-01"
        assert body["frequency"] == "once/day"
        assert body["status"] == "completed"

    def test_null_clears_the_end_date(self, client: TestClient, create: Create) -> None:
        existing = create(end_date="2026-01-20")

        response = client.patch(f"/medication-requests/{existing['id']}", json={"end_date": None})

        assert response.status_code == 200
        assert response.json()["end_date"] is None

    def test_fields_left_out_are_untouched(self, client: TestClient, create: Create) -> None:
        existing = create()

        body = client.patch(
            f"/medication-requests/{existing['id']}", json={"status": "on-hold"}
        ).json()

        assert body["end_date"] == existing["end_date"]
        assert body["frequency"] == existing["frequency"]
        assert body["reason_text"] == existing["reason_text"]

    def test_the_response_still_carries_the_names(self, client: TestClient, create: Create) -> None:
        existing = create()

        body = client.patch(
            f"/medication-requests/{existing['id']}", json={"frequency": "once/day"}
        ).json()

        assert body["medication"]["code_name"] == "Oxamniquine"
        assert body["clinician"]["last_name"] == "Ostrom"

    def test_the_change_sticks(self, client: TestClient, create: Create) -> None:
        existing = create()

        client.patch(f"/medication-requests/{existing['id']}", json={"status": "completed"})
        listed = client.get(f"/patients/{PATIENT}/medication-requests").json()

        assert listed[0]["status"] == "completed"


class TestFieldsOutsideThePermittedSet:
    """Business rule 4. Rejected, not quietly ignored."""

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("patient_id", "33333333-3333-4333-8333-333333333333"),
            ("clinician_id", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            ("medication_id", "dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
            ("start_date", "2026-05-01"),
            ("prescribed_date", "2026-05-01"),
            ("reason_text", "changed my mind"),
        ],
    )
    def test_each_one_is_422(
        self, client: TestClient, create: Create, field: str, value: str
    ) -> None:
        existing = create()

        response = client.patch(f"/medication-requests/{existing['id']}", json={field: value})

        assert response.status_code == 422

    def test_a_rejected_patch_changes_nothing_at_all(
        self, client: TestClient, create: Create
    ) -> None:
        """Even the permitted field in the same payload must not be applied."""
        existing = create()

        client.patch(
            f"/medication-requests/{existing['id']}",
            json={"frequency": "once/day", "start_date": "2026-05-01"},
        )
        after = client.get(f"/patients/{PATIENT}/medication-requests").json()[0]

        assert after["start_date"] == existing["start_date"]
        assert after["frequency"] == existing["frequency"]

    def test_an_empty_patch_is_422(self, client: TestClient, create: Create) -> None:
        existing = create()

        response = client.patch(f"/medication-requests/{existing['id']}", json={})

        assert response.status_code == 422


class TestStatusTransitions:
    @pytest.mark.parametrize("final_status", ["completed", "cancelled"])
    def test_a_finished_request_cannot_go_back_to_active(
        self, client: TestClient, create: Create, final_status: str
    ) -> None:
        existing = create()
        client.patch(f"/medication-requests/{existing['id']}", json={"status": final_status})

        response = client.patch(f"/medication-requests/{existing['id']}", json={"status": "active"})

        assert response.status_code == 409

    def test_on_hold_can_go_back_to_active(self, client: TestClient, create: Create) -> None:
        existing = create()
        client.patch(f"/medication-requests/{existing['id']}", json={"status": "on-hold"})

        response = client.patch(f"/medication-requests/{existing['id']}", json={"status": "active"})

        assert response.status_code == 200
        assert response.json()["status"] == "active"

    def test_resending_a_final_status_is_fine(self, client: TestClient, create: Create) -> None:
        existing = create()
        client.patch(f"/medication-requests/{existing['id']}", json={"status": "cancelled"})

        response = client.patch(
            f"/medication-requests/{existing['id']}", json={"status": "cancelled"}
        )

        assert response.status_code == 200


class TestDates:
    def test_end_date_before_start_date_is_400(self, client: TestClient, create: Create) -> None:
        """Checked against the stored start date, which the payload cannot change."""
        existing = create(start_date="2026-01-06")

        response = client.patch(
            f"/medication-requests/{existing['id']}", json={"end_date": "2026-01-05"}
        )

        assert response.status_code == 400

    def test_ending_on_the_start_date_is_allowed(self, client: TestClient, create: Create) -> None:
        existing = create(start_date="2026-01-06")

        response = client.patch(
            f"/medication-requests/{existing['id']}", json={"end_date": "2026-01-06"}
        )

        assert response.status_code == 200


class TestOverlapOnUpdate:
    """Extending or reviving a request can create a clash that was not there before."""

    def test_extending_into_another_active_period_is_409(
        self, client: TestClient, create: Create
    ) -> None:
        first = create(start_date="2026-01-01", end_date="2026-01-31")
        create(start_date="2026-02-01", end_date="2026-02-28")

        response = client.patch(
            f"/medication-requests/{first['id']}", json={"end_date": "2026-02-10"}
        )

        assert response.status_code == 409

    def test_clearing_the_end_date_into_another_period_is_409(
        self, client: TestClient, create: Create
    ) -> None:
        """Open ended means it now runs forever, straight through the next one."""
        first = create(start_date="2026-01-01", end_date="2026-01-31")
        create(start_date="2026-02-01", end_date="2026-02-28")

        response = client.patch(f"/medication-requests/{first['id']}", json={"end_date": None})

        assert response.status_code == 409

    def test_reactivating_into_an_occupied_period_is_409(
        self, client: TestClient, create: Create
    ) -> None:
        on_hold = create(start_date="2026-01-01", end_date="2026-01-31", status="on-hold")
        create(start_date="2026-01-10", end_date="2026-01-20")

        response = client.patch(f"/medication-requests/{on_hold['id']}", json={"status": "active"})

        assert response.status_code == 409

    def test_shortening_a_request_is_fine(self, client: TestClient, create: Create) -> None:
        """A request must not be treated as overlapping itself."""
        existing = create(start_date="2026-01-01", end_date="2026-01-31")

        response = client.patch(
            f"/medication-requests/{existing['id']}", json={"end_date": "2026-01-15"}
        )

        assert response.status_code == 200


def test_unknown_request_is_404(client: TestClient) -> None:
    response = client.patch(f"/medication-requests/{uuid.uuid4()}", json={"status": "on-hold"})

    assert response.status_code == 404


def test_an_id_that_is_not_a_uuid_is_422(client: TestClient) -> None:
    response = client.patch("/medication-requests/not-a-uuid", json={"status": "on-hold"})

    assert response.status_code == 422

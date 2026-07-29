"""GET /patients/{patient_id}/medication-requests."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import OTHER_MEDICATION, OTHER_PATIENT, PATIENT

Body = Callable[..., dict[str, Any]]


@pytest.fixture
def existing(client: TestClient, new_request: Body) -> dict[str, str]:
    """Three requests for our patient, spread across months and statuses.

    Plus one for a different patient, which must never show up in the results.
    Returns a label to id map so tests can say what they mean.
    """
    spread: dict[str, dict[str, Any]] = {
        "january_active": {
            "prescribed_date": "2026-01-05",
            "start_date": "2026-01-06",
            "end_date": "2026-01-20",
        },
        "february_cancelled": {
            "prescribed_date": "2026-02-05",
            "start_date": "2026-02-06",
            "end_date": "2026-02-20",
            "status": "cancelled",
        },
        "march_on_hold": {
            "prescribed_date": "2026-03-05",
            "start_date": "2026-03-06",
            "end_date": "2026-03-20",
            "status": "on-hold",
            "medication_id": OTHER_MEDICATION,
        },
    }

    created = {}
    for label, overrides in spread.items():
        response = client.post(
            f"/patients/{PATIENT}/medication-requests", json=new_request(**overrides)
        )
        assert response.status_code == 201, response.text
        created[label] = response.json()["id"]

    somebody_else = client.post(
        f"/patients/{OTHER_PATIENT}/medication-requests", json=new_request()
    )
    created["other_patient"] = somebody_else.json()["id"]
    return created


def test_returns_only_this_patients_requests(client: TestClient, existing: dict[str, str]) -> None:
    body = client.get(f"/patients/{PATIENT}/medication-requests").json()

    assert len(body) == 3
    assert existing["other_patient"] not in {item["id"] for item in body}


def test_newest_prescription_first(client: TestClient, existing: dict[str, str]) -> None:
    body = client.get(f"/patients/{PATIENT}/medication-requests").json()

    assert [item["prescribed_date"] for item in body] == ["2026-03-05", "2026-02-05", "2026-01-05"]


def test_every_item_carries_the_names(client: TestClient, existing: dict[str, str]) -> None:
    body = client.get(f"/patients/{PATIENT}/medication-requests").json()

    for item in body:
        assert item["medication"]["code_name"]
        assert item["clinician"]["first_name"] == "Elinor"
        assert item["clinician"]["last_name"] == "Ostrom"


def test_a_patient_with_nothing_gets_an_empty_list(client: TestClient) -> None:
    response = client.get(f"/patients/{PATIENT}/medication-requests")

    assert response.status_code == 200
    assert response.json() == []


def test_unknown_patient_is_404(client: TestClient) -> None:
    """Different from an empty list: this patient does not exist at all."""
    response = client.get(f"/patients/{uuid.uuid4()}/medication-requests")

    assert response.status_code == 404


class TestStatusFilter:
    def test_one_status(self, client: TestClient, existing: dict[str, str]) -> None:
        body = client.get(
            f"/patients/{PATIENT}/medication-requests", params={"status": "cancelled"}
        ).json()

        assert [item["id"] for item in body] == [existing["february_cancelled"]]

    def test_several_statuses(self, client: TestClient, existing: dict[str, str]) -> None:
        body = client.get(
            f"/patients/{PATIENT}/medication-requests",
            params=[("status", "active"), ("status", "on-hold")],
        ).json()

        assert {item["id"] for item in body} == {
            existing["january_active"],
            existing["march_on_hold"],
        }

    def test_a_status_that_does_not_exist_is_422(self, client: TestClient) -> None:
        response = client.get(
            f"/patients/{PATIENT}/medication-requests", params={"status": "paused"}
        )

        assert response.status_code == 422


class TestPrescribedDateFilter:
    def test_from_is_inclusive(self, client: TestClient, existing: dict[str, str]) -> None:
        body = client.get(
            f"/patients/{PATIENT}/medication-requests",
            params={"prescribed_date_from": "2026-02-05"},
        ).json()

        assert {item["id"] for item in body} == {
            existing["february_cancelled"],
            existing["march_on_hold"],
        }

    def test_to_is_inclusive(self, client: TestClient, existing: dict[str, str]) -> None:
        body = client.get(
            f"/patients/{PATIENT}/medication-requests",
            params={"prescribed_date_to": "2026-02-05"},
        ).json()

        assert {item["id"] for item in body} == {
            existing["january_active"],
            existing["february_cancelled"],
        }

    def test_both_ends_together(self, client: TestClient, existing: dict[str, str]) -> None:
        body = client.get(
            f"/patients/{PATIENT}/medication-requests",
            params={"prescribed_date_from": "2026-02-01", "prescribed_date_to": "2026-02-28"},
        ).json()

        assert [item["id"] for item in body] == [existing["february_cancelled"]]

    def test_combined_with_a_status_filter(
        self, client: TestClient, existing: dict[str, str]
    ) -> None:
        """Filters narrow together rather than widening."""
        body = client.get(
            f"/patients/{PATIENT}/medication-requests",
            params={"status": "active", "prescribed_date_from": "2026-02-01"},
        ).json()

        assert body == []

    def test_a_backwards_range_is_422(self, client: TestClient) -> None:
        response = client.get(
            f"/patients/{PATIENT}/medication-requests",
            params={"prescribed_date_from": "2026-03-01", "prescribed_date_to": "2026-01-01"},
        )

        assert response.status_code == 422


class TestPaging:
    def test_limit_and_offset_walk_through_the_results(
        self, client: TestClient, existing: dict[str, str]
    ) -> None:
        first_page = client.get(
            f"/patients/{PATIENT}/medication-requests", params={"limit": 2}
        ).json()
        second_page = client.get(
            f"/patients/{PATIENT}/medication-requests", params={"limit": 2, "offset": 2}
        ).json()

        assert len(first_page) == 2
        assert len(second_page) == 1
        assert {i["id"] for i in first_page}.isdisjoint({i["id"] for i in second_page})

    def test_asking_for_too_much_is_422(self, client: TestClient) -> None:
        response = client.get(f"/patients/{PATIENT}/medication-requests", params={"limit": 1000})

        assert response.status_code == 422

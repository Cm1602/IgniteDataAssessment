"""Whole-app concerns: health and request IDs."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.logging_config import JsonFormatter


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_the_openapi_schema_can_be_generated(client: TestClient) -> None:
    """Schema generation happens on first request and can fail on a bad response
    model, which shows up as a 500 on /docs rather than at start up."""
    assert client.get("/openapi.json").status_code == 200


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    """So a log line can be traced back to the call that produced it."""
    response = client.get("/health")

    assert response.headers["x-request-id"]


def test_a_supplied_request_id_is_kept(client: TestClient) -> None:
    """If a caller or gateway already set one, trace with theirs rather than ours."""
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["x-request-id"] == "abc-123"


def test_log_records_carry_the_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """The header alone is not the point. The point is finding the logs later."""
    with caplog.at_level(logging.INFO, logger="app.middleware"):
        client.get("/health", headers={"X-Request-ID": "trace-me"})

    handled = [record for record in caplog.records if record.getMessage() == "Request handled"]

    assert handled, "no completion log line was written"
    # Read the record's dict rather than its attributes: these are added at
    # runtime, so LogRecord does not declare them.
    fields = handled[0].__dict__
    assert fields["request_id"] == "trace-me"
    assert fields["status_code"] == 200
    assert fields["path"] == "/health"


def test_the_request_id_survives_into_the_json_output(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Stamped when the record is made, so it is still right whenever it is rendered."""
    with caplog.at_level(logging.INFO, logger="app.middleware"):
        client.get("/health", headers={"X-Request-ID": "trace-me"})

    handled = next(r for r in caplog.records if r.getMessage() == "Request handled")
    rendered = json.loads(JsonFormatter().format(handled))

    assert rendered["request_id"] == "trace-me"
    assert rendered["level"] == "INFO"
    assert rendered["message"] == "Request handled"

"""Turning domain errors into HTTP responses.

The whole mapping is in one place so there is a single answer to "why did that
come back as a 409".

FastAPI already returns 422 for anything that fails schema validation, so
nothing here uses that code. That keeps the two apart:

* 422 means the request did not parse or validate
* 400 means it parsed, but a value in it does not work
* 404 means something named in the URL is not there
* 409 means it is fine but clashes with what is already stored
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.errors import ConflictError, DomainError, InvalidRequestError, NotFoundError

STATUS_BY_ERROR: tuple[tuple[type[DomainError], int], ...] = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (InvalidRequestError, status.HTTP_400_BAD_REQUEST),
)


def status_for(error: DomainError) -> int:
    """Which HTTP status represents this error."""
    for error_type, http_status in STATUS_BY_ERROR:
        if isinstance(error, error_type):
            return http_status
    # A DomainError that is not one of the three kinds is a gap in the
    # hierarchy rather than a client mistake, so treat it as our problem.
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def handle_domain_error(_request: Request, exc: Exception) -> JSONResponse:
    """Render a rule violation using FastAPI's usual error shape."""
    assert isinstance(exc, DomainError)
    return JSONResponse(status_code=status_for(exc), content={"detail": str(exc)})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, handle_domain_error)

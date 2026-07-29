"""Builds the FastAPI application."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app import __version__
from app.api.errors import register_error_handlers
from app.api.routes import health, medication_requests
from app.config import get_settings
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware

DESCRIPTION = """
Records medications prescribed for patients by clinicians.

Patients, clinicians and medications are treated as reference data that already
exists and is loaded by the seed script. This service owns the medication
requests that tie them together.
"""


def create_app() -> FastAPI:
    """Build the app.

    A factory rather than only a module level app, so tests can build a fresh
    one with their own dependencies rather than sharing a global.

    Deliberately does not touch logging. Reconfiguring the root logger is a
    process wide side effect, and a function that builds an object should not
    be pulling handlers out from under whatever else is running, tests
    included. That happens once at import, below.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)

    router = APIRouter()
    router.include_router(health.router)
    router.include_router(medication_requests.patient_router)
    router.include_router(medication_requests.request_router)
    app.include_router(router)

    return app


# Configured once when the process loads this module, which is what
# `uvicorn app.main:app` does. Anything that only wants an app object can call
# create_app() and keep its own logging set up.
configure_logging(get_settings().log_level)

app = create_app()

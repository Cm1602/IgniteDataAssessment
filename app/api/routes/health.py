"""Health check."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import SessionDep

logger = logging.getLogger(__name__)

router = APIRouter(tags=["service"])


class Health(BaseModel):
    """Whether the service is working."""

    status: str
    database: str


@router.get("/health", summary="Is the service up and can it reach its database")
def health(session: SessionDep) -> Health:
    """Report health.

    Actually queries the database rather than just returning ok, since a
    service that cannot reach its data is not healthy in any useful sense.
    Docker Compose uses this to decide when the container is ready.
    """
    try:
        session.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check could not reach the database")
        return Health(status="degraded", database="unavailable")
    return Health(status="ok", database="ok")

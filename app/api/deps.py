"""Dependencies the routes share."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.services.medication_requests import MedicationRequestService

SessionDep = Annotated[Session, Depends(get_session)]


def get_service(session: SessionDep) -> MedicationRequestService:
    return MedicationRequestService(session)


ServiceDep = Annotated[MedicationRequestService, Depends(get_service)]

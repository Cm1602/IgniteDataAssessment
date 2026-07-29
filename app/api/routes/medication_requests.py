"""The three endpoints from the brief.

Two routers because the paths are shaped differently. Creating and listing hang
off a patient, since a request only makes sense in the context of one. Updating
addresses the request directly, because by then it has its own id and the
patient cannot change.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, status

from app.api.deps import ServiceDep
from app.schemas.medication_request import (
    MedicationRequestCreate,
    MedicationRequestQuery,
    MedicationRequestRead,
)
from app.schemas.medication_request import MedicationRequestUpdate as UpdatePayload

PatientId = Annotated[uuid.UUID, Path(description="An existing patient.")]
RequestId = Annotated[uuid.UUID, Path(description="The medication request to change.")]

# Documented so the generated OpenAPI page shows what can come back, not just
# the happy path.
Responses = dict[int | str, dict[str, Any]]

CREATE_RESPONSES: Responses = {
    400: {"description": "The clinician or medication does not exist, or the dates are wrong."},
    404: {"description": "No such patient."},
    409: {"description": "An active request for this medication already covers these dates."},
}
LIST_RESPONSES: Responses = {404: {"description": "No such patient."}}
UPDATE_RESPONSES: Responses = {
    400: {"description": "End date would fall before the start date."},
    404: {"description": "No such medication request."},
    409: {"description": "Not a permitted status change, or it would overlap another request."},
}

patient_router = APIRouter(prefix="/patients/{patient_id}", tags=["medication requests"])
request_router = APIRouter(prefix="/medication-requests", tags=["medication requests"])


@patient_router.post(
    "/medication-requests",
    response_model=MedicationRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a medication request for a patient",
    responses=CREATE_RESPONSES,
)
def create_medication_request(
    patient_id: PatientId, payload: MedicationRequestCreate, service: ServiceDep
) -> MedicationRequestRead:
    """Prescribe a medication for a patient.

    The patient comes from the path, so it is not accepted in the body.
    """
    created = service.create(patient_id, payload)
    return MedicationRequestRead.model_validate(created)


@patient_router.get(
    "/medication-requests",
    response_model=list[MedicationRequestRead],
    summary="List a patient's medication requests",
    responses=LIST_RESPONSES,
)
def list_medication_requests(
    patient_id: PatientId,
    query: Annotated[MedicationRequestQuery, Query()],
    service: ServiceDep,
) -> list[MedicationRequestRead]:
    """List a patient's requests, most recently prescribed first.

    Narrow the results by status, which can be repeated, and by a range of
    prescribed dates. Each entry includes the medication's code name and the
    prescribing clinician's name.
    """
    found = service.list_for_patient(patient_id, query)
    return [MedicationRequestRead.model_validate(item) for item in found]


@request_router.patch(
    "/{medication_request_id}",
    response_model=MedicationRequestRead,
    summary="Update a medication request",
    responses=UPDATE_RESPONSES,
)
def update_medication_request(
    medication_request_id: RequestId, payload: UpdatePayload, service: ServiceDep
) -> MedicationRequestRead:
    """Change the end date, frequency or status.

    Any other field is rejected rather than ignored. A completed or cancelled
    request cannot be made active again, and the result must not overlap
    another active request for the same medication.
    """
    updated = service.update(medication_request_id, payload)
    return MedicationRequestRead.model_validate(updated)

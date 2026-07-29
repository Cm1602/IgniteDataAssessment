"""Request schemas for medication requests.

Every model sets ``extra="forbid"``. Unknown fields are a client mistake, and
failing loudly beats accepting a request and quietly doing something else.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import MedicationRequestStatus

# Free text fields are capped and may not be blank. An empty string is nearly
# always a client bug rather than a deliberate value.
ReasonText = Annotated[str, Field(min_length=1, max_length=2000)]
Frequency = Annotated[str, Field(min_length=1, max_length=100, examples=["3 times/day"])]


class MedicationRequestCreate(BaseModel):
    """Body of ``POST /patients/{patient_id}/medication-requests``.

    The patient reference is required on a medication request but comes from
    the path, so it is not accepted here.
    """

    model_config = ConfigDict(extra="forbid")

    clinician_id: UUID = Field(description="Must be an existing clinician.")
    medication_id: UUID = Field(description="Must be an existing medication.")
    reason_text: ReasonText | None = Field(default=None, description="Why it was prescribed.")
    prescribed_date: date = Field(description="When the prescription was written.")
    start_date: date = Field(description="First day the patient takes it.")
    end_date: date | None = Field(
        default=None, description="Last day. Leave out for an open ended request."
    )
    frequency: Frequency | None = Field(default=None, description="Dosing frequency, free text.")
    status: MedicationRequestStatus = Field(
        default=MedicationRequestStatus.ACTIVE, description="Defaults to active."
    )


class MedicationRequestUpdate(BaseModel):
    """Body of ``PATCH /medication-requests/{id}``.

    Only end date, frequency and status may change. Anything else is rejected.

    Omitting a field leaves it alone. Sending an explicit ``null`` clears it,
    which is why the service reads this with ``exclude_unset=True`` rather than
    skipping ``None`` values.
    """

    model_config = ConfigDict(extra="forbid")

    end_date: date | None = Field(default=None, description="Send null to clear the end date.")
    frequency: Frequency | None = Field(default=None, description="Send null to clear it.")
    status: MedicationRequestStatus | None = Field(default=None)

    @model_validator(mode="after")
    def check_something_is_being_changed(self) -> MedicationRequestUpdate:
        if not self.model_fields_set:
            raise ValueError("Provide at least one of end_date, frequency or status.")
        # Clearing an end date is meaningful. Clearing a status is not, since
        # every request has to be in some state.
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("status cannot be null.")
        return self


class MedicationRequestQuery(BaseModel):
    """Query string of ``GET /patients/{patient_id}/medication-requests``.

    ``status`` can be repeated to ask for more than one at a time, for example
    ``?status=active&status=on-hold``.
    """

    model_config = ConfigDict(extra="forbid")

    status: list[MedicationRequestStatus] | None = Field(
        default=None, description="Filter by one or more statuses."
    )
    prescribed_date_from: date | None = Field(
        default=None, description="Prescribed on or after this date."
    )
    prescribed_date_to: date | None = Field(
        default=None, description="Prescribed on or before this date."
    )
    # Paging is bounded so a patient with a long history cannot flood a client
    # or the database with one unqualified request.
    limit: int = Field(default=50, ge=1, le=200, description="Maximum results to return.")
    offset: int = Field(default=0, ge=0, description="Results to skip.")

    @model_validator(mode="after")
    def check_date_range_makes_sense(self) -> MedicationRequestQuery:
        if (
            self.prescribed_date_from is not None
            and self.prescribed_date_to is not None
            and self.prescribed_date_from > self.prescribed_date_to
        ):
            raise ValueError("prescribed_date_from cannot be after prescribed_date_to.")
        return self

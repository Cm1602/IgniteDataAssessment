"""What the three endpoints actually do.

This layer owns the order things happen in and the transaction boundary. The
rules themselves stay in ``app.domain`` so they can be tested without a
database.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.domain.enums import MedicationRequestStatus
from app.domain.errors import (
    ClinicianNotFoundError,
    MedicationNotFoundError,
    MedicationRequestNotFoundError,
    OverlappingRequestError,
    PatientNotFoundError,
)
from app.domain.rules import (
    periods_overlap,
    validate_effective_period,
    validate_status_transition,
)
from app.models import Clinician, Medication, MedicationRequest, Patient
from app.schemas.medication_request import (
    MedicationRequestCreate,
    MedicationRequestQuery,
    MedicationRequestUpdate,
)


class MedicationRequestService:
    """Create, list and update medication requests."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, patient_id: uuid.UUID, payload: MedicationRequestCreate) -> MedicationRequest:
        """Create a request for a patient.

        Everything it points at is checked first, so a request that is going to
        fail never gets as far as writing a row.
        """
        self._require_patient(patient_id)
        self._require_clinician(payload.clinician_id)
        self._require_medication(payload.medication_id)

        validate_effective_period(payload.start_date, payload.end_date)

        if payload.status is MedicationRequestStatus.ACTIVE:
            self._reject_if_overlapping(
                patient_id=patient_id,
                medication_id=payload.medication_id,
                start_date=payload.start_date,
                end_date=payload.end_date,
            )

        request = MedicationRequest(
            patient_id=patient_id,
            clinician_id=payload.clinician_id,
            medication_id=payload.medication_id,
            reason_text=payload.reason_text,
            prescribed_date=payload.prescribed_date,
            start_date=payload.start_date,
            end_date=payload.end_date,
            frequency=payload.frequency,
            status=payload.status,
        )
        self.session.add(request)
        self.session.commit()
        return self._reload(request.id)

    def list_for_patient(
        self, patient_id: uuid.UUID, query: MedicationRequestQuery
    ) -> list[MedicationRequest]:
        """List a patient's requests, most recently prescribed first."""
        self._require_patient(patient_id)

        statement = (
            select(MedicationRequest)
            .where(MedicationRequest.patient_id == patient_id)
            .options(
                joinedload(MedicationRequest.clinician),
                joinedload(MedicationRequest.medication),
            )
        )

        if query.status:
            statement = statement.where(MedicationRequest.status.in_(query.status))
        if query.prescribed_date_from is not None:
            statement = statement.where(
                MedicationRequest.prescribed_date >= query.prescribed_date_from
            )
        if query.prescribed_date_to is not None:
            statement = statement.where(
                MedicationRequest.prescribed_date <= query.prescribed_date_to
            )

        statement = (
            statement.order_by(
                MedicationRequest.prescribed_date.desc(),
                MedicationRequest.created_at.desc(),
                # Last resort tiebreak, so paging cannot show the same row twice
                # or skip one when several share a prescribed date.
                MedicationRequest.id,
            )
            .offset(query.offset)
            .limit(query.limit)
        )

        return list(self.session.execute(statement).scalars().all())

    def update(self, request_id: uuid.UUID, payload: MedicationRequestUpdate) -> MedicationRequest:
        """Apply a partial update. Only end date, frequency and status can change."""
        request = self.session.get(MedicationRequest, request_id)
        if request is None:
            raise MedicationRequestNotFoundError(f"No medication request with id {request_id}.")

        # exclude_unset keeps "left out" separate from "explicitly null", so a
        # key present with a null value means clear it.
        changes = payload.model_dump(exclude_unset=True)
        new_status: MedicationRequestStatus = changes.get("status", request.status)
        new_end_date: date | None = changes.get("end_date", request.end_date)

        if "status" in changes:
            validate_status_transition(request.status, new_status)

        # Compared against the stored start date, which this endpoint cannot change.
        validate_effective_period(request.start_date, new_end_date)

        # Only worth re-checking when the result is active and something that
        # affects the clash has actually moved.
        period_moved = new_end_date != request.end_date
        becoming_active = (
            new_status is MedicationRequestStatus.ACTIVE
            and request.status is not MedicationRequestStatus.ACTIVE
        )
        if new_status is MedicationRequestStatus.ACTIVE and (period_moved or becoming_active):
            self._reject_if_overlapping(
                patient_id=request.patient_id,
                medication_id=request.medication_id,
                start_date=request.start_date,
                end_date=new_end_date,
                ignore_id=request.id,
            )

        for field, value in changes.items():
            setattr(request, field, value)

        self.session.commit()
        return self._reload(request.id)

    def _reload(self, request_id: uuid.UUID) -> MedicationRequest:
        """Read a request back with its clinician and medication attached.

        ``populate_existing`` forces a genuine read rather than reusing the copy
        already in the session, so what a write returns is exactly what a later
        read would return.
        """
        statement = (
            select(MedicationRequest)
            .where(MedicationRequest.id == request_id)
            .options(
                joinedload(MedicationRequest.clinician),
                joinedload(MedicationRequest.medication),
            )
            .execution_options(populate_existing=True)
        )
        return self.session.execute(statement).scalar_one()

    def _require_patient(self, patient_id: uuid.UUID) -> Patient:
        patient = self.session.get(Patient, patient_id)
        if patient is None:
            raise PatientNotFoundError(f"No patient with id {patient_id}.")
        return patient

    def _require_clinician(self, clinician_id: uuid.UUID) -> Clinician:
        clinician = self.session.get(Clinician, clinician_id)
        if clinician is None:
            raise ClinicianNotFoundError(f"No clinician with id {clinician_id}.")
        return clinician

    def _require_medication(self, medication_id: uuid.UUID) -> Medication:
        medication = self.session.get(Medication, medication_id)
        if medication is None:
            raise MedicationNotFoundError(f"No medication with id {medication_id}.")
        return medication

    def _reject_if_overlapping(
        self,
        *,
        patient_id: uuid.UUID,
        medication_id: uuid.UUID,
        start_date: date,
        end_date: date | None,
        ignore_id: uuid.UUID | None = None,
    ) -> None:
        """Refuse if an active request for the same medication covers these dates.

        The query narrows to active requests for this one patient and
        medication, which the composite index serves directly. The date
        comparison is then done by ``periods_overlap``, the same function the
        unit tests cover, rather than being written out a second time in SQL
        where the two could drift apart.

        This stays cheap because the rule itself prevents the list from growing:
        active requests for one patient and medication cannot overlap, so there
        can only ever be a handful.
        """
        conditions = [
            MedicationRequest.patient_id == patient_id,
            MedicationRequest.medication_id == medication_id,
            MedicationRequest.status == MedicationRequestStatus.ACTIVE,
        ]
        if ignore_id is not None:
            conditions.append(MedicationRequest.id != ignore_id)

        existing = self.session.execute(select(MedicationRequest).where(*conditions)).scalars()

        for other in existing:
            if periods_overlap(start_date, end_date, other.start_date, other.end_date):
                raise OverlappingRequestError(
                    f"An active request for this medication already covers "
                    f"{other.start_date.isoformat()} to {other.end_date or 'no end date'}."
                )

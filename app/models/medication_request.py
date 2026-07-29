"""The medication request table, which is what this service is for."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.enums import MedicationRequestStatus
from app.models.clinician import Clinician
from app.models.medication import Medication
from app.models.patient import Patient
from app.models.types import enum_column


class MedicationRequest(UUIDPrimaryKey, Timestamps, Base):
    """A medication prescribed for a patient by a clinician."""

    __tablename__ = "medication_requests"
    __table_args__ = (
        # The domain layer checks this too and gives a friendlier message. This
        # is the backstop for anything that does not go through the service.
        # The null test matters: without it every open ended request is
        # rejected, because NULL >= date is not true.
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="end_date_not_before_start_date",
        ),
        # Serves the list endpoint: filter by patient, order by prescribed date.
        Index("ix_medication_requests_patient_prescribed", "patient_id", "prescribed_date"),
        # Serves the overlap check: find active requests for one patient and
        # one medication.
        Index(
            "ix_medication_requests_patient_medication_status",
            "patient_id",
            "medication_id",
            "status",
        ),
    )

    # RESTRICT throughout. Nothing here should quietly delete a prescribing
    # record, and this service exposes no delete endpoints anyway.
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False
    )
    clinician_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("clinicians.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    medication_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("medications.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    reason_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prescribed_date: Mapped[date] = mapped_column(Date, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[MedicationRequestStatus] = mapped_column(
        enum_column(MedicationRequestStatus, "medication_request_status"),
        nullable=False,
        default=MedicationRequestStatus.ACTIVE,
    )

    patient: Mapped[Patient] = relationship(back_populates="medication_requests")
    clinician: Mapped[Clinician] = relationship(back_populates="medication_requests")
    medication: Mapped[Medication] = relationship(back_populates="medication_requests")

    def __repr__(self) -> str:
        return f"<MedicationRequest {self.id} {self.status}>"

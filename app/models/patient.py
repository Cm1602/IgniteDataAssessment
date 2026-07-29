"""The patient table."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.enums import Sex
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.medication_request import MedicationRequest


class Patient(UUIDPrimaryKey, Timestamps, Base):
    """Somebody who can be prescribed a medication."""

    __tablename__ = "patients"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[Sex] = mapped_column(enum_column(Sex, "sex"), nullable=False)

    # No delete cascade. The foreign key uses RESTRICT, so a patient with
    # prescriptions cannot be deleted rather than silently taking the
    # prescribing record with them.
    medication_requests: Mapped[list[MedicationRequest]] = relationship(back_populates="patient")

    def __repr__(self) -> str:
        return f"<Patient {self.id} {self.last_name}>"

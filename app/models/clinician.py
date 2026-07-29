"""The clinician table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.medication_request import MedicationRequest


class Clinician(UUIDPrimaryKey, Timestamps, Base):
    """Somebody who can prescribe a medication."""

    __tablename__ = "clinicians"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Assumption: registration IDs are unique. The brief does not say so, but
    # "ID" implies it, and relaxing a unique constraint later is easier than
    # adding one once duplicates exist. Written up in the README.
    registration_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )

    medication_requests: Mapped[list[MedicationRequest]] = relationship(back_populates="clinician")

    def __repr__(self) -> str:
        return f"<Clinician {self.id} {self.registration_id}>"

"""The medication table."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Timestamps, UUIDPrimaryKey
from app.domain.enums import MedicationForm
from app.models.types import enum_column

if TYPE_CHECKING:
    from app.models.medication_request import MedicationRequest


class Medication(UUIDPrimaryKey, Timestamps, Base):
    """Something that can be prescribed."""

    __tablename__ = "medications"
    __table_args__ = (
        # Indexed for lookups, but deliberately not unique. The brief models
        # strength and form separately from the code, which suggests one code
        # can cover several variants. A unique constraint here would reject
        # them. Noted in the README.
        Index("ix_medications_code_system_code", "code_system", "code"),
    )

    code: Mapped[str] = mapped_column(String(50), nullable=False)
    code_name: Mapped[str] = mapped_column(String(255), nullable=False)
    code_system: Mapped[str] = mapped_column(String(50), nullable=False)
    # Numeric rather than a float. Doses are not something to round.
    strength_value: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    strength_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    form: Mapped[MedicationForm] = mapped_column(
        enum_column(MedicationForm, "medication_form"), nullable=False
    )

    medication_requests: Mapped[list[MedicationRequest]] = relationship(back_populates="medication")

    def __repr__(self) -> str:
        return f"<Medication {self.id} {self.code_name}>"

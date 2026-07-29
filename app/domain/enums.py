"""Fixed sets of values from the domain model."""

from __future__ import annotations

from enum import Enum


class Sex(str, Enum):
    """Patient sex."""

    MALE = "male"
    FEMALE = "female"


class MedicationForm(str, Enum):
    """The physical form a medication comes in."""

    POWDER = "powder"
    TABLET = "tablet"
    CAPSULE = "capsule"
    SYRUP = "syrup"


class MedicationRequestStatus(str, Enum):
    """Where a medication request is in its lifecycle."""

    ACTIVE = "active"
    ON_HOLD = "on-hold"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


#: Statuses a request never comes back from. Reaching one of these means the
#: request can no longer be made active again.
TERMINAL_STATUSES: frozenset[MedicationRequestStatus] = frozenset(
    {MedicationRequestStatus.COMPLETED, MedicationRequestStatus.CANCELLED}
)

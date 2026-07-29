"""The reference data.

The brief treats patients, clinicians and medications as already existing, so
they come from this fixed snapshot rather than through the API.

IDs are hard coded rather than generated. That way the README examples, a
seeded database and the tests all refer to the same rows, and the loader can
tell an existing row from a new one.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Final
from uuid import UUID

from app.domain.enums import MedicationForm, Sex

PATIENTS: Final[tuple[dict[str, Any], ...]] = (
    {
        "id": UUID("11111111-1111-4111-8111-111111111111"),
        "first_name": "Ada",
        "last_name": "Lovelace",
        "date_of_birth": date(1975, 12, 10),
        "sex": Sex.FEMALE,
    },
    {
        "id": UUID("22222222-2222-4222-8222-222222222222"),
        "first_name": "Alan",
        "last_name": "Turing",
        "date_of_birth": date(1982, 6, 23),
        "sex": Sex.MALE,
    },
    {
        "id": UUID("33333333-3333-4333-8333-333333333333"),
        "first_name": "Grace",
        "last_name": "Hopper",
        "date_of_birth": date(1968, 12, 9),
        "sex": Sex.FEMALE,
    },
)

CLINICIANS: Final[tuple[dict[str, Any], ...]] = (
    {
        "id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "first_name": "Elinor",
        "last_name": "Ostrom",
        "registration_id": "REG-1000001",
    },
    {
        "id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        "first_name": "Rahul",
        "last_name": "Iyer",
        "registration_id": "REG-1000002",
    },
)

MEDICATIONS: Final[tuple[dict[str, Any], ...]] = (
    {
        "id": UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        "code": "747006",
        "code_name": "Oxamniquine",
        "code_system": "SNOMED",
        "strength_value": Decimal("250.000"),
        "strength_unit": "mg",
        "form": MedicationForm.CAPSULE,
    },
    {
        "id": UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        "code": "387517004",
        "code_name": "Paracetamol",
        "code_system": "SNOMED",
        "strength_value": Decimal("500.000"),
        "strength_unit": "mg",
        "form": MedicationForm.TABLET,
    },
    {
        "id": UUID("eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"),
        "code": "372687004",
        "code_name": "Amoxicillin",
        "code_system": "SNOMED",
        "strength_value": Decimal("125.000"),
        "strength_unit": "mg/5mL",
        "form": MedicationForm.SYRUP,
    },
    {
        "id": UUID("ffffffff-ffff-4fff-8fff-ffffffffffff"),
        "code": "108537001",
        "code_name": "Mesalazine",
        "code_system": "SNOMED",
        "strength_value": Decimal("1.000"),
        "strength_unit": "g",
        "form": MedicationForm.POWDER,
    },
)

"""The reference data loader.

The Docker entrypoint runs this on every container start, so running it twice
has to be safe. That is the only reason these tests exist.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Clinician, Medication, Patient
from app.seed import load_reference_data
from app.seed_data import CLINICIANS, MEDICATIONS, PATIENTS


def row_counts(session: Session) -> tuple[int, int, int]:
    return (
        session.execute(select(func.count()).select_from(Patient)).scalar_one(),
        session.execute(select(func.count()).select_from(Clinician)).scalar_one(),
        session.execute(select(func.count()).select_from(Medication)).scalar_one(),
    )


def test_loads_every_row(db_session: Session) -> None:
    load_reference_data(db_session)

    assert row_counts(db_session) == (len(PATIENTS), len(CLINICIANS), len(MEDICATIONS))


def test_running_it_again_changes_nothing(db_session: Session) -> None:
    load_reference_data(db_session)
    after_first_run = row_counts(db_session)

    load_reference_data(db_session)
    load_reference_data(db_session)

    assert row_counts(db_session) == after_first_run


def test_edited_rows_are_put_back(db_session: Session) -> None:
    """Reference data is a fixed snapshot, so a local edit should not survive."""
    load_reference_data(db_session)
    patient = db_session.get(Patient, PATIENTS[0]["id"])
    assert patient is not None
    patient.last_name = "Edited"
    db_session.flush()

    load_reference_data(db_session)

    assert patient.last_name == PATIENTS[0]["last_name"]

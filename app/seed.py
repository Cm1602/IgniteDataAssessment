"""Load the reference data. Safe to run as many times as you like.

Run it with ``python -m app.seed``.

Kept out of the migrations on purpose: schema changes and demo data are
different things, and a real deployment would want the migrations without the
fixtures.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Clinician, Medication, Patient
from app.seed_data import CLINICIANS, MEDICATIONS, PATIENTS

logger = logging.getLogger(__name__)


def _load(session: Session, model: type[Base], rows: tuple[dict[str, Any], ...]) -> int:
    """Insert rows that are missing, and reset ones that have been edited."""
    inserted = 0
    for row in rows:
        existing = session.get(model, row["id"])
        if existing is None:
            session.add(model(**row))
            inserted += 1
        else:
            for field, value in row.items():
                setattr(existing, field, value)
    return inserted


def load_reference_data(session: Session) -> None:
    """Load patients, clinicians and medications."""
    inserted = (
        _load(session, Patient, PATIENTS)
        + _load(session, Clinician, CLINICIANS)
        + _load(session, Medication, MEDICATIONS)
    )
    session.flush()
    logger.info("Reference data loaded, %s new rows", inserted)


def main() -> None:
    """Entry point for ``python -m app.seed``."""
    from app.db.session import session_scope

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with session_scope() as session:
        load_reference_data(session)


if __name__ == "__main__":
    main()

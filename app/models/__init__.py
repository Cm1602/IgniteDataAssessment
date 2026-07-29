"""SQLAlchemy models.

Importing them all here means anything that touches the metadata, in
particular Alembic, sees every table.
"""

from app.models.clinician import Clinician
from app.models.medication import Medication
from app.models.medication_request import MedicationRequest
from app.models.patient import Patient

__all__ = ["Clinician", "Medication", "MedicationRequest", "Patient"]

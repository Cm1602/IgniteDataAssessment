"""Create patient, clinician, medication and medication request tables.

Revision ID: 0001
Revises:
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def audit_columns() -> list[sa.Column[sa.DateTime]]:
    """The created and updated columns every table carries."""
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column(
            "sex",
            sa.Enum("male", "female", name="sex", native_enum=False, length=32),
            nullable=False,
        ),
        *audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
    )

    op.create_table(
        "clinicians",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("registration_id", sa.String(length=50), nullable=False),
        *audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinicians")),
    )
    op.create_index(
        op.f("ix_clinicians_registration_id"), "clinicians", ["registration_id"], unique=True
    )

    op.create_table(
        "medications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("code_name", sa.String(length=255), nullable=False),
        sa.Column("code_system", sa.String(length=50), nullable=False),
        sa.Column("strength_value", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("strength_unit", sa.String(length=20), nullable=False),
        sa.Column(
            "form",
            sa.Enum(
                "powder",
                "tablet",
                "capsule",
                "syrup",
                name="medication_form",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        *audit_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medications")),
    )
    op.create_index(
        "ix_medications_code_system_code", "medications", ["code_system", "code"], unique=False
    )

    op.create_table(
        "medication_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("clinician_id", sa.Uuid(), nullable=False),
        sa.Column("medication_id", sa.Uuid(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=True),
        sa.Column("prescribed_date", sa.Date(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("frequency", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "on-hold",
                "cancelled",
                "completed",
                name="medication_request_status",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        *audit_columns(),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_medication_requests_end_date_not_before_start_date"),
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_medication_requests_patient_id_patients"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["clinicians.id"],
            name=op.f("fk_medication_requests_clinician_id_clinicians"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["medication_id"],
            ["medications.id"],
            name=op.f("fk_medication_requests_medication_id_medications"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medication_requests")),
    )
    op.create_index(
        op.f("ix_medication_requests_clinician_id"),
        "medication_requests",
        ["clinician_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_medication_requests_medication_id"),
        "medication_requests",
        ["medication_id"],
        unique=False,
    )
    op.create_index(
        "ix_medication_requests_patient_medication_status",
        "medication_requests",
        ["patient_id", "medication_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_medication_requests_patient_prescribed",
        "medication_requests",
        ["patient_id", "prescribed_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_medication_requests_patient_prescribed", table_name="medication_requests")
    op.drop_index(
        "ix_medication_requests_patient_medication_status", table_name="medication_requests"
    )
    op.drop_index(op.f("ix_medication_requests_medication_id"), table_name="medication_requests")
    op.drop_index(op.f("ix_medication_requests_clinician_id"), table_name="medication_requests")
    op.drop_table("medication_requests")
    op.drop_index("ix_medications_code_system_code", table_name="medications")
    op.drop_table("medications")
    op.drop_index(op.f("ix_clinicians_registration_id"), table_name="clinicians")
    op.drop_table("clinicians")
    op.drop_table("patients")

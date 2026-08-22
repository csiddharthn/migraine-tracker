"""Store multiple medication intakes per migraine entry.

Revision ID: 0004_multiple_medications
Revises: 0003_medication_taken_at
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0004_multiple_medications"
down_revision = "0003_medication_taken_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medication_intakes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.SmallInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("taken_at", sa.Time(), nullable=True),
        sa.Column("dose", sa.String(length=120), nullable=True),
        sa.Column("effectiveness", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["entry_id"], ["migraine_entries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entry_id", "sequence", name="uq_medication_intakes_entry_sequence"),
    )
    op.create_index("ix_medication_intakes_entry_id", "medication_intakes", ["entry_id"])
    op.create_index("ix_medication_intakes_name", "medication_intakes", ["name"])
    op.create_index("ix_medication_intakes_taken_at", "medication_intakes", ["taken_at"])
    op.execute(
        sa.text(
            """
            INSERT INTO medication_intakes
                (entry_id, sequence, name, taken_at, dose, effectiveness)
            SELECT id, 0, btrim(medication_name), medication_taken_at,
                   medication_dose, medication_effectiveness
            FROM migraine_entries
            WHERE medication_name IS NOT NULL AND btrim(medication_name) <> ''
            """
        )
    )
    op.drop_index("ix_migraine_entries_medication_name", table_name="migraine_entries")
    op.drop_column("migraine_entries", "medication_effectiveness")
    op.drop_column("migraine_entries", "medication_dose")
    op.drop_column("migraine_entries", "medication_taken_at")
    op.drop_column("migraine_entries", "medication_name")


def downgrade() -> None:
    op.add_column("migraine_entries", sa.Column("medication_name", sa.String(length=200), nullable=True))
    op.add_column("migraine_entries", sa.Column("medication_taken_at", sa.Time(), nullable=True))
    op.add_column("migraine_entries", sa.Column("medication_dose", sa.String(length=120), nullable=True))
    op.add_column("migraine_entries", sa.Column("medication_effectiveness", sa.String(length=20), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE migraine_entries AS entry
            SET medication_name = intake.name,
                medication_taken_at = intake.taken_at,
                medication_dose = intake.dose,
                medication_effectiveness = intake.effectiveness
            FROM medication_intakes AS intake
            WHERE intake.entry_id = entry.id AND intake.sequence = 0
            """
        )
    )
    op.create_index("ix_migraine_entries_medication_name", "migraine_entries", ["medication_name"])
    op.drop_index("ix_medication_intakes_taken_at", table_name="medication_intakes")
    op.drop_index("ix_medication_intakes_name", table_name="medication_intakes")
    op.drop_index("ix_medication_intakes_entry_id", table_name="medication_intakes")
    op.drop_table("medication_intakes")

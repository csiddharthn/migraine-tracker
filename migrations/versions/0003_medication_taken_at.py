"""Add the optional acute-medication intake time.

Revision ID: 0003_medication_taken_at
Revises: 0002_constraint_names
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0003_medication_taken_at"
down_revision = "0002_constraint_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("migraine_entries", sa.Column("medication_taken_at", sa.Time(), nullable=True))


def downgrade() -> None:
    op.drop_column("migraine_entries", "medication_taken_at")

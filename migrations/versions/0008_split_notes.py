"""Split notes into 4 structured columns.

Revision ID: 0008_split_notes
Revises: 0007_generalize_legacy_trigger
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_split_notes"
down_revision = "0007_generalize_legacy_trigger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new split columns
    op.add_column("migraine_entries", sa.Column("timeline_notes", sa.Text(), nullable=False, server_default=""))
    op.add_column("migraine_entries", sa.Column("possible_factors", sa.Text(), nullable=False, server_default=""))
    op.add_column("migraine_entries", sa.Column("symptoms_and_actions", sa.Text(), nullable=False, server_default=""))
    op.add_column("migraine_entries", sa.Column("other_notes", sa.Text(), nullable=False, server_default=""))
    # Preserve the complete legacy text before removing its source column. A
    # later, user-reviewed cleanup can split this text more precisely, but the
    # schema migration itself must never discard or reinterpret diary content.
    op.execute(
        sa.text(
            "UPDATE migraine_entries "
            "SET timeline_notes = COALESCE(notes, '')"
        )
    )
    op.drop_column("migraine_entries", "notes")


def downgrade() -> None:
    op.add_column("migraine_entries", sa.Column("notes", sa.Text(), nullable=False, server_default=""))
    op.drop_column("migraine_entries", "other_notes")
    op.drop_column("migraine_entries", "symptoms_and_actions")
    op.drop_column("migraine_entries", "possible_factors")
    op.drop_column("migraine_entries", "timeline_notes")

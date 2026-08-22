"""Store provenance for reviewed AI-assisted entry drafts.

Revision ID: 0005_ai_assisted_intake
Revises: 0004_multiple_medications
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0005_ai_assisted_intake"
down_revision = "0004_multiple_medications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = postgresql.JSONB(astext_type=sa.Text())
    op.add_column("migraine_entries", sa.Column("source_narrative", sa.Text(), nullable=True))
    op.add_column("migraine_entries", sa.Column("ai_provider", sa.String(length=40), nullable=True))
    op.add_column("migraine_entries", sa.Column("ai_model", sa.String(length=100), nullable=True))
    op.add_column("migraine_entries", sa.Column("ai_prompt_version", sa.String(length=40), nullable=True))
    op.add_column("migraine_entries", sa.Column("ai_extraction", json_type, nullable=True))
    op.add_column("migraine_entries", sa.Column("ai_reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("migraine_entries", "ai_reviewed_at")
    op.drop_column("migraine_entries", "ai_extraction")
    op.drop_column("migraine_entries", "ai_prompt_version")
    op.drop_column("migraine_entries", "ai_model")
    op.drop_column("migraine_entries", "ai_provider")
    op.drop_column("migraine_entries", "source_narrative")

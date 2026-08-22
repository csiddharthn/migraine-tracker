"""Allow descriptive audit action names.

Revision ID: 0006_expand_audit_action
Revises: 0005_ai_assisted_intake
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_expand_audit_action"
down_revision = "0005_ai_assisted_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "entry_audit_log",
        "action",
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "entry_audit_log",
        "action",
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=False,
    )

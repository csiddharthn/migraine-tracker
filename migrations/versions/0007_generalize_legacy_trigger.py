"""Generalize the legacy missing-trigger description.

Revision ID: 0007_generalize_legacy_trigger
Revises: 0006_expand_audit_action
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0007_generalize_legacy_trigger"
down_revision = "0006_expand_audit_action"
branch_labels = None
depends_on = None


trigger_definitions = sa.table(
    "trigger_definitions",
    sa.column("code", sa.String(length=10)),
    sa.column("description", sa.Text()),
)


def upgrade() -> None:
    op.execute(
        trigger_definitions.update()
        .where(trigger_definitions.c.code == "ND")
        .values(description="Nur für ältere Einträge ohne dokumentierten Auslöser.")
    )


def downgrade() -> None:
    op.execute(
        trigger_definitions.update()
        .where(trigger_definitions.c.code == "ND")
        .values(description="Nur für migrierte Excel-Einträge ohne ausgefüllten Auslöser.")
    )

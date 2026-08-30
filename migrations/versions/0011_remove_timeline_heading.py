"""Remove the redundant heading from dedicated timeline values.

Revision ID: 0011_remove_timeline_heading
Revises: 0010_separate_note_content
"""
from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op


revision = "0011_remove_timeline_heading"
down_revision = "0010_separate_note_content"
branch_labels = None
depends_on = None


TIMELINE_HEADING_PATTERN = re.compile(r"^\s*Zeitlicher Ablauf\s*:\s*", re.IGNORECASE)


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, timeline_notes FROM migraine_entries WHERE timeline_notes <> ''")
    ).mappings()
    for row in rows:
        current = row["timeline_notes"] or ""
        cleaned = _remove_timeline_heading(current)
        if cleaned == current:
            continue
        connection.execute(
            sa.text(
                "UPDATE migraine_entries SET timeline_notes = :timeline_notes WHERE id = :entry_id"
            ),
            {"entry_id": row["id"], "timeline_notes": cleaned},
        )


def downgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, timeline_notes FROM migraine_entries WHERE timeline_notes <> ''")
    ).mappings()
    for row in rows:
        current = (row["timeline_notes"] or "").strip()
        if not current or TIMELINE_HEADING_PATTERN.match(current):
            continue
        connection.execute(
            sa.text(
                "UPDATE migraine_entries SET timeline_notes = :timeline_notes WHERE id = :entry_id"
            ),
            {
                "entry_id": row["id"],
                "timeline_notes": f"Zeitlicher Ablauf:\n\n{current}",
            },
        )


def _remove_timeline_heading(value: str) -> str:
    return TIMELINE_HEADING_PATTERN.sub("", value, count=1).strip()

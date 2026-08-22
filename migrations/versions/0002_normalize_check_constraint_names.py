"""Normalize check-constraint names created by the initial naming convention.

Revision ID: 0002_constraint_names
Revises: 0001_initial
"""
from __future__ import annotations

from alembic import op


revision = "0002_constraint_names"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


CONSTRAINTS = {
    "migraine_entries": (
        (
            "ck_migraine_entries_ck_migraine_entries_duration_nonnegative",
            "ck_migraine_entries_duration_nonnegative",
            "duration_hours >= 0",
        ),
        (
            "ck_migraine_entries_ck_migraine_entries_strength_0_10",
            "ck_migraine_entries_strength_0_10",
            "strength >= 0 AND strength <= 10",
        ),
    ),
    "note_interpretations": (
        (
            "ck_note_interpretations_ck_note_interpretations_end_min_dea3",
            "ck_note_interpretations_end_minute_range",
            "end_minute IS NULL OR end_minute BETWEEN 0 AND 4320",
        ),
        (
            "ck_note_interpretations_ck_note_interpretations_onset_m_a2e7",
            "ck_note_interpretations_onset_minute_range",
            "onset_minute IS NULL OR onset_minute BETWEEN 0 AND 4320",
        ),
        (
            "ck_note_interpretations_ck_note_interpretations_peak_en_c1e3",
            "ck_note_interpretations_peak_end_minute_range",
            "peak_end_minute IS NULL OR peak_end_minute BETWEEN 0 AND 4320",
        ),
        (
            "ck_note_interpretations_ck_note_interpretations_peak_st_39a2",
            "ck_note_interpretations_peak_start_minute_range",
            "peak_start_minute IS NULL OR peak_start_minute BETWEEN 0 AND 4320",
        ),
    ),
}


def upgrade() -> None:
    for table_name, constraints in CONSTRAINTS.items():
        for old_name, new_name, condition in constraints:
            op.drop_constraint(op.f(old_name), table_name, type_="check")
            op.create_check_constraint(op.f(new_name), table_name, condition)


def downgrade() -> None:
    for table_name, constraints in reversed(CONSTRAINTS.items()):
        for old_name, new_name, condition in reversed(constraints):
            op.drop_constraint(op.f(new_name), table_name, type_="check")
            op.create_check_constraint(op.f(old_name), table_name, condition)

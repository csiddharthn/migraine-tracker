from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = PROJECT_ROOT / "migrations" / "versions" / "0008_split_notes.py"


def test_legacy_notes_are_copied_before_the_source_column_is_dropped() -> None:
    migration = MIGRATION_PATH.read_text(encoding="utf-8")

    copy_notes = "SET timeline_notes = COALESCE(notes, '')"
    drop_notes = 'op.drop_column("migraine_entries", "notes")'

    assert copy_notes in migration
    assert drop_notes in migration
    assert migration.index(copy_notes) < migration.index(drop_notes)

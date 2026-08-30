from __future__ import annotations

"""Purpose: Tests for removing redundant headings from timeline values."""

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = PROJECT_ROOT / "migrations" / "versions" / "0011_remove_timeline_heading.py"
SPEC = importlib.util.spec_from_file_location("migration_0011_remove_timeline_heading", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_only_the_leading_timeline_heading_is_removed() -> None:
    value = (
        "Zeitlicher Ablauf:\n\n"
        "05:00 Uhr: Beginn.\n"
        "Hinweis: Der Ausdruck Zeitlicher Ablauf: wurde später erwähnt."
    )

    assert MIGRATION._remove_timeline_heading(value) == (
        "05:00 Uhr: Beginn.\n"
        "Hinweis: Der Ausdruck Zeitlicher Ablauf: wurde später erwähnt."
    )


def test_heading_free_timeline_is_unchanged() -> None:
    value = "05:00 Uhr: Beginn.\n15:00 Uhr: Ende."
    assert MIGRATION._remove_timeline_heading(value) == value

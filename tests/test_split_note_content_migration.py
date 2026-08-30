from __future__ import annotations

"""Purpose: Tests for separating legacy note sections into dedicated columns."""

import importlib.util
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_PATH = PROJECT_ROOT / "migrations" / "versions" / "0010_separate_note_content.py"
SPEC = importlib.util.spec_from_file_location("migration_0010_separate_note_content", MIGRATION_PATH)
assert SPEC is not None and SPEC.loader is not None
MIGRATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MIGRATION)


def test_combined_note_sections_are_routed_without_losing_preamble() -> None:
    notes = (
        "Freie Zusatzangabe.\n\n"
        "Zeitlicher Ablauf:\n\n15:00 Uhr: Beginn.\n22:00 Uhr: Ende.\n\n"
        "Mögliche Einflussfaktoren: Zu wenig Schlaf.\n\n"
        "Beschreibung der Kopfschmerzen: Rechtsseitige Schmerzen.\n\n"
        "Einnahme von Medikamenten: Keine Medikamente eingenommen."
    )

    assert MIGRATION._split_entry_note(notes) == (
        "Zeitlicher Ablauf:\n\n15:00 Uhr: Beginn.\n22:00 Uhr: Ende.",
        "Zu wenig Schlaf.",
        "Rechtsseitige Schmerzen.\n\nKeine Medikamente eingenommen.",
        "Freie Zusatzangabe.",
    )


def test_known_unheaded_legacy_notes_are_semantically_classified() -> None:
    notes = (
        "Beidseitig. Möglicherweise an dem Tag etwas zu wenig Wasser getrunken. "
        "Keine Begleitsymptome; keine Medikation."
    )

    assert MIGRATION._split_entry_note(notes) == (
        "",
        "Möglicherweise an dem Tag etwas zu wenig Wasser getrunken.",
        "Beidseitig. Keine Begleitsymptome; keine Medikation.",
        "",
    )


def test_existing_destination_text_is_preserved_without_exact_duplicates() -> None:
    assert MIGRATION._merge_text("Zu wenig Schlaf.", "Zu wenig Schlaf.") == "Zu wenig Schlaf."
    assert MIGRATION._merge_text("Manuell ergänzt.", "Extrahiert.") == (
        "Manuell ergänzt.\n\nExtrahiert."
    )


def test_unclassifiable_legacy_text_moves_to_other_notes() -> None:
    assert MIGRATION._split_entry_note("Freier Hinweis ohne erkennbare Zuordnung.") == (
        "",
        "",
        "",
        "Freier Hinweis ohne erkennbare Zuordnung.",
    )

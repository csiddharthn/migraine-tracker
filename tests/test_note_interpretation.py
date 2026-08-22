from __future__ import annotations

from backend.note_interpretation import NoteInterpreter


def test_shared_uhr_ranges_and_laterality_are_extracted() -> None:
    notes = (
        "Ca. 15:00 Uhr: Beginn der Kopfschmerzen. "
        "Ca. 17:00–20:00 Uhr: Kopfschmerzen blieben auf ihrer höchsten Intensität. "
        "Ca. 21:30–22:00 Uhr: Kopfschmerzen vollständig verschwunden. "
        "Ausschließlich auf der rechten Kopfseite. Unterbrochener Schlaf durch Unruhe."
    )
    result = NoteInterpreter().interpret(notes, "Rechts")

    assert result.onset_minute == 15 * 60
    assert result.peak_start_minute == 17 * 60
    assert result.peak_end_minute == 20 * 60
    assert result.end_minute == 22 * 60
    assert result.laterality == "rechts"
    assert "Unterbrochener Schlaf / Unruhe" in result.contexts


def test_reviewed_legacy_hours_are_converted_to_minutes() -> None:
    result = NoteInterpreter().interpret(
        "Original bleibt unberührt",
        "Einseitig",
        {"onsetHour": 14.5, "endHour": 26, "laterality": "links", "contexts": ["Kälte / Zugluft"]},
    )
    assert result.onset_minute == 870
    assert result.end_minute == 1560
    assert result.extraction_method == "semantisch geprüft"


def test_compact_begin_end_and_side_wording_is_extracted() -> None:
    result = NoteInterpreter().interpret(
        "Beginn 08:00 Uhr rechts, Ende 10:30 Uhr.",
    )

    assert result.onset_minute == 8 * 60
    assert result.end_minute == 10 * 60 + 30
    assert result.end_status == "dokumentiert"
    assert result.laterality == "rechts"


def test_structured_timeline_recognises_headache_on_waking_and_disappearance() -> None:
    result = NoteInterpreter().interpret(
        "12:30–14:30 Uhr: Aufgewacht. Dabei einen leichten Kopfschmerz wahrgenommen.\n"
        "14:30–16:30 Uhr: Die Kopfschmerzen hielten an und verschwanden anschließend von selbst.\n"
        "Höhepunkt: 12:30–13:00 Uhr (Dauer: 30 Minuten)."
    )

    assert result.onset_minute == 12 * 60 + 30
    assert result.peak_start_minute == 12 * 60 + 30
    assert result.peak_end_minute == 13 * 60
    assert result.end_minute == 16 * 60 + 30
    assert result.end_status == "vollständig"


def test_structured_timeline_does_not_use_negated_headache_as_onset() -> None:
    result = NoteInterpreter().interpret(
        "12:00 Uhr: Erneut aufgewacht, jedoch keine Kopfschmerzen gehabt.\n"
        "15:00 Uhr: Beginn der Kopfschmerzen.\n"
        "22:00 Uhr: Kopfschmerzen vollständig verschwunden."
    )

    assert result.onset_minute == 15 * 60
    assert result.end_minute == 22 * 60


def test_structured_timeline_recognises_headache_that_held_until_a_time() -> None:
    result = NoteInterpreter().interpret(
        "12:00–16:00 Uhr: Kopfschmerz begann beim Aufwachen, hielt bis etwa 16:00 Uhr an, "
        "leichte Intensität.\n"
        "Höhepunkt: 12:00–13:00 Uhr (Dauer: 60 Minuten)."
    )

    assert result.onset_minute == 12 * 60
    assert result.end_minute == 16 * 60
    assert result.end_status == "dokumentiert"

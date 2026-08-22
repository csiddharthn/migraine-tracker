from datetime import time

from backend.note_interpretation import (
    NoteInterpreter,
    StructuredNotes,
    TimelineNoteRow,
    format_structured_notes,
    parse_structured_notes,
)


def test_structured_notes_round_trip_and_feed_time_interpretation() -> None:
    value = StructuredNotes(
        timeline=(
            TimelineNoteRow(time(15, 0), None, "Beginn der Kopfschmerzen."),
            TimelineNoteRow(time(21, 30), time(22, 0), "Kopfschmerzen vollständig verschwunden."),
        ),
        peak_start_minute=17 * 60,
        peak_duration_minutes=180,
        possible_factors="Unterbrochener Schlaf und zu wenig Schlaf.",
        symptoms_and_actions="Rechtsseitige Kopfschmerzen. Keine Tabletten eingenommen.",
    )

    notes = format_structured_notes(value)
    interpretation = NoteInterpreter().interpret(notes)
    parsed = parse_structured_notes(
        notes,
        peak_start_minute=interpretation.peak_start_minute,
        peak_end_minute=interpretation.peak_end_minute,
    )

    assert notes.startswith("Zeitlicher Ablauf:")
    assert "Höhepunkt: 17:00–20:00 Uhr (Dauer: 180 Minuten)." in notes
    assert interpretation.onset_minute == 15 * 60
    assert interpretation.peak_start_minute == 17 * 60
    assert interpretation.peak_end_minute == 20 * 60
    assert interpretation.end_minute == 22 * 60
    assert parsed == value


def test_peak_format_handles_crossing_midnight() -> None:
    notes = format_structured_notes(
        StructuredNotes(peak_start_minute=23 * 60, peak_duration_minutes=120)
    )
    interpretation = NoteInterpreter().interpret("15:00 Uhr: Beginn der Kopfschmerzen.\n" + notes)

    assert "23:00 Uhr–Folgetag, 01:00 Uhr" in notes
    assert interpretation.peak_start_minute == 23 * 60
    assert interpretation.peak_end_minute == 25 * 60


def test_legacy_note_without_headings_remains_available() -> None:
    notes = "Rechtsseitig. Vorherige Nacht bei kühlen Temperaturen geschlafen."

    parsed = parse_structured_notes(notes)

    assert parsed.timeline == ()
    assert parsed.symptoms_and_actions == notes

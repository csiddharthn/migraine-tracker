"""Purpose: Tests for structured notes parsing.

Usage: Tests timeline parsing and midnight-crossing peaks.

Functions available:
- test_structured_notes_round_trip_and_feed_time_interpretation, etc.

Classes available:
- None

Call hierarchy:
- test_structured_notes.py -> backend.note_interpretation
"""

from datetime import time

from backend.note_interpretation import (
    NoteInterpreter,
    StructuredNotes,
    TimelineNoteRow,
    format_structured_notes,
    format_timeline_notes,
    parse_structured_notes,
)

START_TIME = time(15, 0)
END_TIME = time(22, 0)
PEAK_START_MINUTE = 17 * 60
PEAK_DURATION_MINUTES = 180
PEAK_END_MINUTE = 20 * 60
ONSET_MINUTE = 15 * 60
POSSIBLE_FACTORS = "Unterbrochener Schlaf und zu wenig Schlaf."
SYMPTOMS_AND_ACTIONS = "Rechtsseitige Kopfschmerzen. Keine Tabletten eingenommen."
NOTES_START_PREFIX = "Zeitlicher Ablauf:"
PEAK_FORMAT_STRING = "Höhepunkt: 17:00–20:00 Uhr (Dauer: 180 Minuten)."
MIDNIGHT_PEAK_START = 23 * 60
MIDNIGHT_PEAK_DURATION = 120
MIDNIGHT_PEAK_END = 25 * 60
MIDNIGHT_FORMAT_STRING = "23:00 Uhr–Folgetag, 01:00 Uhr"
LEGACY_NOTES = "Rechtsseitig. Vorherige Nacht bei kühlen Temperaturen geschlafen."


def test_structured_notes_round_trip_and_feed_time_interpretation() -> None:
    value = StructuredNotes(
        timeline=(
            TimelineNoteRow(START_TIME, None, "Beginn der Kopfschmerzen."),
            TimelineNoteRow(time(21, 30), END_TIME, "Kopfschmerzen vollständig verschwunden."),
        ),
        peak_start_minute=PEAK_START_MINUTE,
        peak_duration_minutes=PEAK_DURATION_MINUTES,
        possible_factors=POSSIBLE_FACTORS,
        symptoms_and_actions=SYMPTOMS_AND_ACTIONS,
    )

    notes = format_structured_notes(value)
    interpretation = NoteInterpreter().interpret(notes)
    parsed = parse_structured_notes(
        notes,
        peak_start_minute=interpretation.peak_start_minute,
        peak_end_minute=interpretation.peak_end_minute,
    )

    assert notes.startswith(NOTES_START_PREFIX)
    assert PEAK_FORMAT_STRING in notes
    assert interpretation.onset_minute == ONSET_MINUTE
    assert interpretation.peak_start_minute == PEAK_START_MINUTE
    assert interpretation.peak_end_minute == PEAK_END_MINUTE
    assert interpretation.end_minute == 22 * 60
    assert parsed == value


def test_peak_format_handles_crossing_midnight() -> None:
    notes = format_structured_notes(
        StructuredNotes(peak_start_minute=MIDNIGHT_PEAK_START, peak_duration_minutes=MIDNIGHT_PEAK_DURATION)
    )
    interpretation = NoteInterpreter().interpret("15:00 Uhr: Beginn der Kopfschmerzen.\n" + notes)

    assert MIDNIGHT_FORMAT_STRING in notes
    assert interpretation.peak_start_minute == MIDNIGHT_PEAK_START
    assert interpretation.peak_end_minute == MIDNIGHT_PEAK_END


def test_timeline_formatter_excludes_content_stored_in_separate_columns() -> None:
    value = StructuredNotes(
        timeline=(TimelineNoteRow(START_TIME, END_TIME, "Kopfschmerzen bestanden."),),
        peak_start_minute=PEAK_START_MINUTE,
        peak_duration_minutes=PEAK_DURATION_MINUTES,
        possible_factors=POSSIBLE_FACTORS,
        symptoms_and_actions=SYMPTOMS_AND_ACTIONS,
    )

    notes = format_timeline_notes(value)
    parsed = parse_structured_notes(notes)

    assert notes.startswith(NOTES_START_PREFIX)
    assert POSSIBLE_FACTORS not in notes
    assert SYMPTOMS_AND_ACTIONS not in notes
    assert parsed.timeline == value.timeline
    assert parsed.peak_start_minute == value.peak_start_minute
    assert parsed.peak_duration_minutes == value.peak_duration_minutes
    assert parsed.possible_factors == ""
    assert parsed.symptoms_and_actions == ""


def test_legacy_note_without_headings_remains_available() -> None:
    parsed = parse_structured_notes(LEGACY_NOTES)
    assert parsed.timeline == ()
    assert parsed.symptoms_and_actions == LEGACY_NOTES

from __future__ import annotations

"""Purpose: Tests for entry form validation and decoding.

Usage: Tests symptom selection mapping and validation errors.

Functions available:
- test_unified_symptom_selection_maps_to_existing_fields, etc.

Classes available:
- None

Call hierarchy:
- test_entry_form.py -> frontend.forms.entry_form
"""

from datetime import time

from backend.note_interpretation import TimelineNoteRow
from frontend.forms.entry_form import (
    _decode_symptom_selection,
    _medication_validation_error,
    _peak_minute_for_form_value,
    _timeline_validation_error,
)

SYMPTOM_SELECTION = ["aura:F", "aura:S", "symptom:nausea", "symptom:photophobia", "other:T"]
EXPECTED_SYMPTOM_VALUES = {
    "aura_codes": ["F", "S"],
    "vomiting": False,
    "nausea": True,
    "phonophobia": False,
    "photophobia": True,
    "osmophobia": False,
    "other_symptom_codes": ["T"],
}
PEAK_TIME = time(17, 0)
LEGACY_OFFSET_MINUTES = 25 * 60 + 30
MEDICATION_TIME = time(9, 15)


def test_unified_symptom_selection_maps_to_existing_fields() -> None:
    values = _decode_symptom_selection(SYMPTOM_SELECTION)
    assert values == EXPECTED_SYMPTOM_VALUES


def test_timeline_time_rows_reject_end_without_start() -> None:
    rows = [
        TimelineNoteRow(time(15, 0), None, "Beginn der Kopfschmerzen"),
        TimelineNoteRow(time(17, 0), time(20, 0), "Stärkste Phase"),
    ]

    assert _timeline_validation_error(rows) is None
    assert isinstance(rows[0].start_time, time)
    assert isinstance(rows[1].end_time, time)

    error = _timeline_validation_error([TimelineNoteRow(None, time(20, 0), "Ende")])

    assert "Startzeit" in error


def test_peak_time_defaults_to_entry_day_but_preserves_unchanged_legacy_offset() -> None:
    assert _peak_minute_for_form_value(PEAK_TIME, None) == 17 * 60
    assert _peak_minute_for_form_value(time(1, 30), LEGACY_OFFSET_MINUTES) == LEGACY_OFFSET_MINUTES
    assert _peak_minute_for_form_value(time(2, 0), LEGACY_OFFSET_MINUTES) == 2 * 60


def test_medication_rows_require_a_name_when_details_are_entered() -> None:
    assert _medication_validation_error(
        [{"name": None, "taken_at": None, "dose": "", "effectiveness": None}]
    ) is None
    error = _medication_validation_error(
        [{"name": None, "taken_at": MEDICATION_TIME, "dose": "", "effectiveness": None}]
    )
    assert "Medikament" in error

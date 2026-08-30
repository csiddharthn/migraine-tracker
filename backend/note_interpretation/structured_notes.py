from __future__ import annotations

"""Purpose: Structured notes parsing and timeline extraction.

Usage: Parses sections, peaks, ranges, and single lines from notes.

Functions available:
- parse_timeline_notes
- extract_peak
- parse_range_line
- parse_single_line

Classes available:
- TimelineNoteRow
- StructuredNotes

Call hierarchy:
- structured_notes.py -> backend.note_interpretation.interpreter
"""

import re
from dataclasses import dataclass
from datetime import time


SECTION_PATTERN = re.compile(
    r"^(Zeitlicher Ablauf|Mögliche Einflussfaktoren|Umstände vor Beginn der Kopfschmerzen|"
    r"Beschwerden und Maßnahmen|Beschreibung der Kopfschmerzen|Einnahme von Medikamenten)\s*:\s*",
    re.IGNORECASE | re.MULTILINE,
)
PEAK_PATTERN = re.compile(
    r"^Höhepunkt:\s*(?P<next_day>Folgetag,\s*)?(?P<start>[0-2]?\d:[0-5]\d)\s*(?:Uhr)?"
    r"(?:\s*[–-]\s*(?:Folgetag,\s*)?(?P<end>[0-2]?\d:[0-5]\d)\s*Uhr)?"
    r"(?:\s*\(Dauer:\s*(?P<duration>\d+)\s*Minuten\))?\.?$",
    re.IGNORECASE,
)
RANGE_LINE_PATTERN = re.compile(
    r"(?P<start>[0-2]?\d(?::[0-5]\d)?)\s*(?:Uhr)?\s*[–-]\s*"
    r"(?P<end>[0-2]?\d(?::[0-5]\d)?)\s*Uhr\s*:\s*(?P<note>.*)$",
    re.IGNORECASE,
)
SINGLE_LINE_PATTERN = re.compile(
    r"(?P<start>[0-2]?\d(?::[0-5]\d)?)\s*Uhr\s*:\s*(?P<note>.*)$",
    re.IGNORECASE,
)
APPROXIMATE_PREFIXES = {
    "ab",
    "ab ca.",
    "bis",
    "bis ca.",
    "ca.",
    "gegen",
    "gegen ca.",
    "vermutlich ca.",
}


@dataclass(frozen=True)
class TimelineNoteRow:
    start_time: time | None = None
    end_time: time | None = None
    note: str = ""


@dataclass(frozen=True)
class StructuredNotes:
    timeline: tuple[TimelineNoteRow, ...] = ()
    peak_start_minute: int | None = None
    peak_duration_minutes: int = 0
    possible_factors: str = ""
    symptoms_and_actions: str = ""


def parse_structured_notes(
    notes: str,
    *,
    peak_start_minute: int | None = None,
    peak_end_minute: int | None = None,
) -> StructuredNotes:
    cleaned = notes.strip()
    if not cleaned:
        return StructuredNotes(
            peak_start_minute=peak_start_minute,
            peak_duration_minutes=_peak_duration(peak_start_minute, peak_end_minute),
        )

    matches = list(SECTION_PATTERN.finditer(cleaned))
    if not matches:
        return StructuredNotes(
            peak_start_minute=peak_start_minute,
            peak_duration_minutes=_peak_duration(peak_start_minute, peak_end_minute),
            symptoms_and_actions=cleaned,
        )

    section_values: dict[str, list[str]] = {"timeline": [], "factors": [], "symptoms": []}
    preamble = cleaned[: matches[0].start()].strip()
    if preamble:
        section_values["symptoms"].append(preamble)
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        value = cleaned[match.end() : end].strip()
        section_values[_section_key(match.group(1))].append(value)

    resolved_peak_start = peak_start_minute
    resolved_peak_duration = _peak_duration(peak_start_minute, peak_end_minute)
    timeline_rows: list[TimelineNoteRow] = []
    for value in section_values["timeline"]:
        for line in (item.strip() for item in value.splitlines()):
            if not line:
                continue
            peak_match = PEAK_PATTERN.match(line)
            if peak_match:
                if resolved_peak_start is None:
                    resolved_peak_start = _minute_value(peak_match.group("start"))
                    if peak_match.group("next_day"):
                        resolved_peak_start += 1440
                if resolved_peak_duration == 0:
                    if peak_match.group("duration"):
                        resolved_peak_duration = int(peak_match.group("duration"))
                    elif peak_match.group("end"):
                        end_minute = _minute_value(peak_match.group("end"))
                        start_clock = resolved_peak_start % 1440
                        resolved_peak_duration = (end_minute - start_clock) % 1440
                continue
            timeline_rows.append(_parse_timeline_line(line))

    return StructuredNotes(
        timeline=tuple(timeline_rows),
        peak_start_minute=resolved_peak_start,
        peak_duration_minutes=resolved_peak_duration,
        possible_factors=_join_sections(section_values["factors"]),
        symptoms_and_actions=_join_sections(section_values["symptoms"]),
    )


def format_structured_notes(value: StructuredNotes) -> str:
    timeline_lines = [_format_timeline_row(row) for row in value.timeline if _row_has_content(row)]
    if value.peak_start_minute is not None:
        timeline_lines.append(_format_peak(value.peak_start_minute, value.peak_duration_minutes))
    possible_factors = value.possible_factors.strip()
    symptoms_and_actions = value.symptoms_and_actions.strip()
    if not timeline_lines and not possible_factors and not symptoms_and_actions:
        return ""
    return (
        "Zeitlicher Ablauf:\n\n"
        + "\n".join(timeline_lines)
        + "\n\nMögliche Einflussfaktoren: "
        + possible_factors
        + "\n\nBeschwerden und Maßnahmen: "
        + symptoms_and_actions
    ).strip()


def format_timeline_notes(value: StructuredNotes) -> str:
    """Format only the content that belongs in the timeline database column."""
    timeline_lines = [_format_timeline_row(row) for row in value.timeline if _row_has_content(row)]
    if value.peak_start_minute is not None:
        timeline_lines.append(_format_peak(value.peak_start_minute, value.peak_duration_minutes))
    if not timeline_lines:
        return ""
    return "Zeitlicher Ablauf:\n\n" + "\n".join(timeline_lines)


def _section_key(heading: str) -> str:
    normalized = heading.casefold()
    if normalized == "zeitlicher ablauf":
        return "timeline"
    if "einflussfaktoren" in normalized or normalized.startswith("umstände"):
        return "factors"
    return "symptoms"


def _parse_timeline_line(line: str) -> TimelineNoteRow:
    range_match = RANGE_LINE_PATTERN.search(line)
    if range_match:
        return TimelineNoteRow(
            start_time=_clock_value(range_match.group("start")),
            end_time=_clock_value(range_match.group("end")),
            note=_preserved_note(line[: range_match.start()], range_match.group("note")),
        )
    single_match = SINGLE_LINE_PATTERN.search(line)
    if single_match:
        return TimelineNoteRow(
            start_time=_clock_value(single_match.group("start")),
            note=_preserved_note(line[: single_match.start()], single_match.group("note")),
        )
    return TimelineNoteRow(note=line)


def _preserved_note(prefix: str, note: str) -> str:
    cleaned_prefix = prefix.strip(" ,")
    cleaned_note = note.strip()
    if cleaned_prefix and cleaned_prefix.casefold() not in APPROXIMATE_PREFIXES:
        return f"{cleaned_prefix}: {cleaned_note}" if cleaned_note else cleaned_prefix
    return cleaned_note


def _format_timeline_row(row: TimelineNoteRow) -> str:
    note = row.note.strip()
    if row.start_time is not None and row.end_time is not None:
        return f"{_clock_text(row.start_time)}–{_clock_text(row.end_time)} Uhr: {note}".rstrip()
    if row.start_time is not None:
        return f"{_clock_text(row.start_time)} Uhr: {note}".rstrip()
    if row.end_time is not None:
        return f"Bis {_clock_text(row.end_time)} Uhr: {note}".rstrip()
    return note


def _format_peak(start_minute: int, duration_minutes: int) -> str:
    day = start_minute // 1440
    start = start_minute % 1440
    prefix = "Folgetag, " if day == 1 else "Zwei Tage später, " if day >= 2 else ""
    start_text = _minute_text(start)
    if duration_minutes <= 0:
        return f"Höhepunkt: {prefix}{start_text} Uhr."
    end_absolute = start_minute + duration_minutes
    end_text = _minute_text(end_absolute % 1440)
    if end_absolute // 1440 > day:
        interval = f"{prefix}{start_text} Uhr–Folgetag, {end_text} Uhr"
    else:
        interval = f"{prefix}{start_text}–{end_text} Uhr"
    return f"Höhepunkt: {interval} (Dauer: {duration_minutes} Minuten)."


def _clock_value(value: str) -> time:
    hour, separator, minute = value.partition(":")
    return time(int(hour) % 24, int(minute) if separator else 0)


def _minute_value(value: str) -> int:
    clock = _clock_value(value)
    return clock.hour * 60 + clock.minute


def _clock_text(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def _minute_text(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _peak_duration(start: int | None, end: int | None) -> int:
    if start is None or end is None or end < start:
        return 0
    return end - start


def _join_sections(values: list[str]) -> str:
    return "\n\n".join(value for value in values if value)


def _row_has_content(row: TimelineNoteRow) -> bool:
    return row.start_time is not None or row.end_time is not None or bool(row.note.strip())

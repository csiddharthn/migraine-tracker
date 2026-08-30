"""Separate legacy note sections into their dedicated columns.

Revision ID: 0010_separate_note_content
Revises: 0009_role_and_credentials
"""
from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op


revision = "0010_separate_note_content"
down_revision = "0009_role_and_credentials"
branch_labels = None
depends_on = None


SECTION_PATTERN = re.compile(
    r"^(Zeitlicher Ablauf|Mögliche Einflussfaktoren|Umstände vor Beginn der Kopfschmerzen|"
    r"Beschwerden und Maßnahmen|Beschreibung der Kopfschmerzen|Einnahme von Medikamenten)\s*:\s*",
    re.IGNORECASE | re.MULTILINE,
)

LEGACY_NOTE_CLASSIFICATIONS = {
    (
        "Rechtsseitig. Vorherige Nacht bei kühlen Temperaturen (ca. 17-18 °C) mit offenem "
        "Fenster geschlafen; das löst bei mir Kopfschmerzen aus. Keine Begleitsymptome."
    ): (
        "",
        (
            "Vorherige Nacht bei kühlen Temperaturen (ca. 17-18 °C) mit offenem Fenster "
            "geschlafen; das löst bei mir Kopfschmerzen aus."
        ),
        "Rechtsseitig. Keine Begleitsymptome.",
        "",
    ),
    (
        "Rechtsseitig. Vorherige Nacht bei kühlen Temperaturen mit offenem Fenster geschlafen. "
        "Keine Begleitsymptome; keine Medikation."
    ): (
        "",
        "Vorherige Nacht bei kühlen Temperaturen mit offenem Fenster geschlafen.",
        "Rechtsseitig. Keine Begleitsymptome; keine Medikation.",
        "",
    ),
    (
        "Beidseitig. Möglicherweise an dem Tag etwas zu wenig Wasser getrunken. "
        "Keine Begleitsymptome; keine Medikation."
    ): (
        "",
        "Möglicherweise an dem Tag etwas zu wenig Wasser getrunken.",
        "Beidseitig. Keine Begleitsymptome; keine Medikation.",
        "",
    ),
    (
        "Einseitig. Eher wärmerer Tag; tagsüber Außentemperatur >38 °C. Nachts mit offenem "
        "Fenster in etwas kühlerem Zimmer geschlafen statt im Wohnzimmer mit geschlossenen "
        "Fenstern. Keine Begleitsymptome; keine Medikation."
    ): (
        "",
        (
            "Eher wärmerer Tag; tagsüber Außentemperatur >38 °C. Nachts mit offenem Fenster "
            "in etwas kühlerem Zimmer geschlafen statt im Wohnzimmer mit geschlossenen Fenstern."
        ),
        "Einseitig. Keine Begleitsymptome; keine Medikation.",
        "",
    ),
}


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, timeline_notes, possible_factors, symptoms_and_actions, other_notes "
            "FROM migraine_entries"
        )
    ).mappings()

    for row in rows:
        split = _split_entry_note(row["timeline_notes"] or "")
        if split is None:
            continue
        timeline, factors, symptoms, other = split
        connection.execute(
            sa.text(
                "UPDATE migraine_entries SET "
                "timeline_notes = :timeline_notes, "
                "possible_factors = :possible_factors, "
                "symptoms_and_actions = :symptoms_and_actions, "
                "other_notes = :other_notes "
                "WHERE id = :entry_id"
            ),
            {
                "entry_id": row["id"],
                "timeline_notes": timeline,
                "possible_factors": _merge_text(row["possible_factors"], factors),
                "symptoms_and_actions": _merge_text(row["symptoms_and_actions"], symptoms),
                "other_notes": _merge_text(row["other_notes"], other),
            },
        )


def downgrade() -> None:
    # This cleanup is intentionally one-way. Recombining the columns would
    # destroy information about which content was already separated beforehand.
    pass


def _split_entry_note(notes: str) -> tuple[str, str, str, str] | None:
    cleaned = notes.strip()
    if not cleaned:
        return None
    if cleaned in LEGACY_NOTE_CLASSIFICATIONS:
        return LEGACY_NOTE_CLASSIFICATIONS[cleaned]

    matches = list(SECTION_PATTERN.finditer(cleaned))
    if not matches:
        return "", "", "", cleaned

    values: dict[str, list[str]] = {
        "timeline": [],
        "factors": [],
        "symptoms": [],
        "other": [],
    }
    preamble = cleaned[: matches[0].start()].strip()
    if preamble:
        values["other"].append(preamble)

    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(cleaned)
        value = cleaned[match.end() : end].strip()
        if value:
            values[_section_key(match.group(1))].append(value)

    timeline_content = _join_sections(values["timeline"], separator="\n")
    timeline = f"Zeitlicher Ablauf:\n\n{timeline_content}" if timeline_content else ""
    return (
        timeline,
        _join_sections(values["factors"]),
        _join_sections(values["symptoms"]),
        _join_sections(values["other"]),
    )


def _section_key(heading: str) -> str:
    normalized = heading.casefold()
    if normalized == "zeitlicher ablauf":
        return "timeline"
    if "einflussfaktoren" in normalized or normalized.startswith("umstände"):
        return "factors"
    return "symptoms"


def _join_sections(values: list[str], *, separator: str = "\n\n") -> str:
    return separator.join(value.strip() for value in values if value.strip())


def _merge_text(existing: str | None, extracted: str | None) -> str:
    values: list[str] = []
    for value in (existing, extracted):
        cleaned = (value or "").strip()
        if cleaned and cleaned not in values:
            values.append(cleaned)
    return "\n\n".join(values)

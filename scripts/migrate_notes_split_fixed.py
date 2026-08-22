#!/usr/bin/env python3
"""Migrate existing migraine_entries.notes into 4 split columns."""
from __future__ import annotations

import sys
sys.path.insert(0, ".")

from backend.note_interpretation.structured_notes import parse_structured_notes, format_structured_notes
from backend.config import get_settings
from backend.database.session import create_session_factory
from sqlalchemy import text


def migrate():
    settings = get_settings()
    factory = create_session_factory(settings.database_url)
    with factory() as session:
        result = session.execute(text("SELECT id, notes FROM migraine_entries"))
        rows = result.fetchall()
        for row in rows:
            entry_id, notes_text = row
            parsed = parse_structured_notes(notes_text or "")
            timeline_lines = []
            for row in parsed.timeline:
                note = row.note.strip()
                if row.start_time is not None and row.end_time is not None:
                    timeline_lines.append(f"{row.start_time.strftime('%H:%M')}–{row.end_time.strftime('%H:%M')} Uhr: {note}")
                elif row.start_time is not None:
                    timeline_lines.append(f"{row.start_time.strftime('%H:%M')} Uhr: {note}")
                else:
                    timeline_lines.append(note)
            if parsed.peak_start_minute is not None:
                timeline_lines.append(f"Höhepunkt: {parsed.peak_start_minute // 60:02d}:{parsed.peak_start_minute % 60:02d} Uhr (Dauer: {parsed.peak_duration_minutes} Minuten)")
            timeline_notes = "\n".join(timeline_lines) if timeline_lines else (notes_text or "")
            possible_factors = parsed.possible_factors
            symptoms_and_actions = parsed.symptoms_and_actions
            other_notes = ""
            session.execute(
                text("UPDATE migraine_entries SET timeline_notes = :t, possible_factors = :p, symptoms_and_actions = :s, other_notes = :o WHERE id = :id"),
                {
                    "t": timeline_notes,
                    "p": possible_factors,
                    "s": symptoms_and_actions,
                    "o": other_notes,
                    "id": entry_id,
                },
            )
        session.commit()
        print(f"Migrated {len(rows)} entries.")


if __name__ == "__main__":
    migrate()

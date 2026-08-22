from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from backend.analytics.calculations import AnalyticsDataset, monthly_summaries, summary_stats
from backend.config import get_settings
from backend.database.session import create_session_factory, session_scope
from backend.migration.excel_importer import ExcelImporter
from backend.models import DailyRecord, MigraineEntry, MigrationSourceRow
from backend.repositories import UserRepository
from backend.services.user_service import normalize_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Validiert PostgreSQL-Zahlen gegen die Excel-Quelle.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--user", required=True, help="Person, deren importierte Daten geprüft werden")
    args = parser.parse_args()
    rows = ExcelImporter._read_rows(args.workbook.resolve())
    cutoff = date.today()
    in_scope = [(row, values) for row, values in rows if isinstance(values.get("Datum"), date) and values["Datum"] <= cutoff]
    expected_rows = [(row, values) for row, values in in_scope if ExcelImporter._has_migraine_data(values)]
    expected_entries = len(expected_rows)

    factory = create_session_factory(get_settings().database_url)
    with session_scope(factory) as session:
        user = UserRepository(session).get_by_name_key(normalize_name(args.user))
        if user is None:
            raise SystemExit(f"Die Person '{args.user}' wurde nicht gefunden.")
        entries = list(session.scalars(select(MigraineEntry).where(MigraineEntry.user_id == user.id).order_by(MigraineEntry.entry_date)))
        daily = list(session.scalars(select(DailyRecord).where(DailyRecord.user_id == user.id).order_by(DailyRecord.record_date)))
        source_rows = session.scalar(
            select(func.count()).select_from(MigrationSourceRow).where(MigrationSourceRow.user_id == user.id)
        ) or 0
        data = AnalyticsDataset.build(entries, daily)
        stats = summary_stats(data)
        months = monthly_summaries(data)

    failures = []
    if len(entries) != expected_entries:
        failures.append(f"Einträge: PostgreSQL={len(entries)}, Excel={expected_entries}")
    if len(daily) != len(in_scope):
        failures.append(f"Beobachtungstage: PostgreSQL={len(daily)}, Excel={len(in_scope)}")
    if source_rows < len(in_scope):
        failures.append(f"Quellzeilen: PostgreSQL={source_rows}, erwartet mindestens {len(in_scope)}")
    if any(entry.notes != str(next(values["Notizen"] or "" for _, values in in_scope if values["Datum"] == entry.entry_date)) for entry in entries):
        failures.append("Mindestens eine Originalnotiz weicht von Excel ab.")
    expected_duration = sum(Decimal(str(values.get("Dauer (h)") or 0)) for _, values in expected_rows)
    actual_duration = sum(entry.duration_hours for entry in entries)
    if actual_duration != expected_duration:
        failures.append(f"Gesamtdauer: PostgreSQL={actual_duration}, Excel={expected_duration}")

    by_date = {entry.entry_date: entry for entry in entries}
    representative = []
    if expected_rows:
        indexes = sorted({0, len(expected_rows) // 2, len(expected_rows) - 1})
        for index in indexes:
            excel_row, values = expected_rows[index]
            record_date = values["Datum"]
            entry = by_date.get(record_date)
            if entry is None:
                failures.append(f"Repräsentative Zeile {excel_row}: Eintrag fehlt.")
                continue
            expected_strength = int(values["Stärke (0-10)"])
            expected_hours = Decimal(str(values["Dauer (h)"])).quantize(Decimal("0.01"))
            if entry.strength != expected_strength or entry.duration_hours != expected_hours:
                failures.append(
                    f"Repräsentative Zeile {excel_row}: Stärke/Dauer weichen ab."
                )
            representative.append(f"Zeile {excel_row} ({record_date:%d.%m.%Y})")

    print(f"Kopfschmerztage: {stats['headache_days']}")
    print(f"Person: {user.display_name}")
    print(f"Beobachtungstage: {stats['period_days']}")
    print(f"Gesamtdauer: {stats['total_duration']:.1f} Stunden")
    print("Monate: " + ", ".join(f"{item['label']}={item['headache_days']}" for item in months))
    print("Repräsentative Zeilen geprüft: " + ", ".join(representative))
    if failures:
        raise SystemExit("Migration nicht vollständig abgeglichen:\n- " + "\n- ".join(failures))
    print("Migration erfolgreich abgeglichen.")


if __name__ == "__main__":
    main()

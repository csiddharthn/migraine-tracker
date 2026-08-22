from __future__ import annotations

import argparse
from pathlib import Path

from backend.config import get_settings
from backend.database.session import create_session_factory, session_scope
from backend.migration.excel_importer import ExcelImporter, load_annotations
from backend.services.user_service import UserService


def main() -> None:
    parser = argparse.ArgumentParser(description="Einmaliger, idempotenter Import des Excel-Kopfschmerzkalenders.")
    parser.add_argument("workbook", type=Path, help="Pfad zur Excel-Arbeitsmappe")
    parser.add_argument("--user", required=True, help="Person, der die importierten Daten zugeordnet werden")
    parser.add_argument("--annotations", type=Path, help="Optionale semantisch geprüfte Alt-Annotationen")
    parser.add_argument("--report", type=Path, default=Path("artifacts/migration_report.json"), help="JSON-Migrationsbericht")
    args = parser.parse_args()

    factory = create_session_factory(get_settings().database_url)
    with session_scope(factory) as session:
        dated_rows = [
            values["Datum"]
            for _, values in ExcelImporter._read_rows(args.workbook.resolve())
            if values.get("Datum") is not None
        ]
        tracking_start = min(dated_rows) if dated_rows else None
        user = UserService(session).get_or_create(args.user, tracking_start)
        report = ExcelImporter(session, user.id, annotations=load_annotations(args.annotations)).import_workbook(args.workbook)
        report.save(args.report)
    print(
        f"Import abgeschlossen: {report.imported} importiert, {report.updated} aktualisiert, "
        f"{report.skipped} übersprungen, {report.duplicates} Duplikate, {report.rejected} abgelehnt."
    )
    print(f"Bericht: {args.report.resolve()}")
    print(f"Person: {user.display_name}")


if __name__ == "__main__":
    main()

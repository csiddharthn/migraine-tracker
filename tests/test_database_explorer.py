from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from backend.services.database_explorer import DatabaseExplorerService
from backend.services.entry_service import EntryService
from backend.services.schemas import EntryInput, MedicationInput
from backend.services.user_service import UserService


def test_database_explorer_scopes_personal_tables(session, user) -> None:
    second_user = UserService(session).create("Zweite Person", date(2026, 7, 1))
    EntryService(session, user.id).create(
        EntryInput(
            entry_date=date(2026, 7, 2),
            trigger_codes=["8"],
            strength=4,
            duration_hours=Decimal("3.5"),
            medications=[MedicationInput(name="Paracetamol", taken_at=time(9, 15))],
            notes="Beginn 08:00 Uhr, Ende 11:30 Uhr.",
        )
    )
    EntryService(session, second_user.id).create(
        EntryInput(
            entry_date=date(2026, 7, 2),
            trigger_codes=["1"],
            strength=8,
            duration_hours=Decimal("6.0"),
        )
    )
    session.commit()

    explorer = DatabaseExplorerService(session, user.id)
    counts = explorer.counts()
    entry_table = explorer.load("entries")
    medication_table = explorer.load("medication_intakes")
    user_table = explorer.load("users")

    assert counts == {"users": 2, "entries": 1, "daily_records": 1, "interpretations": 1}
    assert len(entry_table.rows) == 1
    assert entry_table.rows[0]["Person"] == "Testperson"
    assert entry_table.rows[0]["Stärke"] == 4
    assert entry_table.rows[0]["Medikamente"] == "Paracetamol"
    assert medication_table.rows[0]["Einnahmezeit"] == "09:15"
    assert medication_table.rows[0]["Medikament"] == "Paracetamol"
    assert entry_table.rows[0]["Auslöser"] == "Unsicher"
    assert {row["Name"] for row in user_table.rows} == {"Testperson", "Zweite Person"}
    assert "Person-ID" in entry_table.technical_columns

    for table_key in ("daily_records", "interpretations", "trigger_assignments", "audit_logs"):
        table = explorer.load(table_key)
        assert table.rows
        assert {row["Person"] for row in table.rows} == {"Testperson"}

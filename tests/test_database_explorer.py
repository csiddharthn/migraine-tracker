from __future__ import annotations

"""Purpose: Database explorer isolation tests.

Usage: Tests multi-user data isolation.

Functions available:
- test_database_explorer_scopes_personal_tables

Classes available:
- None

Call hierarchy:
- test_database_explorer.py -> backend.services.database_explorer
"""

from datetime import date, time
from decimal import Decimal

from backend.services.database_explorer import DatabaseExplorerService
from backend.services.entry_service import EntryService
from backend.services.schemas import EntryInput, MedicationInput
from backend.services.user_service import UserService

SECOND_USER_NAME = "Zweite Person"
SECOND_USER_BIRTH = date(2026, 7, 1)
ENTRY_DATE = date(2026, 7, 2)
TRIGGER_CODE_PRIMARY = "8"
TRIGGER_CODE_SECONDARY = "1"
STRENGTH_PRIMARY = 4
STRENGTH_SECONDARY = 8
DURATION_PRIMARY = Decimal("3.5")
DURATION_SECONDARY = Decimal("6.0")
MEDICATION_NAME = "Paracetamol"
MEDICATION_TIME = time(9, 15)
NOTES_PRIMARY = "Beginn 08:00 Uhr, Ende 11:30 Uhr."


def test_database_explorer_scopes_personal_tables(session, user) -> None:
    second_birth = SECOND_USER_BIRTH
    second_user = UserService(session).create(SECOND_USER_NAME, second_birth)
    entry_date = ENTRY_DATE
    user_strength = STRENGTH_PRIMARY
    user_duration = DURATION_PRIMARY
    second_strength = STRENGTH_SECONDARY
    second_duration = DURATION_SECONDARY
    EntryService(session, user.id).create(
        EntryInput(
            entry_date=entry_date,
            trigger_codes=[TRIGGER_CODE_PRIMARY],
            strength=user_strength,
            duration_hours=user_duration,
            medications=[MedicationInput(name=MEDICATION_NAME, taken_at=MEDICATION_TIME)],
            timeline_notes=NOTES_PRIMARY,
            possible_factors="",
            symptoms_and_actions="",
            other_notes="",
        )
    )
    EntryService(session, second_user.id).create(
        EntryInput(
            entry_date=entry_date,
            trigger_codes=[TRIGGER_CODE_SECONDARY],
            strength=second_strength,
            duration_hours=second_duration,
        )
    )
    session.commit()

    explorer = DatabaseExplorerService(session, user.id)
    counts = explorer.counts()
    entry_table = explorer.load("entries")
    medication_table = explorer.load("medication_intakes")
    user_table = explorer.load("users")

    assert counts == {"users": 2, "entries": 1, "daily_records": 1, "interpretations": 1}
    assert explorer.latest_entry_date() == entry_date
    assert len(entry_table.rows) == 1
    assert entry_table.rows[0]["Person"] == "Testperson"
    assert entry_table.rows[0]["Stärke"] == user_strength
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

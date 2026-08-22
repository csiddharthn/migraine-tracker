from __future__ import annotations

"""Purpose: PostgreSQL integration tests.

Usage: Tests isolated schema creation and updates.

Functions available:
- test_postgres_create_and_update_in_isolated_schema

Classes available:
- None

Call hierarchy:
- test_postgres_integration.py -> backend.services, backend.database
"""

import uuid
from datetime import date, time
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from backend.config import get_settings
from backend.database.base import Base
from backend.database.seed import seed_reference_data
from backend.services.entry_service import EntryService
from backend.services.schemas import EntryInput, EntryPatch, MedicationInput
from backend.services.user_service import UserService

TEST_USER_NAME = "PostgreSQL-Testperson"
TEST_USER_BIRTH = date(2026, 8, 1)
TEST_ENTRY_DATE = date(2026, 8, 10)
TEST_TRIGGER_CODE = "8"
TEST_STRENGTH = 5
TEST_DURATION = Decimal("7.0")
TEST_MEDICATIONS = [
    MedicationInput(name="Eletriptan", taken_at=time(16, 0)),
    MedicationInput(name="Amitriptylin neuraxpharm", taken_at=time(22, 0)),
]
TEST_NOTES = "Beginn 15:00 Uhr, rechts; Ende 22:00 Uhr."
UPDATED_STRENGTH = 6
EXPECTED_DURATION = Decimal("7.00")
EXPECTED_MEDICATION_NAMES = ["Eletriptan", "Amitriptylin neuraxpharm"]
EXPECTED_ONSET_MINUTE = 15 * 60
EXPECTED_END_MINUTE = 22 * 60

@pytest.mark.postgres
def test_postgres_create_and_update_in_isolated_schema() -> None:
    database_url = get_settings().test_database_url
    if not database_url:
        pytest.skip("MIGRAINE_TEST_DATABASE_URL ist nicht gesetzt.")
    if make_url(database_url).get_backend_name() != "postgresql":
        pytest.skip("Der Integrationstest benötigt PostgreSQL.")

    schema = f"test_migraine_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    test_engine = create_engine(
        database_url,
        connect_args={"options": f"-csearch_path={schema}"},
        pool_pre_ping=True,
    )
    try:
        Base.metadata.create_all(test_engine)
        factory = sessionmaker(bind=test_engine, expire_on_commit=False)
        with factory.begin() as session:
            seed_reference_data(session)
            user = UserService(session).create(TEST_USER_NAME, TEST_USER_BIRTH)
            service = EntryService(session, user.id)
            entry = service.create(
                EntryInput(
                    entry_date=TEST_ENTRY_DATE,
                    trigger_codes=[TEST_TRIGGER_CODE],
                    strength=TEST_STRENGTH,
                    duration_hours=TEST_DURATION,
                    medications=TEST_MEDICATIONS,
                    timeline_notes=TEST_NOTES,
                    possible_factors="",
                    symptoms_and_actions="",
                    other_notes="",
                )
            )
            entry_id = entry.id

        with factory.begin() as session:
            updated = EntryService(session, user.id).update(entry_id, EntryPatch(strength=UPDATED_STRENGTH))
            assert updated.strength == UPDATED_STRENGTH
            assert updated.duration_hours == EXPECTED_DURATION
            assert [item.name for item in updated.medications] == EXPECTED_MEDICATION_NAMES
            assert updated.interpretation.onset_minute == EXPECTED_ONSET_MINUTE
            assert updated.interpretation.end_minute == EXPECTED_END_MINUTE
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()

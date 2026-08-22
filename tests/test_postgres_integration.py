from __future__ import annotations

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
            user = UserService(session).create("PostgreSQL-Testperson", date(2026, 8, 1))
            service = EntryService(session, user.id)
            entry = service.create(
                EntryInput(
                    entry_date=date(2026, 8, 10),
                    trigger_codes=["8"],
                    strength=5,
                    duration_hours=Decimal("7.0"),
                    medications=[
                        MedicationInput(name="Eletriptan", taken_at=time(16, 0)),
                        MedicationInput(name="Amitriptylin neuraxpharm", taken_at=time(22, 0)),
                    ],
                    notes="Beginn 15:00 Uhr, rechts; Ende 22:00 Uhr.",
                )
            )
            entry_id = entry.id

        with factory.begin() as session:
            updated = EntryService(session, user.id).update(entry_id, EntryPatch(strength=6))
            assert updated.strength == 6
            assert updated.duration_hours == Decimal("7.00")
            assert [item.name for item in updated.medications] == ["Eletriptan", "Amitriptylin neuraxpharm"]
            assert updated.interpretation.onset_minute == 15 * 60
            assert updated.interpretation.end_minute == 22 * 60
    finally:
        test_engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()

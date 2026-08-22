from __future__ import annotations

"""Purpose: Entry repository for migraine entry CRUD operations.

Usage: Manages MigraineEntry, triggers, medications, and interpretations.

Functions available:
- EntryRepository.get, list, create, update, delete

Classes available:
- EntryRepository

Call hierarchy:
- entries.py -> backend.models
"""

import uuid
from datetime import date

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from backend.models import DailyRecord, EntryTrigger, MedicationIntake, MigraineEntry, TriggerDefinition


class EntryRepository:
    def __init__(self, session: Session, user_id: uuid.UUID) -> None:
        self.session = session
        self.user_id = user_id

    @staticmethod
    def _entry_options() -> tuple:
        return (
            selectinload(MigraineEntry.triggers).selectinload(EntryTrigger.definition),
            selectinload(MigraineEntry.interpretation),
            selectinload(MigraineEntry.medications),
        )

    def get(self, entry_id: uuid.UUID) -> MigraineEntry | None:
        statement = select(MigraineEntry).options(*self._entry_options()).where(
            MigraineEntry.id == entry_id,
            MigraineEntry.user_id == self.user_id,
        )
        return self.session.scalar(statement)

    def get_by_date(self, entry_date: date) -> MigraineEntry | None:
        statement = select(MigraineEntry).options(*self._entry_options()).where(
            MigraineEntry.user_id == self.user_id,
            MigraineEntry.entry_date == entry_date,
        )
        return self.session.scalar(statement)

    def list_entries(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        min_strength: int | None = None,
        max_strength: int | None = None,
        trigger_codes: list[str] | None = None,
        medication_query: str | None = None,
    ) -> list[MigraineEntry]:
        statement: Select = select(MigraineEntry).options(*self._entry_options()).where(MigraineEntry.user_id == self.user_id)
        if start_date is not None:
            statement = statement.where(MigraineEntry.entry_date >= start_date)
        if end_date is not None:
            statement = statement.where(MigraineEntry.entry_date <= end_date)
        if min_strength is not None:
            statement = statement.where(MigraineEntry.strength >= min_strength)
        if max_strength is not None:
            statement = statement.where(MigraineEntry.strength <= max_strength)
        if trigger_codes:
            statement = statement.join(MigraineEntry.triggers).where(EntryTrigger.trigger_code.in_(trigger_codes)).distinct()
        if medication_query:
            statement = statement.join(MigraineEntry.medications).where(MedicationIntake.name.ilike(f"%{medication_query}%")).distinct()
        statement = statement.order_by(MigraineEntry.entry_date.desc())
        return list(self.session.scalars(statement).unique())

    def list_medication_names(self) -> list[str]:
        statement = (
            select(MedicationIntake.name)
            .join(MigraineEntry, MedicationIntake.entry_id == MigraineEntry.id)
            .where(MigraineEntry.user_id == self.user_id)
            .order_by(MigraineEntry.entry_date, MedicationIntake.sequence)
        )
        unique: dict[str, str] = {}
        for value in self.session.scalars(statement):
            cleaned = value.strip()
            if cleaned:
                unique.setdefault(cleaned.casefold(), cleaned)
        return sorted(unique.values(), key=str.casefold)

    def list_daily_records(self, start_date: date | None = None, end_date: date | None = None) -> list[DailyRecord]:
        statement = select(DailyRecord).where(DailyRecord.user_id == self.user_id)
        if start_date is not None:
            statement = statement.where(DailyRecord.record_date >= start_date)
        if end_date is not None:
            statement = statement.where(DailyRecord.record_date <= end_date)
        return list(self.session.scalars(statement.order_by(DailyRecord.record_date)))

    def get_daily_record(self, record_date: date) -> DailyRecord | None:
        return self.session.scalar(
            select(DailyRecord).where(
                DailyRecord.user_id == self.user_id,
                DailyRecord.record_date == record_date,
            )
        )

    def list_trigger_definitions(self, *, active_only: bool = True) -> list[TriggerDefinition]:
        statement = select(TriggerDefinition)
        if active_only:
            statement = statement.where(TriggerDefinition.active.is_(True))
        return list(self.session.scalars(statement.order_by(TriggerDefinition.sort_order)))

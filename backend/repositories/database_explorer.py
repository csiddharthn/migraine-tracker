from __future__ import annotations

"""Purpose: Database explorer repository for multi-user data isolation.

Usage: Provides counts and exploration methods per user.

Functions available:
- DatabaseExplorerRepository.counts, explore, etc.

Classes available:
- DatabaseExplorerRepository

Call hierarchy:
- database_explorer.py -> backend.models
"""

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.models import (
    DailyRecord,
    EntryAuditLog,
    EntryTrigger,
    MedicationIntake,
    MigraineEntry,
    NoteInterpretation,
    TriggerDefinition,
    UserProfile,
)


class DatabaseExplorerRepository:
    def __init__(self, session: Session, user_id: uuid.UUID) -> None:
        self.session = session
        self.user_id = user_id

    def counts(self) -> dict[str, int]:
        return {
            "users": self._count(UserProfile),
            "entries": self._count(MigraineEntry, MigraineEntry.user_id == self.user_id),
            "daily_records": self._count(DailyRecord, DailyRecord.user_id == self.user_id),
            "interpretations": int(
                self.session.scalar(
                    select(func.count())
                    .select_from(NoteInterpretation)
                    .join(MigraineEntry, NoteInterpretation.entry_id == MigraineEntry.id)
                    .where(MigraineEntry.user_id == self.user_id)
                )
                or 0
            ),
        }

    def latest_entry_date(self) -> date | None:
        return self.session.scalar(
            select(func.max(MigraineEntry.entry_date)).where(MigraineEntry.user_id == self.user_id)
        )

    def users(self) -> list[UserProfile]:
        return list(self.session.scalars(select(UserProfile).order_by(UserProfile.display_name)))

    def selected_user(self) -> UserProfile | None:
        return self.session.get(UserProfile, self.user_id)

    def entries(self) -> list[MigraineEntry]:
        statement = (
            select(MigraineEntry)
            .options(
                selectinload(MigraineEntry.triggers).selectinload(EntryTrigger.definition),
                selectinload(MigraineEntry.medications),
            )
            .where(MigraineEntry.user_id == self.user_id)
            .order_by(MigraineEntry.entry_date.desc())
        )
        return list(self.session.scalars(statement).unique())

    def daily_records(self) -> list[DailyRecord]:
        return list(
            self.session.scalars(
                select(DailyRecord)
                .where(DailyRecord.user_id == self.user_id)
                .order_by(DailyRecord.record_date.desc())
            )
        )

    def interpretations(self) -> list[tuple[NoteInterpretation, object]]:
        statement = (
            select(NoteInterpretation, MigraineEntry.entry_date)
            .join(MigraineEntry, NoteInterpretation.entry_id == MigraineEntry.id)
            .where(MigraineEntry.user_id == self.user_id)
            .order_by(MigraineEntry.entry_date.desc())
        )
        return list(self.session.execute(statement).tuples())

    def trigger_assignments(self) -> list[tuple[EntryTrigger, object]]:
        statement = (
            select(EntryTrigger, MigraineEntry.entry_date)
            .join(MigraineEntry, EntryTrigger.entry_id == MigraineEntry.id)
            .where(MigraineEntry.user_id == self.user_id)
            .order_by(MigraineEntry.entry_date.desc(), EntryTrigger.trigger_code)
        )
        return list(self.session.execute(statement).tuples())

    def medication_intakes(self) -> list[tuple[MedicationIntake, object]]:
        statement = (
            select(MedicationIntake, MigraineEntry.entry_date)
            .join(MigraineEntry, MedicationIntake.entry_id == MigraineEntry.id)
            .where(MigraineEntry.user_id == self.user_id)
            .order_by(MigraineEntry.entry_date.desc(), MedicationIntake.sequence)
        )
        return list(self.session.execute(statement).tuples())

    def trigger_definitions(self) -> list[TriggerDefinition]:
        return list(self.session.scalars(select(TriggerDefinition).order_by(TriggerDefinition.sort_order)))

    def audit_logs(self) -> list[tuple[EntryAuditLog, object]]:
        statement = (
            select(EntryAuditLog, MigraineEntry.entry_date)
            .join(MigraineEntry, EntryAuditLog.entry_id == MigraineEntry.id)
            .where(MigraineEntry.user_id == self.user_id)
            .order_by(EntryAuditLog.changed_at.desc())
        )
        return list(self.session.execute(statement).tuples())

    def _count(self, model: type, *conditions: object) -> int:
        statement = select(func.count()).select_from(model)
        if conditions:
            statement = statement.where(*conditions)
        return int(self.session.scalar(statement) or 0)

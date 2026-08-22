from __future__ import annotations

"""Purpose: Entry service for migraine entry management.

Usage: Creates, updates, deletes, and interprets migraine entries.

Functions available:
- EntryService.create, update, delete, interpret

Classes available:
- EntryService, DuplicateEntryError, EntryNotFoundError

Call hierarchy:
- entry_service.py -> backend.repositories, backend.note_interpretation
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.models import DailyRecord, EntryAuditLog, EntryTrigger, MedicationIntake, MigraineEntry, NoteInterpretation
from backend.note_interpretation import NoteInterpreter
from backend.repositories import EntryRepository
from backend.services.schemas import EntryInput, EntryPatch


class DuplicateEntryError(ValueError):
    pass


class EntryNotFoundError(ValueError):
    pass


class EntryService:
    ENTRY_FIELDS = (
        "entry_date",
        "strength",
        "duration_hours",
        "pain_type",
        "entered_laterality",
        "aura_codes",
        "vomiting",
        "nausea",
        "phonophobia",
        "photophobia",
        "osmophobia",
        "other_symptom_codes",
        "timeline_notes",
        "possible_factors",
        "symptoms_and_actions",
        "other_notes",
        "source_narrative",
        "ai_provider",
        "ai_model",
        "ai_prompt_version",
        "ai_extraction",
    )
    DAILY_FIELDS = ("aimovig_injection", "momeallerg_nasal_spray", "amitriptyline_neuraxpharm")

    def __init__(self, session: Session, user_id: uuid.UUID, interpreter: NoteInterpreter | None = None) -> None:
        self.session = session
        self.user_id = user_id
        self.repository = EntryRepository(session, user_id)
        self.interpreter = interpreter or NoteInterpreter()

    def create(
        self,
        payload: EntryInput,
        *,
        origin: str = "streamlit",
        reviewed_annotation: dict[str, Any] | None = None,
    ) -> MigraineEntry:
        if self.repository.get_by_date(payload.entry_date) is not None:
            raise DuplicateEntryError(f"Für den {payload.entry_date:%d.%m.%Y} existiert bereits ein Eintrag.")
        self._validate_triggers(payload.trigger_codes)

        entry_values = payload.model_dump(include=set(self.ENTRY_FIELDS))
        entry = MigraineEntry(user_id=self.user_id, **entry_values, source_system=origin)
        if payload.ai_provider:
            entry.ai_reviewed_at = datetime.now(timezone.utc)
        entry.triggers = [EntryTrigger(trigger_code=code) for code in payload.trigger_codes]
        entry.medications = self._medication_entities(payload.medications)
        self.session.add(entry)
        self.session.flush()
        self._set_interpretation(entry, reviewed_annotation=reviewed_annotation or payload.note_annotation)
        self._upsert_daily_record(payload.entry_date, payload.model_dump(include=set(self.DAILY_FIELDS)), origin=origin)
        self._audit(entry, "created", origin, None, self._snapshot(entry))
        self.session.flush()
        return entry

    def update(
        self,
        entry_id: uuid.UUID,
        patch: EntryPatch,
        *,
        origin: str = "streamlit",
        reviewed_annotation: dict[str, Any] | None = None,
    ) -> MigraineEntry:
        entry = self.repository.get(entry_id)
        if entry is None:
            raise EntryNotFoundError("Der ausgewählte Eintrag wurde nicht gefunden.")
        before = self._snapshot(entry)
        old_date = entry.entry_date
        changes = patch.model_dump(exclude_unset=True)

        new_date = changes.get("entry_date")
        if new_date is not None and new_date != entry.entry_date:
            existing = self.repository.get_by_date(new_date)
            if existing is not None and existing.id != entry.id:
                raise DuplicateEntryError(f"Für den {new_date:%d.%m.%Y} existiert bereits ein Eintrag.")

        trigger_codes = changes.pop("trigger_codes", None)
        if trigger_codes is not None:
            if not trigger_codes:
                raise ValueError("Mindestens ein Auslöser ist erforderlich.")
            existing_codes = {trigger.trigger_code for trigger in entry.triggers}
            self._validate_triggers(trigger_codes, allowed_inactive_codes=existing_codes)
            entry.triggers = [EntryTrigger(trigger_code=code) for code in trigger_codes]

        medications = changes.pop("medications", None)
        if medications is not None:
            entry.medications.clear()
            self.session.flush()
            entry.medications.extend(self._medication_entities(medications))

        daily_changes = {field: changes.pop(field) for field in self.DAILY_FIELDS if field in changes}
        nullable_fields = {"pain_type", "entered_laterality"}
        for field, value in changes.items():
            if field in self.ENTRY_FIELDS and (value is not None or field in nullable_fields):
                setattr(entry, field, value)

        notes_changed = any(
            field in changes for field in ("timeline_notes", "possible_factors", "symptoms_and_actions", "other_notes", "entered_laterality")
        )
        if notes_changed:
            self._set_interpretation(
                entry,
                reviewed_annotation=reviewed_annotation,
                preserve_review=reviewed_annotation is None,
            )
        if entry.entry_date != old_date:
            old_daily = self.repository.get_daily_record(old_date)
            if old_daily is not None:
                for field in self.DAILY_FIELDS:
                    daily_changes.setdefault(field, getattr(old_daily, field))
            self._upsert_daily_record(entry.entry_date, daily_changes, origin=origin)
            if old_daily is not None and old_daily.source_system == "streamlit":
                self.session.delete(old_daily)
        elif daily_changes:
            self._upsert_daily_record(entry.entry_date, daily_changes, origin=origin)

        self.session.flush()
        self._audit(entry, "updated", origin, before, self._snapshot(entry))
        return entry

    def review_interpretation(self, entry_id: uuid.UUID, changes: dict[str, Any], *, origin: str = "streamlit") -> NoteInterpretation:
        entry = self.repository.get(entry_id)
        if entry is None or entry.interpretation is None:
            raise EntryNotFoundError("Für den Eintrag ist keine Interpretation vorhanden.")
        allowed = {
            "onset_minute",
            "peak_start_minute",
            "peak_end_minute",
            "end_minute",
            "end_status",
            "laterality",
            "side_detail",
            "contexts",
            "symptoms",
            "interventions",
        }
        for field, value in changes.items():
            if field in allowed:
                setattr(entry.interpretation, field, value)
        entry.interpretation.is_reviewed = True
        entry.interpretation.extraction_method = "manuell geprüft"
        entry.interpretation.reviewed_at = datetime.now(timezone.utc)
        self._audit(entry, "interpretation_reviewed", origin, None, self._snapshot(entry))
        self.session.flush()
        return entry.interpretation

    def _set_interpretation(
        self,
        entry: MigraineEntry,
        *,
        reviewed_annotation: dict[str, Any] | None = None,
        preserve_review: bool = False,
    ) -> None:
        automatic_result = self.interpreter.interpret(entry.timeline_notes, entry.entered_laterality)
        automatic_snapshot = automatic_result.to_payload()
        result = automatic_result
        if reviewed_annotation is not None:
            merged_annotation = {
                "onsetMinute": automatic_result.onset_minute,
                "peakStartMinute": automatic_result.peak_start_minute,
                "peakEndMinute": automatic_result.peak_end_minute,
                "endMinute": automatic_result.end_minute,
                "endStatus": automatic_result.end_status,
                "laterality": automatic_result.laterality,
                "sideDetail": automatic_result.side_detail,
                "contexts": list(automatic_result.contexts),
                "symptoms": list(automatic_result.symptoms),
                "interventions": list(automatic_result.interventions),
                "confidence": automatic_result.confidence,
            }
            merged_annotation.update(reviewed_annotation)
            result = self.interpreter.interpret(entry.timeline_notes, entry.entered_laterality, merged_annotation)
        snapshot = result.to_payload()
        current = entry.interpretation
        if current is not None and preserve_review and current.is_reviewed:
            current.automatic_snapshot = automatic_snapshot
            return
        if current is None:
            current = NoteInterpretation(entry=entry)
            entry.interpretation = current
            self.session.add(current)
        for field, value in snapshot.items():
            if field == "extraction_method":
                setattr(current, field, value)
            elif hasattr(current, field):
                setattr(current, field, value)
        current.automatic_snapshot = automatic_snapshot
        current.is_reviewed = reviewed_annotation is not None
        current.reviewed_at = datetime.now(timezone.utc) if reviewed_annotation is not None else None

    def _upsert_daily_record(self, record_date, changes: dict[str, Any], *, origin: str) -> DailyRecord:
        record = self.repository.get_daily_record(record_date)
        if record is None:
            values = {field: bool(changes.get(field, False)) for field in self.DAILY_FIELDS}
            record = DailyRecord(user_id=self.user_id, record_date=record_date, source_system=origin, **values)
            self.session.add(record)
        else:
            for field, value in changes.items():
                if field in self.DAILY_FIELDS:
                    setattr(record, field, bool(value))
        self.session.flush()
        return record

    def _validate_triggers(self, codes: list[str], *, allowed_inactive_codes: set[str] | None = None) -> None:
        valid = {item.code for item in self.repository.list_trigger_definitions()}
        valid.update(allowed_inactive_codes or set())
        unknown = sorted(set(codes) - valid)
        if unknown:
            raise ValueError(f"Unbekannte Auslöser-Codes: {', '.join(unknown)}")

    def _audit(
        self,
        entry: MigraineEntry,
        action: str,
        origin: str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self.session.add(
            EntryAuditLog(
                entry_id=entry.id,
                action=action,
                changed_at=datetime.now(timezone.utc),
                origin=origin,
                before_payload=before,
                after_payload=after,
            )
        )

    @staticmethod
    def _medication_entities(items) -> list[MedicationIntake]:
        entities = []
        for index, item in enumerate(items):
            values = item if isinstance(item, dict) else item.model_dump()
            entities.append(MedicationIntake(sequence=index, **values))
        return entities

    @staticmethod
    def _snapshot(entry: MigraineEntry) -> dict[str, Any]:
        return {
            "id": str(entry.id),
            "user_id": str(entry.user_id),
            "entry_date": entry.entry_date.isoformat(),
            "trigger_codes": sorted(trigger.trigger_code for trigger in entry.triggers),
            "strength": entry.strength,
            "duration_hours": float(entry.duration_hours),
            "pain_type": entry.pain_type,
            "entered_laterality": entry.entered_laterality,
            "aura_codes": list(entry.aura_codes),
            "vomiting": entry.vomiting,
            "nausea": entry.nausea,
            "phonophobia": entry.phonophobia,
            "photophobia": entry.photophobia,
            "osmophobia": entry.osmophobia,
            "other_symptom_codes": list(entry.other_symptom_codes),
            "medications": [
                {
                    "name": item.name,
                    "taken_at": item.taken_at.isoformat(timespec="minutes") if item.taken_at else None,
                    "dose": item.dose,
                    "effectiveness": item.effectiveness,
                }
                for item in entry.medications
            ],
            "timeline_notes": entry.timeline_notes,
            "possible_factors": entry.possible_factors,
            "symptoms_and_actions": entry.symptoms_and_actions,
            "other_notes": entry.other_notes,
            "source_system": entry.source_system,
            "ai_provider": entry.ai_provider,
            "ai_model": entry.ai_model,
            "ai_prompt_version": entry.ai_prompt_version,
        }

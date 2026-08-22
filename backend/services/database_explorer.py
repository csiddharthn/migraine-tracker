from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from backend.repositories.database_explorer import DatabaseExplorerRepository


@dataclass(frozen=True)
class TableDescriptor:
    key: str
    label: str
    physical_table: str
    description: str
    personal: bool


@dataclass(frozen=True)
class DatabaseTable:
    descriptor: TableDescriptor
    rows: list[dict[str, Any]]
    technical_columns: tuple[str, ...] = ()


class DatabaseExplorerService:
    TABLES = (
        TableDescriptor("entries", "Kopfschmerzeinträge", "migraine_entries", "Dokumentierte Kopfschmerz- und Migränetage.", True),
        TableDescriptor("medication_intakes", "Medikamenteneinnahmen", "medication_intakes", "Alle einzelnen Medikamenteneinnahmen mit Uhrzeit, Dosis und dokumentierter Wirkung.", True),
        TableDescriptor("daily_records", "Beobachtungstage", "daily_records", "Kalendertage und vorbeugende Behandlungen.", True),
        TableDescriptor("interpretations", "Automatisch ausgewertete Notizen", "note_interpretations", "Uhrzeiten, Schmerzseite und Begleitumstände, die im Notiztext erkannt und gegebenenfalls geprüft wurden.", True),
        TableDescriptor("trigger_assignments", "Ausgewählte Auslöser", "entry_triggers", "Die möglichen Auslöser, die bei den einzelnen Kopfschmerztagen ausgewählt wurden.", True),
        TableDescriptor("audit_logs", "Änderungsprotokoll", "entry_audit_log", "Erstellungen und Änderungen an Kopfschmerzeinträgen.", True),
        TableDescriptor("migration_rows", "Übernahme aus Excel", "migration_source_rows", "Informationen zur einmaligen Übernahme der ursprünglichen Excel-Zeilen.", True),
        TableDescriptor("users", "Personen", "user_profiles", "In der Datenbank angelegte Personenprofile.", False),
        TableDescriptor("trigger_definitions", "Verfügbare Auslöser", "trigger_definitions", "Alle Auslöser, die im Eingabeformular ausgewählt werden können.", False),
    )

    def __init__(self, session: Session, user_id: uuid.UUID) -> None:
        self.repository = DatabaseExplorerRepository(session, user_id)
        profile = self.repository.selected_user()
        self.user_display_name = profile.display_name if profile else str(user_id)
        self._loaders: dict[str, Callable[[], DatabaseTable]] = {
            "entries": self._entries,
            "medication_intakes": self._medication_intakes,
            "daily_records": self._daily_records,
            "interpretations": self._interpretations,
            "trigger_assignments": self._trigger_assignments,
            "audit_logs": self._audit_logs,
            "migration_rows": self._migration_rows,
            "users": self._users,
            "trigger_definitions": self._trigger_definitions,
        }

    def counts(self) -> dict[str, int]:
        return self.repository.counts()

    def descriptors(self) -> tuple[TableDescriptor, ...]:
        return self.TABLES

    def load(self, key: str) -> DatabaseTable:
        try:
            return self._loaders[key]()
        except KeyError as exc:
            raise ValueError("Der ausgewählte Datenbereich ist nicht verfügbar.") from exc

    def _entries(self) -> DatabaseTable:
        rows = []
        for entry in self.repository.entries():
            rows.append(
                {
                    "Person": self.user_display_name,
                    "Datum": entry.entry_date,
                    "Stärke": entry.strength,
                    "Dauer (Stunden)": float(entry.duration_hours),
                    "Auslöser": " · ".join(item.definition.label for item in entry.triggers),
                    "Schmerzart": entry.pain_type,
                    "Seite (eingetragen)": entry.entered_laterality,
                    "Vorboten": _join(entry.aura_codes),
                    "Erbrechen": entry.vomiting,
                    "Übelkeit": entry.nausea,
                    "Lärmscheu": entry.phonophobia,
                    "Lichtscheu": entry.photophobia,
                    "Geruchsempfindlich": entry.osmophobia,
                    "Andere Symptome": _join(entry.other_symptom_codes),
                    "Medikamente": " · ".join(item.name for item in entry.medications),
                    "Notizen": entry.notes,
                    "Quelle": entry.source_system,
                    "Ursprünglicher KI-Eingabetext": entry.source_narrative,
                    "KI-Anbieter": entry.ai_provider,
                    "KI-Modell": entry.ai_model,
                    "KI-Promptversion": entry.ai_prompt_version,
                    "KI-Entwurf geprüft am": entry.ai_reviewed_at,
                    "Eintrag-ID": str(entry.id),
                    "Person-ID": str(entry.user_id),
                    "Quellzeile": entry.source_row,
                    "Quellfingerabdruck": entry.source_fingerprint,
                    "Erstellt": entry.created_at,
                    "Geändert": entry.updated_at,
                }
            )
        return DatabaseTable(
            self._descriptor("entries"),
            rows,
            (
                "Ursprünglicher KI-Eingabetext",
                "KI-Anbieter",
                "KI-Modell",
                "KI-Promptversion",
                "KI-Entwurf geprüft am",
                "Eintrag-ID",
                "Person-ID",
                "Quellzeile",
                "Quellfingerabdruck",
                "Erstellt",
                "Geändert",
            ),
        )

    def _medication_intakes(self) -> DatabaseTable:
        rows = [
            {
                "Person": self.user_display_name,
                "Datum": entry_date,
                "Medikament": row.name,
                "Einnahmezeit": _time_text(row.taken_at),
                "Dosis / Form": row.dose,
                "Wirkung": row.effectiveness,
                "Reihenfolge": row.sequence + 1,
                "Einnahme-ID": str(row.id),
                "Eintrag-ID": str(row.entry_id),
                "Erstellt": row.created_at,
                "Geändert": row.updated_at,
            }
            for row, entry_date in self.repository.medication_intakes()
        ]
        return DatabaseTable(
            self._descriptor("medication_intakes"),
            rows,
            ("Reihenfolge", "Einnahme-ID", "Eintrag-ID", "Erstellt", "Geändert"),
        )

    def _daily_records(self) -> DatabaseTable:
        rows = [
            {
                "Person": self.user_display_name,
                "Datum": row.record_date,
                "Aimovig-Injektion": row.aimovig_injection,
                "Momeallerg Nasenspray": row.momeallerg_nasal_spray,
                "Amitriptylin neuraxpharm": row.amitriptyline_neuraxpharm,
                "Quelle": row.source_system,
                "Tagesdatensatz-ID": str(row.id),
                "Person-ID": str(row.user_id),
                "Quellzeile": row.source_row,
                "Quellfingerabdruck": row.source_fingerprint,
                "Erstellt": row.created_at,
                "Geändert": row.updated_at,
            }
            for row in self.repository.daily_records()
        ]
        return DatabaseTable(self._descriptor("daily_records"), rows, ("Tagesdatensatz-ID", "Person-ID", "Quellzeile", "Quellfingerabdruck", "Erstellt", "Geändert"))

    def _interpretations(self) -> DatabaseTable:
        rows = [
            {
                "Person": self.user_display_name,
                "Datum": entry_date,
                "Beginn": _minute_text(row.onset_minute),
                "Höhepunkt Beginn": _minute_text(row.peak_start_minute),
                "Höhepunkt Ende": _minute_text(row.peak_end_minute),
                "Ende": _minute_text(row.end_minute),
                "Endstatus": row.end_status,
                "Automatisch erkannte Schmerzseite": row.laterality,
                "Genauere Angabe zur Schmerzseite": row.side_detail,
                "Erkannte Begleitumstände": _join(row.contexts),
                "Symptome": _join(row.symptoms),
                "Maßnahmen": _join(row.interventions),
                "Sicherheit der automatischen Erkennung": row.confidence,
                "Art der automatischen Erkennung": row.extraction_method,
                "Manuell geprüft": row.is_reviewed,
                "Interpretation-ID": str(row.id),
                "Eintrag-ID": str(row.entry_id),
                "Automatischer Stand": _json(row.automatic_snapshot),
                "Geprüft am": row.reviewed_at,
                "Erstellt": row.created_at,
                "Geändert": row.updated_at,
            }
            for row, entry_date in self.repository.interpretations()
        ]
        return DatabaseTable(self._descriptor("interpretations"), rows, ("Endstatus", "Sicherheit der automatischen Erkennung", "Art der automatischen Erkennung", "Interpretation-ID", "Eintrag-ID", "Automatischer Stand", "Geprüft am", "Erstellt", "Geändert"))

    def _trigger_assignments(self) -> DatabaseTable:
        rows = [
            {
                "Person": self.user_display_name,
                "Datum": entry_date,
                "Code": row.trigger_code,
                "Auslöser": row.definition.label,
                "Beschreibung": row.definition.description,
                "Eintrag-ID": str(row.entry_id),
            }
            for row, entry_date in self.repository.trigger_assignments()
        ]
        return DatabaseTable(self._descriptor("trigger_assignments"), rows, ("Code", "Eintrag-ID"))

    def _audit_logs(self) -> DatabaseTable:
        rows = [
            {
                "Person": self.user_display_name,
                "Datum des Eintrags": entry_date,
                "Aktion": row.action,
                "Zeitpunkt": row.changed_at,
                "Ursprung": row.origin,
                "Vorher": _json(row.before_payload),
                "Nachher": _json(row.after_payload),
                "Protokoll-ID": str(row.id),
                "Eintrag-ID": str(row.entry_id),
            }
            for row, entry_date in self.repository.audit_logs()
        ]
        return DatabaseTable(self._descriptor("audit_logs"), rows, ("Protokoll-ID", "Eintrag-ID"))

    def _migration_rows(self) -> DatabaseTable:
        rows = [
            {
                "Person": self.user_display_name,
                "Datum": row.record_date,
                "Quelldatei": Path(row.source_file).name,
                "Tabellenblatt": row.source_sheet,
                "Quellzeile": row.source_row,
                "Status": row.status,
                "Hinweise": _join(row.issues),
                "Importiert am": row.imported_at,
                "Import-ID": str(row.id),
                "Person-ID": str(row.user_id),
                "Vollständiger Quellpfad": row.source_file,
                "Rohdaten": _json(row.raw_payload),
                "Inhaltshash": row.content_hash,
                "Eintrag-ID": str(row.entry_id) if row.entry_id else None,
                "Tagesdatensatz-ID": str(row.daily_record_id) if row.daily_record_id else None,
            }
            for row in self.repository.migration_rows()
        ]
        return DatabaseTable(
            self._descriptor("migration_rows"),
            rows,
            ("Import-ID", "Person-ID", "Vollständiger Quellpfad", "Rohdaten", "Inhaltshash", "Eintrag-ID", "Tagesdatensatz-ID"),
        )

    def _users(self) -> DatabaseTable:
        rows = [
            {
                "Name": row.display_name,
                "Erfassungsbeginn": row.tracking_start_date,
                "Aktiv": row.active,
                "Person-ID": str(row.id),
                "Namensschlüssel": row.name_key,
                "Erstellt": row.created_at,
                "Geändert": row.updated_at,
            }
            for row in self.repository.users()
        ]
        return DatabaseTable(self._descriptor("users"), rows, ("Person-ID", "Namensschlüssel", "Erstellt", "Geändert"))

    def _trigger_definitions(self) -> DatabaseTable:
        rows = [
            {
                "Code": row.code,
                "Bezeichnung": row.label,
                "Beschreibung": row.description,
                "Reihenfolge": row.sort_order,
                "Aktiv": row.active,
            }
            for row in self.repository.trigger_definitions()
        ]
        return DatabaseTable(self._descriptor("trigger_definitions"), rows, ("Code", "Reihenfolge"))

    def _descriptor(self, key: str) -> TableDescriptor:
        return next(item for item in self.TABLES if item.key == key)


def _join(values: list[str]) -> str:
    return " · ".join(values)


def _json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _minute_text(value: int | None) -> str | None:
    if value is None:
        return None
    day_offset, minute_of_day = divmod(value, 1440)
    hour, minute = divmod(minute_of_day, 60)
    suffix = f" ({'nächster Tag' if day_offset == 1 else f'{day_offset} Tage später'})" if day_offset else ""
    return f"{hour:02d}:{minute:02d}{suffix}"


def _time_text(value: time | None) -> str | None:
    return value.strftime("%H:%M") if value else None

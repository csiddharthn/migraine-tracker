from __future__ import annotations

"""Purpose: Pydantic schemas for AI intake drafts and timeline rows.

Usage: Defines AITimelineRow, AIIntakeDraft, and related models
used by AIIntakeService for structured output validation.

Functions available:
- None (schema definitions)

Classes available:
- AITimelineRow
- AIIntakeDraft
- AIClarificationQuestion
- AIMedicationDraft

Call hierarchy:
- schemas.py -> pydantic.BaseModel, Field, field_validator
- schemas.py -> backend.note_interpretation.StructuredNotes, TimelineNoteRow
"""

import hashlib
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.note_interpretation import StructuredNotes, TimelineNoteRow


TIME_PATTERN = r"^(?:[01]\d|2[0-3]):[0-5]\d$"


class AITimelineRow(BaseModel):
    start_time: str | None = Field(default=None, pattern=TIME_PATTERN)
    end_time: str | None = Field(default=None, pattern=TIME_PATTERN)
    note: str = ""

    @field_validator("note")
    @classmethod
    def clean_note(cls, value: str) -> str:
        return value.strip()

    def to_structured_row(self) -> TimelineNoteRow:
        return TimelineNoteRow(
            start_time=_clock(self.start_time),
            end_time=_clock(self.end_time),
            note=self.note,
        )


class AIMedicationDraft(BaseModel):
    name: str
    taken_at: str | None = Field(default=None, pattern=TIME_PATTERN)
    dose: str | None = None
    effectiveness: Literal["Ja", "Teilweise", "Nein"] | None = None

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Medication name must not be empty.")
        return cleaned

    @field_validator("dose")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None

    def taken_at_value(self) -> time | None:
        return _clock(self.taken_at)


class AIClarificationQuestion(BaseModel):
    field: str
    question_de: str
    question_en: str

    @field_validator("field", "question_de", "question_en")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()

    def localized(self, language: str) -> str:
        return self.question_en if language == "en" else self.question_de


class AIIntakeDraft(BaseModel):
    entry_date: date | None = None
    strength: int | None = Field(default=None, ge=0, le=10)
    duration_hours: float | None = Field(default=None, ge=0, le=168)
    trigger_codes: list[str] = Field(default_factory=list)
    proposed_triggers: list[str] = Field(default_factory=list)
    pain_type: Literal["Dumpf / drückend", "Pulsierend / stechend"] | None = None
    entered_laterality: Literal["Einseitig", "Beidseitig", "Rechts", "Links"] | None = None
    aura_codes: list[Literal["F", "G", "S", "O", "*"]] = Field(default_factory=list)
    vomiting: bool | None = None
    nausea: bool | None = None
    phonophobia: bool | None = None
    photophobia: bool | None = None
    osmophobia: bool | None = None
    other_symptom_codes: list[Literal["T", "R", "N"]] = Field(default_factory=list)
    medications: list[AIMedicationDraft] = Field(default_factory=list)
    timeline: list[AITimelineRow] = Field(default_factory=list)
    peak_time: str | None = Field(default=None, pattern=TIME_PATTERN)
    peak_duration_minutes: int | None = Field(default=None, ge=0, le=1440)
    possible_factors: str = ""
    symptoms_and_actions: str = ""
    aimovig_injection: bool | None = None
    momeallerg_nasal_spray: bool | None = None
    amitriptyline_neuraxpharm: bool | None = None
    clarification_questions: list[AIClarificationQuestion] = Field(default_factory=list)
    interpretation_notes_de: list[str] = Field(default_factory=list)
    interpretation_notes_en: list[str] = Field(default_factory=list)

    @field_validator("trigger_codes", "proposed_triggers", "aura_codes", "other_symptom_codes")
    @classmethod
    def unique_values(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @field_validator("possible_factors", "symptoms_and_actions")
    @classmethod
    def clean_long_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("interpretation_notes_de", "interpretation_notes_en")
    @classmethod
    def clean_notes(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    def structured_notes(self) -> StructuredNotes:
        peak = _minute(self.peak_time)
        return StructuredNotes(
            timeline=tuple(row.to_structured_row() for row in self.timeline),
            peak_start_minute=peak,
            peak_duration_minutes=self.peak_duration_minutes or 0,
            possible_factors=self.possible_factors,
            symptoms_and_actions=self.symptoms_and_actions,
        )

    def fingerprint(self) -> str:
        content = self.model_dump_json(exclude={"clarification_questions"})
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]

    def localized_notes(self, language: str) -> list[str]:
        return self.interpretation_notes_en if language == "en" else self.interpretation_notes_de


def _clock(value: str | None) -> time | None:
    if value is None:
        return None
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def _minute(value: str | None) -> int | None:
    clock = _clock(value)
    return clock.hour * 60 + clock.minute if clock else None

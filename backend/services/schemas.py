from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MedicationInput(BaseModel):
    name: str
    taken_at: time | None = None
    dose: str | None = None
    effectiveness: str | None = None

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Ein Medikamentenname ist erforderlich.")
        return cleaned

    @field_validator("dose", "effectiveness")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class EntryInput(BaseModel):
    entry_date: date
    trigger_codes: list[str] = Field(min_length=1)
    strength: int = Field(ge=0, le=10)
    duration_hours: Decimal = Field(ge=0, max_digits=6, decimal_places=2)
    pain_type: str | None = None
    entered_laterality: str | None = None
    aura_codes: list[str] = Field(default_factory=list)
    vomiting: bool = False
    nausea: bool = False
    phonophobia: bool = False
    photophobia: bool = False
    osmophobia: bool = False
    other_symptom_codes: list[str] = Field(default_factory=list)
    medications: list[MedicationInput] = Field(default_factory=list)
    notes: str = ""
    note_annotation: dict[str, Any] | None = Field(default=None, exclude=True)
    aimovig_injection: bool = False
    momeallerg_nasal_spray: bool = False
    amitriptyline_neuraxpharm: bool = False
    source_narrative: str | None = None
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_prompt_version: str | None = None
    ai_extraction: dict[str, Any] | None = None

    @field_validator("trigger_codes", "aura_codes", "other_symptom_codes")
    @classmethod
    def normalize_codes(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip() for item in value if item.strip()))

    @field_validator("pain_type", "entered_laterality")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("source_narrative", "ai_provider", "ai_model", "ai_prompt_version")
    @classmethod
    def empty_provenance_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class EntryPatch(BaseModel):
    entry_date: date | None = None
    trigger_codes: list[str] | None = None
    strength: int | None = Field(default=None, ge=0, le=10)
    duration_hours: Decimal | None = Field(default=None, ge=0, max_digits=6, decimal_places=2)
    pain_type: str | None = None
    entered_laterality: str | None = None
    aura_codes: list[str] | None = None
    vomiting: bool | None = None
    nausea: bool | None = None
    phonophobia: bool | None = None
    photophobia: bool | None = None
    osmophobia: bool | None = None
    other_symptom_codes: list[str] | None = None
    medications: list[MedicationInput] | None = None
    notes: str | None = None
    aimovig_injection: bool | None = None
    momeallerg_nasal_spray: bool | None = None
    amitriptyline_neuraxpharm: bool | None = None

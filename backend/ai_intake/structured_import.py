from __future__ import annotations

"""Validation and normalization for versioned structured-entry imports.

This module accepts JSON produced outside the migraine tracker (for example by
ChatGPT), validates it against the existing AI intake draft schema, and resolves
trigger labels/codes against the local trigger catalogue. It never writes to the
database; saving still happens through EntryService after normal form review.
"""

from datetime import date
from typing import Literal, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.models import TriggerDefinition
from backend.ai_intake.schemas import AIIntakeDraft


class StructuredImportError(ValueError):
    """User-safe validation failure for a structured import payload."""


class StructuredEntryImport(BaseModel):
    """Versioned envelope for importing a pre-structured migraine entry draft."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"] = "1"
    source: str = Field(default="ChatGPT", max_length=80)
    source_narrative: str | None = None
    draft: AIIntakeDraft

    @field_validator("source")
    @classmethod
    def clean_source(cls, value: str) -> str:
        return value.strip() or "ChatGPT"

    @field_validator("source_narrative")
    @classmethod
    def clean_source_narrative(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


def parse_structured_import(
    raw_json: str,
    *,
    trigger_definitions: Sequence[TriggerDefinition],
    current_date: date,
) -> StructuredEntryImport:
    """Parse and normalize a structured import without touching the database."""

    cleaned = raw_json.strip()
    if not cleaned:
        raise StructuredImportError("Bitte fügen Sie zuerst einen JSON-Import ein.")

    try:
        imported = StructuredEntryImport.model_validate_json(cleaned)
    except (ValidationError, ValueError) as exc:
        raise StructuredImportError(
            "Der strukturierte Import entspricht nicht dem erwarteten JSON-Schema."
        ) from exc

    draft = imported.draft
    missing_required = [
        field
        for field, value in (
            ("entry_date", draft.entry_date),
            ("strength", draft.strength),
            ("duration_hours", draft.duration_hours),
        )
        if value is None
    ]
    if missing_required:
        raise StructuredImportError(
            "Im strukturierten Import fehlen Pflichtangaben: "
            + ", ".join(missing_required)
            + "."
        )
    if draft.entry_date and draft.entry_date > current_date:
        raise StructuredImportError("Das Datum des Eintrags darf nicht in der Zukunft liegen.")

    active_triggers = [item for item in trigger_definitions if item.active]
    by_code = {item.code: item for item in active_triggers}
    by_label = {item.label.strip().casefold(): item.code for item in active_triggers if item.label.strip()}

    resolved_codes: list[str] = []
    unresolved_labels: list[str] = []

    for code in draft.trigger_codes:
        if code in by_code:
            resolved_codes.append(code)
        else:
            unresolved_labels.append(f"Unbekannter Auslöser-Code {code}")

    for label in draft.proposed_triggers:
        matching_code = by_label.get(label.strip().casefold())
        if matching_code:
            resolved_codes.append(matching_code)
        elif label.strip():
            unresolved_labels.append(label.strip())

    normalized_draft = draft.model_copy(
        update={
            "trigger_codes": list(dict.fromkeys(resolved_codes)),
            "proposed_triggers": list(dict.fromkeys(unresolved_labels)),
        }
    )
    return imported.model_copy(update={"draft": normalized_draft})

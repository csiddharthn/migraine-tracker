from __future__ import annotations

"""Tests for versioned structured migraine-entry imports."""

import json
from datetime import date

import pytest

from backend.ai_intake.structured_import import StructuredImportError, parse_structured_import
from backend.models import TriggerDefinition


CURRENT_DATE = date(2026, 8, 29)


def make_trigger(code: str, label: str, *, active: bool = True) -> TriggerDefinition:
    return TriggerDefinition(
        code=code,
        label=label,
        description="",
        sort_order=1,
        active=active,
    )


def test_structured_import_parses_complete_draft_and_resolves_trigger_label() -> None:
    raw = json.dumps(
        {
            "schema_version": "1",
            "source": "ChatGPT",
            "source_narrative": "Today the headache started at 08:30.",
            "draft": {
                "entry_date": "2026-08-29",
                "strength": 6,
                "duration_hours": 4.5,
                "trigger_codes": [],
                "proposed_triggers": ["Unsicher"],
                "medications": [
                    {
                        "name": "Eletriptan",
                        "taken_at": "10:15",
                        "dose": "40 mg",
                        "effectiveness": "Ja",
                    }
                ],
            },
        }
    )

    imported = parse_structured_import(
        raw,
        trigger_definitions=[make_trigger("8", "Unsicher")],
        current_date=CURRENT_DATE,
    )

    assert imported.schema_version == "1"
    assert imported.source == "ChatGPT"
    assert imported.draft.entry_date == CURRENT_DATE
    assert imported.draft.trigger_codes == ["8"]
    assert imported.draft.proposed_triggers == []
    assert imported.draft.medications[0].taken_at == "10:15"


def test_structured_import_keeps_unmatched_trigger_for_manual_review() -> None:
    raw = json.dumps(
        {
            "schema_version": "1",
            "draft": {
                "entry_date": "2026-08-28",
                "strength": 5,
                "duration_hours": 2,
                "trigger_codes": ["999"],
                "proposed_triggers": ["Unregelmäßige Mahlzeit"],
            },
        }
    )

    imported = parse_structured_import(
        raw,
        trigger_definitions=[make_trigger("8", "Unsicher")],
        current_date=CURRENT_DATE,
    )

    assert imported.draft.trigger_codes == []
    assert imported.draft.proposed_triggers == [
        "Unbekannter Auslöser-Code 999",
        "Unregelmäßige Mahlzeit",
    ]


@pytest.mark.parametrize(
    "draft, expected_fragment",
    [
        (
            {"strength": 5, "duration_hours": 2},
            "entry_date",
        ),
        (
            {"entry_date": "2026-08-28", "duration_hours": 2},
            "strength",
        ),
        (
            {"entry_date": "2026-08-28", "strength": 5},
            "duration_hours",
        ),
    ],
)
def test_structured_import_requires_core_fields(draft: dict, expected_fragment: str) -> None:
    raw = json.dumps({"schema_version": "1", "draft": draft})

    with pytest.raises(StructuredImportError, match=expected_fragment):
        parse_structured_import(raw, trigger_definitions=[], current_date=CURRENT_DATE)


def test_structured_import_rejects_future_date_and_unknown_top_level_fields() -> None:
    future = json.dumps(
        {
            "schema_version": "1",
            "draft": {
                "entry_date": "2026-08-30",
                "strength": 5,
                "duration_hours": 2,
            },
        }
    )
    with pytest.raises(StructuredImportError, match="Zukunft"):
        parse_structured_import(future, trigger_definitions=[], current_date=CURRENT_DATE)

    extra = json.dumps(
        {
            "schema_version": "1",
            "unexpected": "not allowed",
            "draft": {
                "entry_date": "2026-08-28",
                "strength": 5,
                "duration_hours": 2,
            },
        }
    )
    with pytest.raises(StructuredImportError, match="JSON-Schema"):
        parse_structured_import(extra, trigger_definitions=[], current_date=CURRENT_DATE)

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from backend.ai_intake import AIIntakeDraft, AIIntakeError, AIIntakeService, AIMedicationDraft, AITimelineRow
from backend.models import TriggerDefinition


def trigger(code: str, label: str) -> TriggerDefinition:
    return TriggerDefinition(code=code, label=label, description="", sort_order=int(code), active=True)


class FakeCompletions:
    def __init__(self, results: dict[str, AIIntakeDraft | Exception]) -> None:
        self.results = results
        self.arguments: list[dict] = []

    def create(self, **kwargs):
        self.arguments.append(kwargs)
        result = self.results[kwargs["model"]]
        if isinstance(result, Exception):
            raise result
        message = SimpleNamespace(content=result.model_dump_json())
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    def __init__(self, results: dict[str, AIIntakeDraft | Exception]) -> None:
        self.chat = SimpleNamespace(completions=FakeCompletions(results))


def test_ai_intake_extracts_typed_draft_and_normalizes_triggers() -> None:
    parsed = AIIntakeDraft(
        entry_date=date(2026, 8, 10),
        strength=7,
        duration_hours=5.5,
        trigger_codes=["5", "unknown"],
        pain_type="Dumpf / drückend",
        entered_laterality="Rechts",
        nausea=False,
        medications=[AIMedicationDraft(name="Eletriptan", taken_at="10:15", dose="40 mg", effectiveness="Ja")],
        timeline=[AITimelineRow(start_time="08:30", end_time="10:00", note="Langsamer Beginn")],
        peak_time="11:00",
        peak_duration_minutes=60,
    )
    client = FakeClient({"test-model": parsed})
    service = AIIntakeService(
        api_key="test-key",
        model="test-model",
        prompt_version="test-v1",
        client_factory=lambda **_: client,
    )

    draft = service.extract(
        "Gestern begann der Kopfschmerz um 08:30 Uhr.",
        trigger_definitions=[trigger("5", "Kalte Schlafumgebung")],
        medication_names=["Eletriptan"],
        current_date=date(2026, 8, 11),
    )

    assert draft.trigger_codes == ["5"]
    assert draft.proposed_triggers == ["Unbekannter Auslöser-Code unknown"]
    assert draft.medications[0].taken_at_value().isoformat(timespec="minutes") == "10:15"
    assert draft.structured_notes().timeline[0].start_time.isoformat(timespec="minutes") == "08:30"
    request = client.chat.completions.arguments[0]
    assert request["model"] == "test-model"
    assert request["response_format"]["json_schema"]["strict"] is True
    assert "Kalte Schlafumgebung" in request["messages"][1]["content"]
    assert "Translate all user-visible free text into clear, natural German" in request["messages"][0]["content"]
    assert "medication dose/form" in request["messages"][0]["content"]
    assert service.model_used == "test-model"


def test_ai_intake_adds_questions_only_for_missing_required_fields() -> None:
    client = FakeClient({"test-model": AIIntakeDraft(possible_factors="Schlechter Schlaf")})
    service = AIIntakeService(
        api_key="test-key",
        model="test-model",
        prompt_version="test-v1",
        client_factory=lambda **_: client,
    )

    draft = service.extract(
        "Schlechter Schlaf.",
        trigger_definitions=[trigger("8", "Unsicher")],
        medication_names=[],
        current_date=date(2026, 8, 11),
    )

    assert [question.field for question in draft.clarification_questions] == [
        "entry_date",
        "strength",
        "duration_hours",
        "trigger_codes",
    ]


def test_ai_intake_rejects_empty_key_and_empty_narrative() -> None:
    with pytest.raises(AIIntakeError):
        AIIntakeService(api_key=" ", model="test", prompt_version="1")

    service = AIIntakeService(
        api_key="test-key",
        model="test-model",
        prompt_version="test-v1",
        client_factory=lambda **_: FakeClient({"test-model": AIIntakeDraft()}),
    )
    with pytest.raises(AIIntakeError):
        service.extract(" ", trigger_definitions=[], medication_names=[], current_date=date(2026, 8, 11))


def test_ai_intake_uses_next_groq_model_after_failure() -> None:
    parsed = AIIntakeDraft(
        entry_date=date(2026, 8, 10),
        strength=5,
        duration_hours=4,
        trigger_codes=["8"],
    )
    client = FakeClient(
        {
            "openai/gpt-oss-120b": RuntimeError("rate limited"),
            "openai/gpt-oss-20b": parsed,
        }
    )
    service = AIIntakeService(
        api_key="test-key",
        models=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        prompt_version="test-v1",
        client_factory=lambda **_: client,
    )

    draft = service.extract(
        "Am 10. August hatte ich vier Stunden lang Kopfschmerzen der Stärke 5.",
        trigger_definitions=[trigger("8", "Unsicher")],
        medication_names=[],
        current_date=date(2026, 8, 11),
    )

    assert draft.strength == 5
    assert service.model_used == "openai/gpt-oss-20b"
    assert service.attempted_models == ("openai/gpt-oss-120b", "openai/gpt-oss-20b")
    assert [request["model"] for request in client.chat.completions.arguments] == [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
    ]


def test_ai_intake_strict_schema_closes_and_requires_every_object_field() -> None:
    response_format = AIIntakeService._response_format()
    schema = response_format["json_schema"]["schema"]

    def assert_closed(node) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("properties"), dict):
                assert node["additionalProperties"] is False
                assert node["required"] == list(node["properties"])
            assert "default" not in node
            for value in node.values():
                assert_closed(value)
        elif isinstance(node, list):
            for value in node:
                assert_closed(value)

    assert_closed(schema)

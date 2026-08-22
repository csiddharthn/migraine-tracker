from __future__ import annotations

import pytest

from backend.services.trigger_service import DuplicateTriggerError, TriggerService


def test_trigger_service_creates_next_global_code(session) -> None:
    service = TriggerService(session)

    first = service.create("Unregelmäßige Mahlzeit", "Lange Pause zwischen Mahlzeiten")
    second = service.create("Bildschirmbelastung")

    assert first.code == "9"
    assert first.sort_order == 9
    assert first.active is True
    assert second.code == "10"
    assert [item.label for item in service.repository.list_all() if item.active][-2:] == [
        "Unregelmäßige Mahlzeit",
        "Bildschirmbelastung",
    ]


def test_trigger_service_rejects_duplicate_and_blank_labels(session) -> None:
    service = TriggerService(session)
    service.create("Unregelmäßige Mahlzeit")

    with pytest.raises(DuplicateTriggerError):
        service.create("  unregelmäßige   mahlzeit  ")
    with pytest.raises(ValueError):
        service.create(" ")

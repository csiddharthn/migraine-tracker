from __future__ import annotations

"""Purpose: Tests for trigger service.

Usage: Tests trigger creation, duplicate detection, and code generation.

Functions available:
- test_trigger_service_creates_next_global_code, etc.

Classes available:
- None

Call hierarchy:
- test_trigger_service.py -> backend.services.trigger_service
"""

import pytest

from backend.services.trigger_service import DuplicateTriggerError, TriggerService

TRIGGER_LABEL_FIRST = "Unregelmäßige Mahlzeit"
TRIGGER_DESC_FIRST = "Lange Pause zwischen Mahlzeiten"
TRIGGER_LABEL_SECOND = "Bildschirmbelastung"
TRIGGER_CODE_FIRST = "9"
TRIGGER_SORT_FIRST = 9
TRIGGER_CODE_SECOND = "10"
TRIGGER_SORT_SECOND = 10
DUPLICATE_LABEL_VARIANT = "  unregelmäßige   mahlzeit  "
BLANK_LABEL = " "


def test_trigger_service_creates_next_global_code(session) -> None:
    service = TriggerService(session)

    first = service.create(TRIGGER_LABEL_FIRST, TRIGGER_DESC_FIRST)
    second = service.create(TRIGGER_LABEL_SECOND)

    assert first.code == TRIGGER_CODE_FIRST
    assert first.sort_order == TRIGGER_SORT_FIRST
    assert first.active is True
    assert second.code == TRIGGER_CODE_SECOND
    assert [item.label for item in service.repository.list_all() if item.active][-2:] == [
        TRIGGER_LABEL_FIRST,
        TRIGGER_LABEL_SECOND,
    ]


def test_trigger_service_rejects_duplicate_and_blank_labels(session) -> None:
    service = TriggerService(session)
    service.create(TRIGGER_LABEL_FIRST)

    with pytest.raises(DuplicateTriggerError):
        service.create(DUPLICATE_LABEL_VARIANT)
    with pytest.raises(ValueError):
        service.create(BLANK_LABEL)

from __future__ import annotations

"""Purpose: Multi-user isolation tests.

Usage: Verifies analytics isolation between users.

Functions available:
- test_same_date_is_allowed_for_different_users_and_analytics_are_isolated

Classes available:
- None

Call hierarchy:
- test_multi_user_isolation.py -> backend.services
"""

from datetime import date
from decimal import Decimal

from backend.services.analytics_service import AnalyticsService
from backend.services.entry_service import EntryService
from backend.services.schemas import EntryInput
from backend.services.user_service import UserService

ANNA_NAME = "Anna Beispiel"
BEN_NAME = "Ben Beispiel"
USER_BIRTH = date(2026, 8, 1)
ENTRY_DATE = date(2026, 8, 10)
TRIGGER_CODE = "8"
DURATION_HOURS = Decimal("4.0")
ANNA_STRENGTH = 3
BEN_STRENGTH = 8
ANNA_NOTES = "rechts"
BEN_NOTES = "links"


def test_same_date_is_allowed_for_different_users_and_analytics_are_isolated(session) -> None:
    users = UserService(session)
    anna = users.create(ANNA_NAME, USER_BIRTH)
    ben = users.create(BEN_NAME, USER_BIRTH)
    session.flush()

    common = {
        "entry_date": ENTRY_DATE,
        "trigger_codes": [TRIGGER_CODE],
        "duration_hours": DURATION_HOURS,
    }
    EntryService(session, anna.id).create(EntryInput(**common, strength=ANNA_STRENGTH, notes=ANNA_NOTES))
    EntryService(session, ben.id).create(EntryInput(**common, strength=BEN_STRENGTH, notes=BEN_NOTES))
    session.commit()

    anna_data = AnalyticsService(session, anna).dataset(end_date=ENTRY_DATE)
    ben_data = AnalyticsService(session, ben).dataset(end_date=ENTRY_DATE)

    assert [entry.strength for entry in anna_data.entries] == [ANNA_STRENGTH]
    assert [entry.strength for entry in ben_data.entries] == [BEN_STRENGTH]
    assert anna_data.daily_records[0].user_id == anna.id
    assert ben_data.daily_records[0].user_id == ben.id

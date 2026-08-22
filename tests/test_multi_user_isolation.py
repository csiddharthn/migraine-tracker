from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.services.analytics_service import AnalyticsService
from backend.services.entry_service import EntryService
from backend.services.schemas import EntryInput
from backend.services.user_service import UserService


def test_same_date_is_allowed_for_different_users_and_analytics_are_isolated(session) -> None:
    users = UserService(session)
    anna = users.create("Anna Beispiel", date(2026, 8, 1))
    ben = users.create("Ben Beispiel", date(2026, 8, 1))
    session.flush()

    common = {
        "entry_date": date(2026, 8, 10),
        "trigger_codes": ["8"],
        "duration_hours": Decimal("4.0"),
    }
    EntryService(session, anna.id).create(EntryInput(**common, strength=3, notes="rechts"))
    EntryService(session, ben.id).create(EntryInput(**common, strength=8, notes="links"))
    session.commit()

    anna_data = AnalyticsService(session, anna).dataset(end_date=date(2026, 8, 10))
    ben_data = AnalyticsService(session, ben).dataset(end_date=date(2026, 8, 10))

    assert [entry.strength for entry in anna_data.entries] == [3]
    assert [entry.strength for entry in ben_data.entries] == [8]
    assert anna_data.daily_records[0].user_id == anna.id
    assert ben_data.daily_records[0].user_id == ben.id

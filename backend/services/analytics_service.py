from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.analytics.calculations import AnalyticsDataset
from backend.models import UserProfile
from backend.repositories import EntryRepository


class AnalyticsService:
    def __init__(self, session: Session, user: UserProfile) -> None:
        self.user = user
        self.repository = EntryRepository(session, user.id)

    def dataset(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        min_strength: int | None = None,
        max_strength: int | None = None,
        trigger_codes: list[str] | None = None,
    ) -> AnalyticsDataset:
        effective_start = start_date or self.user.tracking_start_date
        effective_end = end_date or date.today()
        entries = self.repository.list_entries(
            start_date=effective_start,
            end_date=effective_end,
            min_strength=min_strength,
            max_strength=max_strength,
            trigger_codes=trigger_codes,
        )
        daily = self.repository.list_daily_records(start_date=effective_start, end_date=effective_end)
        return AnalyticsDataset.build(entries, daily, first_day=effective_start, analysis_end=effective_end)

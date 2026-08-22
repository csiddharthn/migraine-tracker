from __future__ import annotations

from backend.analytics.calculations import AnalyticsDataset
from backend.services.analytics_service import AnalyticsService
from frontend.components.filters import report_period
from frontend.components.users import selected_user, user_caption


def filtered_dataset(session) -> AnalyticsDataset:
    user = selected_user(session)
    user_caption(user)
    service = AnalyticsService(session, user)
    start_date, end_date = report_period(user)
    return service.dataset(start_date=start_date, end_date=end_date)

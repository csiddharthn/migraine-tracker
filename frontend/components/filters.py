from __future__ import annotations

import calendar
from datetime import date
from typing import Iterable

import streamlit as st

from backend.models import UserProfile
from frontend.i18n import date_input_format, tr


def render_report_period(user: UserProfile) -> tuple[date, date]:
    default = (user.tracking_start_date, date.today())
    with st.sidebar:
        st.subheader(tr("Zeitraum", "Date range"))
        selected = st.date_input(
            tr("Auswertungszeitraum", "Reporting period"),
            value=default,
            min_value=user.tracking_start_date,
            max_value=date.today(),
            format=date_input_format(),
            key=f"report_period_{user.id}",
        )
    return _date_range(selected, default)


def report_period(user: UserProfile) -> tuple[date, date]:
    default = (user.tracking_start_date, date.today())
    return _date_range(st.session_state.get(f"report_period_{user.id}"), default)


def latest_month_range(dates: Iterable[date], minimum: date, maximum: date) -> tuple[date, date]:
    if maximum < minimum:
        raise ValueError("The maximum date must not be before the minimum date.")
    available = [value for value in dates if minimum <= value <= maximum]
    latest = max(available, default=maximum)
    month_start = date(latest.year, latest.month, 1)
    month_end = date(latest.year, latest.month, calendar.monthrange(latest.year, latest.month)[1])
    return max(minimum, month_start), min(maximum, month_end)


def _date_range(value, default: tuple[date, date]) -> tuple[date, date]:
    if isinstance(value, (tuple, list)) and len(value) == 2 and all(isinstance(item, date) for item in value):
        return value[0], value[1]
    return default

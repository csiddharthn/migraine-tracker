from datetime import date

import pytest

from frontend.components.filters import latest_month_range

LATEST_ACTIVITY = date(2026, 8, 10)
EARLIEST = date(2026, 6, 1)
BOUNDARY_START = date(2026, 7, 15)
BOUNDARY_END = date(2026, 7, 20)
REVERSED_START = date(2026, 8, 2)
REVERSED_END = date(2026, 8, 1)


def test_latest_month_range_uses_latest_month_with_data() -> None:
    result = latest_month_range(
        [date(2026, 6, 9), LATEST_ACTIVITY],
        EARLIEST,
        LATEST_ACTIVITY,
    )
    assert result == (date(2026, 8, 1), LATEST_ACTIVITY)


def test_latest_month_range_respects_filtered_boundaries() -> None:
    result = latest_month_range([], BOUNDARY_START, BOUNDARY_END)
    assert result == (BOUNDARY_START, BOUNDARY_END)


def test_latest_month_range_rejects_reversed_boundaries() -> None:
    with pytest.raises(ValueError):
        latest_month_range([], REVERSED_START, REVERSED_END)

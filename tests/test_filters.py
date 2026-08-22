from datetime import date

import pytest

from frontend.components.filters import latest_month_range


def test_latest_month_range_uses_latest_month_with_data() -> None:
    result = latest_month_range(
        [date(2026, 6, 9), date(2026, 8, 10)],
        date(2026, 6, 1),
        date(2026, 8, 10),
    )

    assert result == (date(2026, 8, 1), date(2026, 8, 10))


def test_latest_month_range_respects_filtered_boundaries() -> None:
    result = latest_month_range([], date(2026, 7, 15), date(2026, 7, 20))

    assert result == (date(2026, 7, 15), date(2026, 7, 20))


def test_latest_month_range_rejects_reversed_boundaries() -> None:
    with pytest.raises(ValueError):
        latest_month_range([], date(2026, 8, 2), date(2026, 8, 1))

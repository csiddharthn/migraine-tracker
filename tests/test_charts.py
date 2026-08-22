from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from frontend.components.charts import (
    STRENGTH_COLORS,
    attack_timeline,
    completeness_chart,
    duration_by_date_bar,
    histogram,
    medication_effectiveness_chart,
    monthly_frequency_chart,
    monthly_metric_scatter,
    observation_days_bar,
    pattern_source_chart,
    strength_duration_scatter,
    weekday_rate_chart,
)


def test_observation_days_bar_reconciles_headache_free_and_total_days() -> None:
    figure = observation_days_bar(19, 52, lang="en")

    assert [trace.name for trace in figure.data] == ["Headache days", "Headache-free days"]
    assert [trace.x[0] for trace in figure.data] == [19, 52]
    assert [trace.text[0] for trace in figure.data] == ["<b>19</b><br>27%", "<b>52</b><br>73%"]
    assert figure.layout.barmode == "stack"
    assert figure.layout.legend.traceorder == "normal"


def test_attack_timeline_uses_all_ten_strength_colours() -> None:
    interpretation = SimpleNamespace(onset_minute=8 * 60, end_minute=14 * 60, peak_start_minute=11 * 60)
    entries = [
        SimpleNamespace(entry_date=date(2026, 7, 10), duration_hours=Decimal("6.0"), strength=1, interpretation=interpretation),
        SimpleNamespace(entry_date=date(2026, 7, 11), duration_hours=Decimal("6.0"), strength=10, interpretation=interpretation),
    ]
    data = SimpleNamespace(first_day=date(2026, 7, 1), analysis_end=date(2026, 7, 31), entries=entries)

    figure = attack_timeline(data, "2026-07", lang="en")
    bars = [trace for trace in figure.data if trace.type == "bar"]

    assert len(STRENGTH_COLORS) == 10
    assert [list(bar.marker.color) for bar in bars] == [[10], [1]]
    assert list(bars[0].marker.colorbar.tickvals) == list(range(1, 11))
    assert bars[0].marker.showscale is True
    assert bars[1].marker.showscale is False
    assert all(list(bar.width) == [0.72] for bar in bars)
    assert figure.layout.yaxis.type == "category"
    assert len(figure.layout.yaxis.tickvals) == 31
    assert figure.layout.yaxis.tickvals[0] == "2026-07-31"
    assert figure.layout.yaxis.tickvals[-1] == "2026-07-01"
    assert figure.layout.yaxis.autorange == "reversed"
    assert list(figure.layout.xaxis.ticktext) == [
        "00:00",
        "12:00",
        "+1 d<br>00:00",
        "+1 d<br>12:00",
    ]
    assert figure.layout.xaxis.tickangle == 0


def test_attack_timeline_shows_peak_without_complete_onset_and_end() -> None:
    interpretation = SimpleNamespace(onset_minute=None, end_minute=None, peak_start_minute=12 * 60 + 30)
    entry = SimpleNamespace(
        entry_date=date(2026, 8, 16),
        duration_hours=Decimal("4.0"),
        strength=1,
        interpretation=interpretation,
    )
    data = SimpleNamespace(first_day=date(2026, 8, 1), analysis_end=date(2026, 8, 17), entries=[entry])

    figure = attack_timeline(data, "2026-08", lang="en")
    peaks = [trace for trace in figure.data if trace.name == "Peak"]

    assert len(peaks) == 1
    assert list(peaks[0].x) == [12.5]
    assert list(peaks[0].y) == ["2026-08-16"]


def test_attack_timeline_uses_recorded_duration_when_end_is_missing() -> None:
    interpretation = SimpleNamespace(onset_minute=12 * 60, end_minute=None, peak_start_minute=12 * 60)
    entry = SimpleNamespace(
        entry_date=date(2026, 8, 19),
        duration_hours=Decimal("4.0"),
        strength=1,
        interpretation=interpretation,
    )
    data = SimpleNamespace(first_day=date(2026, 8, 1), analysis_end=date(2026, 8, 22), entries=[entry])

    figure = attack_timeline(data, "2026-08", lang="en")
    bars = [trace for trace in figure.data if trace.type == "bar"]

    assert len(bars) == 1
    assert list(bars[0].base) == [12]
    assert list(bars[0].x) == [4]
    assert bars[0].customdata[0][3] == "16:00 (calculated from recorded duration)"


def test_duration_by_date_bar_includes_every_calendar_day() -> None:
    entries = [
        SimpleNamespace(entry_date=date(2026, 6, 10), duration_hours=Decimal("7.0"), strength=6),
        SimpleNamespace(entry_date=date(2026, 6, 9), duration_hours=Decimal("12.0"), strength=9),
    ]

    figure = duration_by_date_bar(
        entries,
        start_date=date(2026, 6, 8),
        end_date=date(2026, 6, 11),
        lang="en",
    )
    bars = figure.data[0]

    assert list(bars.x) == ["2026-06-08", "2026-06-09", "2026-06-10", "2026-06-11"]
    assert list(bars.y) == [0.0, 12.0, 7.0, 0.0]
    assert list(bars.marker.color) == [1, 9, 6, 1]
    assert list(figure.layout.xaxis.ticktext) == ["8 Jun", "9 Jun", "10 Jun", "11 Jun"]
    assert bars.customdata[0][1] == "No headache recorded"
    assert figure.layout.xaxis.tickangle == -75
    assert figure.layout.xaxis.title.text == "Calendar date"
    assert figure.layout.coloraxis.cmin == 1
    assert figure.layout.coloraxis.cmax == 10


def test_strength_and_duration_histograms_use_the_same_neutral_colour() -> None:
    entries = [SimpleNamespace(strength=6, duration_hours=Decimal("7.0"))]

    strength_figure = histogram(entries, "strength", lang="en")
    duration_figure = histogram(entries, "duration", lang="en")

    assert strength_figure.data[0].marker.color == duration_figure.data[0].marker.color


def test_strength_duration_scatter_uses_one_neutral_point_colour() -> None:
    entries = [
        SimpleNamespace(entry_date=date(2026, 6, 9), strength=1, duration_hours=Decimal("5.0")),
        SimpleNamespace(entry_date=date(2026, 6, 10), strength=10, duration_hours=Decimal("12.0")),
    ]

    figure = strength_duration_scatter(entries, lang="en")

    assert figure.data[0].marker.color == "#3f6fa8"
    assert figure.layout.coloraxis.cmin is None
    assert figure.layout.coloraxis.cmax is None
    assert figure.layout.xaxis.title.text == "Intensity from 1 to 10"
    assert list(figure.layout.xaxis.range) == [0.5, 10.5]
    assert figure.layout.xaxis.title.standoff == 18
    assert figure.layout.yaxis.title.standoff == 22


def test_monthly_metric_scatter_centres_and_symmetrically_dodges_duplicates() -> None:
    entries = [
        SimpleNamespace(entry_date=date(2026, 6, 9), strength=6, duration_hours=Decimal("5.0")),
        SimpleNamespace(entry_date=date(2026, 6, 10), strength=6, duration_hours=Decimal("7.0")),
        SimpleNamespace(entry_date=date(2026, 6, 11), strength=8, duration_hours=Decimal("9.0")),
        SimpleNamespace(entry_date=date(2026, 7, 1), strength=5, duration_hours=Decimal("4.0")),
    ]

    figure = monthly_metric_scatter(entries)
    coordinates = [
        (float(x), int(y))
        for trace in figure.data
        for x, y in zip(trace.x, trace.y, strict=True)
    ]
    june_sixes = sorted(x for x, strength in coordinates if strength == 6)

    assert june_sixes == [-0.0425, 0.0425]
    assert sum(june_sixes) == 0
    assert (0.0, 8) in coordinates
    assert (1.0, 5) in coordinates
    assert len(coordinates) == len(set(coordinates))


def test_monthly_metric_scatter_swaps_axis_and_colour_encoding() -> None:
    entries = [SimpleNamespace(entry_date=date(2026, 6, 9), strength=9, duration_hours=Decimal("12.0"))]

    strength_axis = monthly_metric_scatter(entries, y_metric="strength", lang="en")
    duration_axis = monthly_metric_scatter(entries, y_metric="duration", lang="en")

    assert strength_axis.layout.xaxis.title.text == "Month"
    assert list(strength_axis.layout.xaxis.ticktext) == ["June 2026"]
    assert list(strength_axis.data[0].y) == [9]
    assert list(strength_axis.data[0].marker.color) == [12.0]
    assert strength_axis.data[0].marker.colorbar.title.text == "Duration in hours"
    assert strength_axis.layout.yaxis.title.text == "Intensity from 1 to 10"

    assert list(duration_axis.data[0].y) == [12.0]
    assert list(duration_axis.data[0].marker.color) == [9]
    assert duration_axis.data[0].marker.cmin == 1
    assert duration_axis.data[0].marker.cmax == 10
    assert duration_axis.data[0].marker.colorbar.title.text == "Intensity from 1 to 10"
    assert duration_axis.layout.yaxis.title.text == "Duration in hours"


def test_monthly_frequency_chart_preserves_frequency_metrics() -> None:
    monthly = [
        {
            "key": "2026-06",
            "observed_days": 30,
            "headache_days": 4,
            "rate_per_30": 4.0,
            "avg_strength": 6.5,
            "avg_duration": 8.25,
            "total_duration": 33.0,
        }
    ]

    figure = monthly_frequency_chart(monthly, lang="en")

    assert len(figure.data) == 1
    assert list(figure.data[0].y) == [4]
    assert figure.data[0].customdata[0][0] == 30
    assert figure.data[0].customdata[0][1] == "4.0"


def test_context_and_weekday_charts_keep_comparison_details() -> None:
    patterns = pattern_source_chart(
        [{"label": "Sleep", "count": 2, "share": 1 / 3, "avg_strength": 6.0, "avg_duration": 8.0}],
        [{"label": "Cold", "count": 3, "share": 0.5, "avg_strength": 7.0, "avg_duration": 9.5}],
        lang="en",
    )
    weekday = weekday_rate_chart(
        [{"label": "Monday", "observed_days": 10, "headache_days": 3, "rate": 0.3}],
        lang="en",
    )

    assert [trace.name for trace in patterns.data] == ["Selected in the form", "Mentioned in the notes"]
    assert list(patterns.data[0].x) == [2]
    assert list(patterns.data[0].customdata[0]) == ["Sleep", "33%", "6.0", "8.0"]
    assert list(patterns.data[1].x) == [3]
    assert list(patterns.data[1].customdata[0]) == ["Cold", "50%", "7.0", "9.5"]
    assert list(weekday.data[0].y) == [30.0]
    assert list(weekday.data[0].customdata[0]) == [3, 10]
    assert list(weekday.data[0].text) == ["3 of 10 days"]
    assert list(weekday.layout.xaxis.ticktext) == ["Monday"]
    assert weekday.layout.yaxis.title.text == "Percentage with headache"


def test_medication_chart_preserves_all_assessment_values() -> None:
    medication = medication_effectiveness_chart(
        [{"label": "Paracetamol", "days": 4, "helped_yes": 1, "helped_partial": 1, "helped_no": 1, "avg_strength": 6.0}],
        lang="en",
    )

    assert [trace.x[0] for trace in medication.data] == [1, 1, 1, 1]
    assert medication.data[0].customdata[0][1] == 4
    assert medication.layout.xaxis.dtick == 1


def test_completeness_chart_encodes_rate_and_record_counts() -> None:
    figure = completeness_chart(
        [{"label": "Original note", "complete": 15, "total": 20, "rate": 0.75}],
        lang="en",
    )

    assert list(figure.data[0].x) == [75.0]
    assert list(figure.data[0].customdata[0]) == ["Original note", 15, 20]
    assert list(figure.data[0].text) == ["15 of 20 (75%)"]

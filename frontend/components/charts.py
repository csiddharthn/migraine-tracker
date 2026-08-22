from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Iterable, Literal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from backend.analytics.calculations import AnalyticsDataset, linear_regression
from backend.models import MigraineEntry
from frontend.i18n import current_language, format_date_value, format_number, month_label, tr


COLORS = {"teal": "#187a78", "blue": "#3f6fa8", "amber": "#c38a20", "red": "#c44747", "purple": "#7259a6"}
STRENGTH_COLORS = {
    1: "#2a9d8f",
    2: "#52a86b",
    3: "#7abf45",
    4: "#a6c63a",
    5: "#d6c635",
    6: "#e6aa2c",
    7: "#e58b32",
    8: "#d95f41",
    9: "#b9363e",
    10: "#7a1626",
}
STRENGTH_COLOR_SCALE = [
    (boundary, STRENGTH_COLORS[strength])
    for strength in range(1, 11)
    for boundary in (max(0.0, (strength - 1.5) / 9), min(1.0, (strength - 0.5) / 9))
]
DURATION_COLOR_SCALE = [(0.0, "#93c5fd"), (0.35, "#4f8fce"), (0.7, "#285b9a"), (1.0, "#17365d")]


def _style(fig: go.Figure, *, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=34, b=26),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Segoe UI, Arial", color="#1f2937"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(gridcolor="#e6ebef", zeroline=False)
    fig.update_yaxes(gridcolor="#e6ebef", zeroline=False)
    return fig


def _empty_figure(message: str, *, height: int = 330) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(color="#667085", size=14),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _style(fig, height=height)


def _wrap_label(value: str, max_chars: int = 24) -> str:
    words = value.split()
    if not words:
        return value
    lines = [words[0]]
    for word in words[1:]:
        if len(lines[-1]) + len(word) + 1 <= max_chars:
            lines[-1] += f" {word}"
        else:
            lines.append(word)
    return "<br>".join(lines)


def _clock_text(minutes: int, *, lang: str) -> str:
    day_offset, minute_of_day = divmod(minutes, 1440)
    hour, minute = divmod(minute_of_day, 60)
    clock = f"{hour:02d}:{minute:02d}"
    if day_offset == 0:
        return tr(f"{clock} Uhr", clock, lang=lang)
    return tr(f"{clock} Uhr ({day_offset} Tag später)", f"{clock} ({day_offset} day later)", lang=lang) if day_offset == 1 else tr(f"{clock} Uhr ({day_offset} Tage später)", f"{clock} ({day_offset} days later)", lang=lang)


def _clock_axis_text(hours: int, *, lang: str) -> str:
    day_offset, hour = divmod(hours, 24)
    clock = f"{hour:02d}:00"
    if day_offset == 0:
        return clock
    return tr(f"+{day_offset} T<br>{clock}", f"+{day_offset} d<br>{clock}", lang=lang)


def observation_days_bar(
    headache_days: int,
    headache_free_days: int,
    *,
    lang: str | None = None,
) -> go.Figure:
    lang = lang or current_language()
    total_days = headache_days + headache_free_days
    if total_days <= 0:
        return _empty_figure(tr("Keine Beobachtungstage vorhanden.", "No observation days are available.", lang=lang), height=210)

    segments = [
        (tr("Kopfschmerztage", "Headache days", lang=lang), headache_days, COLORS["amber"]),
        (tr("Kopfschmerzfreie Tage", "Headache-free days", lang=lang), headache_free_days, COLORS["teal"]),
    ]
    fig = go.Figure()
    for label, days, color in segments:
        share = days / total_days * 100
        fig.add_trace(
            go.Bar(
                x=[days],
                y=[tr("Beobachtungszeitraum", "Observation period", lang=lang)],
                name=label,
                orientation="h",
                marker_color=color,
                text=[f"<b>{days}</b><br>{share:.0f}%"],
                textposition="inside",
                insidetextanchor="middle",
                customdata=[[format_number(share, lang=lang)]],
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    + tr("Tage", "Days", lang=lang)
                    + ": %{x}<br>"
                    + tr("Anteil am gesamten Zeitraum", "Share of the full period", lang=lang)
                    + ": %{customdata[0]}%<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        legend_traceorder="normal",
        margin=dict(l=18, r=18, t=52, b=20),
        uniformtext=dict(minsize=11, mode="show"),
    )
    fig.update_xaxes(visible=False, range=[0, total_days], fixedrange=True)
    fig.update_yaxes(visible=False, fixedrange=True)
    fig = _style(fig, height=190)
    fig.update_layout(margin=dict(l=18, r=18, t=52, b=20))
    return fig


def monthly_metric_scatter(
    entries: Iterable[MigraineEntry],
    *,
    y_metric: Literal["strength", "duration"] = "strength",
    lang: str | None = None,
) -> go.Figure:
    lang = lang or current_language()
    entries = sorted(entries, key=lambda entry: entry.entry_date)
    if not entries:
        return _empty_figure(tr("Im gewählten Zeitraum wurden keine Kopfschmerztage eingetragen.", "No headache days were entered in the selected period.", lang=lang), height=360)
    if y_metric not in {"strength", "duration"}:
        raise ValueError(f"Unsupported monthly scatter metric: {y_metric}")
    month_keys = sorted({entry.entry_date.strftime("%Y-%m") for entry in entries})
    month_positions = {month: index for index, month in enumerate(month_keys)}
    points: list[dict] = []
    for month in month_keys:
        month_entries = [entry for entry in entries if entry.entry_date.strftime("%Y-%m") == month]
        metric_value = lambda entry: entry.strength if y_metric == "strength" else float(entry.duration_hours)
        for value in sorted({metric_value(entry) for entry in month_entries}):
            matching = [entry for entry in month_entries if metric_value(entry) == value]
            offsets = _symmetric_offsets(len(matching))
            for entry, offset in zip(matching, offsets, strict=True):
                points.append(
                    {
                        "x": month_positions[month] + offset,
                        "strength": entry.strength,
                        "duration": float(entry.duration_hours),
                        "date": format_date_value(entry.entry_date, lang=lang),
                    }
                )

    if y_metric == "strength":
        y_values = [point["strength"] for point in points]
        color_values = [point["duration"] for point in points]
        color_scale = DURATION_COLOR_SCALE
        color_min = 0
        color_max = max(1, max(color_values))
        colorbar = dict(title=tr("Dauer in Stunden", "Duration in hours", lang=lang), thickness=18)
        y_title = tr("Stärke von 1 bis 10", "Intensity from 1 to 10", lang=lang)
    else:
        y_values = [point["duration"] for point in points]
        color_values = [point["strength"] for point in points]
        color_scale = STRENGTH_COLOR_SCALE
        color_min = 1
        color_max = 10
        colorbar = _strength_colorbar(lang)
        y_title = tr("Dauer in Stunden", "Duration in hours", lang=lang)

    fig = go.Figure(
        go.Scatter(
            x=[point["x"] for point in points],
            y=y_values,
            mode="markers",
            marker=dict(
                size=10,
                color=color_values,
                colorscale=color_scale,
                cmin=color_min,
                cmax=color_max,
                colorbar=colorbar,
                line=dict(width=1, color="white"),
            ),
            showlegend=False,
            customdata=[
                [point["date"], point["strength"], format_number(point["duration"], lang=lang)]
                for point in points
            ],
            hovertemplate=(
                "%{customdata[0]}<br>"
                + tr("Stärke", "Intensity", lang=lang)
                + ": %{customdata[1]} "
                + tr("von 10", "out of 10", lang=lang)
                + "<br>"
                + tr("Dauer", "Duration", lang=lang)
                + ": %{customdata[2]} "
                + tr("Stunden", "hours", lang=lang)
                + "<extra></extra>"
            ),
        )
    )
    for position in month_positions.values():
        fig.add_vline(x=position, line_width=1, line_dash="dot", line_color="#d7e0e7", layer="below")
    fig.update_xaxes(
        tickmode="array",
        tickvals=list(month_positions.values()),
        ticktext=[month_label(month, lang=lang) for month in month_keys],
        range=[-0.45, len(month_keys) - 0.55],
        title=tr("Monat", "Month", lang=lang),
    )
    if y_metric == "strength":
        fig.update_yaxes(range=[0.5, 10.5], dtick=1, title=y_title)
    else:
        fig.update_yaxes(rangemode="tozero", title=y_title)
    return _style(fig, height=360)


def _symmetric_offsets(count: int, spacing: float = 0.085) -> list[float]:
    midpoint = (count - 1) / 2
    return [(index - midpoint) * spacing for index in range(count)]


def _strength_colorbar(lang: str) -> dict:
    return {
        "title": tr("Stärke von 1 bis 10", "Intensity from 1 to 10", lang=lang),
        "tickmode": "array",
        "tickvals": list(range(1, 11)),
        "ticktext": [str(value) for value in range(1, 11)],
        "thickness": 18,
    }


def monthly_frequency_chart(monthly: list[dict], *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    if not monthly:
        return _empty_figure(tr("Für diesen Zeitraum liegen keine Monatswerte vor.", "No monthly values are available for this period.", lang=lang))

    labels = [month_label(item["key"], lang=lang) for item in monthly]
    common = [
        [
            item["observed_days"],
            format_number(item["rate_per_30"], lang=lang),
            format_number(item["avg_strength"], lang=lang),
        ]
        for item in monthly
    ]
    fig = go.Figure(
        go.Bar(
            x=labels,
            y=[item["headache_days"] for item in monthly],
            name=tr("Kopfschmerztage", "Headache days", lang=lang),
            marker_color=COLORS["blue"],
            text=[item["headache_days"] for item in monthly],
            textposition="outside",
            cliponaxis=False,
            customdata=common,
            hovertemplate=(
                "<b>%{x}</b><br>"
                + tr("Kopfschmerztage", "Headache days", lang=lang)
                + ": %{y}<br>"
                + tr("Kalendertage in diesem Monat", "Calendar days in this month", lang=lang)
                + ": %{customdata[0]}<br>"
                + tr("Umgerechnet auf 30 Tage", "Converted to a 30-day period", lang=lang)
                + ": %{customdata[1]}<br>"
                + tr("Durchschnittliche Stärke", "Average intensity", lang=lang)
                + ": %{customdata[2]} "
                + tr("von 10", "out of 10", lang=lang)
                + "<extra></extra>"
            ),
        )
    )
    fig.update_yaxes(title_text=tr("Kopfschmerztage", "Headache days", lang=lang), dtick=1, rangemode="tozero")
    fig.update_xaxes(title_text=tr("Monat", "Month", lang=lang), type="category", categoryorder="array", categoryarray=labels)
    return _style(fig, height=360)


def rolling_line(points: list[dict], value: str, label: str, color: str = "teal", *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    if not points:
        return _empty_figure(tr("Für diesen Zeitraum liegen noch keine Verlaufswerte vor.", "No trend values are available for this period yet.", lang=lang), height=320)
    frame = pd.DataFrame(points)
    fig = px.line(frame, x="date", y=value, markers=False, labels={"date": tr("Datum", "Date", lang=lang), value: label}, color_discrete_sequence=[COLORS[color]])
    date_format = "%Y-%m-%d" if lang == "en" else "%d.%m.%Y"
    fig.update_traces(line_width=3, hovertemplate=f"%{{x|{date_format}}}<br>{label}: %{{y:.1f}}<extra></extra>")
    return _style(fig, height=320)


def strength_duration_scatter(entries: Iterable[MigraineEntry], *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    entries = list(entries)
    if not entries:
        return _empty_figure(tr("Im gewählten Zeitraum wurden keine Kopfschmerztage eingetragen.", "No headache days were entered in the selected period.", lang=lang), height=420)
    frame = pd.DataFrame(
        {
            "strength": [entry.strength for entry in entries],
            "duration": [float(entry.duration_hours) for entry in entries],
            "date": [format_date_value(entry.entry_date, lang=lang) for entry in entries],
        }
    )
    fig = px.scatter(
        frame,
        x="strength",
        y="duration",
        hover_name="date",
        custom_data=["date"],
        color_discrete_sequence=[COLORS["blue"]],
        labels={
            "strength": tr("Stärke von 1 bis 10", "Intensity from 1 to 10", lang=lang),
            "duration": tr("Dauer in Stunden", "Duration in hours", lang=lang),
        },
    )
    fig.update_traces(
        marker_size=11,
        marker_color=COLORS["blue"],
        marker_line_width=1,
        marker_line_color="white",
        hovertemplate=(
            "%{customdata[0]}<br>"
            + tr("Stärke", "Intensity", lang=lang)
            + ": %{x} "
            + tr("von 10", "out of 10", lang=lang)
            + "<br>"
            + tr("Dauer", "Duration", lang=lang)
            + ": %{y:.1f} "
            + tr("Stunden", "hours", lang=lang)
            + "<extra></extra>"
        ),
    )
    if len(frame) >= 3:
        slope, intercept = linear_regression(frame["strength"].astype(float).tolist(), frame["duration"].astype(float).tolist())
        if slope is not None and intercept is not None:
            fig.add_trace(
                go.Scatter(
                    x=[1, 10],
                    y=[slope + intercept, slope * 10 + intercept],
                    mode="lines",
                    line=dict(color="#6b7280", dash="dash"),
                    name=tr("Berechnete Trendlinie", "Calculated trend line", lang=lang),
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
    fig = _style(fig, height=420)
    fig.update_xaxes(range=[0.5, 10.5], dtick=1, title_standoff=18, automargin=True)
    fig.update_yaxes(title_standoff=22, automargin=True)
    fig.update_layout(margin=dict(l=90, r=28, t=26, b=72), showlegend=False)
    return fig


def duration_by_date_bar(
    entries: Iterable[MigraineEntry],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    lang: str | None = None,
) -> go.Figure:
    lang = lang or current_language()
    items = sorted(entries, key=lambda entry: entry.entry_date)
    if not items and (start_date is None or end_date is None):
        return _empty_figure(tr("Im gewählten Zeitraum wurden keine Kopfschmerztage eingetragen.", "No headache days were entered in the selected period.", lang=lang), height=390)
    resolved_start = start_date or items[0].entry_date
    resolved_end = end_date or items[-1].entry_date
    if resolved_end < resolved_start:
        raise ValueError("The end date must not be before the start date.")
    entries_by_date = {
        entry.entry_date: entry
        for entry in items
        if resolved_start <= entry.entry_date <= resolved_end
    }
    calendar_dates: list[date] = []
    current = resolved_start
    while current <= resolved_end:
        calendar_dates.append(current)
        current += timedelta(days=1)

    durations: list[float] = []
    strengths: list[int] = []
    statuses: list[str] = []
    for calendar_date in calendar_dates:
        entry = entries_by_date.get(calendar_date)
        if entry is None:
            durations.append(0.0)
            strengths.append(1)
            statuses.append(tr("Kein Kopfschmerz eingetragen", "No headache recorded", lang=lang))
            continue
        duration = float(entry.duration_hours)
        durations.append(duration)
        strengths.append(entry.strength)
        statuses.append(
            tr(
                f"Dauer: {format_number(duration, lang=lang)} Stunden · Stärke: {entry.strength} von 10",
                f"Duration: {format_number(duration, lang=lang)} hours · Intensity: {entry.strength} out of 10",
                lang=lang,
            )
        )
    frame = pd.DataFrame(
        {
            "date_key": [calendar_date.isoformat() for calendar_date in calendar_dates],
            "date_short": [
                calendar_date.strftime("%d.%m.")
                if lang == "de"
                else f"{calendar_date.day} {calendar.month_abbr[calendar_date.month]}"
                for calendar_date in calendar_dates
            ],
            "date_text": [format_date_value(calendar_date, lang=lang) for calendar_date in calendar_dates],
            "duration": durations,
            "strength": strengths,
            "status": statuses,
        }
    )
    fig = px.bar(
        frame,
        x="date_key",
        y="duration",
        color="strength",
        color_continuous_scale=STRENGTH_COLOR_SCALE,
        range_color=(1, 10),
        custom_data=["date_text", "status"],
    )
    fig.update_traces(
        hovertemplate="%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
        marker_line_color="white",
        marker_line_width=0.8,
    )
    date_keys = frame["date_key"].tolist()
    short_dates = frame["date_short"].tolist()
    fig.update_layout(bargap=0.22)
    fig.update_xaxes(
        title=tr("Kalendertag", "Calendar date", lang=lang),
        type="category",
        categoryorder="array",
        categoryarray=date_keys,
        tickmode="array",
        tickvals=date_keys,
        ticktext=short_dates,
        tickangle=-75,
        tickfont=dict(size=10),
        automargin=True,
    )
    fig.update_yaxes(title=tr("Dauer in Stunden", "Duration in hours", lang=lang), rangemode="tozero")
    fig.update_coloraxes(colorbar=dict(title=tr("Stärke von 1 bis 10", "Intensity from 1 to 10", lang=lang), tickvals=list(range(1, 11))))
    fig = _style(fig, height=430)
    fig.update_layout(margin=dict(l=72, r=18, t=34, b=92))
    return fig


def histogram(entries: Iterable[MigraineEntry], field: str, *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    items = list(entries)
    if not items:
        return _empty_figure(tr("Im gewählten Zeitraum wurden keine Kopfschmerztage eingetragen.", "No headache days were entered in the selected period.", lang=lang))
    if field == "strength":
        frame = pd.DataFrame({"strength": [item.strength for item in items]})
        fig = px.histogram(frame, x="strength", nbins=10, labels={"strength": tr("Stärke von 1 bis 10", "Intensity from 1 to 10", lang=lang)}, color_discrete_sequence=[COLORS["blue"]])
        fig.update_xaxes(dtick=1, range=[0.5, 10.5])
        fig.update_yaxes(title=tr("Anzahl der Kopfschmerztage", "Number of headache days", lang=lang))
    else:
        frame = pd.DataFrame({"duration": [float(item.duration_hours) for item in items]})
        fig = px.histogram(frame, x="duration", nbins=min(12, max(4, len(items) // 2)), labels={"duration": tr("Dauer in Stunden", "Duration in hours", lang=lang)}, color_discrete_sequence=[COLORS["blue"]])
        fig.update_yaxes(title=tr("Anzahl der Kopfschmerztage", "Number of headache days", lang=lang))
    return _style(fig, height=330)


def horizontal_bar(items: list[dict], *, value: str = "count", label: str = "label", color: str = "teal", height: int | None = None, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    frame = pd.DataFrame(items).sort_values(value, ascending=True) if items else pd.DataFrame({label: [], value: []})
    raw_labels = frame[label].astype(str).tolist()
    fig = go.Figure(
        go.Bar(
            x=frame[value].tolist(),
            y=[_wrap_label(item) for item in raw_labels],
            orientation="h",
            text=frame[value].tolist(),
            marker_color=COLORS[color],
            textposition="outside",
            cliponaxis=False,
            customdata=[[item] for item in raw_labels],
            hovertemplate=f"<b>%{{customdata[0]}}</b><br>{tr('Kopfschmerztage', 'Headache days', lang=lang)}: %{{x}}<extra></extra>",
        )
    )
    fig.update_xaxes(nticks=6, tickformat="d", rangemode="tozero", title=tr("Anzahl der Kopfschmerztage", "Number of headache days", lang=lang))
    fig.update_yaxes(title="")
    return _style(fig, height=height or max(280, 44 * max(1, len(frame)) + 80))


def pattern_source_chart(trigger_items: list[dict], context_items: list[dict], *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    if not trigger_items and not context_items:
        return _empty_figure(tr("Im gewählten Zeitraum wurden keine möglichen Auslöser oder Begleitumstände eingetragen.", "No possible triggers or accompanying circumstances were entered in the selected period.", lang=lang), height=360)

    totals: dict[str, int] = {}
    for item in [*trigger_items, *context_items]:
        totals[item["label"]] = totals.get(item["label"], 0) + item["count"]
    labels = sorted(totals, key=lambda label: (totals[label], label))
    display_labels = {label: _wrap_label(label) for label in labels}

    fig = go.Figure()
    sources = (
        (trigger_items, tr("Im Formular ausgewählt", "Selected in the form", lang=lang), COLORS["teal"]),
        (context_items, tr("In den Notizen erwähnt", "Mentioned in the notes", lang=lang), COLORS["blue"]),
    )
    for items, source_label, color in sources:
        if not items:
            continue
        ordered = sorted(items, key=lambda item: labels.index(item["label"]))
        customdata = [
            [
                item["label"],
                f"{item['share']:.0%}",
                format_number(item["avg_strength"], lang=lang),
                format_number(item["avg_duration"], lang=lang),
            ]
            for item in ordered
        ]
        fig.add_trace(
            go.Bar(
                x=[item["count"] for item in ordered],
                y=[display_labels[item["label"]] for item in ordered],
                orientation="h",
                name=source_label,
                marker_color=color,
                text=[item["count"] for item in ordered],
                textposition="outside",
                cliponaxis=False,
                customdata=customdata,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    + source_label
                    + "<br>"
                    + tr("Kopfschmerztage", "Headache days", lang=lang)
                    + ": %{x}<br>"
                    + tr("Anteil aller Kopfschmerztage", "Share of all headache days", lang=lang)
                    + ": %{customdata[1]}<br>"
                    + tr("Durchschnittliche Stärke", "Average intensity", lang=lang)
                    + ": %{customdata[2]} "
                    + tr("von 10", "out of 10", lang=lang)
                    + "<br>"
                    + tr("Durchschnittliche Dauer", "Average duration", lang=lang)
                    + ": %{customdata[3]} "
                    + tr("Stunden", "hours", lang=lang)
                    + "<extra></extra>"
                ),
            )
        )
    fig.update_layout(barmode="group", legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
    fig.update_xaxes(nticks=6, tickformat="d", rangemode="tozero", title=tr("Anzahl der Kopfschmerztage", "Number of headache days", lang=lang))
    fig.update_yaxes(title="", categoryorder="array", categoryarray=[display_labels[label] for label in labels])
    return _style(fig, height=max(390, 48 * len(labels) + 130))


def weekday_rate_chart(items: list[dict], *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    if not items:
        return _empty_figure(tr("Keine Wochentagswerte vorhanden.", "No weekday values are available.", lang=lang))
    rates = [item["rate"] * 100 for item in items]
    maximum = max(rates, default=0)
    fig = go.Figure(
        go.Bar(
            x=[item["label"] for item in items],
            y=rates,
            marker_color=COLORS["blue"],
            text=[
                tr(
                    f"{item['headache_days']} von {item['observed_days']} Tagen",
                    f"{item['headache_days']} of {item['observed_days']} days",
                    lang=lang,
                )
                for item in items
            ],
            textposition="outside",
            cliponaxis=False,
            customdata=[[item["headache_days"], item["observed_days"]] for item in items],
            hovertemplate=(
                "<b>%{x}</b><br>"
                + tr("Kopfschmerzen an", "Headache on", lang=lang)
                + ": %{customdata[0]} "
                + tr("von", "of", lang=lang)
                + " %{customdata[1]} "
                + tr("Tagen", "days", lang=lang)
                + "<br>"
                + tr("Anteil", "Share", lang=lang)
                + ": %{y:.0f}%<extra></extra>"
            ),
        )
    )
    weekday_labels = [item["label"] for item in items]
    fig.update_xaxes(
        title=tr("Wochentag", "Weekday", lang=lang),
        tickmode="array",
        tickvals=weekday_labels,
        ticktext=weekday_labels,
        tickangle=-25,
    )
    fig.update_yaxes(title=tr("Anteil mit Kopfschmerzen", "Percentage with headache", lang=lang), ticksuffix="%", range=[0, min(100, max(10, maximum * 1.28))])
    return _style(fig, height=340)


def medication_effectiveness_chart(items: list[dict], *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    if not items:
        return _empty_figure(tr("Keine Akutmedikation dokumentiert.", "No acute medication is documented.", lang=lang))
    ordered = sorted(items, key=lambda item: (item["days"], item["label"]))
    labels = [item["label"] for item in ordered]
    display_labels = [_wrap_label(label) for label in labels]
    responses = (
        ("helped_yes", tr("Hat geholfen", "Helped", lang=lang), COLORS["teal"]),
        ("helped_partial", tr("Hat teilweise geholfen", "Helped partly", lang=lang), COLORS["amber"]),
        ("helped_no", tr("Hat nicht geholfen", "Did not help", lang=lang), COLORS["red"]),
        ("undocumented", tr("Wirkung nicht eingetragen", "Effect not entered", lang=lang), "#a5adb8"),
    )
    fig = go.Figure()
    for key, response_label, color in responses:
        values = [
            item["days"] - item["helped_yes"] - item["helped_partial"] - item["helped_no"]
            if key == "undocumented"
            else item[key]
            for item in ordered
        ]
        fig.add_trace(
            go.Bar(
                x=values,
                y=display_labels,
                orientation="h",
                name=response_label,
                marker_color=color,
                text=[value if value else "" for value in values],
                textposition="inside",
                customdata=[[item["label"], item["days"], format_number(item["avg_strength"], lang=lang)] for item in ordered],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    + tr("Tage mit dieser Bewertung", "Days with this assessment", lang=lang)
                    + ": %{x}<br>"
                    + tr("Tage mit dieser Medikation", "Days with this medication", lang=lang)
                    + ": %{customdata[1]}<br>"
                    + tr("Durchschnittliche Stärke an diesen Tagen", "Average intensity on these days", lang=lang)
                    + ": %{customdata[2]} "
                    + tr("von 10", "out of 10", lang=lang)
                    + "<extra></extra>"
                ),
            )
        )
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    fig.update_xaxes(dtick=1, tickformat="d", title=tr("Tage mit Akutmedikation", "Days with acute medication", lang=lang), rangemode="tozero")
    fig.update_yaxes(title="", categoryorder="array", categoryarray=display_labels)
    return _style(fig, height=max(320, 46 * len(ordered) + 130))


def completeness_chart(items: list[dict], *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    if not items:
        return _empty_figure(tr("Keine Vollständigkeitswerte vorhanden.", "No completeness values are available.", lang=lang))
    ordered = list(reversed(items))
    rates = [item["rate"] * 100 for item in ordered]
    colors = [COLORS["teal"] if rate >= 80 else COLORS["amber"] if rate >= 50 else COLORS["red"] for rate in rates]
    fig = go.Figure(
        go.Bar(
            x=rates,
            y=[_wrap_label(item["label"]) for item in ordered],
            orientation="h",
            text=[
                tr(
                    f'{item["complete"]} von {item["total"]} ({rate:.0f}%)',
                    f'{item["complete"]} of {item["total"]} ({rate:.0f}%)',
                    lang=lang,
                )
                for item, rate in zip(ordered, rates, strict=True)
            ],
            textposition="inside",
            marker_color=colors,
            customdata=[[item["label"], item["complete"], item["total"]] for item in ordered],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                + tr("Ausgefüllt bei", "Completed for", lang=lang)
                + ": %{customdata[1]} "
                + tr("von", "of", lang=lang)
                + " %{customdata[2]} "
                + tr("relevanten Einträgen", "relevant entries", lang=lang)
                + "<br>"
                + tr("Anteil", "Share", lang=lang)
                + ": %{x:.0f}%<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(title=tr("Anteil der ausgefüllten Angaben", "Share of completed information", lang=lang), ticksuffix="%", range=[0, 100])
    fig.update_yaxes(title="")
    return _style(fig, height=max(370, 46 * len(ordered) + 100))


def attack_timeline(data: AnalyticsDataset, month_key: str, *, lang: str | None = None) -> go.Figure:
    lang = lang or current_language()
    year, month = (int(part) for part in month_key.split("-"))
    first = max(data.first_day, date(year, month, 1))
    last = min(data.analysis_end, date(year, month, calendar.monthrange(year, month)[1]))
    entries = {entry.entry_date: entry for entry in data.entries}
    days = []
    current = first
    while current <= last:
        days.append(current)
        current += timedelta(days=1)
    labels = [format_date_value(day, lang=lang) for day in sorted(days, reverse=True)]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[0] * len(labels),
            y=labels,
            mode="markers",
            marker=dict(opacity=0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    colorbar_added = False
    peak_legend_added = False
    for day in sorted(days, reverse=True):
        entry = entries.get(day)
        if entry is None or entry.interpretation is None:
            continue
        onset_minute = entry.interpretation.onset_minute
        end_minute = entry.interpretation.end_minute
        end_was_calculated = False
        if onset_minute is not None and end_minute is None and float(entry.duration_hours) > 0:
            end_minute = onset_minute + int(round(float(entry.duration_hours) * 60))
            end_was_calculated = True
        if onset_minute is not None and end_minute is not None:
            start = onset_minute / 60
            duration = max(0.15, (end_minute - onset_minute) / 60)
            end_text = _clock_text(end_minute, lang=lang)
            if end_was_calculated:
                end_text += tr(" (aus der eingetragenen Dauer berechnet)", " (calculated from recorded duration)", lang=lang)
            fig.add_trace(
                go.Bar(
                    x=[duration],
                    y=[format_date_value(day, lang=lang)],
                    base=[start],
                    width=[0.72],
                    orientation="h",
                    marker=dict(
                        color=[entry.strength],
                        colorscale=STRENGTH_COLOR_SCALE,
                        cmin=1,
                        cmax=10,
                        showscale=not colorbar_added,
                        colorbar=_strength_colorbar(lang),
                    ),
                    showlegend=False,
                    customdata=[
                        [
                            entry.strength,
                            format_number(float(entry.duration_hours), lang=lang),
                            _clock_text(onset_minute, lang=lang),
                            end_text,
                        ]
                    ],
                    hovertemplate=(
                        tr("Stärke", "Intensity", lang=lang)
                        + ": %{customdata[0]} "
                        + tr("von 10", "out of 10", lang=lang)
                        + "<br>"
                        + tr("Eingetragene Dauer", "Recorded duration", lang=lang)
                        + ": %{customdata[1]} "
                        + tr("Stunden", "hours", lang=lang)
                        + "<br>"
                        + tr("Beginn", "Onset", lang=lang)
                        + ": %{customdata[2]}<br>"
                        + tr("Ende", "End", lang=lang)
                        + ": %{customdata[3]}<extra></extra>"
                    ),
                )
            )
            colorbar_added = True
        peak = entry.interpretation.peak_start_minute
        if peak is not None:
            fig.add_trace(
                go.Scatter(
                    x=[peak / 60],
                    y=[format_date_value(day, lang=lang)],
                    mode="markers",
                    marker=dict(
                        color=COLORS["purple"],
                        symbol="line-ns",
                        size=20,
                        line=dict(width=3, color=COLORS["purple"]),
                    ),
                    name=tr("Höhepunkt", "Peak", lang=lang),
                    legendgroup="peak",
                    showlegend=not peak_legend_added,
                    customdata=[[_clock_text(peak, lang=lang)]],
                    hovertemplate=tr("Höhepunkt", "Peak", lang=lang) + ": %{customdata[0]}<extra></extra>",
                )
            )
            peak_legend_added = True
    fig.update_layout(
        barmode="overlay",
        bargap=0.18,
        legend=dict(orientation="h", x=0, xanchor="left", y=1.06, yanchor="bottom"),
    )
    fig.update_yaxes(
        type="category",
        categoryorder="array",
        categoryarray=labels,
        autorange="reversed",
        tickmode="array",
        tickvals=labels,
        ticktext=labels,
        tickfont=dict(size=10),
        showgrid=True,
        gridcolor="#e7ebf0",
        title="",
        automargin=True,
    )
    tick_values = [0, 12, 24, 36]
    fig.update_xaxes(
        range=[0, 36],
        tickmode="array",
        tickvals=tick_values,
        ticktext=[_clock_axis_text(value, lang=lang) for value in tick_values],
        tickangle=0,
        tickfont=dict(size=10),
        automargin=True,
        title=tr("Uhrzeit", "Time", lang=lang),
    )
    fig = _style(fig, height=max(520, min(1250, 34 * len(labels) + 150)))
    fig.update_layout(margin=dict(l=92, r=32, t=64, b=64))
    return fig

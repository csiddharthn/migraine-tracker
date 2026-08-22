from __future__ import annotations

"""Purpose: Strength and duration page showing intensity metrics.

Usage: Displays scatter plots, histograms, and correlation summaries.

Functions available:
- None (page script)

Classes available:
- None

Call hierarchy:
- strength_duration.py -> backend.analytics.calculations, frontend.components
"""

from datetime import date

import streamlit as st

from backend.analytics.calculations import correlation_summary
from frontend.components.charts import duration_by_date_bar, histogram, monthly_metric_scatter, strength_duration_scatter
from frontend.components.filters import latest_month_range
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, format_decimal, page_header, scrollable_plotly_chart
from frontend.config.name_space import cfg
from frontend.i18n import date_input_format, tr
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(
    tr(cfg, "Stärke und Dauer", "Intensity and duration"),
    tr(cfg, "Wie stark die Kopfschmerzen waren, wie lange sie dauerten und ob beides zusammenhing.", "How intense the headaches were, how long they lasted, and whether the two were related."),
)

with database_session() as session:
    data = filtered_dataset(session)
    correlation = correlation_summary(data.entries)

    st.subheader(tr(cfg, "Stärke und Dauer nach Monat", "Intensity and duration by month"))
    y_metric = st.segmented_control(
        tr(cfg, "Was soll die Höhe der Punkte zeigen?", "What should the height of the points show?"),
        ["strength", "duration"],
        default="strength",
        required=True,
        format_func=lambda value: tr(cfg, "Stärke", "Intensity") if value == "strength" else tr(cfg, "Dauer", "Duration"),
        key="strength_duration_y_metric",
    ) or "strength"
    st.caption(
        tr(cfg, 
            f"Jeder Punkt steht für einen Kopfschmerztag. Angezeigt werden {len(data.entries)} Kopfschmerztage. Wenn die Höhe die Stärke zeigt, steht die Farbe für die Dauer – und umgekehrt.",
            f"Each point represents one headache day. {len(data.entries)} headache days are shown. When height shows intensity, colour shows duration, and vice versa.",
        )
    )
    st.plotly_chart(monthly_metric_scatter(data.entries, y_metric=y_metric), width="stretch", config=chart_config())

    st.subheader(tr(cfg, "Dauer der Kopfschmerzen nach Kalendertag", "Headache duration by calendar date"))
    default_chart_period = latest_month_range(
        (entry.entry_date for entry in data.entries),
        data.first_day,
        data.analysis_end,
    )
    selected_chart_period = st.date_input(
        tr(cfg, "Zeitraum für dieses Diagramm", "Date range for this chart"),
        value=default_chart_period,
        min_value=data.first_day,
        max_value=data.analysis_end,
        format=date_input_format(cfg, ),
        key=(
            f"duration_chart_period_{st.session_state.get('active_user_id')}_"
            f"{data.first_day.isoformat()}_{data.analysis_end.isoformat()}_{default_chart_period[1].isoformat()}"
        ),
    )
    if (
        isinstance(selected_chart_period, (tuple, list))
        and len(selected_chart_period) == 2
        and all(isinstance(value, date) for value in selected_chart_period)
    ):
        chart_start, chart_end = selected_chart_period
    else:
        chart_start, chart_end = default_chart_period
    chart_entries = tuple(entry for entry in data.entries if chart_start <= entry.entry_date <= chart_end)
    chart_days = (chart_end - chart_start).days + 1
    st.caption(
        tr(cfg, 
            f"Die x-Achse zeigt alle {chart_days} Kalendertage im gewählten Zeitraum. Tage ohne Balken sind kopfschmerzfrei. Die Balkenhöhe zeigt die Dauer, die Farbe die Stärke von 1 bis 10.",
            f"The x-axis shows all {chart_days} calendar days in the selected range. Days without a bar are headache-free. Bar height shows duration and colour shows intensity from 1 to 10.",
        )
    )
    scrollable_plotly_chart(
        duration_by_date_bar(chart_entries, start_date=chart_start, end_date=chart_end),
        width=max(1000, chart_days * 30),
    )

    left, right = st.columns(2)
    with left:
        st.subheader(tr(cfg, "Wie häufig kam welche Stärke vor?", "How often did each intensity occur?"))
        st.plotly_chart(histogram(data.entries, "strength"), width="stretch", config=chart_config())
    with right:
        st.subheader(tr(cfg, "Wie lange dauerten die Kopfschmerzen?", "How long did the headaches last?"))
        st.plotly_chart(histogram(data.entries, "duration"), width="stretch", config=chart_config())

    st.subheader(tr(cfg, "Dauerten stärkere Kopfschmerzen länger?", "Did more intense headaches last longer?"))
    coefficient = correlation["spearman"]
    if correlation["n"] < 2 or coefficient is None:
        correlation_text = tr(cfg, 
            "Für diese Auswertung sind noch nicht genügend Kopfschmerztage vorhanden.",
            "There are not yet enough headache days for this comparison.",
        )
    else:
        strength = abs(float(coefficient))
        if strength < 0.2:
            interpretation = tr(cfg, "Es ist kein klares gemeinsames Muster zu erkennen.", "There is no clear shared pattern.")
        elif coefficient > 0 and strength < 0.5:
            interpretation = tr(cfg, "Stärkere Kopfschmerzen dauerten tendenziell etwas länger.", "More intense headaches tended to last somewhat longer.")
        elif coefficient > 0:
            interpretation = tr(cfg, "Stärkere Kopfschmerzen dauerten meist länger.", "More intense headaches usually lasted longer.")
        elif strength < 0.5:
            interpretation = tr(cfg, "Stärkere Kopfschmerzen dauerten tendenziell etwas kürzer.", "More intense headaches tended to be somewhat shorter.")
        else:
            interpretation = tr(cfg, "Stärkere Kopfschmerzen dauerten meist kürzer.", "More intense headaches usually lasted less time.")
        correlation_text = tr(cfg, 
            f"{interpretation} Grundlage sind {correlation['n']} Kopfschmerztage. Der berechnete Zusammenhang beträgt {format_decimal(coefficient, 2)} auf einer Skala von −1 bis +1; Werte nahe 0 bedeuten wenig Zusammenhang. Die gestrichelte Linie fasst die Richtung zusammen, beweist aber keine Ursache.",
            f"{interpretation} This is based on {correlation['n']} headache days. The calculated relationship is {format_decimal(coefficient, 2)} on a scale from −1 to +1; values near 0 mean little relationship. The dashed line summarises the direction but does not prove causation.",
    )
    st.caption(correlation_text)
    scrollable_plotly_chart(strength_duration_scatter(data.entries))
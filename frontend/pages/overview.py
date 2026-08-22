from __future__ import annotations

import streamlit as st

from backend.analytics.calculations import summary_stats
from frontend.components.charts import observation_days_bar
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, format_decimal, page_header
from frontend.i18n import tr
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(tr("Übersicht", "Overview"), tr("Die wichtigsten Zahlen für den ausgewählten Zeitraum.", "The key figures for the selected period."))

try:
    with database_session() as session:
        data = filtered_dataset(session)
        stats = summary_stats(data)
        st.subheader(
            tr(
                f'Beobachtungstage: {stats["period_days"]} insgesamt',
                f'Observation days: {stats["period_days"]} total',
            )
        )
        st.plotly_chart(
            observation_days_bar(stats["headache_days"], stats["headache_free_days"]),
            width="stretch",
            config=chart_config(),
        )
        st.caption(
            tr(
                f'Umgerechnet auf 30 Tage: {format_decimal(stats["rate_per_30"])} Kopfschmerztage. Längste Zeit ohne Kopfschmerzen: {stats["longest_headache_free_streak"]} Tage am Stück.',
                f'Converted to a 30-day period: {format_decimal(stats["rate_per_30"])} headache days. Longest time without a headache: {stats["longest_headache_free_streak"]} consecutive days.',
            )
        )

        metrics = st.columns(4)
        metrics[0].metric(tr("Durchschnittliche Stärke", "Average intensity"), f'{format_decimal(stats["avg_strength"])} {tr("von 10", "out of 10")}')
        metrics[0].caption(tr(f'Mittlerer Wert (Median): {format_decimal(stats["median_strength"])} von 10', f'Middle value (median): {format_decimal(stats["median_strength"])} out of 10'))
        metrics[1].metric(tr("Durchschnittliche Dauer", "Average duration"), f'{format_decimal(stats["avg_duration"])} {tr("Stunden", "hours")}')
        metrics[1].caption(tr(f'Summe aller eingetragenen Kopfschmerzdauern: {format_decimal(stats["total_duration"], 0)} Stunden', f'Total of all recorded headache durations: {format_decimal(stats["total_duration"], 0)} hours'))
        metrics[2].metric(tr("Im Durchschnitt ein Kopfschmerztag alle", "On average, one headache day every"), f'{format_decimal(stats["days_per_headache"])} {tr("Tage", "days")}')
        metrics[3].metric(tr("Kopfschmerztage mit Stärke 8 bis 10", "Headache days with intensity 8 to 10"), stats["intensity_8_to_10_days"])
except Exception as exc:
    st.error(tr(f"Die PostgreSQL-Datenbank ist nicht erreichbar oder noch nicht eingerichtet: {exc}", f"The PostgreSQL database is unavailable or has not been set up yet: {exc}"))
    st.info(tr("Bitte führen Sie die in der README beschriebenen Schritte für PostgreSQL, Alembic und den einmaligen Excel-Import aus.", "Follow the README steps for PostgreSQL, Alembic, and the one-time Excel import."))

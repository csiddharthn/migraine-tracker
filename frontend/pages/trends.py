from __future__ import annotations

"""Purpose: Trends page showing frequency over time.

Usage: Displays monthly summaries, rolling intervals, and weekday rates.

Functions available:
- None (page script)

Classes available:
- None

Call hierarchy:
- trends.py -> backend.analytics.calculations, frontend.components
"""

import streamlit as st

from backend.analytics.calculations import monthly_summaries, rolling_interval, weekday_summary
from frontend.components.charts import monthly_frequency_chart, rolling_line, weekday_rate_chart
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, page_header
from frontend.config.name_space import cfg
from frontend.i18n import localize_items, tr
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(tr(cfg, "Häufigkeit im Zeitverlauf", "Frequency over time"), tr(cfg, "Wie oft Kopfschmerzen im ausgewählten Zeitraum auftraten.", "How often headaches occurred during the selected period."))

with database_session() as session:
    data = filtered_dataset(session)
    monthly = monthly_summaries(data)

    st.subheader(tr(cfg, "Kopfschmerztage je Monat", "Headache days per month"))
    st.plotly_chart(monthly_frequency_chart(monthly), width="stretch", config=chart_config())

    st.subheader(tr(cfg, "Durchschnittlicher Abstand zwischen Kopfschmerztagen", "Average gap between headache days"))
    st.caption(tr(cfg, "Für jeden Tag wird der Durchschnitt aus den vorherigen 28 Tagen berechnet. Ein kleinerer Abstand bedeutet, dass Kopfschmerzen häufiger auftraten.", "For each day, the average is calculated from the previous 28 days. A smaller gap means headaches occurred more often."))
    st.plotly_chart(rolling_line(rolling_interval(data, 28), "days_per_headache", tr(cfg, "Durchschnittlicher Abstand in Tagen", "Average gap in days"), "purple"), width="stretch", config=chart_config())

    st.subheader(tr(cfg, "An welchen Wochentagen traten Kopfschmerzen auf?", "On which weekdays did headaches occur?"))
    st.caption(tr(cfg, "Die Beschriftung „4 von 10 Tagen“ bedeutet zum Beispiel: An 4 der 10 beobachteten Dienstage wurden Kopfschmerzen eingetragen.", "For example, “4 of 10 days” means that headaches were entered on 4 of the 10 observed Tuesdays."))
    st.plotly_chart(weekday_rate_chart(localize_items(cfg, weekday_summary(data))), width="stretch", config=chart_config())
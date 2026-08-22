from __future__ import annotations

import streamlit as st

from backend.analytics.calculations import monthly_summaries, onset_summary
from frontend.components.charts import attack_timeline, horizontal_bar
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, page_header
from frontend.i18n import localize_items, month_label, tr
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(tr("Tagesverlauf der Kopfschmerzen", "Timing of headaches"), tr("Wann die Kopfschmerzen an jedem Tag begannen, am stärksten waren und endeten.", "When the headache began, was strongest, and ended on each day."))

with database_session() as session:
    data = filtered_dataset(session)
    months = monthly_summaries(data)
    month_keys = [item["key"] for item in months]
    month_key = st.selectbox(tr("Angezeigter Monat", "Month shown"), list(reversed(month_keys)), index=0, format_func=month_label)
    st.plotly_chart(attack_timeline(data, month_key), width="stretch", config=chart_config())

    st.subheader(tr("Zu welcher Tageszeit begannen die Kopfschmerzen?", "At what time of day did the headaches begin?"))
    month_entries = [entry for entry in data.entries if entry.entry_date.strftime("%Y-%m") == month_key]
    st.plotly_chart(horizontal_bar(localize_items(onset_summary(month_entries)), height=300), width="stretch", config=chart_config())

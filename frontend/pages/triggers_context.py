from __future__ import annotations

import streamlit as st

from backend.analytics.calculations import context_summary, trigger_summary
from frontend.components.charts import pattern_source_chart
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, page_header
from frontend.config.name_space import cfg
from frontend.i18n import localize_items, tr, trigger_label
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(
    tr(cfg, "Mögliche Auslöser", "Possible triggers"),
    tr(cfg, "Welche Auslöser ausgewählt oder in den Notizen erwähnt wurden.", "Which possible triggers were selected or mentioned in the notes."),
)

with database_session() as session:
    data = filtered_dataset(session)
    trigger_items = trigger_summary(data.entries)
    for item in trigger_items:
        item["label"] = trigger_label(cfg, item["code"], item["label"])
    total_entries = max(1, len(data.entries))
    for item in trigger_items:
        item["share"] = item["count"] / total_entries
    contexts = localize_items(cfg, context_summary(data.entries))

    st.subheader(tr(cfg, "Welche möglichen Auslöser wurden am häufigsten genannt?", "Which possible triggers were mentioned most often?"))
    st.caption(tr(cfg, "Die Grafik unterscheidet zwischen Auslösern, die im Formular ausgewählt wurden, und Begleitumständen, die im Notiztext erwähnt wurden. Eine häufige Nennung bedeutet nicht automatisch, dass dieser Umstand die Kopfschmerzen verursacht hat.", "The chart distinguishes between triggers selected in the form and circumstances mentioned in the notes. Frequent mention does not automatically mean that the circumstance caused the headaches."))
    st.plotly_chart(pattern_source_chart(trigger_items, contexts), width="stretch", config=chart_config())
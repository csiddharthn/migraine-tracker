from __future__ import annotations

"""Purpose: Pain symptoms page showing laterality and symptoms.

Usage: Displays charts for pain side, type, and associated symptoms.

Functions available:
- None (page script)

Classes available:
- None

Call hierarchy:
- pain_symptoms.py -> backend.analytics.calculations, frontend.components
"""

import streamlit as st

from backend.analytics.calculations import laterality_summary, pain_type_summary, symptom_summary
from frontend.components.charts import horizontal_bar
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, page_header
from frontend.config.name_space import cfg
from frontend.i18n import aura_label, localize_items, other_symptom_label, tr
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(tr(cfg, "Schmerzart und Symptome", "Pain characteristics and symptoms"), tr(cfg, "Wo und wie der Schmerz auftrat und welche weiteren Symptome dazukamen.", "Where and how the pain occurred and which other symptoms accompanied it."))

with database_session() as session:
    data = filtered_dataset(session)
    left, right = st.columns(2)
    with left:
        st.subheader(tr(cfg, "Schmerzseite", "Side of pain"))
        st.caption(tr(cfg, "Wenn in der Notiz eine Schmerzseite genannt und geprüft wurde, wird diese verwendet. Andernfalls gilt die Auswahl aus dem Eingabeformular.", "If a side was mentioned in the note and reviewed, it is used here. Otherwise, the selection from the entry form is used."))
        st.plotly_chart(horizontal_bar(localize_items(cfg, laterality_summary(data.entries)), color="teal", height=330), width="stretch", config=chart_config())
    with right:
        st.subheader(tr(cfg, "Schmerzart", "Pain type"))
        st.plotly_chart(horizontal_bar(localize_items(cfg, pain_type_summary(data.entries)), color="amber", height=330), width="stretch", config=chart_config())

    st.subheader(tr(cfg, "Begleitsymptome und Aura", "Associated symptoms and aura"))
    symptoms = localize_items(cfg, symptom_summary(data.entries))
    for item in symptoms:
        if item["label"].startswith("Vorboten: "):
            code = item["label"].removeprefix("Vorboten: ")
            item["label"] = f"{tr(cfg, 'Vorboten / Aura', 'Aura')}: {aura_label(cfg, code)}"
        elif item["label"].startswith("Andere Symptome: "):
            code = item["label"].removeprefix("Andere Symptome: ")
            item["label"] = f"{tr(cfg, 'Andere Symptome', 'Other symptoms')}: {other_symptom_label(cfg, code)}"
    if symptoms:
        st.plotly_chart(horizontal_bar(symptoms, color="blue"), width="stretch", config=chart_config())
    else:
        st.info(tr(cfg, "Im gewählten Zeitraum sind keine Begleitsymptome dokumentiert.", "No associated symptoms are documented in the selected period."))
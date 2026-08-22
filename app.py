from __future__ import annotations

from pathlib import Path

import streamlit as st

from frontend.components.filters import render_report_period
from frontend.components.state import database_session
from frontend.components.users import render_user_settings
from frontend.config.name_space import cfg
from frontend.i18n import LANGUAGE_LABELS, tr


ROOT = Path(__file__).resolve().parent
ICON = ROOT / "assets" / "migraine_headache_icon.png"
if st.session_state.get("app_language") not in LANGUAGE_LABELS:
    st.session_state["app_language"] = "de"

st.set_page_config(
    page_title=tr(cfg, "Kopfschmerz-Tracker", "Headache Tracker"),
    page_icon=str(ICON),
    layout="wide",
    initial_sidebar_state="auto",
)

page_sections = [
    (
        tr(cfg, "Verlauf und Muster", "Trends and patterns"),
        [
            ("frontend/pages/overview.py", tr(cfg, "Übersicht", "Overview"), ":material/dashboard:", True),
            ("frontend/pages/trends.py", tr(cfg, "Häufigkeit im Zeitverlauf", "Frequency over time"), ":material/show_chart:", False),
            ("frontend/pages/attack_timeline.py", tr(cfg, "Tagesverlauf der Kopfschmerzen", "Timing of headaches"), ":material/timeline:", False),
        ],
    ),
    (
        tr(cfg, "Merkmale und Behandlung", "Characteristics and treatment"),
        [
            ("frontend/pages/strength_duration.py", tr(cfg, "Stärke und Dauer", "Intensity and duration"), ":material/scatter_plot:", False),
            ("frontend/pages/triggers_context.py", tr(cfg, "Mögliche Auslöser", "Possible triggers"), ":material/psychology:", False),
            ("frontend/pages/pain_symptoms.py", tr(cfg, "Schmerzart und Symptome", "Pain characteristics and symptoms"), ":material/neurology:", False),
            ("frontend/pages/medication.py", tr(cfg, "Medikamente und Behandlung", "Medication and treatment"), ":material/medication:", False),
        ],
    ),
    (
        tr(cfg, "Einträge und Daten", "Entries and data"),
        [
            ("frontend/pages/entries.py", tr(cfg, "Einträge", "Entries"), ":material/edit_note:", False),
            ("frontend/pages/database.py", tr(cfg, "Gespeicherte Daten", "Stored data"), ":material/database:", False),
            ("frontend/pages/data_quality.py", tr(cfg, "Datenprüfung und Berechnung", "Data checks and calculations"), ":material/fact_check:", False),
        ],
    ),
]
page_specs = [spec for _, section_specs in page_sections for spec in section_specs]
pages_by_path = {
    path: st.Page(path, title=title, icon=icon, default=default)
    for path, title, icon, default in page_specs
}
pages = list(pages_by_path.values())
navigation = st.navigation(pages, position="hidden")

with st.sidebar:
    st.segmented_control(
        "Sprache / Language",
        options=list(LANGUAGE_LABELS),
        format_func=LANGUAGE_LABELS.get,
        key="app_language",
        width="stretch",
    )

try:
    with database_session() as session:
        active_user = render_user_settings(session)
        render_report_period(active_user)
except Exception as exc:
    st.sidebar.error(tr(cfg, f"Die PostgreSQL-Datenbank ist nicht erreichbar: {exc}", f"The PostgreSQL database is unavailable: {exc}"))
    st.stop()

with st.sidebar:
    st.divider()
    for section_title, section_specs in page_sections:
        st.caption(section_title)
        for path, title, icon, _ in section_specs:
            st.page_link(pages_by_path[path], label=title, icon=icon, width="stretch")

navigation.run()
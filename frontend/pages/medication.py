from __future__ import annotations

from collections import Counter

import streamlit as st

from backend.analytics.calculations import medication_summary
from frontend.components.charts import medication_effectiveness_chart
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, page_header
from frontend.config.name_space import cfg
from frontend.i18n import tr
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(
    tr(cfg, "Medikamente und Behandlung", "Medication and treatment"),
    tr(cfg, 
        "Welche Medikamente dokumentiert wurden, ob die Akutmedikation half und wie häufig Medikamente eingesetzt wurden.",
        "Which medications were recorded, whether acute medication helped, and how often medications were used.",
    ),
)

with database_session() as session:
    data = filtered_dataset(session)
    daily = data.daily_records
    overview = st.columns(3)
    overview[0].metric(tr(cfg, "Tage mit Momeallerg", "Days with Momeallerg"), sum(record.momeallerg_nasal_spray for record in daily))
    overview[1].metric(tr(cfg, "Tage mit Amitriptylin", "Days with amitriptyline"), sum(record.amitriptyline_neuraxpharm for record in daily))
    overview[2].metric(tr(cfg, "Dokumentierte Aimovig-Injektionen", "Recorded Aimovig injections"), sum(record.aimovig_injection for record in daily))

    st.subheader(tr(cfg, "Hat die Akutmedikation geholfen?", "Did the acute medication help?"))
    medications = medication_summary(data.entries)
    st.plotly_chart(medication_effectiveness_chart(medications), width="stretch", config=chart_config())

    st.subheader(tr(cfg, "Hinweis zur häufigen Einnahme von Akutmedikamenten", "Guidance on frequent use of acute medication"))
    monthly_triptan: Counter[str] = Counter()
    monthly_simple: Counter[str] = Counter()
    for entry in data.entries:
        medication_names = [item.name.casefold() for item in entry.medications]
        month = entry.entry_date.strftime("%Y-%m")
        if any("triptan" in name for name in medication_names):
            monthly_triptan[month] += 1
        if any(
            term in name
            for name in medication_names
            for term in ("paracetamol", "parazetamol", "ibuprofen", "aspirin")
        ):
            monthly_simple[month] += 1
    triptan_days = max(monthly_triptan.values(), default=0)
    simple_days = max(monthly_simple.values(), default=0)
    triptan_day_word = tr(cfg, "Tag" if triptan_days == 1 else "Tagen", "day" if triptan_days == 1 else "days")
    simple_day_word = tr(cfg, "Tag" if simple_days == 1 else "Tagen", "day" if simple_days == 1 else "days")
    note = tr(cfg, 
        f'Im bisher höchsten Monat wurden an {triptan_days} {triptan_day_word} Triptane und an {simple_days} {simple_day_word} einfache Schmerzmittel eingetragen. Die ICHD-3 nennt als mögliche Übergebrauchsschwelle bei Triptanen mindestens 10 Einnahmetage pro Monat und bei einfachen Schmerzmitteln mindestens 15 Einnahmetage pro Monat – jeweils über mehr als drei Monate. Für die Diagnose gehören außerdem Kopfschmerzen an mindestens 15 Tagen pro Monat dazu. Diese Anzeige ist nur eine Orientierung und keine Diagnose.',
        f'In the highest month so far, triptans were recorded on {triptan_days} {triptan_day_word} and simple painkillers on {simple_days} {simple_day_word}. ICHD-3 uses a possible overuse threshold of at least 10 medication days per month for triptans and at least 15 medication days per month for simple painkillers, in each case for more than three months. Diagnosis also requires headache on at least 15 days per month. This display is guidance only and not a diagnosis.',
    )
    st.markdown(f'<div class="mt-note">{note}</div>', unsafe_allow_html=True)
    st.caption(tr(cfg, "Quelle: International Classification of Headache Disorders, ICHD-3, Abschnitt 8.2.", "Source: International Classification of Headache Disorders, ICHD-3, section 8.2."))
    st.link_button(
        tr(cfg, "ICHD-3-Kriterien öffnen", "Open ICHD-3 criteria"),
        tr(cfg, "https://ichd-3.org/de/8-kopfschmerz-zurueckzufuehren-auf-eine-substanz-oder-deren-entzug/8-2-kopfschmerz-zurueckzufuehren-auf-einen-medikamentenuebergebrauch/", "https://ichd-3.org/8-headache-attributed-to-a-substance-or-its-withdrawal/8-2-medication-overuse-headache-moh/"),
        icon=":material/open_in_new:",
    )
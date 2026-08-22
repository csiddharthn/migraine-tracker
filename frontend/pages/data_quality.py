from __future__ import annotations

import streamlit as st

from backend.analytics.calculations import data_quality
from frontend.components.charts import completeness_chart
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, chart_config, page_header
from frontend.config.name_space import cfg
from frontend.i18n import tr
from frontend.pages.page_utils import filtered_dataset


apply_ui()
page_header(tr(cfg, "Datenprüfung und Berechnung", "Data checks and calculations"), tr(cfg, "Welche Angaben vorhanden sind und wie die Auswertungen berechnet werden.", "Which information is available and how the analyses are calculated."))

with database_session() as session:
    data = filtered_dataset(session)
    quality = data_quality(data)
    total = max(1, quality["total"])
    completeness = [
        {"label": tr(cfg, "Notiz vorhanden", "Note available"), "complete": quality["notes"], "total": quality["total"], "rate": quality["notes"] / total},
        {"label": tr(cfg, "Beginn in der Notiz erkannt", "Onset recognised in the note"), "complete": quality["onset"], "total": quality["total"], "rate": quality["onset"] / total},
        {"label": tr(cfg, "Höhepunkt in der Notiz erkannt", "Peak recognised in the note"), "complete": quality["peak"], "total": quality["total"], "rate": quality["peak"] / total},
        {"label": tr(cfg, "Ende in der Notiz erkannt", "End recognised in the note"), "complete": quality["end"], "total": quality["total"], "rate": quality["end"] / total},
        {"label": tr(cfg, "Schmerzseite bekannt", "Side of pain known"), "complete": quality["specific_side"], "total": quality["total"], "rate": quality["specific_side"] / total},
        {"label": tr(cfg, "Automatisch erkannte Angaben geprüft", "Automatically recognised information reviewed"), "complete": quality["reviewed_interpretation"], "total": quality["total"], "rate": quality["reviewed_interpretation"] / total},
        {"label": tr(cfg, "Wirkung der Akutmedikation eingetragen", "Effect of acute medication recorded"), "complete": quality["medication_response"], "total": quality["medication_days"], "rate": quality["medication_response"] / max(1, quality["medication_days"])},
    ]
    st.subheader(tr(cfg, "Welche Angaben sind ausgefüllt?", "Which information has been filled in?"))
    st.plotly_chart(completeness_chart(completeness), width="stretch", config=chart_config())

    st.subheader(tr(cfg, "So werden die Zahlen berechnet", "How the figures are calculated"))
    methodology = tr(cfg, 
        """
        - **Beobachteter Tag:** Jeder Kalendertag im ausgewählten Zeitraum, unabhängig davon, ob Kopfschmerzen eingetragen wurden.
        - **Kopfschmerztag:** Ein Tag, für den ein Kopfschmerzeintrag gespeichert ist. Pro Person kann es je Datum nur einen solchen Eintrag geben.
        - **Angaben aus Notizen:** Uhrzeiten, Schmerzseite, Begleitumstände, Symptome und Maßnahmen werden automatisch im Notiztext gesucht. Sie können anschließend manuell geprüft und korrigiert werden.
        - **Originalnotiz:** Der ursprüngliche Text bleibt immer unverändert erhalten.
        - **Vergleiche:** Ein gemeinsames Auftreten oder ein rechnerischer Zusammenhang beweist nicht, dass ein Umstand die Kopfschmerzen verursacht hat.
        - **Behandlungszeiträume:** Besonders kurze Zeiträume reichen nicht aus, um die Wirksamkeit einer Behandlung zu beurteilen.
        """,
        """
        - **Observed day:** Every calendar day in the selected period, whether or not a headache was recorded.
        - **Headache day:** A day with a saved headache entry. Each person can have only one such entry per date.
        - **Information from notes:** Times, side of pain, circumstances, symptoms, and interventions are automatically sought in the note text. They can then be reviewed and corrected manually.
        - **Original note:** The original text is always retained unchanged.
        - **Comparisons:** Co-occurrence or a calculated relationship does not prove that a circumstance caused the headaches.
        - **Treatment periods:** Especially short periods are not enough to assess whether a treatment was effective.
        """,
    )
    st.markdown(methodology)
    st.markdown(f'<div class="mt-note">{tr(cfg, "Diese Anwendung unterstützt die Dokumentation und ersetzt keine medizinische Beratung.", "This application supports documentation and does not replace medical advice.")}</div>', unsafe_allow_html=True)

    st.subheader(tr(cfg, "Verwendete medizinische Quellen", "Medical sources used"))
    references = tr(cfg, 
        "- [DMKG: Kopfschmerzkalender und Patientenmaterial](https://www.dmkg.de/patienten/downloads-und-studien/)\n- [ICHD-3: Kopfschmerz durch Medikamentenübergebrauch](https://ichd-3.org/de/8-kopfschmerz-zurueckzufuehren-auf-eine-substanz-oder-deren-entzug/8-2-kopfschmerz-zurueckzufuehren-auf-einen-medikamentenuebergebrauch/)\n- [International Headache Society: Bedeutung von Kopfschmerzkalendern](https://ihs-headache.org/en/resources/medication-overuse-headache-awareness-campaign/)",
        "- [DMKG: Headache calendar and patient resources](https://www.dmkg.de/patienten/downloads-und-studien/)\n- [ICHD-3: Medication-overuse headache](https://ichd-3.org/8-headache-attributed-to-a-substance-or-its-withdrawal/8-2-medication-overuse-headache-moh/)\n- [International Headache Society: The role of headache diaries](https://ihs-headache.org/en/resources/medication-overuse-headache-awareness-campaign/)",
    )
    st.markdown(references)
    st.link_button(
        tr(cfg, "Originalen DMKG-Kopfschmerzkalender öffnen", "Open the original DMKG headache calendar"),
        "https://www.dmkg.de/assets/uploads/dateien/kopfschmerzkalender-deutsch-18.3.2021-name.pdf",
        icon=":material/picture_as_pdf:",
    )
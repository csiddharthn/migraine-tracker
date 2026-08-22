from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from backend.services.database_explorer import DatabaseExplorerService
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, page_header
from frontend.components.users import selected_user, user_caption
from frontend.i18n import column_label, localize_value, tr, yes_no


def _localized_cell(value):
    if isinstance(value, bool):
        return yes_no(value)
    return localize_value(value)


apply_ui()
page_header(tr("Gespeicherte Daten", "Stored data"), tr("Hier können Sie die gespeicherten Angaben ansehen und durchsuchen. Änderungen sind auf dieser Seite nicht möglich.", "Here you can view and search the saved information. Changes cannot be made on this page."))

with database_session() as session:
    user = selected_user(session)
    user_caption(user)
    service = DatabaseExplorerService(session, user.id)
    counts = service.counts()

    metrics = st.columns(4)
    metrics[0].metric(tr("Personen", "People"), counts["users"])
    metrics[1].metric(tr("Einträge", "Entries"), counts["entries"])
    metrics[2].metric(tr("Beobachtungstage", "Observation days"), counts["daily_records"])
    metrics[3].metric(tr("Automatisch ausgewertete Notizen", "Automatically analysed notes"), counts["interpretations"])

    descriptors = service.descriptors()
    labels = {item.key: localize_value(item.label) for item in descriptors}
    selected_key = st.selectbox(tr("Welche Daten möchten Sie sehen?", "Which data would you like to see?"), [item.key for item in descriptors], format_func=labels.get)
    table = service.load(selected_key)

    scope = tr(f"Ausgewählte Person: {user.display_name}", f"Selected person: {user.display_name}") if table.descriptor.personal else tr("Alle Personen / global", "All people / global")
    st.caption(f"{localize_value(table.descriptor.description)} · {scope}")

    search_column, option_column = st.columns([3, 1])
    with search_column:
        search = st.text_input(tr("In Tabelle suchen", "Search table"), placeholder=tr("Suchbegriff", "Search term"), key=f"database_search_{user.id}_{selected_key}")
    with option_column:
        show_technical = st.toggle(tr("IDs und technische Felder anzeigen", "Show IDs and technical fields"), value=False)

    frame = pd.DataFrame(table.rows)
    if not show_technical and not frame.empty:
        frame = frame.drop(columns=list(table.technical_columns), errors="ignore")
    if not frame.empty:
        frame = frame.map(_localized_cell).rename(columns=column_label)
    if search and not frame.empty:
        matches = frame.fillna("").astype(str).apply(
            lambda column: column.str.contains(search, case=False, regex=False)
        )
        frame = frame[matches.any(axis=1)]

    row_label = tr("Datensatz", "record") if len(frame) == 1 else tr("Datensätze", "records")
    st.caption(f"{len(frame)} {row_label}")
    if frame.empty:
        st.info(tr("Für diese Auswahl sind keine Datensätze vorhanden.", "No records are available for this selection."))
    else:
        column_config = {
            column: st.column_config.DateColumn(format="DD.MM.YYYY")
            for column in (tr("Datum", "Date"), tr("Datum des Eintrags", "Entry date"), tr("Erfassungsbeginn", "Tracking start"))
            if column in frame.columns
        }
        column_config.update(
            {
                column: st.column_config.DatetimeColumn(format="DD.MM.YYYY HH:mm:ss")
                for column in (tr("Zeitpunkt", "Timestamp"), tr("Importiert am", "Imported at"), tr("Geprüft am", "Reviewed at"), tr("Erstellt", "Created"), tr("Geändert", "Updated"))
                if column in frame.columns
            }
        )
        st.dataframe(
            frame,
            hide_index=True,
            width="stretch",
            height=min(720, max(280, 36 * len(frame) + 42)),
            column_config=column_config,
        )
        st.download_button(
            tr("CSV herunterladen", "Download CSV"),
            data=frame.to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name=f"{selected_key}_{date.today():%Y%m%d}.csv",
            mime="text/csv",
            icon=":material/download:",
        )

    with st.expander(tr("Technische Informationen zu den Datenbereichen", "Technical information about the data areas")):
        st.dataframe(
            pd.DataFrame(
                {
                    tr("Bereich", "Area"): [localize_value(item.label) for item in descriptors],
                    tr("PostgreSQL-Tabelle", "PostgreSQL table"): [item.physical_table for item in descriptors],
                    tr("Geltungsbereich", "Scope"): [tr("Ausgewählte Person", "Selected person") if item.personal else tr("Alle Personen / global", "All people / global") for item in descriptors],
                    tr("Inhalt", "Contents"): [localize_value(item.description) for item in descriptors],
                }
            ),
            hide_index=True,
            width="stretch",
        )

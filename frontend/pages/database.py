from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from backend.services.database_explorer import DatabaseExplorerService
from frontend.components.csv_export import (
    dataframe_to_semicolon_csv,
    table_date_format,
    table_datetime_format,
)
from frontend.components.state import database_session
from frontend.components.ui import apply_ui, page_header
from frontend.components.users import selected_user, user_caption
from frontend.config.name_space import cfg
from frontend.i18n import column_label, current_language, localize_value, tr, yes_no


def _localized_cell(value):
    if isinstance(value, bool):
        return yes_no(cfg, value)
    return localize_value(cfg, value)


apply_ui()
page_header(tr(cfg, "Gespeicherte Daten", "Stored data"), tr(cfg, "Hier können Sie die gespeicherten Angaben ansehen und durchsuchen. Änderungen sind auf dieser Seite nicht möglich.", "Here you can view and search the saved information. Changes cannot be made on this page."))

with database_session() as session:
    user = selected_user(session)
    user_caption(user)
    service = DatabaseExplorerService(session, user.id)
    counts = service.counts()

    metrics = st.columns(4)
    metrics[0].metric(tr(cfg, "Personen", "People"), counts["users"])
    metrics[1].metric(tr(cfg, "Einträge", "Entries"), counts["entries"])
    metrics[2].metric(tr(cfg, "Beobachtungstage", "Observation days"), counts["daily_records"])
    metrics[3].metric(tr(cfg, "Automatisch ausgewertete Notizen", "Automatically analysed notes"), counts["interpretations"])

    descriptors = service.descriptors()
    labels = {item.key: localize_value(cfg, item.label) for item in descriptors}
    selected_key = st.selectbox(tr(cfg, "Welche Daten möchten Sie sehen?", "Which data would you like to see?"), [item.key for item in descriptors], format_func=labels.get)
    table = service.load(selected_key)

    scope = tr(cfg, f"Ausgewählte Person: {user.display_name}", f"Selected person: {user.display_name}") if table.descriptor.personal else tr(cfg, "Alle Personen / global", "All people / global")
    st.caption(f"{localize_value(cfg, table.descriptor.description)} · {scope}")

    search_column, option_column = st.columns([3, 1])
    with search_column:
        search = st.text_input(tr(cfg, "In Tabelle suchen", "Search table"), placeholder=tr(cfg, "Suchbegriff", "Search term"), key=f"database_search_{user.id}_{selected_key}")
    with option_column:
        show_technical = st.toggle(tr(cfg, "IDs und technische Felder anzeigen", "Show IDs and technical fields"), value=False)

    frame = pd.DataFrame(table.rows)
    if not show_technical and not frame.empty:
        frame = frame.drop(columns=list(table.technical_columns), errors="ignore")
    if not frame.empty:
        frame = frame.map(_localized_cell).rename(columns=lambda col: column_label(cfg, col))
    if search and not frame.empty:
        matches = frame.fillna("").astype(str).apply(
            lambda column: column.str.contains(search, case=False, regex=False)
        )
        frame = frame[matches.any(axis=1)]

    row_label = tr(cfg, "Datensatz", "record") if len(frame) == 1 else tr(cfg, "Datensätze", "records")
    st.caption(f"{len(frame)} {row_label}")
    if frame.empty:
        st.info(tr(cfg, "Für diese Auswahl sind keine Datensätze vorhanden.", "No records are available for this selection."))
    else:
        language = current_language(cfg)
        column_config = {
            column: st.column_config.DateColumn(format=table_date_format(language))
            for column in (tr(cfg, "Datum", "Date"), tr(cfg, "Datum des Eintrags", "Entry date"), tr(cfg, "Erfassungsbeginn", "Tracking start"))
            if column in frame.columns
        }
        column_config.update(
            {
                column: st.column_config.DatetimeColumn(format=table_datetime_format(language))
                for column in (tr(cfg, "Zeitpunkt", "Timestamp"), tr(cfg, "Importiert am", "Imported at"), tr(cfg, "Geprüft am", "Reviewed at"), tr(cfg, "Erstellt", "Created"), tr(cfg, "Geändert", "Updated"))
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
            tr(cfg, "CSV herunterladen", "Download CSV"),
            data=dataframe_to_semicolon_csv(frame, language=language),
            file_name=f"{selected_key}_{date.today():%Y%m%d}.csv",
            mime="text/csv; charset=utf-16le",
            icon=":material/download:",
        )

    with st.expander(tr(cfg, "Technische Informationen zu den Datenbereichen", "Technical information about the data areas")):
        st.dataframe(
            pd.DataFrame(
                {
                    tr(cfg, "Bereich", "Area"): [localize_value(cfg, item.label) for item in descriptors],
                    tr(cfg, "PostgreSQL-Tabelle", "PostgreSQL table"): [item.physical_table for item in descriptors],
                    tr(cfg, "Geltungsbereich", "Scope"): [tr(cfg, "Ausgewählte Person", "Selected person") if item.personal else tr(cfg, "Alle Personen / global", "All people / global") for item in descriptors],
                    tr(cfg, "Inhalt", "Contents"): [localize_value(cfg, item.description) for item in descriptors],
                }
            ),
            hide_index=True,
            width="stretch",
        )

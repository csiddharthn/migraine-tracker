from __future__ import annotations

from datetime import date

import streamlit as st

from backend.services.entry_service import DuplicateEntryError, EntryService
from backend.services.schemas import EntryPatch
from backend.services.trigger_service import DuplicateTriggerError, TriggerService
from frontend.components.state import clear_data_cache, database_session
from frontend.components.ui import apply_ui, format_date, page_header
from frontend.components.users import selected_user, user_caption
from frontend.forms import render_entry_form, render_interpretation_review
from frontend.forms.ai_intake import render_ai_intake
from frontend.config.name_space import cfg
from frontend.i18n import (
    date_input_format,
    error_message,
    format_datetime_value,
    tr,
    trigger_description,
    trigger_label as localized_trigger_label,
)


apply_ui()
page_header(tr(cfg, "Einträge", "Entries"), tr(cfg, "Neue Kopfschmerztage eintragen, vorhandene Angaben ändern und mögliche Auslöser verwalten.", "Record new headache days, change existing information, and manage possible triggers."))

with database_session() as session:
    user = selected_user(session)
    user_caption(user)
    service = EntryService(session, user.id)
    active_triggers = service.repository.list_trigger_definitions(active_only=True)
    all_triggers = service.repository.list_trigger_definitions(active_only=False)
    medication_options = service.repository.list_medication_names()
    new_tab, ai_tab, edit_tab, trigger_tab = st.tabs(
        [
            tr(cfg, "Neuer Eintrag", "New entry"),
            tr(cfg, "KI-gestützter Eintrag", "AI-assisted entry"),
            tr(cfg, "Eintrag bearbeiten", "Edit entry"),
            tr(cfg, "Auslöser verwalten", "Manage triggers"),
        ]
    )

    with new_tab:
        payload = render_entry_form(active_triggers, medication_options, key="new")
        if payload is not None:
            try:
                entry = service.create(payload)
                session.commit()
                clear_data_cache()
                st.success(tr(cfg, f"Der Eintrag für den {format_date(entry.entry_date)} wurde gespeichert.", f"The entry for {format_date(entry.entry_date)} was saved."))
            except (DuplicateEntryError, ValueError) as exc:
                session.rollback()
                st.error(error_message(cfg, exc))

    with ai_tab:
        render_ai_intake(
            entry_service=service,
            trigger_definitions=active_triggers,
            medication_options=medication_options,
            user_id=str(user.id),
            session=session,
        )

    with edit_tab:
        entries = service.repository.list_entries()
        if not entries:
            st.info(tr(cfg, "Noch keine Einträge vorhanden.", "No entries exist yet."))
        else:
            search_col, date_col = st.columns([2, 1])
            search = search_col.text_input(tr(cfg, "Suchen", "Search"), placeholder=tr(cfg, "Notiz, Medikation oder Auslöser", "Note, medication, or trigger"))
            selected_date = date_col.date_input(tr(cfg, "Nur dieses Datum", "Only this date"), value=None, format=date_input_format(cfg, ))
            filtered = []
            needle = search.strip().lower()
            for entry in entries:
                haystack = " ".join(
                    [
                        entry.timeline_notes,
                        entry.possible_factors,
                        entry.symptoms_and_actions,
                        entry.other_notes,
                        " ".join(item.name for item in entry.medications),
                        " ".join(item.dose or "" for item in entry.medications),
                        " ".join(localized_trigger_label(cfg, trigger.trigger_code, trigger.definition.label) for trigger in entry.triggers),
                    ]
                ).lower()
                if needle and needle not in haystack:
                    continue
                if selected_date and entry.entry_date != selected_date:
                    continue
                filtered.append(entry)
            if not filtered:
                st.warning(tr(cfg, "Keine passenden Einträge gefunden.", "No matching entries found."))
            else:
                entries_by_id = {entry.id: entry for entry in filtered}
                selected_id = st.selectbox(
                    tr(cfg, "Eintrag auswählen", "Select entry"),
                    list(entries_by_id),
                    format_func=lambda entry_id: tr(cfg, 
                        f"{format_date(entries_by_id[entry_id].entry_date)} · Stärke {entries_by_id[entry_id].strength} von 10 · Dauer {float(entries_by_id[entry_id].duration_hours):g} Stunden",
                        f"{format_date(entries_by_id[entry_id].entry_date)} · Intensity {entries_by_id[entry_id].strength} out of 10 · Duration {float(entries_by_id[entry_id].duration_hours):g} hours",
                    ),
                )
                entry = service.repository.get(selected_id)
                if entry is not None:
                    st.caption(f"{tr(cfg, 'Zuletzt aktualisiert', 'Last updated')}: {format_datetime_value(cfg, entry.updated_at)}")
                    daily_record = service.repository.get_daily_record(entry.entry_date)
                    payload = render_entry_form(all_triggers, medication_options, existing=entry, daily_record=daily_record, key=f"edit_{entry.id}")
                    if payload is not None:
                        try:
                            updated = service.update(
                                entry.id,
                                EntryPatch(**payload.model_dump()),
                                reviewed_annotation=payload.note_annotation,
                            )
                            session.commit()
                            clear_data_cache()
                            st.success(tr(cfg, f"Der Eintrag für den {format_date(updated.entry_date)} wurde aktualisiert.", f"The entry for {format_date(updated.entry_date)} was updated."))
                        except (DuplicateEntryError, ValueError) as exc:
                            session.rollback()
                            st.error(error_message(cfg, exc))

                    with st.expander(tr(cfg, "Automatisch aus der Notiz erkannte Angaben prüfen", "Review information recognised automatically from the note"), expanded=False):
                        interpretation_changes = render_interpretation_review(entry)
                        if interpretation_changes is not None:
                            service.review_interpretation(entry.id, interpretation_changes)
                            session.commit()
                            clear_data_cache()
                            st.success(tr(cfg, "Die geprüften Angaben aus der Notiz wurden gespeichert.", "The reviewed information from the note was saved."))

    with trigger_tab:
        trigger_service = TriggerService(session)
        created_message = st.session_state.pop("created_trigger_message", None)
        if created_message:
            st.success(created_message)

        st.subheader(tr(cfg, "Neuen Auslöser anlegen", "Add a new trigger"))
        st.caption(tr(cfg, "Der Auslöser wird dem gemeinsamen Katalog hinzugefügt und steht allen Personenprofilen zur Verfügung.", "The trigger is added to the shared catalogue and is available to all people profiles."))
        with st.form("create_trigger"):
            trigger_label = st.text_input(tr(cfg, "Bezeichnung", "Label"), placeholder=tr(cfg, "Zum Beispiel: Unregelmäßige Mahlzeit", "For example: Irregular meal"))
            new_trigger_description = st.text_area(tr(cfg, "Beschreibung (optional)", "Description (optional)"), height=100)
            create_trigger = st.form_submit_button(tr(cfg, "Auslöser anlegen", "Add trigger"), type="primary", icon=":material/add:")
        if create_trigger:
            try:
                trigger = trigger_service.create(trigger_label, new_trigger_description)
                session.commit()
                clear_data_cache()
                st.session_state["created_trigger_message"] = tr(cfg, f"Der Auslöser „{trigger.label}“ wurde angelegt.", f"The trigger “{trigger.label}” was added.")
                st.rerun()
            except (DuplicateTriggerError, ValueError) as exc:
                session.rollback()
                st.error(error_message(cfg, exc))

        st.subheader(tr(cfg, "Vorhandene Auslöser", "Existing triggers"))
        trigger_rows = [
            {
                tr(cfg, "Bezeichnung", "Label"): localized_trigger_label(cfg, trigger.code, trigger.label),
                tr(cfg, "Beschreibung", "Description"): trigger_description(cfg, trigger.code, trigger.description),
                tr(cfg, "Status", "Status"): tr(cfg, "Aktiv", "Active") if trigger.active else tr(cfg, "Inaktiv", "Inactive"),
            }
            for trigger in trigger_service.repository.list_all()
        ]
        st.dataframe(trigger_rows, hide_index=True, width="stretch")

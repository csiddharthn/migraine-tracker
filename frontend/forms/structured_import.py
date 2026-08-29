from __future__ import annotations

"""Streamlit UI for importing a pre-structured migraine entry as JSON."""

import json
from datetime import date

import streamlit as st

from backend.ai_intake.structured_import import (
    StructuredEntryImport,
    StructuredImportError,
    parse_structured_import,
)
from backend.services.entry_service import DuplicateEntryError, EntryService
from frontend.components.state import clear_data_cache
from frontend.components.ui import format_date
from frontend.config.name_space import cfg
from frontend.forms.entry_form import render_entry_form
from frontend.i18n import error_message, tr


EXAMPLE_IMPORT = {
    "schema_version": "1",
    "source": "ChatGPT",
    "source_narrative": "Optional: the original dictated description.",
    "draft": {
        "entry_date": "2026-08-29",
        "strength": 6,
        "duration_hours": 4.5,
        "trigger_codes": [],
        "proposed_triggers": ["Unsicher"],
        "pain_type": "Dumpf / drückend",
        "entered_laterality": "Rechts",
        "nausea": True,
        "medications": [
            {
                "name": "Eletriptan",
                "taken_at": "10:15",
                "dose": "40 mg",
                "effectiveness": "Ja",
            }
        ],
        "timeline": [
            {
                "start_time": "08:30",
                "end_time": None,
                "note": "Kopfschmerz begann.",
            }
        ],
        "possible_factors": "",
        "symptoms_and_actions": "",
    },
}


def render_structured_import(
    *,
    entry_service: EntryService,
    trigger_definitions,
    medication_options: list[str],
    user_id: str,
    session,
) -> None:
    """Render the no-extra-AI structured import and normal review/save flow."""

    raw_key = f"structured_import_raw_{user_id}"
    draft_key = f"structured_import_draft_{user_id}"

    st.subheader(tr(cfg, "Strukturierten Eintrag importieren", "Import structured entry"))
    st.caption(
        tr(
            cfg,
            "Fügen Sie hier einen versionierten JSON-Entwurf ein, zum Beispiel einen in ChatGPT aus einer freien Diktatbeschreibung erzeugten Eintrag.",
            "Paste a versioned JSON draft here, for example an entry produced in ChatGPT from a freely dictated description.",
        )
    )
    st.info(
        tr(
            cfg,
            "Für diesen Import wird keine Groq- oder OpenRouter-Anfrage ausgeführt. Vor dem Speichern erscheint immer das normale Prüf- und Bearbeitungsformular.",
            "This import does not call Groq or OpenRouter. The normal review and edit form is always shown before anything is saved.",
        ),
        icon=":material/lock:",
    )

    with st.expander(tr(cfg, "Erwartetes JSON-Format", "Expected JSON format"), expanded=False):
        st.code(json.dumps(EXAMPLE_IMPORT, ensure_ascii=False, indent=2), language="json")
        st.caption(
            tr(
                cfg,
                "Auslöser können als bekannte Codes oder als Bezeichnungen unter proposed_triggers geliefert werden. Exakt passende Bezeichnungen werden gegen Ihren lokalen Auslöser-Katalog aufgelöst.",
                "Triggers may be supplied as known codes or as labels under proposed_triggers. Exact label matches are resolved against your local trigger catalogue.",
            )
        )

    raw_json = st.text_area(
        tr(cfg, "Strukturierter JSON-Entwurf", "Structured JSON draft"),
        key=raw_key,
        height=300,
        placeholder='{"schema_version":"1","source":"ChatGPT","draft":{...}}',
    )
    action_cols = st.columns([1, 1, 3])
    load_import = action_cols[0].button(
        tr(cfg, "Entwurf laden", "Load draft"),
        type="primary",
        icon=":material/upload:",
        disabled=not raw_json.strip(),
        width="stretch",
    )
    discard_import = action_cols[1].button(
        tr(cfg, "Import verwerfen", "Discard import"),
        icon=":material/delete:",
        disabled=draft_key not in st.session_state,
        width="stretch",
    )

    if discard_import:
        st.session_state.pop(draft_key, None)
        st.session_state.pop(raw_key, None)
        st.rerun()

    if load_import:
        try:
            imported = parse_structured_import(
                raw_json,
                trigger_definitions=trigger_definitions,
                current_date=date.today(),
            )
            st.session_state[draft_key] = imported.model_dump(mode="json")
            st.rerun()
        except StructuredImportError as exc:
            st.error(
                tr(cfg, "Der Import konnte nicht geladen werden: ", "The import could not be loaded: ")
                + str(exc)
            )

    raw_import = st.session_state.get(draft_key)
    if not raw_import:
        return

    imported = StructuredEntryImport.model_validate(raw_import)
    draft = imported.draft

    st.divider()
    st.subheader(tr(cfg, "Importierten Entwurf prüfen", "Review imported draft"))
    st.caption(
        tr(cfg, f"Quelle: {imported.source}", f"Source: {imported.source}")
        + f" · Schema v{imported.schema_version}"
    )

    if draft.proposed_triggers:
        st.warning(
            tr(cfg, "Nicht automatisch zugeordnete Auslöser: ", "Triggers not matched automatically: ")
            + ", ".join(draft.proposed_triggers)
        )
    if not draft.trigger_codes:
        st.warning(
            tr(
                cfg,
                "Es wurde noch kein Auslöser zugeordnet. Wählen Sie im Prüf-Formular mindestens einen Auslöser aus.",
                "No trigger has been matched yet. Select at least one trigger in the review form.",
            )
        )

    save_source = st.checkbox(
        tr(
            cfg,
            "Ursprünglichen diktierten Text zusammen mit dem Eintrag speichern",
            "Store the original dictated text with the entry",
        ),
        value=bool(imported.source_narrative),
        disabled=not bool(imported.source_narrative),
        key=f"structured_import_store_source_{user_id}_{draft.fingerprint()}",
        help=tr(
            cfg,
            "Der Ursprungstext bleibt getrennt von den strukturierten Feldern gespeichert.",
            "The source narrative is stored separately from the structured fields.",
        ),
    )

    payload = render_entry_form(
        trigger_definitions,
        medication_options,
        draft=draft,
        key=f"structured_import_review_{user_id}_{draft.fingerprint()}",
    )
    if payload is None:
        return

    extraction = draft.model_dump(mode="json")
    extraction["_structured_import"] = {
        "schema_version": imported.schema_version,
        "source": imported.source,
    }
    payload = payload.model_copy(
        update={
            "source_narrative": imported.source_narrative if save_source else None,
            "ai_provider": "structured_import",
            "ai_model": imported.source,
            "ai_prompt_version": f"structured-import-v{imported.schema_version}",
            "ai_extraction": extraction,
        }
    )

    try:
        entry = entry_service.create(payload, origin="structured_import")
        session.commit()
        clear_data_cache()
        st.session_state.pop(draft_key, None)
        st.session_state.pop(raw_key, None)
        st.success(
            tr(
                cfg,
                f"Der geprüfte importierte Eintrag für den {format_date(entry.entry_date)} wurde gespeichert.",
                f"The reviewed imported entry for {format_date(entry.entry_date)} was saved.",
            )
        )
    except (DuplicateEntryError, ValueError) as exc:
        session.rollback()
        st.error(error_message(cfg, exc))

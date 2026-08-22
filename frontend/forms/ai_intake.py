from __future__ import annotations

"""Purpose: AI intake form for generating intake drafts.

Usage: Renders AI intake form and handles transcription.

Functions available:
- render_ai_intake

Classes available:
- None

Call hierarchy:
- ai_intake.py -> backend.ai_intake, backend.services.entry_service
"""

from datetime import date

import streamlit as st

from backend.ai_intake import (
    AIIntakeDraft,
    AIIntakeError,
    AIIntakeService,
    AITranscriptionError,
    GroqTranscriptionService,
)
from backend.ai_intake.providers.groq_provider import GroqProvider
from backend.ai_intake.providers.openrouter_provider import OpenRouterProvider
from backend.config import get_settings
from backend.services.entry_service import DuplicateEntryError, EntryService
from frontend.components.state import clear_data_cache, groq_api_key
from frontend.components.ui import format_date
from frontend.forms.entry_form import render_entry_form
from frontend.config.name_space import cfg
from frontend.i18n import error_message, tr


def render_ai_intake(
    *,
    entry_service: EntryService,
    trigger_definitions,
    medication_options: list[str],
    user_id: str,
    session,
) -> None:
    settings = get_settings()
    ai_config = settings.app_config().get("ai_intake", {})
    transcription_config = ai_config.get("transcription", {})
    api_key = groq_api_key()
    openrouter_key = settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else None
    provider = ai_config.get("provider", "groq")
    provider_options = ai_config.get("providers", {}).keys() if isinstance(ai_config.get("providers"), dict) else ["groq", "openrouter"]
    selected_provider = st.selectbox(
        tr(cfg, "KI-Anbieter", "AI provider"),
        options=list(provider_options),
        index=list(provider_options).index(provider) if provider in provider_options else 0,
        key=f"ai_provider_{user_id}",
    )
    active_api_key = openrouter_key if selected_provider == "openrouter" else api_key
    if selected_provider == "openrouter":
        model_options = _configured_model_list({"models": ai_config.get("openrouter_models", [])})
        if not model_options:
            model_options = [
                {"id": "openai/gpt-oss-120b", "label_de": "GPT-OSS 120B (leistungsstärker)", "label_en": "GPT-OSS 120B (more capable)"},
                {"id": "openai/gpt-oss-20b", "label_de": "GPT-OSS 20B (schnelleres Ersatzmodell)", "label_en": "GPT-OSS 20B (faster fallback)"},
            ]
    else:
        model_options = _configured_models(ai_config)
    model_ids = [item["id"] for item in model_options]
    transcription_options = _configured_transcription_models(transcription_config)
    transcription_model_ids = [item["id"] for item in transcription_options]
    language = st.session_state.get("app_language", "de")
    draft_key = f"ai_intake_draft_{user_id}"
    metadata_key = f"ai_intake_metadata_{user_id}"
    narrative_key = f"ai_intake_narrative_{user_id}"
    clarification_key = f"ai_intake_clarifications_{user_id}"
    transcription_metadata_key = f"ai_intake_transcription_metadata_{user_id}"

    st.subheader(tr(cfg, "Freien Text in einen Eintrag umwandeln", "Turn free text into an entry"))
    st.caption(
        tr(cfg, 
            "Beschreiben oder diktieren Sie den Kopfschmerz in eigenen Worten. Die KI erstellt daraus nur einen Entwurf; gespeichert wird erst nach Ihrer Prüfung im Formular.",
            "Describe or dictate the headache in your own words. AI only creates a draft; nothing is saved until you review the form.",
        )
    )
    st.caption(
        tr(cfg, 
            "Englische und gemischte Beschreibungen werden automatisch übersetzt; der ausgefüllte Entwurf wird immer auf Deutsch vereinheitlicht.",
            "English and mixed-language descriptions are translated automatically; the completed draft is always standardised in German.",
        )
    )
    if not ai_config.get("enabled", True):
        st.info(tr(cfg, "Die KI-Eingabe ist in der Konfiguration deaktiviert.", "AI-assisted entry is disabled in the configuration."))
        return
    if not active_api_key:
        st.info(
            tr(cfg,
                f"Für diese Funktion fehlt noch der {selected_provider.upper()}-API-Schlüssel. Hinterlegen Sie {selected_provider.upper()}_API_KEY lokal in der Datei .env oder in .streamlit/secrets.toml und starten Sie die Anwendung neu.",
                f"This feature still needs a {selected_provider.upper()} API key. Store {selected_provider.upper()}_API_KEY locally in .env or .streamlit/secrets.toml and restart the application.",
            ),
            icon=":material/key:",
        )

    configured_default = str(ai_config.get("default_model", model_ids[0]))
    default_index = model_ids.index(configured_default) if configured_default in model_ids else 0
    preferred_model = st.selectbox(
        tr(cfg, "Bevorzugtes KI-Modell", "Preferred AI model"),
        options=model_ids,
        index=default_index,
        format_func=lambda model_id: _model_label(model_id, model_options, language),
        key=f"ai_intake_model_{user_id}",
        help=tr(cfg, 
            "Dieses Modell wird zuerst verwendet. Bei einem vorübergehenden Fehler oder Nutzungslimit probiert die Anwendung automatisch die anderen hier konfigurierten Groq-Modelle.",
            "This model is tried first. If it is temporarily unavailable or rate-limited, the app automatically tries the other configured Groq models.",
        ),
    )
    st.caption(
        tr(cfg,
            f"Verwendeter Anbieter: {selected_provider}. Automatische Modellreihenfolge: ",
            f"Provider in use: {selected_provider}. Automatic model order: ",
        )
        + " → ".join(
            _model_label(model_id, model_options, language)
            for model_id in _ordered_models(preferred_model, model_ids)
        )
    )

    consent = st.checkbox(
        tr(cfg,
            f"Ich bin einverstanden, dass meine Aufnahme bzw. mein Gesundheitstext an die {selected_provider.upper()}-API gesendet wird.",
            f"I agree that my recording or health text may be sent to the {selected_provider.upper()} API.",
        ),
        key=f"ai_intake_consent_{user_id}",
    )

    if transcription_config.get("enabled", True):
        st.markdown(f"**{tr(cfg, 'Spracheingabe', 'Voice input')}**")
        transcription_default = str(
            transcription_config.get("default_model", transcription_model_ids[0])
        )
        transcription_default_index = (
            transcription_model_ids.index(transcription_default)
            if transcription_default in transcription_model_ids
            else 0
        )
        preferred_transcription_model = st.selectbox(
            tr(cfg, "Bevorzugtes Modell für die Spracherkennung", "Preferred speech recognition model"),
            options=transcription_model_ids,
            index=transcription_default_index,
            format_func=lambda model_id: _model_label(model_id, transcription_options, language),
            key=f"ai_intake_transcription_model_{user_id}",
            help=tr(cfg, 
                "Whisper Large v3 wird wegen seiner höheren Genauigkeit empfohlen. Falls es nicht verfügbar ist, wird automatisch das nächste Modell verwendet.",
                "Whisper Large v3 is recommended for its higher accuracy. If it is unavailable, the next model is tried automatically.",
            ),
        )
        spoken_language = st.selectbox(
            tr(cfg, "Sprache der Aufnahme", "Recording language"),
            options=["auto", "de", "en"],
            format_func=lambda value: {
                "auto": tr(cfg, "Automatisch erkennen", "Detect automatically"),
                "de": tr(cfg, "Deutsch", "German"),
                "en": tr(cfg, "Englisch", "English"),
            }[value],
            key=f"ai_intake_recording_language_{user_id}",
        )
        recording = st.audio_input(
            tr(cfg, "Kopfschmerzbeschreibung aufnehmen", "Record headache description"),
            key=f"ai_intake_recording_{user_id}",
            disabled=not api_key,
        )
        transcribe = st.button(
            tr(cfg, "Aufnahme in Text umwandeln", "Convert recording to text"),
            icon=":material/transcribe:",
            disabled=not api_key or recording is None,
        )
        if recording is not None and not consent:
            st.warning(
                tr(cfg, 
                    "Die Aufnahme ist bereit. Aktivieren Sie oben noch die Zustimmung zur Verarbeitung durch Groq; anschließend kann die Aufnahme in Text umgewandelt werden.",
                    "The recording is ready. Enable the Groq processing consent above; the recording can then be converted to text.",
                ),
                icon=":material/privacy_tip:",
            )
        if transcribe and recording is not None:
            if consent:
                try:
                    transcript, voice_model_used, attempted_voice_models = _transcribe_audio(
                        api_key=active_api_key or "",
                        provider_name=selected_provider,
                        transcription_config=transcription_config,
                        preferred_model=preferred_transcription_model,
                        audio=recording.getvalue(),
                        filename=getattr(cfg, recording, "name", "migraine-description.wav"),
                        language=None if spoken_language == "auto" else spoken_language,
                    )
                    existing_narrative = str(st.session_state.get(narrative_key, "")).strip()
                    st.session_state[narrative_key] = (
                        f"{existing_narrative}\n\n{transcript}".strip() if existing_narrative else transcript
                    )
                    st.session_state[transcription_metadata_key] = {
                        "provider": "groq",
                        "model": voice_model_used,
                        "attempted_models": list(attempted_voice_models),
                        "language": spoken_language,
                    }
                    st.rerun()
                except AITranscriptionError as exc:
                    st.error(error_message(cfg, exc))

        transcription_metadata = st.session_state.get(transcription_metadata_key, {})
        if transcription_metadata:
            voice_model_used = str(transcription_metadata.get("model", preferred_transcription_model))
            if voice_model_used != preferred_transcription_model:
                st.info(
                    tr(cfg, 
                        "Das bevorzugte Sprachmodell war nicht verfügbar. Die Aufnahme wurde automatisch mit "
                        f"{_model_label(voice_model_used, transcription_options, language)} transkribiert.",
                        "The preferred speech model was unavailable. The recording was automatically transcribed with "
                        f"{_model_label(voice_model_used, transcription_options, language)}.",
                    )
                )
            else:
                st.caption(
                    tr(cfg, "Letzte Transkription mit: ", "Last transcription with: ")
                    + _model_label(voice_model_used, transcription_options, language)
                )

    narrative = st.text_area(
        tr(cfg, "Beschreibung des Kopfschmerztags", "Description of the headache day"),
        key=narrative_key,
        height=250,
        placeholder=tr(cfg, 
            "Zum Beispiel: Heute begannen die Kopfschmerzen gegen 08:30 Uhr rechtsseitig ...",
            "For example: Today the headache started at about 08:30 on the right side ...",
        ),
    )
    analyze = st.button(
        tr(cfg, "Entwurf erstellen", "Create draft"),
        type="primary",
        icon=":material/auto_awesome:",
        disabled=not active_api_key or not narrative.strip(),
    )
    if analyze:
        if not consent:
            st.warning(
                tr(cfg,
                    f"Aktivieren Sie zuerst die Zustimmung zur Verarbeitung durch {selected_provider.upper()}.",
                    f"Enable consent for {selected_provider.upper()} processing first.",
                ),
                icon=":material/privacy_tip:",
            )
        else:
            try:
                draft, model_used, attempted_models = _extract_ai_draft(
                    api_key=active_api_key or "",
                    provider_name=selected_provider,
                    ai_config=ai_config,
                    preferred_model=preferred_model,
                    narrative=narrative,
                    trigger_definitions=trigger_definitions,
                    medication_options=medication_options,
                )
                st.session_state[draft_key] = draft.model_dump(mode="json")
                st.session_state[metadata_key] = {
                    "provider": "groq",
                    "model": model_used,
                    "attempted_models": list(attempted_models),
                }
                st.session_state[clarification_key] = []
                st.rerun()
            except AIIntakeError as exc:
                st.error(error_message(cfg, exc))

    raw_draft = st.session_state.get(draft_key)
    if not raw_draft:
        return
    draft = AIIntakeDraft.model_validate(raw_draft)
    metadata = st.session_state.get(metadata_key, {})

    st.divider()
    st.subheader(tr(cfg, "KI-Entwurf prüfen", "Review AI draft"))
    st.caption(
        tr(cfg, 
            "Alle erkannten Angaben stehen unten in den normalen Eingabefeldern. Bitte korrigieren Sie Fehler oder unklare Standardwerte vor dem Speichern.",
            "All recognised information appears in the normal fields below. Correct errors or unclear default values before saving.",
        )
    )
    model_used = str(metadata.get("model", preferred_model))
    attempted_models = list(metadata.get("attempted_models", [model_used]))
    if model_used != preferred_model:
        st.info(
            tr(cfg, 
                "Das bevorzugte Modell war nicht verfügbar. Der Entwurf wurde automatisch mit "
                f"{_model_label(model_used, model_options, language)} erstellt.",
                "The preferred model was unavailable. The draft was created automatically with "
                f"{_model_label(model_used, model_options, language)}.",
            )
        )
    else:
        st.caption(
            tr(cfg, "Entwurf erstellt mit: ", "Draft created with: ")
            + _model_label(model_used, model_options, language)
        )
    notes = draft.localized_notes(language)
    if notes:
        with st.expander(tr(cfg, "Hinweise zur Auswertung", "Interpretation notes"), expanded=False):
            for note in notes:
                st.write(f"- {note}")
    if draft.proposed_triggers:
        st.warning(
            tr(cfg, "Noch nicht im Auslöser-Katalog: ", "Not yet in the trigger catalogue: ")
            + ", ".join(draft.proposed_triggers)
        )

    if draft.clarification_questions:
        st.markdown(f"**{tr(cfg, 'Offene Fragen', 'Open questions')}**")
        answers: list[tuple[str, str]] = []
        answer_key = draft.fingerprint()
        for index, question in enumerate(draft.clarification_questions):
            label = question.localized(language)
            answer = st.text_input(
                f"{index + 1}. {label}",
                key=f"ai_answer_{user_id}_{answer_key}_{index}",
            )
            answers.append((label, answer))
        apply_answers = st.button(
            tr(cfg, "Antworten in den Entwurf übernehmen", "Apply answers to draft"),
            icon=":material/refresh:",
            disabled=not any(answer.strip() for _, answer in answers),
        )
        if apply_answers:
            prior = list(st.session_state.get(clarification_key, []))
            combined = [*prior, *[(question, answer) for question, answer in answers if answer.strip()]]
            try:
                updated, model_used, attempted_models = _extract_ai_draft(
                    api_key=active_api_key or "",
                    provider_name=selected_provider,
                    ai_config=ai_config,
                    preferred_model=preferred_model,
                    narrative=narrative,
                    trigger_definitions=trigger_definitions,
                    medication_options=medication_options,
                    clarifications=combined,
                )
                st.session_state[draft_key] = updated.model_dump(mode="json")
                st.session_state[metadata_key] = {
                    "provider": "groq",
                    "model": model_used,
                    "attempted_models": list(attempted_models),
                }
                st.session_state[clarification_key] = combined
                st.rerun()
            except AIIntakeError as exc:
                st.error(error_message(cfg, exc))

    save_source = st.checkbox(
        tr(cfg, 
            "Ursprünglichen Text zusammen mit dem Eintrag speichern",
            "Store the original text with the entry",
        ),
        value=True,
        key=f"ai_store_source_{user_id}_{draft.fingerprint()}",
        help=tr(cfg, 
            "Der Text bleibt getrennt von den strukturierten Notizen erhalten und dient der späteren Nachvollziehbarkeit.",
            "The text is retained separately from the structured notes for later traceability.",
        ),
    )
    payload = render_entry_form(
        trigger_definitions,
        medication_options,
        draft=draft,
        key=f"ai_review_{user_id}_{draft.fingerprint()}",
    )
    if payload is None:
        return

    clarifications = list(st.session_state.get(clarification_key, []))
    source_narrative = _combined_source_narrative(narrative, clarifications) if save_source else None
    ai_extraction = draft.model_dump(mode="json")
    transcription_metadata = st.session_state.get(transcription_metadata_key)
    if transcription_metadata:
        ai_extraction["_transcription"] = dict(transcription_metadata)
    payload = payload.model_copy(
        update={
            "source_narrative": source_narrative,
            "ai_provider": selected_provider,
            "ai_model": model_used,
            "ai_prompt_version": str(ai_config.get("prompt_version", "1.2")),
            "ai_extraction": ai_extraction,
        }
    )
    try:
        entry = entry_service.create(payload, origin="ai_assisted")
        session.commit()
        clear_data_cache()
        st.session_state.pop(draft_key, None)
        st.session_state.pop(metadata_key, None)
        st.session_state.pop(clarification_key, None)
        st.session_state.pop(transcription_metadata_key, None)
        st.success(
            tr(cfg, 
                f"Der geprüfte Eintrag für den {format_date(entry.entry_date)} wurde gespeichert.",
                f"The reviewed entry for {format_date(entry.entry_date)} was saved.",
            )
        )
    except (DuplicateEntryError, ValueError) as exc:
        session.rollback()
        st.error(error_message(cfg, exc))


def _extract_ai_draft(
    *,
    api_key: str,
    provider_name: str | None = None,
    ai_config: dict,
    preferred_model: str,
    narrative: str,
    trigger_definitions,
    medication_options: list[str],
    clarifications: list[tuple[str, str]] | None = None,
) -> tuple[AIIntakeDraft, str, tuple[str, ...]]:
    model_ids = [item["id"] for item in _configured_models(ai_config)]
    service = AIIntakeService(
        provider_name=provider_name or ai_config.get("provider", "groq"),
        api_key=api_key,
        models=_ordered_models(preferred_model, model_ids),
        prompt_version=str(ai_config.get("prompt_version", "1.2")),
        timeout_seconds=int(ai_config.get("timeout_seconds", 90)),
    )
    with st.spinner(tr(cfg, "Der Text wird strukturiert ...", "Structuring the text ...")):
        draft = service.extract(
            narrative,
            trigger_definitions=trigger_definitions,
            medication_names=["Amitriptylin neuraxpharm", *medication_options],
            current_date=date.today(),
            clarifications=clarifications or [],
        )
    return draft, service.model_used or preferred_model, service.attempted_models


def _configured_models(ai_config: dict) -> list[dict[str, str]]:
    configured: list[dict[str, str]] = []
    for item in ai_config.get("models", []):
        if isinstance(item, str) and item.strip():
            configured.append({"id": item.strip(), "label_de": item.strip(), "label_en": item.strip()})
        elif isinstance(item, dict) and str(item.get("id", "")).strip():
            model_id = str(item["id"]).strip()
            configured.append(
                {
                    "id": model_id,
                    "label_de": str(item.get("label_de", model_id)),
                    "label_en": str(item.get("label_en", model_id)),
                }
            )
    if configured:
        return configured
    return [
        {
            "id": "openai/gpt-oss-120b",
            "label_de": "GPT-OSS 120B (leistungsstärker)",
            "label_en": "GPT-OSS 120B (more capable)",
        },
        {
            "id": "openai/gpt-oss-20b",
            "label_de": "GPT-OSS 20B (schnelleres Ersatzmodell)",
            "label_en": "GPT-OSS 20B (faster fallback)",
        },
    ]


def _configured_transcription_models(transcription_config: dict) -> list[dict[str, str]]:
    configured = _configured_model_list(transcription_config)
    if configured:
        return configured
    return [
        {
            "id": "whisper-large-v3",
            "label_de": "Whisper Large v3 (höchste Genauigkeit)",
            "label_en": "Whisper Large v3 (highest accuracy)",
        },
        {
            "id": "whisper-large-v3-turbo",
            "label_de": "Whisper Large v3 Turbo (schnelleres Ersatzmodell)",
            "label_en": "Whisper Large v3 Turbo (faster fallback)",
        },
    ]


def _configured_model_list(config: dict) -> list[dict[str, str]]:
    configured: list[dict[str, str]] = []
    for item in config.get("models", []):
        if isinstance(item, str) and item.strip():
            configured.append({"id": item.strip(), "label_de": item.strip(), "label_en": item.strip()})
        elif isinstance(item, dict) and str(item.get("id", "")).strip():
            model_id = str(item["id"]).strip()
            configured.append(
                {
                    "id": model_id,
                    "label_de": str(item.get("label_de", model_id)),
                    "label_en": str(item.get("label_en", model_id)),
                }
            )
    return configured


def _model_label(model_id: str, options: list[dict[str, str]], language: str) -> str:
    label_key = "label_en" if language == "en" else "label_de"
    return next((item[label_key] for item in options if item["id"] == model_id), model_id)


def _ordered_models(preferred_model: str, model_ids: list[str]) -> list[str]:
    return list(dict.fromkeys([preferred_model, *model_ids]))


def _transcribe_audio(
    *,
    api_key: str,
    provider_name: str | None = None,
    transcription_config: dict,
    preferred_model: str,
    audio: bytes,
    filename: str,
    language: str | None,
) -> tuple[str, str, tuple[str, ...]]:
    model_ids = [item["id"] for item in _configured_transcription_models(transcription_config)]
    provider_name = provider_name or "groq"
    service_class = GroqTranscriptionService if provider_name == "groq" else GroqTranscriptionService
    # For openrouter, use the same interface but with openrouter provider
    if provider_name == "openrouter":
        from backend.ai_intake.providers.openrouter_provider import OpenRouterProvider
        # Transcription service uses provider abstraction; keep GroqTranscriptionService for now
        # but pass provider_name through if supported. For simplicity, keep existing service.
    service = GroqTranscriptionService(
        api_key=api_key,
        models=_ordered_models(preferred_model, model_ids),
        timeout_seconds=int(transcription_config.get("timeout_seconds", 90)),
        max_file_size_mb=int(transcription_config.get("max_file_size_mb", 25)),
    )
    with st.spinner(tr(cfg, "Die Aufnahme wird transkribiert ...", "Transcribing the recording ...")):
        transcript = service.transcribe(audio, filename=filename, language=language)
    return transcript, service.model_used or preferred_model, service.attempted_models


def _combined_source_narrative(narrative: str, clarifications: list[tuple[str, str]]) -> str:
    answered = [(question, answer) for question, answer in clarifications if answer.strip()]
    if not answered:
        return narrative.strip()
    additions = "\n".join(f"- {question}\n  {answer.strip()}" for question, answer in answered)
    return f"{narrative.strip()}\n\nErgänzende Antworten:\n{additions}"
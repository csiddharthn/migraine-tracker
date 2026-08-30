from __future__ import annotations

"""Purpose: Entry form for migraine entry input.

Usage: Renders form fields for entry creation and editing.

Functions available:
- render_entry_form

Classes available:
- None

Call hierarchy:
- entry_form.py -> backend.services.schemas, backend.note_interpretation
"""

from datetime import date, time, timedelta
from decimal import Decimal
from typing import Any

import streamlit as st
from pydantic import ValidationError

from backend.ai_intake import AIIntakeDraft
from backend.models import DailyRecord, MigraineEntry, TriggerDefinition
from backend.note_interpretation import StructuredNotes, TimelineNoteRow, format_timeline_notes, parse_structured_notes
from backend.services.schemas import EntryInput, MedicationInput
from frontend.config.name_space import cfg
from frontend.i18n import (
    aura_label,
    canonical_value,
    date_input_format,
    derived_laterality_label,
    localize_value,
    other_symptom_label,
    tr,
    trigger_text,
)


PAIN_TYPES = ["Dumpf / drückend", "Pulsierend / stechend"]
LATERALITIES = ["Einseitig", "Beidseitig", "Rechts", "Links"]
AURA_CODES = ["F", "G", "S", "O", "*"]
OTHER_SYMPTOM_CODES = ["T", "R", "N"]
DERIVED_LATERALITIES = ["unbekannt", "rechts", "links", "beidseitig", "beidseitig_linksbetont", "einseitig_unbekannt"]
CORE_SYMPTOMS = {
    "vomiting": ("Erbrechen", "Vomiting"),
    "nausea": ("Übelkeit", "Nausea"),
    "phonophobia": ("Lärmscheu", "Sound sensitivity"),
    "photophobia": ("Lichtscheu", "Light sensitivity"),
    "osmophobia": ("Geruchsempfindlich", "Smell sensitivity"),
}
SYMPTOM_OPTIONS = [
    *(f"aura:{code}" for code in AURA_CODES),
    *(f"symptom:{field}" for field in CORE_SYMPTOMS),
    *(f"other:{code}" for code in OTHER_SYMPTOM_CODES),
]
DEFAULT_MEDICATIONS = ["Amitriptylin neuraxpharm"]


def render_entry_form(
    trigger_definitions: list[TriggerDefinition],
    medication_options: list[str],
    *,
    existing: MigraineEntry | None = None,
    daily_record: DailyRecord | None = None,
    draft: AIIntakeDraft | None = None,
    key: str,
) -> EntryInput | None:
    triggers_by_code = {item.code: item for item in trigger_definitions}
    existing_trigger_codes = {item.trigger_code for item in existing.triggers} if existing else set(draft.trigger_codes if draft else [])
    default_triggers = [code for code in triggers_by_code if code in existing_trigger_codes]
    symptom_defaults = _symptom_defaults(existing) if existing else _draft_symptom_defaults(draft)
    existing_interpretation = existing.interpretation if existing else None
    if draft is not None and existing is None:
        note_defaults = draft.structured_notes()
    else:
        note_defaults = parse_structured_notes(
            existing.timeline_notes if existing else "",
            peak_start_minute=existing_interpretation.peak_start_minute if existing_interpretation else None,
            peak_end_minute=existing_interpretation.peak_end_minute if existing_interpretation else None,
        )
    timeline_defaults = list(note_defaults.timeline) or [TimelineNoteRow()]
    timeline_count_key = f"timeline_count_{key}"
    if timeline_count_key not in st.session_state:
        st.session_state[timeline_count_key] = len(timeline_defaults)
    timeline_row_count = max(1, int(st.session_state[timeline_count_key]))
    medication_defaults = [
        MedicationInput(
            name=item.name,
            taken_at=item.taken_at,
            dose=item.dose,
            effectiveness=item.effectiveness,
        )
        for item in (existing.medications if existing else draft.medications if draft else [])
    ]
    default_amitriptyline = bool(
        (daily_record and daily_record.amitriptyline_neuraxpharm)
        or (draft and draft.amitriptyline_neuraxpharm)
    )
    if default_amitriptyline and not any(
        "amitriptylin" in item.name.casefold() for item in medication_defaults
    ):
        medication_defaults.append(MedicationInput(name="Amitriptylin neuraxpharm"))
    medication_count_key = f"medication_count_{key}"
    if medication_count_key not in st.session_state:
        st.session_state[medication_count_key] = max(1, len(medication_defaults))
    medication_row_count = max(1, int(st.session_state[medication_count_key]))

    with st.form(f"entry_form_{key}", clear_on_submit=False):
        st.subheader(tr(cfg, "Pflichtangaben", "Required information"))
        date_col, strength_col, duration_col = st.columns([1.2, 1, 1])
        entry_date = date_col.date_input(
            tr(cfg, "Datum", "Date"),
            value=existing.entry_date if existing else draft.entry_date if draft and draft.entry_date else date.today(),
            max_value=date.today(),
            format=date_input_format(cfg, ),
        )
        strength = strength_col.slider(
            tr(cfg, "Stärke", "Intensity"),
            0,
            10,
            existing.strength if existing else draft.strength if draft and draft.strength is not None else 5,
        )
        duration = duration_col.number_input(
            tr(cfg, "Dauer (Stunden)", "Duration (hours)"),
            min_value=0.0,
            max_value=168.0,
            value=float(existing.duration_hours) if existing else float(draft.duration_hours) if draft and draft.duration_hours is not None else 1.0,
            step=0.5,
        )
        selected_trigger_codes = st.multiselect(
            tr(cfg, "Auslöser", "Triggers"),
            list(triggers_by_code),
            default=default_triggers,
            format_func=lambda code: trigger_text(cfg, code, triggers_by_code[code].label),
            placeholder=tr(cfg, "Mindestens einen Auslöser auswählen", "Select at least one trigger"),
        )

        st.subheader(tr(cfg, "Schmerzbild", "Pain profile"))
        pain_col, side_col = st.columns(2)
        pain_options: list[str | None] = [None, *PAIN_TYPES]
        pain_type = pain_col.selectbox(
            tr(cfg, "Schmerzart", "Pain type"),
            pain_options,
            index=_choice_index(pain_options, existing.pain_type if existing else draft.pain_type if draft else None),
            format_func=lambda value: tr(cfg, "Nicht ausgewählt", "Not selected") if value is None else localize_value(cfg, value),
        )
        laterality_options: list[str | None] = [None, *LATERALITIES]
        laterality = side_col.selectbox(
            tr(cfg, "Schmerzseite", "Side of pain"),
            laterality_options,
            index=_choice_index(laterality_options, existing.entered_laterality if existing else draft.entered_laterality if draft else None),
            format_func=lambda value: tr(cfg, "Nicht ausgewählt", "Not selected") if value is None else localize_value(cfg, value),
        )

        st.subheader(tr(cfg, "Begleitsymptome", "Associated symptoms"))
        selected_symptoms = st.multiselect(
            tr(cfg, "Symptome", "Symptoms"),
            SYMPTOM_OPTIONS,
            default=symptom_defaults,
            format_func=_symptom_option_label,
            placeholder=tr(cfg, "Begleitsymptome auswählen", "Select associated symptoms"),
        )

        st.subheader(tr(cfg, "Medikation und Behandlung", "Medication and treatment"))
        known_names = list(dict.fromkeys([*DEFAULT_MEDICATIONS, *medication_options]))
        effect_options: list[str | None] = [None, "Ja", "Teilweise", "Nein"]
        medication_values: list[dict[str, Any]] = []
        for row_index in range(medication_row_count):
            default_item = medication_defaults[row_index] if row_index < len(medication_defaults) else None
            current_name = default_item.name if default_item else None
            row_names: list[str | None] = [None, *known_names]
            if current_name and current_name not in row_names:
                row_names.insert(1, current_name)
            med_col, time_col, dose_col, effect_col = st.columns([1.5, 0.8, 0.8, 1.2])
            medication_name = med_col.selectbox(
                tr(cfg, f"Medikament {row_index + 1}", f"Medication {row_index + 1}"),
                row_names,
                index=row_names.index(current_name),
                format_func=lambda value: tr(cfg, "Keine Auswahl", "No selection") if value is None else value,
                placeholder=tr(cfg, "Auswählen oder neu eingeben", "Select or enter a new medication"),
                accept_new_options=True,
                filter_mode="fuzzy",
                key=f"medication_name_{key}_{row_index}",
            )
            medication_taken_at = time_col.time_input(
                tr(cfg, f"Einnahmezeit {row_index + 1}", f"Time taken {row_index + 1}"),
                value=default_item.taken_at if default_item else None,
                step=timedelta(minutes=5),
                format="24h",
                key=f"medication_time_{key}_{row_index}",
            )
            medication_dose = dose_col.text_input(
                tr(cfg, f"Dosis / Form {row_index + 1}", f"Dose / form {row_index + 1}"),
                value=default_item.dose or "" if default_item else "",
                key=f"medication_dose_{key}_{row_index}",
            )
            effectiveness = effect_col.selectbox(
                tr(cfg, f"Hat geholfen? {row_index + 1}", f"Did it help? {row_index + 1}"),
                effect_options,
                index=_choice_index(effect_options, default_item.effectiveness if default_item else None),
                format_func=lambda value: tr(cfg, "Nicht dokumentiert", "Not documented") if value is None else localize_value(cfg, value),
                key=f"medication_effect_{key}_{row_index}",
            )
            medication_values.append(
                {
                    "name": medication_name,
                    "taken_at": medication_taken_at,
                    "dose": medication_dose.strip(),
                    "effectiveness": effectiveness,
                }
            )
        medication_actions = st.columns([1, 1, 3])
        add_medication_row = medication_actions[0].form_submit_button(
            tr(cfg, "Medikament hinzufügen", "Add medication"),
            icon=":material/add:",
            width="stretch",
        )
        remove_medication_row = medication_actions[1].form_submit_button(
            tr(cfg, "Letztes entfernen", "Remove last"),
            icon=":material/remove:",
            disabled=medication_row_count <= 1,
            width="stretch",
        )
        preventive_cols = st.columns([1, 1, 2])
        aimovig = preventive_cols[0].checkbox(
            tr(cfg, "Aimovig-Injektion", "Aimovig injection"),
            value=bool((daily_record and daily_record.aimovig_injection) or (draft and draft.aimovig_injection)),
        )
        momeallerg = preventive_cols[1].checkbox(
            "Momeallerg Nasenspray",
            value=bool((daily_record and daily_record.momeallerg_nasal_spray) or (draft and draft.momeallerg_nasal_spray)),
        )

        st.subheader(tr(cfg, "Notizen", "Notes"))
        st.markdown(f"**{tr(cfg, 'Zeitlicher Ablauf', 'Timeline')}**")
        timeline_header = st.columns([1, 1, 3])
        timeline_header[0].caption(tr(cfg, "Start", "Start"))
        timeline_header[1].caption(tr(cfg, "Ende", "End"))
        timeline_header[2].caption(tr(cfg, "Notiz", "Note"))
        timeline_values: list[TimelineNoteRow] = []
        for row_index in range(timeline_row_count):
            default_row = timeline_defaults[row_index] if row_index < len(timeline_defaults) else TimelineNoteRow()
            timeline_columns = st.columns([1, 1, 3])
            start_time = timeline_columns[0].time_input(
                tr(cfg, f"Startzeit Zeile {row_index + 1}", f"Start time row {row_index + 1}"),
                value=default_row.start_time,
                key=f"timeline_start_{key}_{row_index}",
                label_visibility="collapsed",
                step=timedelta(minutes=5),
                format="24h",
            )
            end_time = timeline_columns[1].time_input(
                tr(cfg, f"Endzeit Zeile {row_index + 1}", f"End time row {row_index + 1}"),
                value=default_row.end_time,
                key=f"timeline_end_{key}_{row_index}",
                label_visibility="collapsed",
                step=timedelta(minutes=5),
                format="24h",
            )
            row_note = timeline_columns[2].text_input(
                tr(cfg, f"Notiz Zeile {row_index + 1}", f"Note row {row_index + 1}"),
                value=default_row.note,
                key=f"timeline_note_{key}_{row_index}",
                label_visibility="collapsed",
                placeholder=tr(cfg, "Ereignis oder Beobachtung", "Event or observation"),
            )
            timeline_values.append(TimelineNoteRow(start_time=start_time, end_time=end_time, note=row_note.strip()))
        timeline_actions = st.columns([1, 1, 3])
        add_timeline_row = timeline_actions[0].form_submit_button(
            tr(cfg, "Zeile hinzufügen", "Add row"),
            icon=":material/add:",
            width="stretch",
        )
        remove_timeline_row = timeline_actions[1].form_submit_button(
            tr(cfg, "Letzte Zeile entfernen", "Remove last row"),
            icon=":material/remove:",
            disabled=timeline_row_count <= 1,
            width="stretch",
        )

        st.markdown(f"**{tr(cfg, 'Höhepunkt', 'Peak')}**")
        peak_clock_default = _minute_clock(note_defaults.peak_start_minute)
        peak_time_col, peak_duration_col = st.columns([1, 1.3])
        peak_clock = peak_time_col.time_input(
            tr(cfg, "Höhepunkt erreicht um", "Peak reached at"),
            value=peak_clock_default,
            step=timedelta(minutes=5),
            format="24h",
        )
        peak_duration_minutes = peak_duration_col.number_input(
            tr(cfg, "Dauer am Höhepunkt (Minuten)", "Time at peak (minutes)"),
            min_value=0,
            max_value=1440,
            value=note_defaults.peak_duration_minutes,
            step=15,
        )

        possible_factors = st.text_area(
            tr(cfg, "Mögliche Einflussfaktoren", "Possible contributing factors"),
            value=existing.possible_factors if existing else note_defaults.possible_factors,
            height=120,
        )
        symptoms_and_actions = st.text_area(
            tr(cfg, "Beschwerden und Maßnahmen", "Symptoms and actions"),
            value=existing.symptoms_and_actions if existing else note_defaults.symptoms_and_actions,
            height=150,
        )
        other_notes = st.text_area(
            tr(cfg, "Andere Notizen", "Other notes"),
            value=existing.other_notes if existing else "",
            height=100,
        )
        submitted = st.form_submit_button(tr(cfg, "Eintrag speichern", "Save entry"), type="primary", width="stretch")

    if not submitted:
        if add_medication_row:
            st.session_state[medication_count_key] = medication_row_count + 1
            st.rerun()
        if remove_medication_row:
            removed_index = medication_row_count - 1
            for field in ("name", "time", "dose", "effect"):
                st.session_state.pop(f"medication_{field}_{key}_{removed_index}", None)
            st.session_state[medication_count_key] = medication_row_count - 1
            st.rerun()
        if add_timeline_row:
            st.session_state[timeline_count_key] = timeline_row_count + 1
            st.rerun()
        if remove_timeline_row:
            removed_index = timeline_row_count - 1
            for field in ("start", "end", "note"):
                st.session_state.pop(f"timeline_{field}_{key}_{removed_index}", None)
            st.session_state[timeline_count_key] = timeline_row_count - 1
            st.rerun()
        return None
    medication_error = _medication_validation_error(medication_values)
    if medication_error:
        st.error(medication_error)
        return None
    medications = [
        MedicationInput(**item)
        for item in medication_values
        if item["name"] is not None
    ]
    timeline_rows = [
        row
        for row in timeline_values
        if row.start_time is not None or row.end_time is not None or row.note
    ]
    timeline_error = _timeline_validation_error(timeline_rows)
    if timeline_error:
        st.error(timeline_error)
        return None
    if peak_clock is None and peak_duration_minutes > 0:
        st.error(tr(cfg, "Bitte geben Sie die Uhrzeit des Höhepunkts an oder setzen Sie dessen Dauer auf 0 Minuten.", "Enter the peak time or set its duration to 0 minutes."))
        return None
    peak_start_minute = _peak_minute_for_form_value(peak_clock, note_defaults.peak_start_minute)
    structured_notes = StructuredNotes(
        timeline=tuple(timeline_rows),
        peak_start_minute=peak_start_minute,
        peak_duration_minutes=int(peak_duration_minutes),
        possible_factors=possible_factors.strip(),
        symptoms_and_actions=symptoms_and_actions.strip(),
    )
    note_fields_changed = existing is None or (
        structured_notes.timeline != (parse_structured_notes(existing.timeline_notes or "").timeline if existing else ())
        or structured_notes.possible_factors != (existing.possible_factors or "")
        or structured_notes.symptoms_and_actions != (existing.symptoms_and_actions or "")
        or other_notes.strip() != (existing.other_notes or "")
    )
    timeline_notes_text = format_timeline_notes(structured_notes) if note_fields_changed else (existing.timeline_notes if existing else "")
    note_annotation = None
    if note_fields_changed and peak_start_minute is not None:
        note_annotation = {
            "peakStartMinute": peak_start_minute,
            "peakEndMinute": peak_start_minute + int(peak_duration_minutes) if peak_duration_minutes > 0 else None,
            "confidence": "hoch",
        }
    symptom_values = _decode_symptom_selection(selected_symptoms)
    try:
        return EntryInput(
            entry_date=entry_date,
            trigger_codes=selected_trigger_codes,
            strength=strength,
            duration_hours=Decimal(str(duration)),
            pain_type=pain_type,
            entered_laterality=laterality,
            aura_codes=symptom_values["aura_codes"],
            vomiting=symptom_values["vomiting"],
            nausea=symptom_values["nausea"],
            phonophobia=symptom_values["phonophobia"],
            photophobia=symptom_values["photophobia"],
            osmophobia=symptom_values["osmophobia"],
            other_symptom_codes=symptom_values["other_symptom_codes"],
            medications=medications,
            timeline_notes=timeline_notes_text,
            possible_factors=possible_factors.strip(),
            symptoms_and_actions=symptoms_and_actions.strip(),
            other_notes=other_notes.strip(),
            note_annotation=note_annotation,
            aimovig_injection=aimovig,
            momeallerg_nasal_spray=momeallerg,
            amitriptyline_neuraxpharm=any("amitriptylin" in item.name.casefold() for item in medications),
        )
    except ValidationError as exc:
        messages = []
        for error in exc.errors():
            field_key = ".".join(str(part) for part in error["loc"])
            field = {
                "trigger_codes": tr(cfg, "Auslöser", "Triggers"),
                "strength": tr(cfg, "Stärke", "Intensity"),
                "duration_hours": tr(cfg, "Dauer", "Duration"),
                "entry_date": tr(cfg, "Datum", "Date"),
            }.get(field_key, field_key)
            message = error["msg"]
            if field_key == "trigger_codes" and error["type"] == "too_short":
                message = tr(cfg, "Mindestens ein Auslöser ist erforderlich.", "At least one trigger is required.")
            messages.append(f"{field}: {message}")
        st.error(tr(cfg, "Bitte korrigieren Sie die Pflichtangaben: ", "Please correct the required information: ") + " · ".join(messages))
        return None


def render_interpretation_review(entry: MigraineEntry) -> dict[str, Any] | None:
    interpretation = entry.interpretation
    if interpretation is None:
        st.info(tr(cfg, "Für diesen Eintrag wurden noch keine Angaben automatisch aus der Notiz erkannt.", "No information has yet been recognised automatically from the note for this entry."))
        return None
    with st.form(f"interpretation_{entry.id}"):
        st.caption(tr(cfg, "Diese Angaben wurden automatisch im Notiztext erkannt. Sie können sie hier korrigieren. Der ursprüngliche Notiztext bleibt dabei unverändert.", "This information was recognised automatically in the note text. You can correct it here. The original note text remains unchanged."))
        onset = _minute_control(tr(cfg, "Beginn", "Onset"), interpretation.onset_minute, "onset")
        peak_start = _minute_control(tr(cfg, "Höhepunkt Beginn", "Peak start"), interpretation.peak_start_minute, "peak_start")
        peak_end = _minute_control(tr(cfg, "Höhepunkt Ende", "Peak end"), interpretation.peak_end_minute, "peak_end")
        end = _minute_control(tr(cfg, "Ende", "End"), interpretation.end_minute, "end")
        laterality = st.selectbox(tr(cfg, "Automatisch erkannte Schmerzseite", "Automatically recognised side of pain"), DERIVED_LATERALITIES, index=_choice_index(DERIVED_LATERALITIES, interpretation.laterality), format_func=lambda code: derived_laterality_label(cfg, code))
        side_detail = st.text_input(tr(cfg, "Genauere Angabe zur Schmerzseite", "More detail about the side of pain"), value=localize_value(cfg, interpretation.side_detail or ""))
        contexts = st.text_area(tr(cfg, "Erkannte Begleitumstände (eine Angabe pro Zeile)", "Recognised circumstances (one item per line)"), value="\n".join(str(localize_value(cfg, value)) for value in interpretation.contexts), height=110)
        symptoms = st.text_area(tr(cfg, "Erkannte Symptome (eine Angabe pro Zeile)", "Recognised symptoms (one item per line)"), value="\n".join(str(localize_value(cfg, value)) for value in interpretation.symptoms), height=90)
        interventions = st.text_area(tr(cfg, "Erkannte Maßnahmen (eine Angabe pro Zeile)", "Recognised interventions (one item per line)"), value="\n".join(str(localize_value(cfg, value)) for value in interpretation.interventions), height=90)
        submitted = st.form_submit_button(tr(cfg, "Korrigierte Angaben speichern", "Save corrected information"), type="primary")
    if not submitted:
        return None
    return {
        "onset_minute": onset,
        "peak_start_minute": peak_start,
        "peak_end_minute": peak_end,
        "end_minute": end,
        "laterality": laterality,
        "side_detail": canonical_value(cfg, side_detail.strip()) or None,
        "contexts": [canonical_value(cfg, value) for value in _lines(contexts)],
        "symptoms": [canonical_value(cfg, value) for value in _lines(symptoms)],
        "interventions": [canonical_value(cfg, value) for value in _lines(interventions)],
    }


def _minute_control(label: str, value: int | None, key: str) -> int | None:
    enabled = st.checkbox(f"{label} {tr(cfg, 'ist in der Notiz angegeben', 'is stated in the note')}", value=value is not None, key=f"{key}_enabled")
    columns = st.columns([2, 1])
    base = value or 0
    clock = columns[0].time_input(label, value=time((base % 1440) // 60, base % 60), disabled=not enabled, key=f"{key}_time")
    day_offset = columns[1].selectbox(
        tr(cfg, "Tag des Zeitpunkts", "Day of this time"),
        [0, 1, 2],
        index=min(2, base // 1440),
        format_func=lambda offset: {
            0: tr(cfg, "Gleicher Tag", "Same day"),
            1: tr(cfg, "Nächster Tag", "Next day"),
            2: tr(cfg, "Zwei Tage später", "Two days later"),
        }[offset],
        disabled=not enabled,
        key=f"{key}_day",
    )
    return day_offset * 1440 + clock.hour * 60 + clock.minute if enabled else None


def _choice_index(options: list[Any], value: Any) -> int:
    return options.index(value) if value in options else 0


def _timeline_validation_error(rows: list[TimelineNoteRow]) -> str | None:
    for index, row in enumerate(rows, start=1):
        if row.end_time is not None and row.start_time is None:
            return tr(cfg, f"Zeitlicher Ablauf, Zeile {index}: Eine Endzeit benötigt eine Startzeit.", f"Timeline, row {index}: An end time requires a start time.")
        if (row.start_time is not None or row.end_time is not None) and not row.note:
            return tr(cfg, f"Zeitlicher Ablauf, Zeile {index}: Bitte ergänzen Sie die Notiz zum Zeitpunkt.", f"Timeline, row {index}: Add a note for this time.")
    return None


def _medication_validation_error(rows: list[dict[str, Any]]) -> str | None:
    for index, row in enumerate(rows, start=1):
        has_details = row["taken_at"] is not None or bool(row["dose"]) or row["effectiveness"] is not None
        if row["name"] is None and has_details:
            return tr(cfg, 
                f"Medikation, Zeile {index}: Bitte wählen Sie ein Medikament aus.",
                f"Medication, row {index}: Select a medication.",
            )
    return None


def _minute_clock(value: int | None) -> time | None:
    if value is None:
        return None
    minute = value % 1440
    return time(minute // 60, minute % 60)


def _peak_minute_for_form_value(clock: time | None, default_minute: int | None) -> int | None:
    if clock is None:
        return None
    if default_minute is not None and clock == _minute_clock(default_minute):
        return default_minute
    return clock.hour * 60 + clock.minute


def _symptom_defaults(existing: MigraineEntry | None) -> list[str]:
    if existing is None:
        return []
    defaults = [f"aura:{code}" for code in AURA_CODES if code in existing.aura_codes]
    defaults.extend(f"symptom:{field}" for field in CORE_SYMPTOMS if getattr(existing, field))
    defaults.extend(f"other:{code}" for code in OTHER_SYMPTOM_CODES if code in existing.other_symptom_codes)
    return defaults


def _draft_symptom_defaults(draft: AIIntakeDraft | None) -> list[str]:
    if draft is None:
        return []
    defaults = [f"aura:{code}" for code in AURA_CODES if code in draft.aura_codes]
    defaults.extend(f"symptom:{field}" for field in CORE_SYMPTOMS if getattr(draft, field) is True)
    defaults.extend(f"other:{code}" for code in OTHER_SYMPTOM_CODES if code in draft.other_symptom_codes)
    return defaults


def _symptom_option_label(option: str) -> str:
    category, value = option.split(":", 1)
    if category == "aura":
        return f"{tr(cfg, 'Vorboten / Aura', 'Aura')}: {aura_label(cfg, value)}"
    if category == "symptom":
        german, english = CORE_SYMPTOMS[value]
        return tr(cfg, german, english)
    return f"{tr(cfg, 'Andere Symptome', 'Other symptoms')}: {other_symptom_label(cfg, value)}"


def _decode_symptom_selection(selected: list[str]) -> dict[str, Any]:
    values = set(selected)
    return {
        "aura_codes": [code for code in AURA_CODES if f"aura:{code}" in values],
        **{field: f"symptom:{field}" in values for field in CORE_SYMPTOMS},
        "other_symptom_codes": [code for code in OTHER_SYMPTOM_CODES if f"other:{code}" in values],
    }


def _lines(value: str) -> list[str]:
    return list(dict.fromkeys(line.strip() for line in value.splitlines() if line.strip()))

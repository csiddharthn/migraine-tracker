from __future__ import annotations

"""Purpose: Internationalization and translation utilities.

Usage: Provides tr(), current_language(), and localize_value().

Functions available:
- current_language, tr, localize_value

Classes available:
- None

Call hierarchy:
- i18n.py -> frontend.config.name_space
"""

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from frontend.config.name_space import cfg

import streamlit as st


def current_language(cfg) -> str:
    try:
        value = st.session_state.get("app_language", cfg.DEFAULT_LANGUAGE)
    except Exception:
        return cfg.DEFAULT_LANGUAGE
    return value if value in cfg.LANGUAGE_LABELS else cfg.DEFAULT_LANGUAGE


def tr(cfg, german: str, english: str, *, lang: str | None = None) -> str:
    return english if (lang or current_language(cfg)) == "en" else german


def localize_value(cfg, value: Any, *, lang: str | None = None) -> Any:
    resolved_language = lang or current_language(cfg)
    if not isinstance(value, str):
        return value
    if " · " in value:
        return " · ".join(str(localize_value(part, lang=lang)) for part in value.split(" · "))
    if value in cfg.AURA_LABELS:
        return aura_label(value, lang=resolved_language)
    if value in cfg.OTHER_SYMPTOM_LABELS:
        return other_symptom_label(value, lang=resolved_language)
    if value in cfg.CODE_LABELS:
        german, english = cfg.CODE_LABELS[value]
        return tr(german, english, lang=resolved_language)
    next_day = re.match(r"^(\d{2}:\d{2}) \(nächster Tag\)$", value)
    if next_day:
        return tr(value, f"{next_day.group(1)} (next day)", lang=resolved_language)
    later_day = re.match(r"^(\d{2}:\d{2}) \((\d+) Tage später\)$", value)
    if later_day:
        return tr(value, f"{later_day.group(1)} ({later_day.group(2)} days later)", lang=resolved_language)
    if resolved_language != "en":
        return value
    if value in cfg.VALUE_TRANSLATIONS:
        return cfg.VALUE_TRANSLATIONS[value]
    if value.startswith("Vorboten: "):
        code = value.removeprefix("Vorboten: ")
        return f"Aura: {aura_label(code, lang=lang)}"
    if value.startswith("Andere Symptome: "):
        code = value.removeprefix("Andere Symptome: ")
        return f"Other symptoms: {other_symptom_label(code, lang=lang)}"
    trigger_match = re.match(r"^([A-Z0-9*]+)\s+–\s+(.+)$", value)
    if trigger_match and trigger_match.group(1) in cfg.TRIGGER_LABELS_EN:
        return f"{trigger_match.group(1)} – {cfg.TRIGGER_LABELS_EN[trigger_match.group(1)]}"
    for index, month in enumerate(cfg.MONTHS_DE):
        if value.startswith(f"{month} "):
            return value.replace(month, cfg.MONTHS_EN[index], 1)
    return value


def canonical_value(cfg, value: str, *, lang: str | None = None) -> str:
    if (lang or current_language(cfg)) != "en":
        return value
    if value.startswith("Aura: "):
        label = value.removeprefix("Aura: ")
        code = next((code for code in cfg.AURA_LABELS if aura_label(code, lang="en") == label), label)
        return f"Vorboten: {code}"
    if value.startswith("Other symptoms: "):
        label = value.removeprefix("Other symptoms: ")
        code = next((code for code in cfg.OTHER_SYMPTOM_LABELS if other_symptom_label(code, lang="en") == label), label)
        return f"Andere Symptome: {code}"
    code_reverse = {english: code for code, (_, english) in cfg.CODE_LABELS.items()}
    if value in code_reverse:
        return code_reverse[value]
    reverse = {english: german for german, english in cfg.VALUE_TRANSLATIONS.items()}
    return reverse.get(value, value)


def column_label(cfg, value: str, *, lang: str | None = None) -> str:
    if (lang or current_language(cfg)) == "en":
        return cfg.COLUMN_TRANSLATIONS.get(value, value)
    return value


def localize_items(cfg, items: list[dict[str, Any]], *, lang: str | None = None) -> list[dict[str, Any]]:
    return [
        {**item, "label": localize_value(cfg, item.get("label"), lang=lang)}
        for item in items
    ]


def yes_no(cfg, value: bool, *, lang: str | None = None) -> str:
    return tr("Ja", "Yes", lang=lang) if value else tr("Nein", "No", lang=lang)


def aura_label(cfg, code: str, *, lang: str | None = None) -> str:
    german, english = cfg.AURA_LABELS.get(code, (code, code))
    return tr(german, english, lang=lang)


def other_symptom_label(cfg, code: str, *, lang: str | None = None) -> str:
    german, english = cfg.OTHER_SYMPTOM_LABELS.get(code, (code, code))
    return tr(german, english, lang=lang)


def derived_laterality_label(cfg, code: str, *, lang: str | None = None) -> str:
    german, english = cfg.DERIVED_LATERALITY_LABELS.get(code, (code, code))
    return tr(german, english, lang=lang)


def trigger_label(cfg, code: str, stored_label: str, *, lang: str | None = None) -> str:
    if (lang or current_language(cfg)) == "en":
        return cfg.TRIGGER_LABELS_EN.get(code, stored_label)
    return stored_label


def trigger_description(cfg, code: str, stored_description: str, *, lang: str | None = None) -> str:
    if (lang or current_language(cfg)) == "en":
        return cfg.TRIGGER_DESCRIPTIONS_EN.get(code, stored_description)
    return stored_description


def trigger_text(cfg, code: str, stored_label: str, *, lang: str | None = None) -> str:
    return trigger_label(cfg, code, stored_label, lang=lang)


def month_label(cfg, month_key: str, *, lang: str | None = None) -> str:
    year, month = month_key.split("-", 1)
    names = cfg.MONTHS_EN if (lang or current_language(cfg)) == "en" else cfg.MONTHS_DE
    return f"{names[int(month) - 1]} {year}"


def format_date_value(cfg, value: date | None, *, lang: str | None = None) -> str:
    if value is None:
        return "–"
    return value.strftime("%Y-%m-%d" if (lang or current_language(cfg)) == "en" else "%d.%m.%Y")


def format_datetime_value(cfg, value: datetime | None, *, lang: str | None = None) -> str:
    if value is None:
        return "–"
    return value.astimezone().strftime("%Y-%m-%d %H:%M" if (lang or current_language(cfg)) == "en" else "%d.%m.%Y %H:%M")


def date_input_format(cfg, *, lang: str | None = None) -> str:
    return "YYYY-MM-DD" if (lang or current_language(cfg)) == "en" else "DD.MM.YYYY"


def format_number(cfg, value: float | Decimal | None, digits: int = 1, *, lang: str | None = None) -> str:
    if value is None:
        return "–"
    text = f"{float(value):.{digits}f}"
    return text if (lang or current_language(cfg)) == "en" else text.replace(".", ",")


def error_message(cfg, error: Exception | str, *, lang: str | None = None) -> str:
    text = str(error)
    if (lang or current_language(cfg)) != "en":
        return text
    if text in cfg.ERROR_TRANSLATIONS:
        return cfg.ERROR_TRANSLATIONS[text]
    duplicate_date = re.match(r"Für den (.+) existiert bereits ein Eintrag\.", text)
    if duplicate_date:
        return f"An entry already exists for {duplicate_date.group(1)}."
    unknown = re.match(r"Unbekannte Auslöser-Codes: (.+)", text)
    if unknown:
        return f"Unknown trigger codes: {unknown.group(1)}"
    return text

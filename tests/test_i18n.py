from __future__ import annotations

from datetime import date

from frontend.config.name_space import cfg
from frontend.i18n import (
    canonical_value,
    format_date_value,
    format_number,
    localize_value,
    month_label,
    trigger_text,
)

LANG_DE = "de"
LANG_EN = "en"
MONTH_2026_06 = "2026-06"
DATE_2026_06_09 = date(2026, 6, 9)
NUMBER_VALUE = 5.25
TRIGGER_CODE_5 = "5"
TRIGGER_LABEL_DE_5 = "Kalte Schlafumgebung / Fenster offen"
TRIGGER_LABEL_EN_5 = "Cold sleeping environment / open window"
TRIGGER_CODE_P1 = "P1"
TRIGGER_LABEL_DE_P1 = "Persönlicher Auslöser"
TRIGGER_LABEL_EN_P1 = "Personal trigger"
CANONICAL_COLD_DRAFT = "Kälte / Zugluft"
TRANSLATED_COLD_DRAFT = "Cold / draught"
CANONICAL_RIGHT = "Rechts"
TRANSLATED_RIGHT = "Right"


def test_month_date_and_number_formats_follow_language() -> None:
    assert month_label(cfg, MONTH_2026_06, lang=LANG_DE) == "Juni 2026"
    assert month_label(cfg, MONTH_2026_06, lang=LANG_EN) == "June 2026"
    assert format_date_value(cfg, DATE_2026_06_09, lang=LANG_DE) == "09.06.2026"
    assert format_date_value(cfg, DATE_2026_06_09, lang=LANG_EN) == "2026-06-09"
    assert format_number(cfg, NUMBER_VALUE, 2, lang=LANG_DE) == "5,25"
    assert format_number(cfg, NUMBER_VALUE, 2, lang=LANG_EN) == "5.25"
    assert format_number(cfg, NUMBER_VALUE, 2, lang=LANG_EN) == "5.25"


def test_stored_values_are_localized_without_changing_the_canonical_value() -> None:
    translated = localize_value(cfg, CANONICAL_COLD_DRAFT, lang=LANG_EN)
    assert translated == TRANSLATED_COLD_DRAFT
    assert canonical_value(cfg, translated, lang=LANG_EN) == CANONICAL_COLD_DRAFT
    assert localize_value(cfg, CANONICAL_RIGHT, lang=LANG_EN) == TRANSLATED_RIGHT


def test_builtin_trigger_labels_are_localized_by_stable_code() -> None:
    assert trigger_text(cfg, TRIGGER_CODE_5, TRIGGER_LABEL_DE_5, lang=LANG_EN) == TRIGGER_LABEL_EN_5
    assert trigger_text(cfg, TRIGGER_CODE_P1, TRIGGER_LABEL_DE_P1, lang=LANG_EN) == TRIGGER_LABEL_EN_P1
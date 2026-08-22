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

# Month / date test values
MONTH_2026_06 = "2026-06"
MONTH_LABEL_DE = "Juni 2026"
MONTH_LABEL_EN = "June 2026"
DATE_2026_06_09 = date(2026, 6, 9)
DATE_FORMAT_DE = "09.06.2026"
DATE_FORMAT_EN = "2026-06-09"

# Number formatting
NUMBER_VALUE = 5.25
NUMBER_PRECISION = 2
NUMBER_FORMAT_DE = "5,25"
NUMBER_FORMAT_EN = "5.25"

# Localization values
CANONICAL_COLD_DRAFT = "Kälte / Zugluft"
TRANSLATED_COLD_DRAFT = "Cold / draught"
CANONICAL_RIGHT_EYE = "rechts, im Bereich des rechten Auges"
TRANSLATED_RIGHT_EYE = "right, around the right eye"

# Trigger codes and labels
TRIGGER_CODE_5 = "5"
TRIGGER_LABEL_5_DE = "Kalte Schlafumgebung / Fenster offen"
TRIGGER_LABEL_5_EN = "Cold sleeping environment / open window"
TRIGGER_CODE_P1 = "P1"
TRIGGER_LABEL_P1_DE = "Eigener Auslöser"


def test_month_date_and_number_formats_follow_language() -> None:
    assert month_label(cfg, MONTH_2026_06, lang=LANG_DE) == MONTH_LABEL_DE
    assert month_label(cfg, MONTH_2026_06, lang=LANG_EN) == MONTH_LABEL_EN
    assert format_date_value(cfg, DATE_2026_06_09, lang=LANG_DE) == DATE_FORMAT_DE
    assert format_date_value(cfg, DATE_2026_06_09, lang=LANG_EN) == DATE_FORMAT_EN
    assert format_number(cfg, NUMBER_VALUE, NUMBER_PRECISION, lang=LANG_DE) == NUMBER_FORMAT_DE
    assert format_number(cfg, NUMBER_VALUE, NUMBER_PRECISION, lang=LANG_EN) == NUMBER_FORMAT_EN


def test_stored_values_are_localized_without_changing_the_canonical_value() -> None:
    translated = localize_value(cfg, CANONICAL_COLD_DRAFT, lang=LANG_EN)

    assert translated == TRANSLATED_COLD_DRAFT
    assert canonical_value(cfg, translated, lang=LANG_EN) == CANONICAL_COLD_DRAFT
    assert localize_value(cfg, CANONICAL_RIGHT_EYE, lang=LANG_EN) == TRANSLATED_RIGHT_EYE


def test_builtin_trigger_labels_are_localized_by_stable_code(cfg) -> None:
    assert trigger_text(cfg, TRIGGER_CODE_5, TRIGGER_LABEL_5_DE, lang=LANG_EN) == TRIGGER_LABEL_5_EN
    assert trigger_text(cfg, TRIGGER_CODE_P1, TRIGGER_LABEL_P1_DE, lang=LANG_EN) == TRIGGER_LABEL_P1_DE
from __future__ import annotations

from datetime import date

from frontend.i18n import (
    canonical_value,
    format_date_value,
    format_number,
    localize_value,
    month_label,
    trigger_text,
)


def test_month_date_and_number_formats_follow_language() -> None:
    assert month_label("2026-06", lang="de") == "Juni 2026"
    assert month_label("2026-06", lang="en") == "June 2026"
    assert format_date_value(date(2026, 6, 9), lang="de") == "09.06.2026"
    assert format_date_value(date(2026, 6, 9), lang="en") == "2026-06-09"
    assert format_number(5.25, 2, lang="de") == "5,25"
    assert format_number(5.25, 2, lang="en") == "5.25"


def test_stored_values_are_localized_without_changing_the_canonical_value() -> None:
    translated = localize_value("Kälte / Zugluft", lang="en")

    assert translated == "Cold / draught"
    assert canonical_value(translated, lang="en") == "Kälte / Zugluft"
    assert localize_value("rechts, im Bereich des rechten Auges", lang="en") == "right, around the right eye"


def test_builtin_trigger_labels_are_localized_by_stable_code() -> None:
    assert trigger_text("5", "Kalte Schlafumgebung / Fenster offen", lang="en") == "Cold sleeping environment / open window"
    assert trigger_text("P1", "Eigener Auslöser", lang="en") == "Eigener Auslöser"

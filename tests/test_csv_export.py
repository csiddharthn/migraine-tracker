from __future__ import annotations

"""Focused tests for the database-table CSV download."""

import csv
import io
from datetime import date, datetime

import pandas as pd

from frontend.components.csv_export import dataframe_to_semicolon_csv


def test_semicolon_csv_matches_german_display_and_keeps_one_line_per_record() -> None:
    frame = pd.DataFrame(
        {
            "Datum": [date(2026, 8, 29), date(2026, 8, 30)],
            "Zeitpunkt": [datetime(2026, 8, 29, 16, 5, 7), None],
            "Mögliche Einflussfaktoren": ["Wenig Schlaf; Baby geweckt", "Hitze"],
            "Zeitlicher Ablauf": [
                "10:00–12:00 Uhr: Beginn – leicht.\n\n16:00 Uhr: Höhepunkt.",
                "Keine Beschwerden",
            ],
            "Erbrechen": ["Nein", "Ja"],
        }
    )

    csv_bytes = dataframe_to_semicolon_csv(frame, language="de")
    csv_text = csv_bytes.decode("utf-16")
    separator_hint, table_text = csv_text.split("\r\n", maxsplit=1)
    rows = list(csv.reader(io.StringIO(table_text, newline=""), delimiter=";", quotechar='"'))

    assert csv_bytes.startswith(b"\xff\xfe")
    assert separator_hint == "sep=;"
    assert table_text.startswith("Datum;Zeitpunkt;Mögliche Einflussfaktoren;")
    assert '"Wenig Schlaf; Baby geweckt"' in table_text
    assert len(csv_text.splitlines()) == len(frame) + 2
    assert rows[0] == list(frame.columns)
    assert rows[1] == [
        "29.08.2026",
        "29.08.2026 16:05:07",
        "Wenig Schlaf; Baby geweckt",
        "10:00-12:00 Uhr: Beginn – leicht. 16:00 Uhr: Höhepunkt.",
        "Nein",
    ]
    assert rows[2] == ["30.08.2026", "", "Hitze", "Keine Beschwerden", "Ja"]


def test_semicolon_csv_uses_the_english_table_date_formats() -> None:
    frame = pd.DataFrame(
        {
            "Date": [date(2026, 8, 29)],
            "Timestamp": [datetime(2026, 8, 29, 16, 5, 7)],
        }
    )

    csv_text = dataframe_to_semicolon_csv(frame, language="en").decode("utf-16")
    _, table_text = csv_text.split("\r\n", maxsplit=1)
    rows = list(csv.reader(io.StringIO(table_text, newline=""), delimiter=";", quotechar='"'))

    assert rows[1] == ["2026-08-29", "2026-08-29 16:05:07"]

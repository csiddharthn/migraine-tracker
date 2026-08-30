from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from zipfile import ZipFile

import pandas as pd

from frontend.components.excel_export import dataframe_to_professional_excel


def _xlsx_text(payload: bytes, path: str) -> str:
    with ZipFile(BytesIO(payload)) as archive:
        return archive.read(path).decode("utf-8")


def test_professional_excel_contains_overview_patient_context_and_data_table() -> None:
    frame = pd.DataFrame(
        {
            "Person": ["Test Patient", "Test Patient"],
            "Datum": [date(2026, 8, 29), date(2026, 8, 30)],
            "Stärke": [4, 8],
            "Zeitlicher Ablauf": [
                "10:00–12:00 Uhr: Beginn.\n16:00 Uhr: Höhepunkt.",
                "Keine Beschwerden",
            ],
        }
    )

    payload = dataframe_to_professional_excel(
        frame,
        language="de",
        patient_name="Test Patient",
        tracking_start_date=date(2022, 6, 1),
        patient_active=True,
        area_label="Kopfschmerzeinträge",
        area_description="Dokumentierte Kopfschmerz- und Migränetage.",
        scope="Ausgewählte Person: Test Patient",
        counts={"entries": 42, "daily_records": 120, "interpretations": 15},
        search_term="Höhepunkt",
        include_technical_fields=False,
        exported_at=datetime(2026, 8, 30, 2, 45, 0),
    )

    assert payload.startswith(b"PK")

    workbook_xml = _xlsx_text(payload, "xl/workbook.xml")
    shared_strings = _xlsx_text(payload, "xl/sharedStrings.xml")
    overview_xml = _xlsx_text(payload, "xl/worksheets/sheet1.xml")
    data_xml = _xlsx_text(payload, "xl/worksheets/sheet2.xml")
    table_xml = _xlsx_text(payload, "xl/tables/table1.xml")

    assert 'name="Übersicht"' in workbook_xml
    assert 'name="Daten"' in workbook_xml
    assert "Test Patient" in shared_strings
    assert "Erfassung seit" in shared_strings
    assert "Kopfschmerzeinträge" in shared_strings
    assert "42" not in shared_strings  # metrics are stored as numbers
    assert "Höhepunkt" in shared_strings
    assert "<pane" in data_xml
    assert 'state="frozen"' in data_xml
    assert "<tableParts" in data_xml
    assert 'name="MigraineExportData"' in table_xml
    assert 'tableStyleMedium2' in table_xml
    assert "<mergeCell" in overview_xml


def test_professional_excel_localizes_overview_for_english() -> None:
    frame = pd.DataFrame(
        {
            "Person": ["Test Patient"],
            "Date": [date(2026, 8, 30)],
            "Strength": [6],
        }
    )

    payload = dataframe_to_professional_excel(
        frame,
        language="en",
        patient_name="Test Patient",
        tracking_start_date=date(2022, 6, 1),
        patient_active=True,
        area_label="Headache entries",
        area_description="Documented headache and migraine days.",
        scope="Selected person: Test Patient",
        counts={"entries": 1, "daily_records": 10, "interpretations": 0},
        exported_at=datetime(2026, 8, 30, 2, 45, 0),
    )

    workbook_xml = _xlsx_text(payload, "xl/workbook.xml")
    shared_strings = _xlsx_text(payload, "xl/sharedStrings.xml")

    assert 'name="Overview"' in workbook_xml
    assert 'name="Data"' in workbook_xml
    assert "Tracking since" in shared_strings
    assert "Technical fields" in shared_strings
    assert "No filter" in shared_strings

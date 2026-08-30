from __future__ import annotations

"""Professional XLSX serialization for database exports."""

from io import BytesIO
from datetime import date, datetime
from typing import Any, Mapping

import pandas as pd
from pandas.api.types import is_scalar
import xlsxwriter

from frontend.config.name_space import cfg
from frontend.i18n import format_datetime_value, tr, yes_no


def dataframe_to_professional_excel(
    frame: pd.DataFrame,
    *,
    language: str,
    patient_name: str,
    tracking_start_date: date,
    patient_active: bool,
    last_entry_date: date | None = None,
    area_label: str,
    area_description: str,
    scope: str,
    counts: Mapping[str, int],
    search_term: str = "",
    include_technical_fields: bool = False,
    exported_at: datetime | None = None,
) -> bytes:
    """Create a polished two-sheet Excel export for the displayed database table."""
    exported_at = exported_at or datetime.now().astimezone()
    output = BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "remove_timezone": True,
            "strings_to_urls": False,
        },
    )
    workbook.set_properties(
        {
            "title": _t(language, "Migräne-Tracker Datenexport", "Migraine Tracker data export"),
            "subject": area_label,
            "author": "Migraine Tracker",
            "company": "Migraine Tracker",
            "comments": _t(
                language,
                "Professioneller Datenexport mit Patientenkontext.",
                "Professional data export with patient context.",
            ),
        }
    )

    formats = _build_formats(workbook, language=language)
    _write_overview_sheet(
        workbook,
        formats=formats,
        language=language,
        patient_name=patient_name,
        tracking_start_date=tracking_start_date,
        patient_active=patient_active,
        last_entry_date=last_entry_date,
        area_label=area_label,
        area_description=area_description,
        scope=scope,
        counts=counts,
        search_term=search_term,
        include_technical_fields=include_technical_fields,
        exported_at=exported_at,
        record_count=len(frame),
    )
    _write_data_sheet(
        workbook,
        frame,
        formats=formats,
        language=language,
        patient_name=patient_name,
        area_label=area_label,
        exported_at=exported_at,
    )

    workbook.close()
    return output.getvalue()


def _build_formats(workbook: xlsxwriter.Workbook, *, language: str) -> dict[str, Any]:
    date_pattern = "yyyy-mm-dd" if language == "en" else "dd.mm.yyyy"
    datetime_pattern = "yyyy-mm-dd hh:mm:ss" if language == "en" else "dd.mm.yyyy hh:mm:ss"
    return {
        "title": workbook.add_format(
            {
                "bold": True,
                "font_size": 22,
                "font_color": "#FFFFFF",
                "bg_color": "#17365D",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "subtitle": workbook.add_format(
            {
                "font_size": 11,
                "font_color": "#44546A",
                "italic": True,
            }
        ),
        "section": workbook.add_format(
            {
                "bold": True,
                "font_size": 12,
                "font_color": "#FFFFFF",
                "bg_color": "#2F75B5",
                "align": "left",
                "valign": "vcenter",
                "bottom": 1,
                "bottom_color": "#D9E2F3",
            }
        ),
        "label": workbook.add_format(
            {
                "bold": True,
                "font_color": "#17365D",
                "bg_color": "#D9EAF7",
                "border": 1,
                "border_color": "#D6DEE8",
                "valign": "top",
            }
        ),
        "value": workbook.add_format(
            {
                "font_color": "#1F1F1F",
                "border": 1,
                "border_color": "#D6DEE8",
                "valign": "top",
                "text_wrap": True,
            }
        ),
        "date": workbook.add_format(
            {
                "font_color": "#1F1F1F",
                "border": 1,
                "border_color": "#D6DEE8",
                "num_format": date_pattern,
                "valign": "top",
            }
        ),
        "datetime": workbook.add_format(
            {
                "font_color": "#1F1F1F",
                "border": 1,
                "border_color": "#D6DEE8",
                "num_format": datetime_pattern,
                "valign": "top",
            }
        ),
        "metric": workbook.add_format(
            {
                "bold": True,
                "font_size": 16,
                "font_color": "#17365D",
                "bg_color": "#F4F8FC",
                "border": 1,
                "border_color": "#D6DEE8",
                "align": "center",
                "valign": "vcenter",
            }
        ),
        "metric_label": workbook.add_format(
            {
                "font_size": 9,
                "font_color": "#5B6573",
                "bg_color": "#F4F8FC",
                "border": 1,
                "border_color": "#D6DEE8",
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,
            }
        ),
        "note": workbook.add_format(
            {
                "font_size": 9,
                "font_color": "#5B6573",
                "bg_color": "#FFF9E6",
                "border": 1,
                "border_color": "#E6D9A2",
                "text_wrap": True,
                "valign": "top",
            }
        ),
        "data_title": workbook.add_format(
            {
                "bold": True,
                "font_size": 18,
                "font_color": "#FFFFFF",
                "bg_color": "#17365D",
                "align": "left",
                "valign": "vcenter",
            }
        ),
        "data_meta": workbook.add_format(
            {
                "font_size": 10,
                "font_color": "#44546A",
                "italic": True,
            }
        ),
        "body": workbook.add_format({"valign": "top"}),
        "body_wrap": workbook.add_format({"valign": "top", "text_wrap": True}),
        "data_date": workbook.add_format({"num_format": date_pattern, "valign": "top"}),
        "data_datetime": workbook.add_format({"num_format": datetime_pattern, "valign": "top"}),
    }


def _write_overview_sheet(
    workbook: xlsxwriter.Workbook,
    *,
    formats: Mapping[str, Any],
    language: str,
    patient_name: str,
    tracking_start_date: date,
    patient_active: bool,
    last_entry_date: date | None,
    area_label: str,
    area_description: str,
    scope: str,
    counts: Mapping[str, int],
    search_term: str,
    include_technical_fields: bool,
    exported_at: datetime,
    record_count: int,
) -> None:
    sheet = workbook.add_worksheet(_t(language, "Übersicht", "Overview"))
    sheet.hide_gridlines(2)
    sheet.set_tab_color("#2F75B5")
    sheet.set_column("A:A", 3)
    sheet.set_column("B:B", 27)
    sheet.set_column("C:F", 21)
    sheet.set_column("G:G", 3)
    sheet.set_row(0, 30)
    sheet.merge_range(
        "B1:F2",
        _t(language, "Migräne-Tracker · Patientenexport", "Migraine Tracker · Patient Export"),
        formats["title"],
    )
    sheet.write(
        "B3",
        _t(
            language,
            "Professionell aufbereiteter Export der aktuell angezeigten Daten.",
            "Professionally formatted export of the currently displayed data.",
        ),
        formats["subtitle"],
    )

    sheet.merge_range(
        "B5:F5",
        _t(language, "Patientenkontext", "Patient context"),
        formats["section"],
    )
    last_entry_value: date | str = last_entry_date if last_entry_date is not None else "—"
    last_entry_format = "date" if last_entry_date is not None else "value"
    profile_rows = [
        (_t(language, "Name", "Name"), patient_name, "value"),
        (
            _t(language, "Erfassung seit", "Tracking since"),
            tracking_start_date,
            "date",
        ),
        (
            _t(language, "Letzter Eintrag am", "Last entry on"),
            last_entry_value,
            last_entry_format,
        ),
        (
            _t(language, "Profilstatus", "Profile status"),
            _t(language, "Aktiv", "Active") if patient_active else _t(language, "Inaktiv", "Inactive"),
            "value",
        ),
    ]
    row = 5
    for label, value, format_key in profile_rows:
        sheet.write(row, 1, label, formats["label"])
        sheet.merge_range(row, 2, row, 5, value, formats[format_key])
        row += 1

    sheet.merge_range(
        "B10:F10",
        _t(language, "Verlauf im Tracker", "Tracker history"),
        formats["section"],
    )
    metrics = [
        (
            counts.get("entries", 0),
            _t(language, "Kopfschmerzeinträge", "Headache entries"),
        ),
        (
            counts.get("daily_records", 0),
            _t(language, "Beobachtungstage", "Observation days"),
        ),
        (
            counts.get("interpretations", 0),
            _t(language, "Ausgewertete Notizen", "Analysed notes"),
        ),
        (
            record_count,
            _t(language, "Datensätze in diesem Export", "Records in this export"),
        ),
    ]
    for index, (value, label) in enumerate(metrics):
        column = 1 + index
        sheet.write(10, column, value, formats["metric"])
        sheet.write(11, column, label, formats["metric_label"])
    sheet.write(10, 5, "", formats["metric"])
    sheet.write(11, 5, "", formats["metric_label"])

    sheet.merge_range(
        "B14:F14",
        _t(language, "Exportdetails", "Export details"),
        formats["section"],
    )
    details = [
        (_t(language, "Datenbereich", "Data area"), area_label),
        (_t(language, "Inhalt", "Contents"), area_description),
        (_t(language, "Geltungsbereich", "Scope"), scope),
        (
            _t(language, "Suchfilter", "Search filter"),
            search_term or _t(language, "Kein Filter", "No filter"),
        ),
        (
            _t(language, "Technische Felder", "Technical fields"),
            yes_no(cfg, include_technical_fields, lang=language),
        ),
        (
            _t(language, "Export erstellt", "Export created"),
            format_datetime_value(cfg, exported_at, lang=language),
        ),
    ]
    row = 14
    for label, value in details:
        sheet.write(row, 1, label, formats["label"])
        sheet.merge_range(row, 2, row, 5, value, formats["value"])
        row += 1

    sheet.merge_range(
        "B22:F23",
        _t(
            language,
            "Hinweis: Der Patientenkontext basiert auf den im Migräne-Tracker gespeicherten Profildaten. "
            "Der Datenreiter enthält genau die aktuell angezeigten und gefilterten Datensätze.",
            "Note: Patient context is based on the profile information stored in Migraine Tracker. "
            "The data sheet contains exactly the records currently displayed after filtering.",
        ),
        formats["note"],
    )
    sheet.set_row(21, 24)
    sheet.set_row(22, 24)
    sheet.freeze_panes(4, 1)
    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.set_margins(left=0.35, right=0.35, top=0.5, bottom=0.5)
    sheet.set_footer(_t(language, "&LMigraine Tracker&CPatientenexport&RSeite &P von &N", "&LMigraine Tracker&CPatient export&RPage &P of &N"))


def _write_data_sheet(
    workbook: xlsxwriter.Workbook,
    frame: pd.DataFrame,
    *,
    formats: Mapping[str, Any],
    language: str,
    patient_name: str,
    area_label: str,
    exported_at: datetime,
) -> None:
    sheet = workbook.add_worksheet(_t(language, "Daten", "Data"))
    sheet.hide_gridlines(2)
    sheet.set_tab_color("#70AD47")
    last_column = max(len(frame.columns) - 1, 0)
    sheet.set_row(0, 28)
    sheet.merge_range(
        0,
        0,
        0,
        last_column,
        f"{area_label} · {patient_name}",
        formats["data_title"],
    )
    meta = (
        f"{_t(language, 'Export erstellt', 'Export created')}: "
        f"{format_datetime_value(cfg, exported_at, lang=language)}"
    )
    sheet.merge_range(1, 0, 1, last_column, meta, formats["data_meta"])

    header_row = 3
    for row_offset, row_values in enumerate(frame.itertuples(index=False, name=None), start=1):
        excel_row = header_row + row_offset
        for column_index, value in enumerate(row_values):
            _write_data_value(
                sheet,
                excel_row,
                column_index,
                value,
                formats=formats,
            )

    if len(frame.columns):
        table_end_row = header_row + len(frame)
        columns = [{"header": str(column)} for column in frame.columns]
        sheet.add_table(
            header_row,
            0,
            table_end_row,
            last_column,
            {
                "name": "MigraineExportData",
                "columns": columns,
                "style": "Table Style Medium 2",
            },
        )
        _set_data_column_widths(sheet, frame)
        _apply_strength_scale(sheet, frame, header_row=header_row)
        sheet.freeze_panes(header_row + 1, 0)
        sheet.repeat_rows(header_row, header_row)
        sheet.print_area(0, 0, table_end_row, last_column)

    sheet.set_landscape()
    sheet.fit_to_pages(1, 0)
    sheet.set_margins(left=0.25, right=0.25, top=0.5, bottom=0.5)
    sheet.set_header(_t(language, "&LMigraine Tracker&CAuszug&R&D", "&LMigraine Tracker&CExport&R&D"))
    sheet.set_footer(_t(language, "&LPatient: ", "&LPatient: ") + patient_name + "&R" + _t(language, "Seite &P von &N", "Page &P of &N"))


def _write_data_value(
    sheet: xlsxwriter.worksheet.Worksheet,
    row: int,
    column: int,
    value: Any,
    *,
    formats: Mapping[str, Any],
) -> None:
    if _is_missing(value):
        sheet.write_blank(row, column, None, formats["body"])
        return
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        sheet.write_datetime(row, column, value, formats["data_datetime"])
        return
    if isinstance(value, date):
        sheet.write_datetime(
            row,
            column,
            datetime.combine(value, datetime.min.time()),
            formats["data_date"],
        )
        return
    if value.__class__.__module__.startswith("numpy") and hasattr(value, "item"):
        value = value.item()
    text_wrap = isinstance(value, str) and ("\n" in value or len(value) > 48)
    sheet.write(row, column, value, formats["body_wrap" if text_wrap else "body"])


def _set_data_column_widths(sheet: xlsxwriter.worksheet.Worksheet, frame: pd.DataFrame) -> None:
    for column_index, column_name in enumerate(frame.columns):
        lengths = [len(str(column_name))]
        for value in frame.iloc[:250, column_index]:
            if _is_missing(value):
                continue
            text = str(value).replace("\r", " ").replace("\n", " ")
            lengths.append(len(text))
        observed = max(lengths, default=12) + 2
        has_long_text = any(length > 45 for length in lengths)
        width = min(max(observed, 12), 46 if has_long_text else 28)
        sheet.set_column(column_index, column_index, width)


def _apply_strength_scale(
    sheet: xlsxwriter.worksheet.Worksheet,
    frame: pd.DataFrame,
    *,
    header_row: int,
) -> None:
    strength_columns = {"Stärke", "Strength"}
    if frame.empty:
        return
    for column_index, column_name in enumerate(frame.columns):
        if str(column_name) not in strength_columns:
            continue
        first_data_row = header_row + 1
        last_data_row = header_row + len(frame)
        sheet.conditional_format(
            first_data_row,
            column_index,
            last_data_row,
            column_index,
            {
                "type": "3_color_scale",
                "min_color": "#E2F0D9",
                "mid_color": "#FFF2CC",
                "max_color": "#F4CCCC",
            },
        )


def _t(language: str, german: str, english: str) -> str:
    return tr(cfg, german, english, lang=language)


def _is_missing(value: Any) -> bool:
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if is_scalar(result) else False

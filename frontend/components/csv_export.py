from __future__ import annotations

"""Excel-friendly CSV serialization for database tables."""

import csv
import re
from datetime import date, datetime
from typing import Any

import pandas as pd
from pandas.api.types import is_scalar

UTF16_LE_BOM = b"\xff\xfe"


def table_date_format(language: str) -> str:
    """Return the Streamlit date format used by database tables."""
    return "YYYY-MM-DD" if language == "en" else "DD.MM.YYYY"


def table_datetime_format(language: str) -> str:
    """Return the Streamlit datetime format used by database tables."""
    return "YYYY-MM-DD HH:mm:ss" if language == "en" else "DD.MM.YYYY HH:mm:ss"


def dataframe_to_semicolon_csv(frame: pd.DataFrame, *, language: str) -> bytes:
    """Serialize the displayed table as an Excel-friendly semicolon CSV."""
    export_frame = frame.map(lambda value: _export_cell(value, language=language))
    table_text = export_frame.to_csv(
        index=False,
        sep=";",
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\r\n",
        na_rep="",
    )
    csv_text = f"sep=;\r\n{table_text}"
    return UTF16_LE_BOM + csv_text.encode("utf-16-le")


def _export_cell(value: Any, *, language: str) -> Any:
    if _is_missing(value):
        return ""
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        localized = value.astimezone() if value.tzinfo is not None else value
        pattern = "%Y-%m-%d %H:%M:%S" if language == "en" else "%d.%m.%Y %H:%M:%S"
        return localized.strftime(pattern)
    if isinstance(value, date):
        pattern = "%Y-%m-%d" if language == "en" else "%d.%m.%Y"
        return value.strftime(pattern)
    if isinstance(value, str):
        return re.sub(r"[ \t]*[\r\n]+[ \t]*", " ", value).strip()
    return value


def _is_missing(value: Any) -> bool:
    try:
        result = pd.isna(value)
    except (TypeError, ValueError):
        return False
    return bool(result) if is_scalar(result) else False

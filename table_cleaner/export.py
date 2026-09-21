"""Safe export helpers for CSV and Excel files."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

FORMULA_PREFIXES = ("=", "+", "-", "@")


def _escape_formula(value: Any) -> Any:
    """Prefix spreadsheet formulas so exported cells are treated as text."""
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def sanitize_dataframe_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with text cells protected from CSV/Excel formula injection."""
    result = df.copy()
    text_columns = result.select_dtypes(include=["object", "string"]).columns
    for column in text_columns:
        result[column] = result[column].map(_escape_formula)
    return result


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Encode a DataFrame as UTF-8 with BOM for Excel compatibility."""
    return df.to_csv(index=False).encode("utf-8-sig")


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "cleaned_data") -> bytes:
    """Write a DataFrame to an in-memory XLSX workbook."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31] or "data")
    return buffer.getvalue()


def suggest_output_name(source_name: str | None, suffix: str, tag: str = "cleaned") -> str:
    """Build a predictable output filename from the source filename."""
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    stem = Path(source_name).stem if source_name else "table"
    return f"{stem}_{tag}{suffix}"

"""Input helpers for CSV and Excel files."""

from __future__ import annotations

from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1")
EXCEL_ENGINES = {".xlsx": "openpyxl", ".xls": "xlrd"}


def _get_source_name(source: Any, filename: str | None = None) -> str:
    """Return a useful filename for paths and file-like objects."""
    if filename:
        return filename
    raw_name = getattr(source, "name", None)
    if raw_name:
        return str(raw_name)
    if isinstance(source, (str, Path)):
        return Path(source).name
    return ""


def _get_suffix(source: Any, filename: str | None = None) -> str:
    name = _get_source_name(source, filename)
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"不支持的文件类型 {suffix or '(无扩展名)'}，支持：{supported}")
    return suffix


def _rewind(source: Any) -> None:
    if hasattr(source, "seek"):
        source.seek(0)


def _read_csv(source: Any, encoding: str | None = None) -> pd.DataFrame:
    """Read CSV while trying common encodings used for Chinese data."""
    encodings = (encoding,) if encoding else CSV_ENCODINGS
    errors: list[str] = []

    for candidate in encodings:
        try:
            _rewind(source)
            return pd.read_csv(
                source,
                encoding=candidate,
                sep=None,
                engine="python",
            )
        except Exception as exc:  # The next encoding may succeed.
            errors.append(f"{candidate}: {exc}")

    error_text = "\n".join(errors[-3:])
    raise ValueError(f"无法识别 CSV 编码或分隔符。已尝试：{', '.join(encodings)}\n{error_text}")


def read_table(
    source: Any,
    filename: str | None = None,
    sheet_name: str | int = 0,
    encoding: str | None = None,
) -> pd.DataFrame:
    """Read a CSV/XLSX/XLS table from a path or binary file-like object."""
    suffix = _get_suffix(source, filename)
    _rewind(source)

    if suffix == ".csv":
        return _read_csv(source, encoding=encoding)

    engine = EXCEL_ENGINES[suffix]
    try:
        return pd.read_excel(source, sheet_name=sheet_name, engine=engine)
    except ImportError as exc:
        package = "openpyxl" if suffix == ".xlsx" else "xlrd"
        raise ValueError(f"读取 {suffix} 需要安装 {package}。") from exc
    except Exception as exc:
        raise ValueError(f"无法读取 Excel 工作表 {sheet_name!r}：{exc}") from exc


def list_excel_sheets(source: Any, filename: str | None = None) -> list[str]:
    """List worksheet names without loading all sheet data."""
    suffix = _get_suffix(source, filename)
    if suffix == ".csv":
        return []
    _rewind(source)
    try:
        with pd.ExcelFile(source, engine=EXCEL_ENGINES[suffix]) as workbook:
            return [str(name) for name in workbook.sheet_names]
    finally:
        _rewind(source)


def read_bytes_safely(source: BinaryIO | bytes) -> bytes:
    """Return bytes from an upload or byte buffer without changing caller state."""
    if isinstance(source, bytes):
        return source
    _rewind(source)
    data = source.read()
    _rewind(source)
    return data

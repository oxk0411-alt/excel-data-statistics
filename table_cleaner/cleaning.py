"""Configurable table-cleaning operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

import pandas as pd

MISSING_STRATEGIES = ("keep", "drop_rows", "fill")
FILL_METHODS = ("auto", "mean", "median", "mode", "constant")
IDENTIFIER_HINTS = (
    "id",
    "编号",
    "编码",
    "代码",
    "邮编",
    "电话",
    "手机",
    "身份证",
)
DATE_HINTS = ("date", "time", "日期", "时间", "年月")


@dataclass(frozen=True)
class CleaningOptions:
    """User-selectable cleaning rules."""

    normalize_columns: bool = True
    trim_whitespace: bool = True
    drop_empty_rows: bool = True
    drop_empty_columns: bool = True
    drop_duplicates: bool = True
    convert_types: bool = True
    missing_strategy: str = "keep"
    fill_method: str = "auto"
    fill_value: str = ""
    numeric_threshold: float = 0.95
    date_threshold: float = 0.80

    def validate(self) -> None:
        if self.missing_strategy not in MISSING_STRATEGIES:
            raise ValueError(f"未知缺失值策略：{self.missing_strategy}")
        if self.fill_method not in FILL_METHODS:
            raise ValueError(f"未知填充方法：{self.fill_method}")
        if not 0 < self.numeric_threshold <= 1:
            raise ValueError("numeric_threshold 必须在 0 到 1 之间")
        if not 0 < self.date_threshold <= 1:
            raise ValueError("date_threshold 必须在 0 到 1 之间")


@dataclass
class CleaningReport:
    """Summary of changes made by :func:`clean_table`."""

    original_rows: int
    cleaned_rows: int
    original_columns: int
    cleaned_columns: int
    removed_duplicates: int = 0
    removed_empty_rows: int = 0
    removed_empty_columns: int = 0
    removed_missing_rows: int = 0
    filled_cells: int = 0
    converted_columns: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _deduplicate_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    output: list[str] = []

    for name in names:
        count = seen.get(name, 0) + 1
        seen[name] = count
        output.append(name if count == 1 else f"{name}_{count}")
    return output


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Convert messy headers into predictable, unique identifiers."""
    names: list[str] = []

    for index, original in enumerate(df.columns):
        name = str(original).strip()
        if re.fullmatch(r"Unnamed:\s*\d+", name, flags=re.IGNORECASE):
            name = f"column_{index + 1}"
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^\w\u4e00-\u9fff]+", "_", name, flags=re.UNICODE)
        name = re.sub(r"_+", "_", name).strip("_")
        names.append(name or f"column_{index + 1}")

    result = df.copy()
    result.columns = _deduplicate_names(names)
    return result


def trim_text_whitespace(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading/trailing whitespace from text cells without changing missing values."""
    result = df.copy()
    for column in result.columns:
        if pd.api.types.is_object_dtype(result[column]) or pd.api.types.is_string_dtype(result[column]):
            result[column] = result[column].map(
                lambda value: value.strip() if isinstance(value, str) else value
            )
    return result


def _is_identifier_column(column_name: Any) -> bool:
    lowered = str(column_name).lower()
    return any(hint in lowered for hint in IDENTIFIER_HINTS)


def _has_date_hint(column_name: Any) -> bool:
    lowered = str(column_name).lower()
    return any(hint in lowered for hint in DATE_HINTS)


def _convert_types(
    df: pd.DataFrame,
    numeric_threshold: float,
    date_threshold: float,
) -> tuple[pd.DataFrame, list[str]]:
    """Best-effort conversion of text columns to numeric or datetime types."""
    result = df.copy()
    converted: list[str] = []

    for column in result.select_dtypes(include=["object", "string"]).columns:
        if _is_identifier_column(column):
            continue

        series = result[column]
        non_empty = series.dropna().astype("string").str.strip()
        if non_empty.empty:
            continue

        if _has_date_hint(column):
            dates = pd.to_datetime(non_empty, errors="coerce")
            if dates.notna().mean() >= date_threshold:
                result[column] = pd.to_datetime(series, errors="coerce")
                converted.append(str(column))
                continue

        numbers = pd.to_numeric(non_empty, errors="coerce")
        if numbers.notna().mean() >= numeric_threshold:
            result[column] = pd.to_numeric(series, errors="coerce")
            converted.append(str(column))

    return result, converted


def _mode_value(series: pd.Series) -> Any:
    modes = series.mode(dropna=True)
    return modes.iloc[0] if not modes.empty else None


def _fill_series(series: pd.Series, method: str, fill_value: str) -> tuple[pd.Series, int]:
    missing_count = int(series.isna().sum())
    if missing_count == 0:
        return series, 0

    filled = series.copy()
    numeric = pd.api.types.is_numeric_dtype(filled)

    if method == "constant":
        value: Any = fill_value
        if numeric:
            value = pd.to_numeric(fill_value, errors="coerce")
            if pd.isna(value):
                value = 0
        filled = filled.fillna(value)
        return filled, missing_count

    if method == "mean" and numeric:
        value = filled.mean()
    elif method == "median" and numeric:
        value = filled.median()
    elif method == "mode":
        value = _mode_value(filled)
    elif method == "auto" and numeric:
        skew = filled.skew()
        value = filled.median() if pd.notna(skew) and abs(skew) > 1 else filled.mean()
    else:
        value = _mode_value(filled)

    if value is None or pd.isna(value):
        if numeric:
            value = 0
        else:
            value = fill_value if fill_value else "未知"

    filled = filled.fillna(value)
    return filled, missing_count


def _fill_missing(df: pd.DataFrame, method: str, fill_value: str) -> tuple[pd.DataFrame, int]:
    result = df.copy()
    filled_cells = 0

    for column in result.columns:
        result[column], count = _fill_series(result[column], method=method, fill_value=fill_value)
        filled_cells += count

    return result, filled_cells


def clean_table(
    df: pd.DataFrame,
    options: CleaningOptions | None = None,
) -> tuple[pd.DataFrame, CleaningReport]:
    """Clean a DataFrame and return the result plus an auditable report."""
    options = options or CleaningOptions()
    options.validate()

    original_rows, original_columns = df.shape
    result = df.copy()
    report = CleaningReport(
        original_rows=original_rows,
        cleaned_rows=original_rows,
        original_columns=original_columns,
        cleaned_columns=original_columns,
    )

    if options.normalize_columns:
        result = normalize_column_names(result)
        report.notes.append("已规范化列名并处理重名列。")

    if options.trim_whitespace:
        result = trim_text_whitespace(result)
        report.notes.append("已清理文本首尾空白。")

    if options.drop_empty_rows:
        before = len(result)
        result = result.dropna(how="all")
        report.removed_empty_rows = before - len(result)

    if options.drop_empty_columns:
        before = len(result.columns)
        result = result.dropna(axis=1, how="all")
        report.removed_empty_columns = before - len(result.columns)

    if options.drop_duplicates:
        before = len(result)
        result = result.drop_duplicates()
        report.removed_duplicates = before - len(result)

    if options.convert_types:
        result, report.converted_columns = _convert_types(
            result,
            numeric_threshold=options.numeric_threshold,
            date_threshold=options.date_threshold,
        )
        if report.converted_columns:
            report.notes.append(f"已转换 {len(report.converted_columns)} 个字段的数据类型。")

    if options.missing_strategy == "drop_rows":
        before = len(result)
        result = result.dropna(how="any")
        report.removed_missing_rows = before - len(result)
        report.notes.append("已删除包含缺失值的行。")
    elif options.missing_strategy == "fill":
        result, report.filled_cells = _fill_missing(
            result,
            method=options.fill_method,
            fill_value=options.fill_value,
        )
        report.notes.append(f"已填充 {report.filled_cells} 个缺失单元格。")

    report.cleaned_rows = len(result)
    report.cleaned_columns = len(result.columns)
    return result.reset_index(drop=True), report

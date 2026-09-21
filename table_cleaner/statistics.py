"""Summary statistics for tabular data."""

from __future__ import annotations

from typing import Any

import pandas as pd

AGGREGATIONS = ("mean", "median", "sum", "min", "max", "std", "count")


def dataset_overview(df: pd.DataFrame) -> dict[str, Any]:
    """Return high-level dataset metrics."""
    rows, columns = df.shape
    total_cells = rows * columns
    missing_cells = int(df.isna().sum().sum())
    return {
        "rows": int(rows),
        "columns": int(columns),
        "total_cells": int(total_cells),
        "missing_cells": missing_cells,
        "missing_rate": (missing_cells / total_cells) if total_cells else 0.0,
        "duplicate_rows": int(df.duplicated().sum()),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
    }


def numeric_columns(df: pd.DataFrame) -> list[str]:
    return [str(column) for column in df.select_dtypes(include="number").columns]


def categorical_columns(df: pd.DataFrame) -> list[str]:
    selected = df.select_dtypes(include=["object", "string", "category", "bool"])
    return [str(column) for column in selected.columns]


def column_profile(df: pd.DataFrame) -> pd.DataFrame:
    """Create one quality/profile row per column."""
    rows = len(df)
    records: list[dict[str, Any]] = []

    for column in df.columns:
        series = df[column]
        non_null = series.dropna()
        examples = [str(value)[:60] for value in non_null.head(3).tolist()]
        records.append(
            {
                "column": str(column),
                "dtype": str(series.dtype),
                "non_null": int(non_null.shape[0]),
                "missing": int(series.isna().sum()),
                "missing_rate": float(series.isna().mean()) if rows else 0.0,
                "unique": int(series.nunique(dropna=True)),
                "example_values": " | ".join(examples),
            }
        )

    return pd.DataFrame(records)


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Describe numeric columns and add median/skew columns."""
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame()

    summary = numeric.describe().T
    summary["median"] = numeric.median()
    summary["skew"] = numeric.skew()
    return summary.reset_index(names="column")


def categorical_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize text, category, and boolean columns."""
    selected = df.select_dtypes(include=["object", "string", "category", "bool"])
    records: list[dict[str, Any]] = []

    for column in selected.columns:
        series = selected[column]
        counts = series.value_counts(dropna=True)
        top_value = counts.index[0] if not counts.empty else None
        top_count = int(counts.iloc[0]) if not counts.empty else 0
        non_null = int(series.notna().sum())
        records.append(
            {
                "column": str(column),
                "non_null": non_null,
                "missing": int(series.isna().sum()),
                "unique": int(series.nunique(dropna=True)),
                "top_value": top_value,
                "top_count": top_count,
                "top_rate": (top_count / non_null) if non_null else 0.0,
            }
        )

    return pd.DataFrame(records)


def correlation_matrix(df: pd.DataFrame, method: str = "pearson") -> pd.DataFrame:
    """Return a correlation matrix when at least two numeric columns exist."""
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return pd.DataFrame()
    return numeric.corr(method=method)


def group_summary(
    df: pd.DataFrame,
    group_column: str,
    value_column: str | None = None,
    aggregation: str = "mean",
    top_n: int = 100,
    include_missing_groups: bool = True,
) -> pd.DataFrame:
    """Aggregate a numeric field by a grouping field, or count group sizes."""
    if group_column not in df.columns:
        raise KeyError(f"找不到分组字段：{group_column}")

    dropna = not include_missing_groups
    grouped = df.groupby(group_column, dropna=dropna)

    if value_column is None:
        result = grouped.size().reset_index(name="count")
        sort_column = "count"
    else:
        if value_column not in df.columns:
            raise KeyError(f"找不到数值字段：{value_column}")
        if aggregation not in AGGREGATIONS:
            raise ValueError(f"不支持的聚合方式：{aggregation}")
        result = grouped[value_column].agg(aggregation).reset_index()
        sort_column = value_column

    return result.sort_values(sort_column, ascending=False).head(top_n).reset_index(drop=True)

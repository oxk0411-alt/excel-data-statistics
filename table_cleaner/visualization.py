"""Plotly chart builders for the Streamlit app."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLOR_SEQUENCE = px.colors.qualitative.Safe


def _finish_figure(fig: go.Figure, title: str, height: int = 430) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        colorway=COLOR_SEQUENCE,
        legend_title_text="",
    )
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=16),
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _finish_figure(fig, "暂无可视化内容", height=360)


def histogram(df: pd.DataFrame, column: str, bins: int = 30) -> go.Figure:
    if column not in df.columns:
        return empty_figure("字段不存在。")
    data = df[[column]].dropna()
    if data.empty:
        return empty_figure("该字段没有可绘制的数据。")
    fig = px.histogram(data, x=column, nbins=max(5, min(int(bins), 100)))
    return _finish_figure(fig, f"{column} 分布")


def box_plot(df: pd.DataFrame, value_column: str, group_column: str | None = None) -> go.Figure:
    if value_column not in df.columns:
        return empty_figure("字段不存在。")
    columns = [value_column] + ([group_column] if group_column else [])
    data = df[columns].dropna(subset=[value_column])
    if data.empty:
        return empty_figure("该字段没有可绘制的数据。")

    if group_column:
        unique_groups = data[group_column].nunique(dropna=True)
        if unique_groups > 40:
            return empty_figure("分组数量超过 40，请先筛选数据或选择其他分组字段。")
        fig = px.box(data, x=group_column, y=value_column, color=group_column)
    else:
        fig = px.box(data, y=value_column)

    return _finish_figure(fig, f"{value_column} 箱线图")


def bar_counts(df: pd.DataFrame, column: str, top_n: int = 20) -> go.Figure:
    if column not in df.columns:
        return empty_figure("字段不存在。")
    counts = df[column].value_counts(dropna=False).head(int(top_n)).rename_axis(column).reset_index(name="count")
    counts[column] = counts[column].where(counts[column].notna(), "(缺失)")
    if counts.empty:
        return empty_figure("该字段没有可绘制的数据。")
    fig = px.bar(counts, x=column, y="count", text="count")
    fig.update_traces(textposition="outside")
    return _finish_figure(fig, f"{column} 取值计数")


def line_chart(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    color_column: str | None = None,
) -> go.Figure:
    if x_column not in df.columns or y_column not in df.columns:
        return empty_figure("字段不存在。")
    columns = [x_column, y_column] + ([color_column] if color_column else [])
    data = df[columns].dropna(subset=[x_column, y_column]).copy()
    if data.empty:
        return empty_figure("没有足够的数据绘制折线图。")
    try:
        data = data.sort_values(x_column)
    except TypeError:
        pass
    fig = px.line(data, x=x_column, y=y_column, color=color_column, markers=True)
    return _finish_figure(fig, f"{y_column} 随 {x_column} 变化")


def scatter_plot(
    df: pd.DataFrame,
    x_column: str,
    y_column: str,
    color_column: str | None = None,
) -> go.Figure:
    if x_column not in df.columns or y_column not in df.columns:
        return empty_figure("字段不存在。")
    columns = [x_column, y_column] + ([color_column] if color_column else [])
    data = df[columns].dropna(subset=[x_column, y_column])
    if data.empty:
        return empty_figure("没有足够的数据绘制散点图。")
    fig = px.scatter(data, x=x_column, y=y_column, color=color_column, opacity=0.75)
    return _finish_figure(fig, f"{x_column} 与 {y_column} 散点图")


def correlation_heatmap(correlation: pd.DataFrame) -> go.Figure:
    if correlation.empty:
        return empty_figure("至少需要两个数值字段才能计算相关性。")
    values = correlation.round(4).values
    labels = [str(column) for column in correlation.columns]
    fig = go.Figure(
        data=go.Heatmap(
            z=values,
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            zmid=0,
            colorscale="RdBu",
            text=values,
            texttemplate="%{text}",
            hovertemplate="%{y} × %{x}<br>相关系数=%{z:.4f}<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    return _finish_figure(fig, "数值字段相关性热力图", height=max(430, 44 * len(labels)))


def missingness_bar(df: pd.DataFrame) -> go.Figure:
    if df.empty or len(df.columns) == 0:
        return empty_figure("没有字段可分析。")
    missing = (df.isna().mean() * 100).sort_values(ascending=True)
    records = pd.DataFrame({"column": missing.index.astype(str), "missing_rate": missing.values})
    fig = px.bar(
        records,
        x="missing_rate",
        y="column",
        orientation="h",
        text="missing_rate",
        labels={"missing_rate": "缺失率 (%)", "column": "字段"},
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    return _finish_figure(fig, "字段缺失率", height=max(380, 32 * len(records) + 120))

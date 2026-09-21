"""Streamlit application for cleaning, profiling, and visualizing tables."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from table_cleaner.cleaning import CleaningOptions, clean_table
from table_cleaner.export import (
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes,
    sanitize_dataframe_for_export,
    suggest_output_name,
)
from table_cleaner.io_utils import list_excel_sheets, read_table
from table_cleaner.statistics import (
    categorical_columns,
    categorical_summary,
    column_profile,
    correlation_matrix,
    dataset_overview,
    group_summary,
    numeric_columns,
    numeric_summary,
)
from table_cleaner.visualization import (
    bar_counts,
    box_plot,
    correlation_heatmap,
    histogram,
    line_chart,
    missingness_bar,
    scatter_plot,
)

BASE_DIR = Path(__file__).resolve().parent
DEMO_PATH = BASE_DIR / "data" / "messy_sales.csv"

st.set_page_config(
    page_title="表格清洗与统计分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_demo_data() -> pd.DataFrame:
    return read_table(DEMO_PATH)


@st.cache_data(show_spinner=False)
def load_uploaded_data(content: bytes, filename: str, sheet_name: str | int) -> pd.DataFrame:
    return read_table(BytesIO(content), filename=filename, sheet_name=sheet_name)


@st.cache_data(show_spinner=False)
def get_sheet_names(content: bytes, filename: str) -> list[str]:
    return list_excel_sheets(BytesIO(content), filename=filename)


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def load_source() -> tuple[pd.DataFrame, str]:
    """Load the uploaded file or the built-in demo dataset."""
    with st.sidebar:
        st.header("数据源")
        uploaded = st.file_uploader(
            "上传 CSV 或 Excel 文件",
            type=["csv", "xlsx", "xls"],
            help="支持 UTF-8、GB18030 等常见编码，以及多工作表 Excel。",
        )

        if uploaded is None:
            signature = ("demo",)
            source_name = DEMO_PATH.name
            if st.session_state.get("source_signature") != signature:
                try:
                    dataframe = load_demo_data()
                except Exception as exc:
                    st.error(f"无法读取演示数据：{exc}")
                    st.stop()
                st.session_state.source_signature = signature
                st.session_state.source_name = source_name
                st.session_state.original_df = dataframe
                st.session_state.cleaned_df = None
                st.session_state.cleaning_report = None
                st.session_state.active_data = "原始数据"
            st.caption("当前使用内置演示数据。上传文件后将自动切换。")
            return st.session_state.original_df, source_name

        suffix = Path(uploaded.name).suffix.lower()
        sheet_name: str | int = 0
        if suffix in {".xlsx", ".xls"}:
            try:
                sheets = get_sheet_names(uploaded.getvalue(), uploaded.name)
            except Exception as exc:
                st.error(f"无法读取工作表列表：{exc}")
                st.stop()
            if not sheets:
                st.error("Excel 文件中没有可读取的工作表。")
                st.stop()
            sheet_name = st.selectbox("选择工作表", sheets, key="selected_sheet")

        signature = (uploaded.name, uploaded.size, str(sheet_name))
        source_name = uploaded.name
        if st.session_state.get("source_signature") != signature:
            try:
                dataframe = load_uploaded_data(uploaded.getvalue(), uploaded.name, sheet_name)
            except Exception as exc:
                st.error(f"读取文件失败：{exc}")
                st.stop()
            st.session_state.source_signature = signature
            st.session_state.source_name = source_name
            st.session_state.original_df = dataframe
            st.session_state.cleaned_df = None
            st.session_state.cleaning_report = None
            st.session_state.active_data = "原始数据"

        st.caption(f"当前文件：{source_name}")
        return st.session_state.original_df, source_name


def render_overview(dataframe: pd.DataFrame) -> None:
    st.subheader("数据概览")
    overview = dataset_overview(dataframe)

    metric_columns = st.columns(5)
    metric_columns[0].metric("行数", f"{overview['rows']:,}")
    metric_columns[1].metric("字段数", f"{overview['columns']:,}")
    metric_columns[2].metric("缺失单元格", f"{overview['missing_cells']:,}")
    metric_columns[3].metric("缺失率", f"{overview['missing_rate']:.1%}")
    metric_columns[4].metric("重复行", f"{overview['duplicate_rows']:,}")

    st.caption(f"内存占用约 {format_bytes(overview['memory_bytes'])}")

    profile = column_profile(dataframe)
    st.markdown("#### 字段质量画像")
    st.dataframe(profile, width="stretch", hide_index=True)

    st.markdown("#### 缺失值分布")
    st.plotly_chart(missingness_bar(dataframe), width="stretch", key="overview_missingness")

    with st.expander("查看当前数据", expanded=False):
        st.dataframe(dataframe.head(200), width="stretch", hide_index=True)
        if len(dataframe) > 200:
            st.caption("仅展示前 200 行，统计和导出仍使用完整数据。")


def render_cleaning(original_df: pd.DataFrame) -> None:
    st.subheader("清洗规则")
    st.caption("清洗不会修改原始数据；确认结果后可切换使用清洗后数据。")

    with st.form("cleaning_form"):
        first_row = st.columns(4)
        normalize_columns = first_row[0].checkbox("规范化列名", value=True)
        trim_whitespace = first_row[1].checkbox("清理文本空白", value=True)
        drop_empty_rows = first_row[2].checkbox("删除全空行", value=True)
        drop_empty_columns = first_row[3].checkbox("删除全空列", value=True)

        second_row = st.columns(3)
        drop_duplicates = second_row[0].checkbox("删除重复行", value=True)
        convert_types = second_row[1].checkbox("自动识别数值和日期", value=True)
        missing_action = second_row[2].selectbox(
            "缺失值处理",
            ["保留", "删除包含缺失值的行", "填充缺失值"],
        )

        fill_method = "auto"
        fill_value = ""
        if missing_action == "填充缺失值":
            third_row = st.columns(2)
            fill_label = third_row[0].selectbox(
                "填充方法",
                ["自动选择", "均值", "中位数", "众数", "固定值"],
                help="数值字段自动选择均值或中位数；文本字段优先使用众数。",
            )
            method_map = {
                "自动选择": "auto",
                "均值": "mean",
                "中位数": "median",
                "众数": "mode",
                "固定值": "constant",
            }
            fill_method = method_map[fill_label]
            if fill_label == "固定值":
                fill_value = third_row[1].text_input("固定填充值", value="未知")

        submitted = st.form_submit_button("应用清洗", type="primary", width="stretch")

    if submitted:
        missing_map = {
            "保留": "keep",
            "删除包含缺失值的行": "drop_rows",
            "填充缺失值": "fill",
        }
        options = CleaningOptions(
            normalize_columns=normalize_columns,
            trim_whitespace=trim_whitespace,
            drop_empty_rows=drop_empty_rows,
            drop_empty_columns=drop_empty_columns,
            drop_duplicates=drop_duplicates,
            convert_types=convert_types,
            missing_strategy=missing_map[missing_action],
            fill_method=fill_method,
            fill_value=fill_value,
        )
        try:
            cleaned_df, report = clean_table(original_df, options)
        except Exception as exc:
            st.error(f"清洗失败：{exc}")
        else:
            st.session_state.cleaned_df = cleaned_df
            st.session_state.cleaning_report = report
            st.session_state.pending_active_data = "清洗后数据"
            st.session_state.clean_success = True
            st.rerun()

    if st.session_state.get("clean_success"):
        st.success("清洗已完成，并已切换到“清洗后数据”。")
        st.session_state.clean_success = False

    report = st.session_state.get("cleaning_report")
    cleaned_df = st.session_state.get("cleaned_df")

    if cleaned_df is None or report is None:
        st.info("尚未应用清洗规则。")
        return

    st.markdown("#### 清洗结果")
    result_columns = st.columns(5)
    result_columns[0].metric("清洗后行数", f"{report.cleaned_rows:,}")
    result_columns[1].metric("清洗后字段", f"{report.cleaned_columns:,}")
    result_columns[2].metric("删除重复行", f"{report.removed_duplicates:,}")
    result_columns[3].metric("删除缺失行", f"{report.removed_missing_rows:,}")
    result_columns[4].metric("填充单元格", f"{report.filled_cells:,}")

    details = {
        "删除全空行": report.removed_empty_rows,
        "删除全空列": report.removed_empty_columns,
        "类型转换字段": ", ".join(report.converted_columns) if report.converted_columns else "无",
    }
    st.json(details)

    if report.notes:
        for note in report.notes:
            st.write(f"- {note}")

    st.markdown("#### 清洗后预览")
    st.dataframe(cleaned_df.head(200), width="stretch", hide_index=True)

    if st.button("清除清洗结果并恢复原始数据"):
        st.session_state.cleaned_df = None
        st.session_state.cleaning_report = None
        st.session_state.pending_active_data = "原始数据"
        st.rerun()


def render_statistics(dataframe: pd.DataFrame) -> None:
    st.subheader("统计分析")
    numeric_cols = numeric_columns(dataframe)
    category_cols = categorical_columns(dataframe)

    numeric_tab, categorical_tab, correlation_tab, group_tab = st.tabs(
        ["数值统计", "分类统计", "相关性", "分组分析"]
    )

    with numeric_tab:
        summary = numeric_summary(dataframe)
        if summary.empty:
            st.info("当前数据中没有数值字段。")
        else:
            st.dataframe(summary, width="stretch", hide_index=True)

    with categorical_tab:
        summary = categorical_summary(dataframe)
        if summary.empty:
            st.info("当前数据中没有可统计的文本或分类字段。")
        else:
            st.dataframe(summary, width="stretch", hide_index=True)

    with correlation_tab:
        if len(numeric_cols) < 2:
            st.info("至少需要两个数值字段才能计算相关性。")
        else:
            method_label = st.selectbox("相关系数", ["Pearson", "Spearman", "Kendall"], key="corr_method")
            method = method_label.lower()
            correlation = correlation_matrix(dataframe, method=method)
            st.plotly_chart(correlation_heatmap(correlation), width="stretch", key="stats_correlation")

    with group_tab:
        if dataframe.empty:
            st.info("当前数据为空。")
            return
        group_column = st.selectbox("分组字段", list(dataframe.columns), key="group_column")
        value_options = ["仅统计行数"] + numeric_cols
        value_choice = st.selectbox("统计字段", value_options, key="group_value")
        aggregation = "count"
        if value_choice != "仅统计行数":
            aggregation = st.selectbox(
                "聚合方式",
                ["mean", "median", "sum", "min", "max", "std", "count"],
                key="group_aggregation",
            )
        result = group_summary(
            dataframe,
            group_column=group_column,
            value_column=None if value_choice == "仅统计行数" else value_choice,
            aggregation=aggregation,
            top_n=200,
        )
        st.dataframe(result, width="stretch", hide_index=True)


def render_visualization(dataframe: pd.DataFrame) -> None:
    st.subheader("交互式可视化")
    numeric_cols = numeric_columns(dataframe)
    category_cols = categorical_columns(dataframe)
    all_columns = list(dataframe.columns)

    chart_type = st.selectbox(
        "图表类型",
        ["缺失值", "直方图", "箱线图", "分类计数", "折线图", "散点图", "相关性热力图"],
        key="chart_type",
    )

    if chart_type == "缺失值":
        figure = missingness_bar(dataframe)
    elif chart_type == "直方图":
        if not numeric_cols:
            st.info("没有数值字段可绘制直方图。")
            return
        column = st.selectbox("数值字段", numeric_cols, key="hist_column")
        bins = st.slider("分箱数量", 5, 100, 30, key="hist_bins")
        figure = histogram(dataframe, column, bins=bins)
    elif chart_type == "箱线图":
        if not numeric_cols:
            st.info("没有数值字段可绘制箱线图。")
            return
        value_column = st.selectbox("数值字段", numeric_cols, key="box_value")
        group_options = ["不分组"] + category_cols
        group_choice = st.selectbox("分组字段", group_options, key="box_group")
        figure = box_plot(
            dataframe,
            value_column=value_column,
            group_column=None if group_choice == "不分组" else group_choice,
        )
    elif chart_type == "分类计数":
        if not all_columns:
            return
        column = st.selectbox("分类字段", all_columns, key="bar_column")
        top_n = st.slider("最多展示类别数", 5, 50, 20, key="bar_top_n")
        figure = bar_counts(dataframe, column, top_n=top_n)
    elif chart_type == "折线图":
        if not numeric_cols:
            st.info("没有数值字段可绘制折线图。")
            return
        x_column = st.selectbox("X 轴字段", all_columns, key="line_x")
        y_column = st.selectbox("Y 轴数值字段", numeric_cols, key="line_y")
        color_options = ["不分组"] + [column for column in category_cols if column != x_column]
        color_choice = st.selectbox("颜色分组", color_options, key="line_color")
        figure = line_chart(
            dataframe,
            x_column=x_column,
            y_column=y_column,
            color_column=None if color_choice == "不分组" else color_choice,
        )
    elif chart_type == "散点图":
        if len(numeric_cols) < 2:
            st.info("至少需要两个数值字段才能绘制散点图。")
            return
        x_column = st.selectbox("X 轴数值字段", numeric_cols, key="scatter_x")
        y_column = st.selectbox(
            "Y 轴数值字段",
            [column for column in numeric_cols if column != x_column],
            key="scatter_y",
        )
        color_options = ["不分组"] + category_cols
        color_choice = st.selectbox("颜色分组", color_options, key="scatter_color")
        figure = scatter_plot(
            dataframe,
            x_column=x_column,
            y_column=y_column,
            color_column=None if color_choice == "不分组" else color_choice,
        )
    else:
        correlation = correlation_matrix(dataframe)
        figure = correlation_heatmap(correlation)

    st.plotly_chart(figure, width="stretch", key=f"visualization_{chart_type}")


def render_export(dataframe: pd.DataFrame, active_label: str, source_name: str) -> None:
    st.subheader("导出结果")
    st.caption("导出文件在浏览器内存中生成；原始文件不会在本应用中写入磁盘。")

    sanitize = st.checkbox(
        "防止 CSV/Excel 公式注入",
        value=True,
        help="若单元格以 =、+、-、@ 开头，会添加单引号，使其按文本处理。",
    )
    export_df = sanitize_dataframe_for_export(dataframe) if sanitize else dataframe
    tag = "cleaned" if active_label == "清洗后数据" else "current"

    csv_name = suggest_output_name(source_name, ".csv", tag=tag)
    xlsx_name = suggest_output_name(source_name, ".xlsx", tag=tag)

    download_columns = st.columns(2)
    download_columns[0].download_button(
        "下载 CSV",
        data=dataframe_to_csv_bytes(export_df),
        file_name=csv_name,
        mime="text/csv",
        width="stretch",
    )
    download_columns[1].download_button(
        "下载 Excel",
        data=dataframe_to_excel_bytes(export_df),
        file_name=xlsx_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    st.markdown("#### 将导出的数据")
    st.dataframe(export_df.head(100), width="stretch", hide_index=True)


st.title("📊 表格清洗、统计与可视化")
st.caption("上传 CSV/XLSX/XLS，完成数据质量检查、清洗、统计分析和交互式图表。")

original_df, source_name = load_source()

active_options = ["原始数据"]
if st.session_state.get("cleaned_df") is not None:
    active_options.append("清洗后数据")

pending_active = st.session_state.pop("pending_active_data", None)
if pending_active in active_options:
    st.session_state.active_data = pending_active
if st.session_state.get("active_data") not in active_options:
    st.session_state.active_data = "原始数据"

active_label = st.sidebar.radio(
    "用于分析和导出的数据",
    active_options,
    key="active_data",
    horizontal=False,
)
active_df = (
    st.session_state.original_df
    if active_label == "原始数据"
    else st.session_state.cleaned_df
)

st.sidebar.markdown("---")
st.sidebar.caption("所有分析默认只在本机完成。请勿上传包含敏感信息的文件到不受信任的环境。")

if active_df is None:
    st.error("当前没有可分析的数据。")
    st.stop()

overview_tab, cleaning_tab, statistics_tab, visualization_tab, export_tab = st.tabs(
    ["数据概览", "数据清洗", "统计分析", "可视化", "导出"]
)

with overview_tab:
    render_overview(active_df)

with cleaning_tab:
    render_cleaning(st.session_state.original_df)

with statistics_tab:
    render_statistics(active_df)

with visualization_tab:
    render_visualization(active_df)

with export_tab:
    render_export(active_df, active_label, source_name)





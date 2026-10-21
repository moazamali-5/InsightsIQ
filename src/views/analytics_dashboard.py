"""Analytics Dashboard page: professional EDA and analytics for the dataset.

Displays dynamic KPI cards, an interactive chart builder, statistical analysis
(descriptive statistics, correlation matrix, IQR outlier analysis) and automated
rule-based insights. All numbers are computed from the current working dataset
(cleaned data if available, otherwise the uploaded dataset). The original upload
is never modified.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.analysis import (
    all_outlier_analysis,
    chart_columns,
    classify_columns,
    column_profile,
    correlation_matrix,
    dataset_summary,
    generate_findings,
    missingness_insights,
    numeric_statistics,
    outlier_analysis,
    strong_correlations,
    time_series_agg,
    top_categories,
)
from src.config import CHART_COLORWAY, COLORS
from src.state import get_dataset, get_setting, go_to
from src.theme import inject_theme, metric_card, page_header
from src.utils import format_int, format_pct

C = COLORS


def _chart_title_default(chart_type: str, x_col: Optional[str], y_col: Optional[str]) -> str:
    parts = [p for p in (x_col, y_col) if p]
    if parts:
        return f"{chart_type}: {' vs '.join(parts)}"
    return chart_type


def _apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Apply optional categorical and date-range filters from session state.

    Returns a filtered copy of ``df``. The original dataset is never modified.
    """
    filtered = df.copy()
    groups = classify_columns(filtered)

    cat_cols = [c for c in groups["categorical"] if filtered[c].nunique(dropna=True) <= 50]
    for col in cat_cols:
        key = f"filt_cat_{col}"
        all_vals = sorted(filtered[col].dropna().astype(str).unique().tolist())
        selected = st.session_state.get(key, all_vals)
        if selected and len(selected) < len(all_vals):
            filtered = filtered[filtered[col].astype(str).isin(selected)]

    for col in groups["datetime"]:
        key_start = f"filt_date_start_{col}"
        key_end = f"filt_date_end_{col}"
        d_min = pd.to_datetime(filtered[col]).min()
        d_max = pd.to_datetime(filtered[col]).max()
        if pd.isna(d_min) or pd.isna(d_max):
            continue
        d_min = d_min.date()
        d_max = d_max.date()
        start_val = st.session_state.get(key_start, d_min)
        end_val = st.session_state.get(key_end, d_max)
        if start_val or end_val:
            start_ts = pd.Timestamp(start_val) if start_val else d_min
            end_ts = pd.Timestamp(end_val) if end_val else d_max
            filtered = filtered[
                (pd.to_datetime(filtered[col]) >= start_ts)
                & (pd.to_datetime(filtered[col]) <= end_ts + pd.Timedelta(days=1))
            ]
    return filtered


def _render_kpi_cards(df: pd.DataFrame) -> None:
    """Display dynamic KPI cards based on the dataset contents."""
    summary = dataset_summary(df)
    groups = classify_columns(df)
    numeric = groups["numeric"]

    st.markdown("### Key performance indicators")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        metric_card("Total rows", format_int(summary["rows"]))
    with c2:
        metric_card("Total columns", format_int(summary["columns"]))
    with c3:
        metric_card(
            "Missing cells",
            format_int(summary["missing_cells"]),
            format_pct(summary["missing_pct"]),
            "danger" if summary["missing_cells"] else "success",
        )
    with c4:
        metric_card(
            "Duplicate rows",
            format_int(summary["duplicate_rows"]),
            format_pct(summary["duplicate_pct"]),
            "danger" if summary["duplicate_rows"] else "success",
        )
    with c5:
        metric_card("Numeric columns", summary["numeric_count"])
    with c6:
        metric_card("Categorical columns", summary["categorical_count"])

    suitable_numeric = [c for c in numeric if df[c].notna().any()]
    if suitable_numeric:
        st.markdown("---")
        st.markdown("### Numeric column metrics")
        for col in suitable_numeric[:4]:
            series = df[col].dropna()
            c1, c2, c3 = st.columns(3)
            with c1:
                metric_card(f"{col} — Sum", format_int(series.sum()))
            with c2:
                metric_card(f"{col} — Mean", f"{series.mean():,.2f}")
            with c3:
                metric_card(f"{col} — Median", f"{series.median():,.2f}")
            st.markdown("")


def render() -> None:
    inject_theme()

    page_header(
        "Analytics Dashboard",
        "Exploratory data analysis and interactive charts built from your dataset.",
    )

    df = get_dataset()
    if df is None:
        st.info("No dataset loaded. Upload a file from the **Upload Dataset** page.")
        if st.button("Go to Upload Dataset", use_container_width=True):
            go_to("Upload Dataset")
            st.rerun()
        return

    summary = dataset_summary(df)
    groups = classify_columns(df)
    numeric = groups["numeric"]
    categorical = groups["categorical"]
    datetime_ = groups["datetime"]

    # ---- Filters -----------------------------------------------------------
    filtered_df = _render_filters(df)

    # ---- KPI cards ---------------------------------------------------------
    _render_kpi_cards(filtered_df)

    st.markdown("---")

    # ---- Interactive chart builder ----------------------------------------
    _render_chart_builder(filtered_df, numeric, categorical, datetime_)

    st.markdown("---")

    # ---- Statistical analysis ---------------------------------------------
    _render_statistical_analysis(filtered_df, numeric, categorical, datetime_)

    st.markdown("---")

    # ---- Automated insights ------------------------------------------------
    _render_automated_insights(filtered_df, numeric, categorical, datetime_)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Go to Data Cleaning Studio", use_container_width=True):
            go_to("Data Cleaning Studio")
            st.rerun()
    with c2:
        if st.button("Go to Reports", use_container_width=True):
            go_to("Reports")
            st.rerun()


def _render_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render filter controls and return the filtered dataset."""
    groups = classify_columns(df)
    cat_cols = [c for c in groups["categorical"] if df[c].nunique(dropna=True) <= 50]
    date_cols = groups["datetime"]

    if not cat_cols and not date_cols:
        st.caption(
            "No filterable columns detected (categorical columns exceed 50 categories "
            "or no date columns are present)."
        )
        return df

    with st.expander("🔎 Filters — narrow the data scope", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            for col in cat_cols:
                key = f"filt_cat_{col}"
                all_vals = sorted(df[col].dropna().astype(str).unique().tolist())
                default = st.session_state.get(key, all_vals)
                st.multiselect(
                    col,
                    options=all_vals,
                    default=default,
                    key=key,
                )
        with c2:
            for col in date_cols:
                d_min = pd.to_datetime(df[col]).min().date()
                d_max = pd.to_datetime(df[col]).max().date()
                key_s = f"filt_date_start_{col}"
                key_e = f"filt_date_end_{col}"
                cs, ce = st.columns(2)
                with cs:
                    st.date_input(
                        f"{col} — from",
                        value=st.session_state.get(key_s, d_min),
                        min_value=d_min,
                        max_value=d_max,
                        key=key_s,
                    )
                with ce:
                    st.date_input(
                        f"{col} — to",
                        value=st.session_state.get(key_e, d_max),
                        min_value=d_min,
                        max_value=d_max,
                        key=key_e,
                    )

    filtered = _apply_filters(df)
    st.caption(
        f"Data scope: {format_int(len(filtered))} of {format_int(len(df))} rows "
        f"({format_pct(len(filtered) / len(df) * 100)}) after filters."
    )
    return filtered


def _render_chart_builder(df: pd.DataFrame, numeric: list, categorical: list, datetime_: list) -> None:
    """Interactive chart builder: bar, line, pie/donut, histogram, scatter, box plot, heatmap."""
    st.markdown("### Interactive chart builder")
    st.caption(
        "Select a chart type and columns to visualise your data. Controls adapt to the chosen chart."
    )

    chart_types = [
        "Bar chart",
        "Line chart",
        "Pie / donut chart",
        "Histogram",
        "Scatter plot",
        "Box plot",
        "Correlation heatmap",
    ]

    c1, c2 = st.columns([1, 1])
    with c1:
        chart_type = st.selectbox(
            "Chart type",
            chart_types,
            index=0,
            key="cb_chart_type",
        )
    with c2:
        chart_title = st.text_input(
            "Chart title (optional)",
            key="cb_title",
            help="Leave blank to use an auto-generated title.",
        )

    x_col = None
    y_col = None
    color_col = None
    size_col = None
    hole = 0.0
    nbins = 30
    top_n = int(get_setting("max_categories"))

    if chart_type != "Correlation heatmap":
        c1, c2, c3 = st.columns(3)
        with c1:
            x_options = ["(none)"] + categorical + numeric + datetime_
            x_col = st.selectbox(
                "X axis / names",
                x_options,
                index=0,
                key="cb_x_col",
            )
        with c2:
            y_options = ["(none)"] + numeric
            y_col = st.selectbox(
                "Y axis / values",
                y_options,
                index=0,
                key="cb_y_col",
            )
        with c3:
            color_options = ["(none)"] + categorical
            color_col = st.selectbox(
                "Colour by",
                color_options,
                index=0,
                key="cb_color_col",
            )

        if chart_type == "Histogram":
            nbins = st.slider("Number of bins", 5, 100, 30, key="cb_nbins")
        if chart_type == "Pie / donut chart":
            hole = st.slider("Donut hole size", 0.0, 0.7, 0.0, 0.1, key="cb_hole")
        if chart_type == "Scatter plot":
            size_options = ["(none)"] + numeric
            size_col = st.selectbox(
                "Bubble size (optional)",
                size_options,
                index=0,
                key="cb_size_col",
            )
        if chart_type == "Bar chart":
            top_n = st.slider("Top N categories", 5, 100, top_n, 5, key="cb_top_n")

    x_col = None if x_col == "(none)" else x_col
    y_col = None if y_col == "(none)" else y_col
    color_col = None if color_col == "(none)" else color_col
    size_col = None if size_col == "(none)" else size_col

    title = chart_title or _chart_title_default(chart_type, x_col, y_col)

    st.markdown("---")
    st.markdown("#### Chart")

    fig = _build_figure(
        df,
        chart_type,
        x_col,
        y_col,
        color_col,
        size_col,
        title,
        hole=hole,
        nbins=nbins,
        top_n=top_n,
        numeric=numeric,
        categorical=categorical,
        datetime_=datetime_,
    )
    if fig is None:
        st.info(
            "Choose compatible columns for this chart type. "
            "Bar/pie/box need a categorical column; histogram/scatter/box need a numeric Y; "
            "line needs a date X; correlation heatmap needs at least two numeric columns."
        )
    else:
        st.plotly_chart(fig, use_container_width=True)

def _build_figure(
    df: pd.DataFrame,
    chart_type: str,
    x_col: Optional[str],
    y_col: Optional[str],
    color_col: Optional[str],
    size_col: Optional[str],
    title: str,
    hole: float = 0.0,
    nbins: int = 30,
    top_n: int = 15,
    numeric: Optional[list] = None,
    categorical: Optional[list] = None,
    datetime_: Optional[list] = None,
):
    """Build a Plotly figure for the given chart type and column selection.

    Returns None if the selection cannot be charted.
    """
    if numeric is None:
        numeric = chart_columns(df)["numeric"]
    if categorical is None:
        categorical = chart_columns(df)["categorical"]
    if datetime_ is None:
        datetime_ = chart_columns(df)["datetime"]

    color_arg = color_col if color_col else None

    if chart_type == "Pie / donut chart":
        if not categorical:
            return None
        names_col = x_col if x_col in categorical else categorical[0]
        if y_col and y_col in numeric:
            agg_df = (
                df.groupby(names_col)[y_col]
                .sum()
                .reset_index()
                .sort_values(y_col, ascending=False)
                .head(top_n)
            )
            fig = px.pie(
                agg_df,
                names=names_col,
                values=y_col,
                hole=hole,
                color_discrete_sequence=CHART_COLORWAY,
            )
        else:
            counts = df[names_col].value_counts(dropna=False).head(top_n)
            fig = px.pie(
                names=counts.index.astype(str),
                values=counts.values,
                hole=hole,
                color_discrete_sequence=CHART_COLORWAY,
            )
        fig.update_layout(title=title, showlegend=bool(color_arg))
        return fig

    if chart_type == "Histogram":
        if not numeric:
            return None
        col = x_col if x_col in numeric else numeric[0]
        fig = px.histogram(
            df,
            x=col,
            nbins=nbins,
            color=color_arg or None,
            color_discrete_sequence=CHART_COLORWAY,
        )
        fig.update_layout(
            title=title,
            showlegend=bool(color_arg),
            xaxis_title=col,
            yaxis_title="Count",
        )
        return fig

    if chart_type == "Scatter plot":
        if not numeric or len(numeric) < 2:
            return None
        x = x_col if x_col in numeric else numeric[0]
        y = y_col if y_col in numeric else (numeric[1] if len(numeric) > 1 else numeric[0])
        if x == y:
            y = numeric[1] if len(numeric) > 1 else numeric[0]
        sample_n = int(get_setting("scatter_sample"))
        plot_df = df.sample(n=min(sample_n, len(df)), random_state=42) if len(df) > sample_n else df
        fig = px.scatter(
            plot_df,
            x=x,
            y=y,
            color=color_arg,
            size=size_col if size_col else None,
            color_discrete_sequence=CHART_COLORWAY,
        )
        fig.update_layout(
            title=title,
            xaxis_title=x,
            yaxis_title=y,
        )
        return fig

    if chart_type == "Box plot":
        if not numeric:
            return None
        y = y_col if y_col in numeric else numeric[0]
        fig = px.box(
            df,
            x=x_col if x_col in categorical else None,
            y=y,
            color=color_arg,
            color_discrete_sequence=CHART_COLORWAY,
            points="outliers",
        )
        fig.update_layout(
            title=title,
            xaxis_title=x_col if x_col in categorical else "",
            yaxis_title=y,
        )
        return fig

    if chart_type == "Correlation heatmap":
        if len(numeric) < 2:
            return None
        corr = df[numeric].corr()
        fig = go.Figure(
            data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.index,
                colorscale="Blues",
                zmid=0,
                colorbar=dict(title="r"),
            )
        )
        fig.update_layout(title=title, xaxis_title="", yaxis_title="")
        return fig

    return None
def _render_statistical_analysis(
    df: pd.DataFrame, numeric: list, categorical: list, datetime_: list
) -> None:
    """Descriptive statistics, correlation matrix and IQR outlier analysis."""
    st.markdown("### Statistical analysis")

    # ---- Descriptive statistics -------------------------------------------
    st.markdown("#### Descriptive statistics (numeric columns)")
    stats_df = numeric_statistics(df)
    if stats_df.empty:
        st.info("No numeric columns available for descriptive statistics.")
    else:
        display = stats_df.copy()
        for col in ["Mean", "Std Dev", "Min", "25%", "Median", "75%", "Max"]:
            if col in display.columns:
                display[col] = display[col].map(lambda v: f"{v:,.4f}" if pd.notna(v) else "—")
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- Correlation matrix -----------------------------------------------
    st.markdown("#### Correlation matrix (numeric columns)")
    corr = correlation_matrix(df)
    if corr.empty:
        st.info("Need at least two numeric columns with sufficient data to compute correlations.")
    else:
        fig = go.Figure(
            data=go.Heatmap(
                z=corr.values,
                x=corr.columns,
                y=corr.index,
                colorscale="RdBu",
                zmid=0,
                zmin=-1,
                zmax=1,
                colorbar=dict(title="Pearson r"),
            )
        )
        fig.update_layout(
            title="Correlation matrix",
            xaxis_title="",
            yaxis_title="",
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

        pairs = strong_correlations(df)
        if pairs:
            st.markdown("**Strong correlations (|r| ≥ 0.7):**")
            for a, b, r in pairs[:10]:
                direction = "positive" if r > 0 else "negative"
                st.markdown(
                    f'<div class="muted">• <strong>{a}</strong> ↔ <strong>{b}</strong>: '
                    f'{direction} (r = {r:.2f})</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No strong correlations (|r| ≥ 0.7) detected.")

    st.markdown("---")

    # ---- Outlier analysis -------------------------------------------------
    st.markdown("#### Outlier analysis (IQR method)")
    st.caption(
        "Outliers are values beyond Q1 − 1.5×IQR or Q3 + 1.5×IQR. "
        "They are potential anomalies, not automatically incorrect values."
    )
    outlier_results = all_outlier_analysis(df)
    if not outlier_results:
        st.info("No numeric columns with sufficient data for outlier analysis.")
    else:
        total_outliers = sum(r["count"] for r in outlier_results.values())
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Columns analysed", len(outlier_results))
        with c2:
            metric_card("Total outliers flagged", format_int(total_outliers))
        with c3:
            total_nonnull = sum(int(df[c].notna().sum()) for c in outlier_results)
            outlier_pct = total_outliers / total_nonnull * 100 if total_nonnull else 0.0
            metric_card("Outlier % of values", format_pct(outlier_pct))

        for col, res in outlier_results.items():
            with st.expander(f"{col} — {res['count']} outlier(s)", expanded=False):
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    metric_card("Q1", f"{res['q1']:,.4f}" if res['q1'] is not None else "—")
                with c2:
                    metric_card("Q3", f"{res['q3']:,.4f}" if res['q3'] is not None else "—")
                with c3:
                    metric_card("IQR", f"{res['iqr']:,.4f}" if res['iqr'] is not None else "—")
                with c4:
                    metric_card("Outlier %", format_pct(res["pct"]))
                st.caption(
                    f"Lower bound: {res['lower_bound']:,.4f} | "
                    f"Upper bound: {res['upper_bound']:,.4f}"
                )
                if res["outlier_values"]:
                    st.markdown("**Outlier values:**")
                    st.write(res["outlier_values"][:20])
                    if len(res["outlier_values"]) > 20:
                        st.caption(f"Showing first 20 of {len(res['outlier_values'])} outliers.")
                else:
                    st.success("No outliers detected.")
def _render_automated_insights(
    df: pd.DataFrame, numeric: list, categorical: list, datetime_: list
) -> None:
    """Rule-based automated insights derived from the actual data."""
    st.markdown("### Automated insights")
    st.caption(
        "All findings below are computed from your data. "
        "They describe observed patterns — no causal claims or recommendations are made."
    )

    findings = generate_findings(df)
    for finding in findings:
        st.markdown(f'<div class="muted">• {finding}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ---- Top categories by selected metric --------------------------------
    st.markdown("#### Top categories")
    if categorical and numeric:
        c1, c2, c3 = st.columns(3)
        with c1:
            cat_col = st.selectbox(
                "Category column",
                categorical,
                key="ai_cat_col",
            )
        with c2:
            val_col = st.selectbox(
                "Value column",
                numeric,
                key="ai_val_col",
            )
        with c3:
            agg = st.selectbox(
                "Aggregation",
                ["Sum", "Mean", "Count", "Min", "Max"],
                index=0,
                key="ai_agg",
            )
        top_df = top_categories(df, cat_col, val_col, agg.lower(), top_n=10)
        if not top_df.empty:
            top_df = top_df.copy()
            top_df["value"] = top_df["value"].map(
                lambda v: f"{v:,.4f}" if isinstance(v, float) else f"{v:,}"
            )
            st.dataframe(top_df, use_container_width=True, hide_index=True)

            # Highlight highest and lowest
            best_row = top_df.iloc[0]
            worst_row = top_df.iloc[-1]
            st.info(
                f"Highest {agg.lower()}: '{best_row[cat_col]}' ({best_row['value']}) · "
                f"Lowest {agg.lower()}: '{worst_row[cat_col]}' ({worst_row['value']})"
            )
    elif categorical:
        st.info("Add a numeric column to rank categories by a metric.")
    else:
        st.info("No categorical columns available for category rankings.")

    st.markdown("---")

    # ---- Time-based trends ------------------------------------------------
    st.markdown("#### Time-based trends")
    if datetime_ and numeric:
        c1, c2, c3 = st.columns(3)
        with c1:
            date_col = st.selectbox(
                "Date column",
                datetime_,
                key="ai_date_col",
            )
        with c2:
            val_col2 = st.selectbox(
                "Value column",
                numeric,
                key="ai_val_col2",
            )
        with c3:
            freq = st.selectbox(
                "Frequency",
                ["D", "W", "M", "Q", "Y"],
                index=2,
                key="ai_freq",
                help="D=daily, W=weekly, M=monthly, Q=quarterly, Y=yearly",
            )
        trend_df = time_series_agg(df, date_col, val_col2, freq=freq, agg="sum")
        if not trend_df.empty:
            fig = px.line(
                trend_df,
                x=date_col,
                y=val_col2,
                title=f"{val_col2} over {date_col} ({freq})",
            )
            fig.update_traces(line=dict(color=C["blue_500"]))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No valid date-value pairs for trend analysis.")
    elif datetime_:
        st.info("Add a numeric column to view time-based trends.")
    else:
        st.info("No date columns available for time-based analysis.")

    st.markdown("---")

    # ---- Missingness insights ---------------------------------------------
    st.markdown("#### Columns with significant missingness")
    missing_insights = missingness_insights(df, threshold=5.0)
    if missing_insights:
        for insight in missing_insights:
            st.markdown(
                f'<div class="muted">• <strong>{insight["column"]}</strong>: '
                f'{format_int(insight["missing"])} missing cells '
                f"({format_pct(insight['pct'])}%)</div>",
                unsafe_allow_html=True,
            )
    else:
        st.success("No columns with ≥5% missingness detected.")

    st.markdown("---")

    # ---- Strong correlations ----------------------------------------------
    st.markdown("#### Strong numeric correlations")
    pairs = strong_correlations(df)
    if pairs:
        for a, b, r in pairs[:10]:
            direction = "positive" if r > 0 else "negative"
            st.markdown(
                f'<div class="muted">• <strong>{a}</strong> ↔ <strong>{b}</strong>: '
                f'{direction} correlation (r = {r:.2f})</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("No strong correlations (|r| ≥ 0.7) detected between numeric columns.")

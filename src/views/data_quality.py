"""Data Quality page: quality score, column profile and detected issues."""

from __future__ import annotations

import streamlit as st

from src.analysis import column_profile, dataset_summary, generate_findings, quality_issues, quality_label, quality_score
from src.state import get_dataset, get_meta, go_to
from src.theme import inject_theme, metric_card, page_header
from src.utils import format_int, format_pct


def render() -> None:
    inject_theme()

    page_header("Data Quality", "Assess completeness and consistency of your dataset.")

    df = get_dataset()
    if df is None:
        st.info("No dataset loaded. Upload a file from the **Upload Dataset** page.")
        if st.button("Go to Upload Dataset", use_container_width=True):
            go_to("Upload Dataset")
            st.rerun()
        return

    summary = dataset_summary(df)
    score = quality_score(summary)
    label = quality_label(score)

    st.markdown("### Quality score")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Score", f"{score:.0f} / 100", f"{label}", "success" if score >= 75 else "warning")
    with c2:
        metric_card("Missing cells", format_int(summary["missing_cells"]), format_pct(summary["missing_pct"]), "danger")
    with c3:
        metric_card("Duplicate rows", format_int(summary["duplicate_rows"]), format_pct(summary["duplicate_pct"]), "danger")
    with c4:
        metric_card("Complete rows", format_int(summary["complete_rows"]), format_pct(summary["complete_rows"] / summary["rows"] * 100), "success")

    st.markdown("### Dataset overview")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Total rows", format_int(summary["rows"]))
    with c2:
        metric_card("Total columns", format_int(summary["columns"]))
    with c3:
        metric_card("Numeric columns", summary["numeric_count"])
    with c4:
        metric_card("Categorical columns", summary["categorical_count"])
    with c5:
        metric_card("Date columns", summary["datetime_count"])

    st.markdown("### Key findings")
    for finding in generate_findings(df):
        st.markdown(f'<div class="muted">• {finding}</div>', unsafe_allow_html=True)

    st.markdown("### Detected issues")
    issues = quality_issues(df)
    if issues:
        for issue in issues:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue["level"], "•")
            st.markdown(f'<div class="muted">{icon} {issue["message"]}</div>', unsafe_allow_html=True)
    else:
        st.success("No significant data-quality issues detected.")

    st.markdown("---")
    st.markdown("### Missing-value table")
    st.caption("One row per column: name, data type, missing values, missing percentage and unique values.")
    profile = column_profile(df)
    show = profile[
        ["Column", "Data Type", "Missing", "Missing %", "Unique", "Kind", "Non-Null"]
    ].copy()
    show["Missing %"] = show["Missing %"].map(lambda v: f"{v:.1f}%")
    st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown("---")
    if st.button("Go to Analytics Dashboard", use_container_width=True):
        go_to("Analytics Dashboard")
        st.rerun()

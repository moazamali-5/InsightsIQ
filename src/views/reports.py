"""Reports page: a plain-text summary of the dataset and its findings."""

from __future__ import annotations

import streamlit as st

from src.analysis import dataset_summary, generate_findings, quality_issues, quality_label, quality_score
from src.state import get_dataset, get_setting, go_to
from src.theme import inject_theme, metric_card, page_header
from src.utils import format_bytes, format_int, format_pct


def render() -> None:
    inject_theme()

    page_header("Reports", "Export a plain-language summary of your dataset.")

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

    st.markdown("### Dataset report")
    st.markdown(
        f"""<div class="info-card">
        <h4>{summary['rows']:,} rows × {summary['columns']} columns</h4>
        <p>
        <strong>Quality score:</strong> {score:.0f} / 100 — {label}<br>
        <strong>Missing cells:</strong> {format_int(summary['missing_cells'])} ({format_pct(summary['missing_pct'])})<br>
        <strong>Duplicate rows:</strong> {format_int(summary['duplicate_rows'])} ({format_pct(summary['duplicate_pct'])})<br>
        <strong>Complete rows:</strong> {format_int(summary['complete_rows'])} ({format_pct(summary['complete_rows'] / summary['rows'] * 100)})<br>
        <strong>Columns by type:</strong> {summary['numeric_count']} numeric, {summary['categorical_count']} categorical, {summary['datetime_count']} date/time<br>
        <strong>In-memory size:</strong> {format_bytes(summary['memory_bytes'])}
        </p>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("### Findings")
    for finding in generate_findings(df):
        st.markdown(f'<div class="muted">• {finding}</div>', unsafe_allow_html=True)

    st.markdown("### Quality issues")
    issues = quality_issues(df)
    if issues:
        for issue in issues:
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(issue["level"], "•")
            st.markdown(f'<div class="muted">{icon} {issue["message"]}</div>', unsafe_allow_html=True)
    else:
        st.success("No significant data-quality issues detected.")

    st.markdown("---")
    st.markdown("### Download")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download cleaned dataset (CSV)",
        data=csv,
        file_name="insightiq_export.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("---")
    if st.button("Go to Settings", use_container_width=True):
        go_to("Settings")
        st.rerun()

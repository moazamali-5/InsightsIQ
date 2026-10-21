"""Professional PDF and Excel reports generated from the selected dataset."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.professional_report import build_excel_report, build_pdf_report, build_report
from src.state import go_to
from src.theme import inject_theme, page_header

CURRENT_SCOPE = "Current working dataset"
ORIGINAL_SCOPE = "Original uploaded dataset"


def render() -> None:
    inject_theme()
    page_header(
        "Professional Reports",
        "Generate a data-driven report with analysis, charts, and PDF/Excel downloads.",
    )

    current_df = st.session_state.get("df")
    original_df = st.session_state.get("df_original")
    if not isinstance(current_df, pd.DataFrame):
        st.info("No dataset loaded. Upload a file from the **Upload Dataset** page.")
        if st.button("Go to Upload Dataset", width="stretch"):
            go_to("Upload Dataset")
            st.rerun()
        return

    scopes = [CURRENT_SCOPE]
    datasets = {CURRENT_SCOPE: current_df}
    if isinstance(original_df, pd.DataFrame):
        scopes.append(ORIGINAL_SCOPE)
        datasets[ORIGINAL_SCOPE] = original_df

    selected_scope = st.segmented_control(
        "Dataset scope",
        scopes,
        default=CURRENT_SCOPE,
        required=True,
        key="professional_report_scope",
        help="Choose whether the report analyses the current working data or the untouched upload.",
    )
    selected_df = datasets[selected_scope]
    st.caption(
        f"Selected scope: {selected_scope} — {selected_df.shape[0]:,} rows × "
        f"{selected_df.shape[1]:,} columns. Report generation does not alter the dataset or cleaning history."
    )

    if st.button("Generate Report", type="primary", width="stretch"):
        with st.spinner("Analysing the selected dataset and building report files..."):
            report = build_report(selected_df, selected_scope)
            pdf_bytes = build_pdf_report(report)
            excel_bytes = build_excel_report(selected_df, report)
        st.session_state["report_files"] = {
            "scope": selected_scope,
            "pdf": pdf_bytes,
            "excel": excel_bytes,
            "report": report,
        }
        st.success("Professional PDF and Excel reports are ready.")

    files = st.session_state.get("report_files")
    if not files or files.get("scope") != selected_scope:
        st.info("Choose a dataset scope and select **Generate Report** to create your downloads.")
        return

    report = files["report"]
    st.markdown("### Executive Summary")
    st.write(report["executive_summary"])
    st.markdown("### Key Data Findings")
    for finding in report["findings"]:
        st.markdown(f"- {finding}")
    st.markdown("### Practical Recommendations")
    for recommendation in report["recommendations"]:
        st.markdown(f"- {recommendation}")

    with st.expander("Report charts", expanded=False):
        if report["charts"]:
            for chart in report["charts"]:
                st.markdown(f"**{chart['title']}**")
                st.image(
                    chart["image"],
                    width="stretch",
                    alt=chart["title"],
                )
        else:
            st.info(
                "No suitable numeric, categorical, date, or multi-numeric columns were found for charts."
            )

    st.markdown("### Download reports")
    st.caption(
        "The Excel workbook contains five worksheets. Its **Cleaned Dataset** sheet contains "
        "the data from the selected scope; the scope is also recorded in Dataset Overview."
    )
    pdf_col, excel_col = st.columns(2)
    with pdf_col:
        st.download_button(
            "Download PDF report",
            data=files["pdf"],
            file_name="insightiq_professional_report.pdf",
            mime="application/pdf",
            width="stretch",
        )
    with excel_col:
        st.download_button(
            "Download Excel report",
            data=files["excel"],
            file_name="insightiq_professional_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )

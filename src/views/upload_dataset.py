"""Upload Dataset page: file uploader with sheet selection and error handling."""

from __future__ import annotations

import streamlit as st

from src.config import SUPPORTED_EXTENSIONS
from src.data_loader import DataLoadError, get_extension, list_excel_sheets, load_dataset
from src.state import clear_dataset, go_to, set_dataset
from src.theme import info_card, inject_theme, metric_card, page_header


def render() -> None:
    inject_theme()

    page_header("Upload Dataset", "Load a CSV or Excel file to begin analysing your data.")

    st.markdown(
        f'<p class="muted">Supported formats: {", ".join("." + e for e in SUPPORTED_EXTENSIONS)} '
        f"(max 200 MB)</p>", unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Choose a file",
        type=SUPPORTED_EXTENSIONS,
        accept_multiple_files=False,
        help="Upload a .csv or .xlsx file containing your dataset.",
    )

    sheet_name = None
    if uploaded is not None and get_extension(uploaded.name) == "xlsx":
        st.markdown("**Excel sheet selection**")
        try:
            sheets = list_excel_sheets(uploaded.getvalue())
        except Exception as exc:  # surface a friendly message instead of crashing
            st.error(f"Could not read the Excel workbook: {exc}")
            return
        sheet_name = st.selectbox("Worksheet", sheets, index=0, help="Pick the sheet that contains your data.")

    if uploaded is not None:
        c1, c2 = st.columns([1, 1])
        with c1:
            load_btn = st.button("Load dataset", use_container_width=True, type="primary")
        with c2:
            if st.button("Clear current", use_container_width=True):
                clear_dataset()
                st.rerun()

        if load_btn:
            try:
                with st.spinner("Reading file..."):
                    df = load_dataset(uploaded.name, uploaded.getvalue(), sheet_name=sheet_name)
                from src.analysis import dataset_summary
                set_dataset(df, dataset_summary(df))
                st.success(f"Loaded **{uploaded.name}** — {df.shape[0]:,} rows × {df.shape[1]} columns.")
                st.rerun()
            except DataLoadError as exc:
                st.error(f"Unable to load file: {exc}")
                info_card(
                    "Tips",
                    "• Make sure the file is not open in another program (e.g. Excel).\n"
                    "• For CSV files, confirm the file uses UTF-8, Latin-1 or Windows-1252 encoding.\n"
                    "• For Excel files, ensure the workbook is not password-protected.",
                )
            except Exception as exc:  # never let the app crash on a bad upload
                st.error(f"Unexpected error while loading the file: {exc}")

    st.markdown("---")

    if st.session_state.get("df") is not None:
        metric_card("Rows", f"{st.session_state['df'].shape[0]:,}")
        metric_card("Columns", st.session_state["df"].shape[1])
        if st.button("Go to Data Preview", use_container_width=True):
            go_to("Data Preview")
            st.rerun()

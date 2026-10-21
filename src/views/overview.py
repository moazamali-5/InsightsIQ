"""Overview / landing page."""

from __future__ import annotations

import streamlit as st

from src.config import APP_FULL_NAME, APP_NAME, APP_VERSION
from src.state import get_page, go_to, has_dataset
from src.theme import app_header, info_card, inject_theme, metric_card, page_header


def render() -> None:
    inject_theme()

    app_header()

    st.markdown("---")

    page_header("Overview", "Welcome to InsightIQ. Upload a CSV or Excel file to explore and analyse your data.")

    st.markdown("### What is InsightIQ?")
    info_card(
        APP_FULL_NAME,
        "InsightIQ lets you upload business spreadsheets (CSV or Excel), preview the data, "
        "check data quality, and explore interactive charts — all without writing code or using "
        "external AI APIs. Everything runs locally on your machine.",
    )

    st.markdown("### Key features")
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Upload", "CSV & Excel", "Drag & drop supported")
        st.caption("Bring your own dataset. Files are read with pandas and kept in memory only.")
    with c2:
        metric_card("Preview & Profile", "Row & column stats", "Missing values at a glance")
        st.caption("See the shape of your data, column types, missing values and duplicates.")
    with c3:
        metric_card("Charts", "Interactive Plotly", "Numeric & categorical")
        st.caption("Bar, line, scatter and histogram charts generated from your data.")

    st.markdown("---")

    page_header("Get started", "Choose an option below to begin analysing your data.")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("Upload a dataset", use_container_width=True):
            go_to("Upload Dataset")
            st.rerun()
    with c2:
        if st.button("View an example", use_container_width=True):
            st.info("Example datasets are not bundled. Upload your own CSV or Excel file to get started.")
    with c3:
        if st.button("Open settings", use_container_width=True):
            go_to("Settings")
            st.rerun()

    if has_dataset():
        st.success("A dataset is currently loaded. Head to Data Preview or Analytics Dashboard to explore it.")
    else:
        st.info("No dataset loaded yet. Use **Upload Dataset** in the sidebar to load a CSV or Excel file.")

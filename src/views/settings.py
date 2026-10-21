"""Settings page: display preferences and dataset management."""

from __future__ import annotations

import streamlit as st

from src.config import APP_NAME, APP_VERSION
from src.state import clear_dataset, get_dataset, get_setting, reset_settings, set_setting
from src.theme import inject_theme, page_header


def render() -> None:
    inject_theme()

    page_header("Settings", "Adjust display preferences and manage the loaded dataset.")

    st.markdown("### Display preferences")
    c1, c2, c3 = st.columns(3)
    with c1:
        preview_rows = st.number_input(
            "Default rows in Data Preview",
            min_value=5, max_value=500, step=5,
            value=int(get_setting("preview_rows")),
        )
        set_setting("preview_rows", preview_rows)
    with c2:
        max_categories = st.number_input(
            "Max categories in bar charts",
            min_value=5, max_value=100, step=5,
            value=int(get_setting("max_categories")),
        )
        set_setting("max_categories", max_categories)
    with c3:
        scatter_sample = st.number_input(
            "Max points in scatter plots",
            min_value=500, max_value=50000, step=500,
            value=int(get_setting("scatter_sample")),
        )
        set_setting("scatter_sample", scatter_sample)

    st.markdown("---")
    st.markdown("### Dataset management")
    df = get_dataset()
    if df is not None:
        st.info(f"A dataset is loaded: {df.shape[0]:,} rows × {df.shape[1]} columns.")
        if st.button("Clear dataset", use_container_width=True):
            clear_dataset()
            st.success("Dataset cleared.")
            st.rerun()
    else:
        st.info("No dataset is currently loaded.")

    st.markdown("---")
    st.markdown("### Reset")
    if st.button("Reset all settings to defaults", use_container_width=True):
        reset_settings()
        st.success("Settings reset to defaults.")
        st.rerun()

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        f'<div class="info-card">'
        f'<h4>{APP_NAME} v{APP_VERSION}</h4>'
        f'<p>AI-Powered Business Intelligence &amp; Analytics Platform.<br>'
        f'Built with Streamlit, Pandas, Plotly and OpenPyXL. Runs locally — no API keys required.</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

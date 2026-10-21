"""InsightIQ — AI-Powered Business Intelligence & Analytics Platform.

Entry point for the Streamlit application.
Run:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src.config import APP_FULL_NAME, APP_NAME, PAGES, PAGE_ICONS
from src.state import get_page, go_to, init_state
from src.theme import inject_theme
from src.views import (
    analytics_dashboard,
    data_cleaning,
    data_quality,
    data_preview,
    overview,
    professional_reports,
    reports,
    settings,
    upload_dataset,
)

VIEW_MODULES = {
    "Overview": overview,
    "Upload Dataset": upload_dataset,
    "Data Preview": data_preview,
    "Data Quality": data_quality,
    "Data Cleaning Studio": data_cleaning,
    "Analytics Dashboard": analytics_dashboard,
    "Reports": reports,
    "Professional Reports": professional_reports,
    "Settings": settings,
}


def _render_sidebar() -> None:
    st.sidebar.markdown(
        f'<div style="padding:0.75rem 1rem 1rem;"><div style="font-size:1.5rem;display:flex;align-items:center;gap:0.5rem;">'
        f'<span style="font-size:1.75rem;">🧠</span><strong style="font-size:1.25rem;">{APP_NAME}</strong></div>'
        f'<p class="muted" style="font-size:0.8rem;margin-top:0.25rem;">v0.1.0</p></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("### Navigation")

    current_page = get_page()
    idx = PAGES.index(current_page) if current_page in PAGES else 0
    selected = st.sidebar.radio(
        "Go to",
        PAGES,
        index=idx,
        format_func=lambda name: f"{PAGE_ICONS.get(name, '📄')}  {name}",
        label_visibility="collapsed",
        key="nav_radio",
    )
    if selected != current_page:
        go_to(selected)
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Status")
    if st.session_state.get("df") is not None:
        df = st.session_state["df"]
        st.sidebar.success(f"Dataset loaded\n{df.shape[0]:,} rows × {df.shape[1]} columns")
    else:
        st.sidebar.info("No dataset loaded")

    st.sidebar.markdown("---")
    st.sidebar.caption("InsightIQ runs locally. No API keys or external services are used.")


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_state()
    inject_theme()
    _render_sidebar()

    page = get_page()
    view_module = VIEW_MODULES.get(page, overview)
    view_module.render()


if __name__ == "__main__":
    main()

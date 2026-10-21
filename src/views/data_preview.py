"""Data Preview page: show a sample of the loaded dataset."""

from __future__ import annotations

import streamlit as st

from src.state import get_dataset, get_setting, go_to, set_setting
from src.theme import inject_theme, metric_card, page_header
from src.utils import format_int


def render() -> None:
    inject_theme()

    page_header("Data Preview", "Inspect the first rows of your uploaded dataset.")

    df = get_dataset()
    if df is None:
        st.info("No dataset loaded. Upload a file from the **Upload Dataset** page.")
        if st.button("Go to Upload Dataset", use_container_width=True):
            go_to("Upload Dataset")
            st.rerun()
        return

    rows, cols = df.shape
    metric_card("Rows", format_int(rows))
    metric_card("Columns", cols)

    st.markdown("### Preview")
    max_rows = int(get_setting("preview_rows"))
    n_rows = st.slider(
        "Rows to display",
        min_value=5,
        max_value=min(500, rows),
        value=min(max_rows, rows),
        step=5,
        help="How many rows to show in the table below.",
    )
    set_setting("preview_rows", n_rows)

    st.dataframe(df.head(n_rows), use_container_width=True, hide_index=True)

    st.markdown("### Column types")
    dtype_counts = df.dtypes.astype(str).value_counts()
    c1, c2, c3 = st.columns(3)
    for i, (dtype, count) in enumerate(dtype_counts.items()):
        with [c1, c2, c3][i % 3]:
            metric_card(dtype, count)

    st.markdown("---")
    if st.button("Go to Data Quality", use_container_width=True):
        go_to("Data Quality")
        st.rerun()

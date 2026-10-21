"""Data Cleaning Studio page: preview and apply cleaning operations.

The original uploaded dataset is never modified; every operation works on the
current working dataset and records itself in the cleaning history.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.analysis import classify_columns, column_profile, dataset_summary
from src.cleaning import (
    CleaningError,
    DROP_RULE_ALL,
    DROP_RULE_ANY,
    fill_categorical_missing,
    fill_numeric_missing,
    remove_columns_missing,
    remove_rows_any_missing,
    remove_rows_by_rule,
    remove_duplicates,
    to_csv_bytes,
    to_excel_bytes,
)
from src.state import (
    add_cleaning_record,
    get_cleaning_history,
    get_dataset,
    get_original_dataset,
    set_working_dataset,
    reset_to_original,
)
from src.theme import inject_theme, metric_card, page_header
from src.utils import format_int, format_pct


def _show_effect(effect: dict, preview_rows: pd.DataFrame) -> None:
    """Display the estimated before/after impact and a preview of affected rows."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Rows affected", format_int(effect["affected_rows"]))
    with c2:
        metric_card("Columns affected", format_int(effect["affected_columns"]))
    with c3:
        metric_card(
            "Before",
            f'{effect["before_shape"][0]:,} × {effect["before_shape"][1]}',
        )
    with c4:
        metric_card(
            "After",
            f'{effect["after_shape"][0]:,} × {effect["after_shape"][1]}',
        )
    if effect.get("cells") is not None:
        st.caption(f"Individual cells changed: {format_int(effect['cells'])}.")
    st.markdown("**Preview of affected rows** (first 10):")
    st.dataframe(preview_rows, use_container_width=True, hide_index=True)


def _apply(effect: dict, new_df: pd.DataFrame, operation_label: str) -> None:
    """Persist a cleaning result, record history and refresh the page."""
    before = effect["before_shape"]
    after = effect["after_shape"]
    set_working_dataset(new_df, dataset_summary(new_df))
    add_cleaning_record(
        {
            "operation": effect["operation"],
            "affected_rows": effect["affected_rows"],
            "affected_columns": effect["affected_columns"],
            "affected_column_names": effect.get("affected_column_names", []),
            "before_shape": before,
            "after_shape": after,
            "timestamp": effect["timestamp"],
        }
    )
    st.success(
        f"{operation_label}: {before[0]:,} × {before[1]} → "
        f"{after[0]:,} × {after[1]} "
        f"({format_int(effect['affected_rows'])} row(s) affected)."
    )
    st.rerun()


def _attempt(compute, preview_button, apply_button, apply_label: str) -> None:
    """Shared preview-then-apply flow for one cleaning operation."""
    if not preview_button and not apply_button:
        return
    try:
        new_df, effect, preview_rows = compute()
    except CleaningError as exc:
        st.error(str(exc))
        return
    _show_effect(effect, preview_rows)
    if apply_button:
        _apply(effect, new_df, apply_label)


def render() -> None:
    inject_theme()
    page_header(
        "Data Cleaning Studio",
        "Preview and apply cleaning operations. Your original upload is never modified.",
    )

    df = get_dataset()
    if df is None:
        st.info("No dataset loaded. Upload a file from the **Upload Dataset** page.")
        if st.button("Go to Upload Dataset", use_container_width=True):
            from src.state import go_to

            go_to("Upload Dataset")
            st.rerun()
        return

    original = get_original_dataset()
    untouched = (
        original is not None
        and df.shape == original.shape
        and df.equals(original)
    )

    # ------------------------------------------------------------------ health
    st.markdown("### Current dataset")
    summary = dataset_summary(df)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Rows", format_int(summary["rows"]))
    with c2:
        metric_card("Columns", format_int(summary["columns"]))
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
    if untouched:
        st.info(
            "The working dataset is identical to the original upload — "
            "no cleaning has been applied yet."
        )
    else:
        st.success(
            "The working dataset has been cleaned. The original upload is "
            "preserved and can be restored at any time."
        )

    # ------------------------------------------------- missing-value table
    st.markdown("---")
    st.markdown("### Missing values by column")
    profile = column_profile(df)
    show = profile[
        ["Column", "Data Type", "Missing", "Missing %", "Unique", "Kind", "Non-Null"]
    ].copy()
    show["Missing %"] = show["Missing %"].map(lambda v: f"{v:.1f}%")
    st.dataframe(show, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ tabs
    tab_missing, tab_duplicates, tab_history, tab_download = st.tabs(
        ["Missing values", "Duplicates", "History & reset", "Download"]
    )

    with tab_missing:
        _render_missing_tab(df)
    with tab_duplicates:
        _render_duplicates_tab(df)
    with tab_history:
        _render_history_tab()
    with tab_download:
        _render_download_tab(df)


# ============================================================================
# Tab: missing values (part 1)
# ============================================================================
def _render_missing_tab(df) -> None:
    groups = classify_columns(df)
    numeric_cols = groups["numeric"]
    categorical_cols = groups["categorical"]
    missing_cols = [c for c in df.columns if df[c].isna().any()]

    st.markdown("#### 1. Remove rows with any missing values")
    st.caption(
        "Deletes every row that contains at least one empty cell, in any column. "
        "Use this when incomplete rows are not worth keeping."
    )
    if not missing_cols:
        st.success("No missing values found — nothing to remove.")
    else:
        c1, c2 = st.columns(2)
        do_preview = c1.button("Preview impact", key="cs_preview_any", use_container_width=True)
        do_apply = c2.button(
            "Apply — remove rows", key="cs_apply_any", type="primary", use_container_width=True
        )
        _attempt(
            lambda: remove_rows_any_missing(df),
            do_preview,
            do_apply,
            "Rows removed",
        )

    st.markdown("---")
    st.markdown("#### 2. Remove rows with missing values in selected columns")
    st.caption(
        "Pick one or more columns. A row is removed if any of the selected "
        "columns is missing in that row. Columns without missing values have no effect."
    )
    if not missing_cols:
        st.info("No column contains missing values — nothing to remove.")
    else:
        sel = st.multiselect(
            "Columns",
            missing_cols,
            default=missing_cols,
            key="cs_cols_selected",
        )
        c1, c2 = st.columns(2)
        do_preview = c1.button("Preview impact", key="cs_preview_selected", use_container_width=True)
        do_apply = c2.button(
            "Apply — remove rows",
            key="cs_apply_selected",
            type="primary",
            use_container_width=True,
        )
        if do_preview or do_apply:
            if not sel:
                st.warning("Select at least one column.")
            else:
                _attempt(
                    lambda: remove_rows_by_rule(df, sel, DROP_RULE_ANY),
                    do_preview,
                    do_apply,
                    "Rows removed",
                )

    st.markdown("---")
    st.markdown("#### 3. Remove columns with missing values")
    st.caption(
        "Deletes every column that contains at least one missing value. "
        "Use with care — this removes whole columns, not just the empty cells."
    )
    if not missing_cols:
        st.success("No column contains missing values — nothing to remove.")
    else:
        st.warning(
            f"{len(missing_cols)} column(s) contain missing values: "
            f"{', '.join(missing_cols)}"
        )
        c1, c2 = st.columns(2)
        do_preview = c1.button("Preview impact", key="cs_preview_cols", use_container_width=True)
        do_apply = c2.button(
            "Apply — remove columns",
            key="cs_apply_cols",
            type="primary",
            use_container_width=True,
        )
        _attempt(
            lambda: remove_columns_missing(df),
            do_preview,
            do_apply,
            "Columns removed",
        )

    st.markdown("---")
    st.markdown("#### 4. Fill missing numeric values")
    st.caption(
        "Replaces empty cells in numeric columns only. Mean/Median are skipped "
        "for a column that is entirely missing; Zero always replaces with 0. "
        "Text and date columns are never touched."
    )
    numeric_missing = [c for c in numeric_cols if df[c].isna().any()]
    if not numeric_cols:
        st.info("The dataset has no numeric columns.")
    elif not numeric_missing:
        st.success("No missing values in numeric columns.")
    else:
        sel_num = st.multiselect(
            "Numeric columns",
            numeric_missing,
            default=numeric_missing,
            key="cs_num_cols",
        )
        method_num = st.selectbox(
            "Fill with",
            ["Mean", "Median", "Zero"],
            key="cs_num_method",
        )
        c1, c2 = st.columns(2)
        do_preview = c1.button("Preview impact", key="cs_preview_num", use_container_width=True)
        do_apply = c2.button(
            "Apply — fill values",
            key="cs_apply_num",
            type="primary",
            use_container_width=True,
        )
        if do_preview or do_apply:
            if not sel_num:
                st.warning("Select at least one numeric column.")
            else:
                _attempt(
                    lambda: fill_numeric_missing(df, sel_num, method_num),
                    do_preview,
                    do_apply,
                    "Numeric values filled",
                )

    st.markdown("---")
    st.markdown("#### 5. Fill missing categorical values")
    st.caption(
        "Replaces empty cells in text/boolean columns only. Mode uses the most "
        "frequent value; Custom value lets you type your own replacement. "
        "Numeric and date columns are never touched."
    )
    categorical_missing = [c for c in categorical_cols if df[c].isna().any()]
    if not categorical_cols:
        st.info("The dataset has no categorical columns.")
    elif not categorical_missing:
        st.success("No missing values in categorical columns.")
    else:
        sel_cat = st.multiselect(
            "Categorical columns",
            categorical_missing,
            default=categorical_missing,
            key="cs_cat_cols",
        )
        method_cat = st.selectbox(
            "Fill with",
            ["Mode", "Custom value"],
            key="cs_cat_method",
        )
        custom_value = None
        if method_cat == "Custom value":
            custom_value = st.text_input(
                "Custom replacement value",
                key="cs_cat_custom",
                help="Typed exactly as it should appear in the filled cells.",
            )
        c1, c2 = st.columns(2)
        do_preview = c1.button("Preview impact", key="cs_preview_cat", use_container_width=True)
        do_apply = c2.button(
            "Apply — fill values",
            key="cs_apply_cat",
            type="primary",
            use_container_width=True,
        )
        if do_preview or do_apply:
            if not sel_cat:
                st.warning("Select at least one categorical column.")
            else:
                _attempt(
                    lambda: fill_categorical_missing(df, sel_cat, method_cat, custom_value),
                    do_preview,
                    do_apply,
                    "Categorical values filled",
                )

    st.markdown("---")
    st.markdown("#### 6. Drop rows by missing-value rule")
    st.caption(
        "Select columns and a rule. 'Any' removes a row when any selected "
        "column is missing; 'All' removes a row only when every selected "
        "column is missing in that same row."
    )
    if not missing_cols:
        st.info("No column contains missing values — nothing to remove.")
    else:
        sel_rule = st.multiselect(
            "Columns",
            missing_cols,
            default=missing_cols,
            key="cs_cols_rule",
        )
        rule_label = st.radio(
            "Missing-value rule",
            ["Any selected column is missing", "All selected columns are missing"],
            key="cs_rule",
            horizontal=True,
        )
        rule = DROP_RULE_ANY if rule_label.startswith("Any") else DROP_RULE_ALL
        c1, c2 = st.columns(2)
        do_preview = c1.button("Preview impact", key="cs_preview_rule", use_container_width=True)
        do_apply = c2.button(
            "Apply — remove rows",
            key="cs_apply_rule",
            type="primary",
            use_container_width=True,
        )
        if do_preview or do_apply:
            if not sel_rule:
                st.warning("Select at least one column.")
            else:
                _attempt(
                    lambda: remove_rows_by_rule(df, sel_rule, rule),
                    do_preview,
                    do_apply,
                    "Rows removed",
                )


# ============================================================================
# Tab: duplicates
# ============================================================================
def _render_duplicates_tab(df) -> None:
    st.markdown("### Duplicate rows")
    duplicate_rows = int(df.duplicated().sum())
    metric_card(
        "Exact duplicate rows",
        format_int(duplicate_rows),
        format_pct(duplicate_rows / df.shape[0] * 100) if df.shape[0] else "0.0%",
        "danger" if duplicate_rows else "success",
    )

    if duplicate_rows == 0:
        st.success("No duplicate rows were detected.")
    else:
        st.markdown("**Preview of duplicate rows** (first 10):")
        st.dataframe(
            df[df.duplicated(keep=False)].head(10),
            use_container_width=True,
            hide_index=True,
        )
        c1, c2 = st.columns(2)
        do_apply = c1.button(
            "Apply — remove duplicates",
            key="cs_apply_duplicates",
            type="primary",
            use_container_width=True,
        )
        if do_apply:
            try:
                new_df, effect, _preview_rows = remove_duplicates(df)
            except CleaningError as exc:
                st.error(str(exc))
            else:
                _apply(effect, new_df, "Duplicates removed")


# ============================================================================
# Tab: history & reset
# ============================================================================
def _render_history_tab() -> None:
    st.markdown("### Cleaning history")
    st.caption(
        "Every applied cleaning operation is recorded here with the number of "
        "affected rows and columns, plus a timestamp."
    )
    history = get_cleaning_history()
    if not history:
        st.info("No cleaning operations applied yet.")
    else:
        rows = []
        for rec in history:
            rows.append(
                {
                    "When": rec["timestamp"],
                    "Operation": rec["operation"],
                    "Rows affected": rec["affected_rows"],
                    "Columns affected": rec["affected_columns"],
                    "Before": f'{rec["before_shape"][0]:,} × {rec["before_shape"][1]}',
                    "After": f'{rec["after_shape"][0]:,} × {rec["after_shape"][1]}',
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Reset to original upload")
    st.caption(
        "Restores the working dataset to the exact file you uploaded, discarding "
        "all cleaning operations. This cannot be undone."
    )
    confirm = st.checkbox(
        "I confirm — restore the original uploaded dataset",
        key="cs_reset_confirm",
    )
    if st.button(
        "Reset working dataset",
        disabled=not confirm,
        type="primary",
        use_container_width=True,
    ):
        reset_to_original()
        st.success("Working dataset restored from the original upload.")
        st.rerun()


# ============================================================================
# Tab: download
# ============================================================================
def _render_download_tab(df) -> None:
    st.markdown("### Download cleaned dataset")
    st.caption(
        "The export contains the current working (cleaned) dataset, not the "
        "original upload."
    )
    c1, c2 = st.columns(2)
    csv_bytes = to_csv_bytes(df)
    with c1:
        st.download_button(
            "Download CSV",
            data=csv_bytes,
            file_name="insightiq_cleaned.csv",
            mime="text/csv",
            use_container_width=True,
        )
    xlsx_bytes = to_excel_bytes(df)
    with c2:
        st.download_button(
            "Download Excel (.xlsx)",
            data=xlsx_bytes,
            file_name="insightiq_cleaned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    st.info(
        f"This export contains {format_int(df.shape[0])} rows × "
        f"{format_int(df.shape[1])} columns."
    )

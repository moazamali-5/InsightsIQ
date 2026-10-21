"""Session-state helpers: current page, loaded dataset and user settings."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.config import PAGES

DEFAULT_SETTINGS = {
    "preview_rows": 50,       # default rows shown in Data Preview
    "max_categories": 15,     # top-N categories shown in bar charts
    "scatter_sample": 5000,   # max points drawn in scatter plots
}


def init_state() -> None:
    """Create all session-state keys the app relies on (runs on every rerun)."""
    st.session_state.setdefault("page", PAGES[0])
    st.session_state.setdefault("df", None)
    st.session_state.setdefault("df_original", None)
    st.session_state.setdefault("meta", {})
    st.session_state.setdefault("settings", dict(DEFAULT_SETTINGS))
    st.session_state.setdefault("report_files", None)
    st.session_state.setdefault("cleaning_history", [])


# ---- Navigation -----------------------------------------------------------
def get_page() -> str:
    page = st.session_state.get("page", PAGES[0])
    return page if page in PAGES else PAGES[0]


def go_to(page: str) -> None:
    """Callback used by navigation buttons."""
    st.session_state["page"] = page


# ---- Dataset --------------------------------------------------------------
def has_dataset() -> bool:
    df = st.session_state.get("df")
    return isinstance(df, pd.DataFrame) and not df.empty


def get_dataset() -> Optional[pd.DataFrame]:
    return st.session_state.get("df") if has_dataset() else None


def get_meta() -> dict:
    return st.session_state.get("meta") or {}


def set_dataset(df: pd.DataFrame, meta: dict) -> None:
    """Store a newly uploaded dataset: working copy, pristine original, fresh history."""
    st.session_state["df"] = df
    st.session_state["df_original"] = df.copy()
    st.session_state["meta"] = meta
    st.session_state["cleaning_history"] = []  # a new upload starts a fresh history
    st.session_state["report_files"] = None  # any earlier report is now stale


def set_working_dataset(df: pd.DataFrame, meta: dict) -> None:
    """Replace the working (cleaned) dataset without touching the original or history."""
    st.session_state["df"] = df
    st.session_state["meta"] = meta
    st.session_state["report_files"] = None


def clear_dataset() -> None:
    st.session_state["df"] = None
    st.session_state["df_original"] = None
    st.session_state["meta"] = {}
    st.session_state["cleaning_history"] = []
    st.session_state["report_files"] = None


# ---- Original dataset (pristine upload) & cleaning history ----------------
def get_original_dataset() -> Optional[pd.DataFrame]:
    """Return the untouched dataset as uploaded; never modified by cleaning."""
    return st.session_state.get("df_original")


def get_cleaning_history() -> list:
    return list(st.session_state.get("cleaning_history", []))


def add_cleaning_record(record: dict) -> None:
    st.session_state.setdefault("cleaning_history", []).append(record)


def clear_cleaning_history() -> None:
    st.session_state["cleaning_history"] = []


def reset_to_original() -> None:
    """Restore the working dataset from the original uploaded dataset."""
    from src.analysis import dataset_summary  # local import keeps import order simple

    original = st.session_state.get("df_original")
    if original is None:
        return
    st.session_state["df"] = original.copy()
    st.session_state["meta"] = dataset_summary(original)
    st.session_state["cleaning_history"] = []
    st.session_state["report_files"] = None


# ---- Settings -------------------------------------------------------------
def get_setting(key: str) -> Any:
    return st.session_state["settings"].get(key, DEFAULT_SETTINGS[key])


def set_setting(key: str, value: Any) -> None:
    st.session_state["settings"][key] = value


def reset_settings() -> None:
    st.session_state["settings"] = dict(DEFAULT_SETTINGS)

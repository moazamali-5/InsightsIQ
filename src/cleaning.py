"""Data-cleaning operations for the InsightIQ Data Cleaning Studio.

Every operation:
  * receives a DataFrame and returns a brand-new DataFrame (the input is never
    mutated in place),
  * returns an ``effect`` dict describing exactly what changed, and
  * returns a small ``preview_rows`` DataFrame so the UI can show which rows
    would be affected before anything is applied.

Operations that would destroy the dataset (e.g. remove every row, or every
column) raise :class:`CleaningError` so the view can show a friendly message
instead of silently producing an empty frame.
"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import pandas as pd
from pandas.api import types as ptypes

from src.analysis import classify_columns

FILL_NUMERIC_METHODS = ("Mean", "Median", "Zero")
FILL_CATEGORICAL_METHODS = ("Mode", "Custom value")
DROP_RULE_ANY = "any"
DROP_RULE_ALL = "all"


class CleaningError(Exception):
    """Raised when a cleaning operation cannot be performed safely."""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _effect(
    operation: str,
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    columns: Optional[List[str]] = None,
    rows: Optional[int] = None,
    cells: Optional[int] = None,
) -> Dict:
    return {
        "operation": operation,
        "timestamp": _now(),
        "affected_rows": int(rows)
        if rows is not None
        else int(df_before.shape[0] - df_after.shape[0]),
        "affected_columns": len(columns) if columns is not None else len(df_before.columns),
        "affected_column_names": list(columns) if columns is not None else [],
        "before_shape": df_before.shape,
        "after_shape": df_after.shape,
        "cells": int(cells) if cells is not None else None,
    }


# ---------------------------------------------------------------------------
# Row removal
# ---------------------------------------------------------------------------
def remove_rows_any_missing(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict, pd.DataFrame]:
    """Remove every row that contains at least one missing value."""
    if df.empty:
        raise CleaningError("The dataset is empty; nothing to clean.")
    mask = df.isna().any(axis=1)
    affected_rows = int(mask.sum())
    if affected_rows == 0:
        raise CleaningError("No rows contain missing values; nothing to remove.")
    cols_with_missing = [c for c in df.columns if df[c].isna().any()]
    new_df = df.loc[~mask].reset_index(drop=True)
    if new_df.empty:
        raise CleaningError(
            "This would remove every row because each row contains a missing value. "
            "Try filling missing values instead of removing rows."
        )
    effect = _effect(
        "Remove rows with any missing values",
        df,
        new_df,
        columns=cols_with_missing,
        rows=affected_rows,
    )
    return new_df, effect, df[mask].head(10)


def remove_rows_by_rule(
    df: pd.DataFrame, columns: List[str], rule: str
) -> Tuple[pd.DataFrame, Dict, pd.DataFrame]:
    """Drop rows based on missing values in selected columns.

    ``rule`` is ``"any"`` (drop if any selected column is missing) or
    ``"all"`` (drop only when every selected column is missing).
    """
    if df.empty:
        raise CleaningError("The dataset is empty; nothing to clean.")
    if not columns:
        raise CleaningError("Select at least one column.")
    unknown = [c for c in columns if c not in df.columns]
    if unknown:
        raise CleaningError(f"Unknown column(s): {', '.join(unknown)}")

    sub = df[columns]
    if rule == DROP_RULE_ANY:
        mask = sub.isna().any(axis=1)
        rule_label = "any selected column is missing"
    else:
        mask = sub.isna().all(axis=1)
        rule_label = "all selected columns are missing"

    affected_rows = int(mask.sum())
    if affected_rows == 0:
        raise CleaningError(
            f"No rows match the rule ({rule_label}); nothing to remove."
        )
    new_df = df.loc[~mask].reset_index(drop=True)
    if new_df.empty:
        raise CleaningError("This would remove every row; nothing would remain.")
    effect = _effect(
        f"Drop rows where {rule_label}",
        df,
        new_df,
        columns=columns,
        rows=affected_rows,
    )
    return new_df, effect, df[mask].head(10)


def remove_columns_missing(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict, pd.DataFrame]:
    """Remove every column that contains at least one missing value."""
    if df.empty:
        raise CleaningError("The dataset is empty; nothing to clean.")
    missing_mask = df.isna().any(axis=0)
    cols = [c for c, m in zip(df.columns, missing_mask) if m]
    if not cols:
        raise CleaningError("No columns contain missing values; nothing to remove.")
    if len(cols) == df.shape[1]:
        raise CleaningError(
            "Every column contains missing values — removing them would leave an empty dataset."
        )
    rows_touched = int(df[cols].isna().any(axis=1).sum())
    new_df = df.drop(columns=cols)
    effect = _effect(
        "Remove columns with missing values",
        df,
        new_df,
        columns=cols,
        rows=rows_touched,
    )
    return new_df, effect, df[df[cols].isna().any(axis=1)].head(10)


# ---------------------------------------------------------------------------
# Missing-value imputation
# ---------------------------------------------------------------------------
def fill_numeric_missing(
    df: pd.DataFrame, columns: List[str], method: str
) -> Tuple[pd.DataFrame, Dict, pd.DataFrame]:
    """Fill missing numeric values with mean, median or zero."""
    if df.empty:
        raise CleaningError("The dataset is empty; nothing to clean.")
    if not columns:
        raise CleaningError("Select at least one numeric column.")
    numeric = classify_columns(df)["numeric"]
    bad = [c for c in columns if c not in numeric]
    if bad:
        raise CleaningError(
            "Numeric fill cannot be applied to text/date columns: " + ", ".join(bad)
        )
    if method not in FILL_NUMERIC_METHODS:
        raise CleaningError(f"Unknown numeric fill method: {method}")

    new_df = df.copy()
    total_filled = 0
    filled_cols: List[str] = []
    any_mask = pd.Series(False, index=df.index)
    for c in columns:
        series = new_df[c]
        missing = int(series.isna().sum())
        if missing == 0:
            continue
        if method == "Mean":
            value = series.mean()
        elif method == "Median":
            value = series.median()
        else:  # Zero
            value = 0
        if isinstance(value, float) and pd.isna(value):
            # Entirely missing column: mean/median cannot be computed.
            continue
        new_df[c] = series.fillna(value)
        total_filled += missing
        filled_cols.append(c)
        any_mask = any_mask | series.isna()

    if total_filled == 0:
        raise CleaningError(
            "No missing values could be filled in the selected numeric columns "
            "(they may already be complete, or entirely missing)."
        )
    effect = _effect(
        f"Fill numeric missing values ({method})",
        df,
        new_df,
        columns=filled_cols,
        rows=int(any_mask.sum()),
        cells=total_filled,
    )
    return new_df, effect, df[any_mask].head(10)


def fill_categorical_missing(
    df: pd.DataFrame, columns: List[str], method: str, custom_value: Optional[str] = None
) -> Tuple[pd.DataFrame, Dict, pd.DataFrame]:
    """Fill missing categorical values with the mode or a custom value."""
    if df.empty:
        raise CleaningError("The dataset is empty; nothing to clean.")
    if not columns:
        raise CleaningError("Select at least one categorical column.")
    categorical = classify_columns(df)["categorical"]
    bad = [c for c in columns if c not in categorical]
    if bad:
        raise CleaningError(
            "Categorical fill cannot be applied to numeric/date columns: " + ", ".join(bad)
        )
    if method not in FILL_CATEGORICAL_METHODS:
        raise CleaningError(f"Unknown categorical fill method: {method}")
    if method == "Custom value" and (custom_value is None or str(custom_value) == ""):
        raise CleaningError("Please enter a custom value to fill missing cells with.")

    new_df = df.copy()
    total_filled = 0
    filled_cols: List[str] = []
    any_mask = pd.Series(False, index=df.index)
    for c in columns:
        series = new_df[c]
        missing = int(series.isna().sum())
        if missing == 0:
            continue
        if method == "Mode":
            modes = series.mode(dropna=True)
            if modes.empty:
                # Entirely missing column: there is no mode to fall back on.
                continue
            value = modes.iloc[0]
        else:
            value = custom_value
        new_df[c] = series.fillna(value)
        total_filled += missing
        filled_cols.append(c)
        any_mask = any_mask | series.isna()

    if total_filled == 0:
        raise CleaningError(
            "No missing values could be filled in the selected categorical columns "
            "(they may already be complete, or entirely missing with no mode)."
        )
    effect = _effect(
        f"Fill categorical missing values ({method})",
        df,
        new_df,
        columns=filled_cols,
        rows=int(any_mask.sum()),
        cells=total_filled,
    )
    return new_df, effect, df[any_mask].head(10)


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------
def remove_duplicates(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict, pd.DataFrame]:
    """Remove exact duplicate rows, keeping the first occurrence."""
    if df.empty:
        raise CleaningError("The dataset is empty; nothing to clean.")
    mask = df.duplicated(keep="first")
    affected_rows = int(mask.sum())
    if affected_rows == 0:
        raise CleaningError("No duplicate rows found; nothing to remove.")
    new_df = df.loc[~mask].reset_index(drop=True)
    effect = _effect(
        "Remove duplicate rows",
        df,
        new_df,
        columns=list(df.columns),
        rows=affected_rows,
    )
    return new_df, effect, df[mask].head(10)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Cleaned data")
    return buffer.getvalue()


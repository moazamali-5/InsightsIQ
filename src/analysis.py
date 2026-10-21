"""Dataset profiling: every number here is computed directly from the data."""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd
from pandas.api import types as ptypes

MAX_CHART_CATEGORIES = 50   # categorical columns with more distinct values are not charted
STRONG_CORRELATION = 0.7


def classify_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Group columns into numeric, datetime and categorical (text / boolean)."""
    groups: Dict[str, List[str]] = {"numeric": [], "datetime": [], "categorical": []}
    for column in df.columns:
        series = df[column]
        if ptypes.is_bool_dtype(series):
            groups["categorical"].append(column)
        elif ptypes.is_numeric_dtype(series):
            groups["numeric"].append(column)
        elif ptypes.is_datetime64_any_dtype(series):
            groups["datetime"].append(column)
        else:
            groups["categorical"].append(column)
    return groups


def chart_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Columns suitable for charts (has data; categoricals are low-cardinality)."""
    groups = classify_columns(df)
    return {
        "numeric": [c for c in groups["numeric"] if df[c].notna().any()],
        "datetime": [c for c in groups["datetime"] if df[c].notna().any()],
        "categorical": [
            c for c in groups["categorical"] if 1 <= df[c].nunique(dropna=True) <= MAX_CHART_CATEGORIES
        ],
    }


def dataset_summary(df: pd.DataFrame) -> Dict[str, float]:
    """High-level metrics describing the dataset (rows, columns, missing, etc.)."""
    rows, cols = df.shape
    total_cells = rows * cols
    missing = int(df.isna().sum().sum())
    duplicates = int(df.duplicated().sum())
    groups = classify_columns(df)
    return {
        "rows": rows,
        "columns": cols,
        "total_cells": total_cells,
        "missing_cells": missing,
        "missing_pct": (missing / total_cells * 100) if total_cells else 0.0,
        "duplicate_rows": duplicates,
        "duplicate_pct": (duplicates / rows * 100) if rows else 0.0,
        "complete_rows": int(df.dropna().shape[0]),
        "numeric_count": len(groups["numeric"]),
        "categorical_count": len(groups["categorical"]),
        "datetime_count": len(groups["datetime"]),
        "memory_bytes": int(df.memory_usage(deep=True).sum()),
    }


def quality_score(summary: Dict[str, float]) -> float:
    """Simple heuristic: 100 minus % missing cells minus % duplicate rows (0-100)."""
    return max(0.0, min(100.0, 100.0 - summary["missing_pct"] - summary["duplicate_pct"]))


def quality_label(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Needs attention"



def column_profile(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: kind, data type, missing values and distinct values."""
    groups = classify_columns(df)
    kinds = {c: k for k, cols in groups.items() for c in cols}
    rows = len(df)
    records = []
    for column in df.columns:
        missing = int(df[column].isna().sum())
        records.append(
            {
                "Column": column,
                "Kind": kinds[column].capitalize(),
                "Data Type": str(df[column].dtype),
                "Non-Null": rows - missing,
                "Missing": missing,
                "Missing %": round(missing / rows * 100, 2) if rows else 0.0,
                "Unique": int(df[column].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(records)


def numeric_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """describe() for numeric columns, one row per column (empty if none)."""
    numeric = classify_columns(df)["numeric"]
    if not numeric:
        return pd.DataFrame()
    stats = df[numeric].describe().T.reset_index().rename(columns={"index": "Column"})
    return stats.rename(columns={"count": "Count", "mean": "Mean", "std": "Std Dev",
                                 "min": "Min", "25%": "25%", "50%": "Median",
                                 "75%": "75%", "max": "Max"})



def strong_correlations(df: pd.DataFrame, threshold: float = STRONG_CORRELATION) -> List[Tuple[str, str, float]]:
    """Return (col_a, col_b, r) for numeric pairs with |r| >= threshold, strongest first."""
    numeric = chart_columns(df)["numeric"]
    if len(numeric) < 2:
        return []
    corr = df[numeric].corr()
    pairs: List[Tuple[str, str, float]] = []
    for i, a in enumerate(numeric):
        for b in numeric[i + 1:]:
            value = corr.loc[a, b]
            if pd.notna(value) and abs(value) >= threshold:
                pairs.append((a, b, float(value)))
    return sorted(pairs, key=lambda p: abs(p[2]), reverse=True)


def quality_issues(df: pd.DataFrame) -> List[Dict[str, str]]:
    """List concrete data-quality problems found in the dataset."""
    issues: List[Dict[str, str]] = []
    summary = dataset_summary(df)
    profile = column_profile(df)

    for _, row in profile.iterrows():
        missing_pct = row["Missing %"]
        if missing_pct > 50:
            issues.append({"level": "high", "message": f"'{row['Column']}' is missing {missing_pct:.1f}% of its values."})
        elif missing_pct > 20:
            issues.append({"level": "medium", "message": f"'{row['Column']}' is missing {missing_pct:.1f}% of its values."})
        unique = row["Unique"]
        if unique <= 1 and row["Non-Null"] > 0 and (rows := len(df)) > 1:
            issues.append({"level": "low", "message": f"'{row['Column']}' has a single constant value and adds no information."})

    if summary["duplicate_rows"]:
        issues.append({"level": "medium", "message": f"{summary['duplicate_rows']:,} duplicate rows ({summary['duplicate_pct']:.1f}% of the data)."})
    return issues


def generate_findings(df: pd.DataFrame) -> List[str]:
    """Plain-language facts about the dataset, derived from the data itself."""
    s = dataset_summary(df)
    findings = [
        f"The dataset has {s['rows']:,} rows and {s['columns']} columns "
        f"({s['numeric_count']} numeric, {s['categorical_count']} categorical, {s['datetime_count']} date/time)."
    ]
    if s["missing_cells"] == 0:
        findings.append("No missing values were found.")
    else:
        profile = column_profile(df)
        worst = profile.sort_values("Missing", ascending=False).iloc[0]
        findings.append(
            f"{s['missing_cells']:,} cells ({s['missing_pct']:.1f}%) are missing. "
            f"'{worst['Column']}' has the most gaps ({int(worst['Missing']):,} values, {worst['Missing %']:.1f}%)."
        )
    if s["duplicate_rows"]:
        findings.append(f"{s['duplicate_rows']:,} duplicate rows were detected.")
    else:
        findings.append("No duplicate rows were detected.")
    for a, b, r in strong_correlations(df)[:3]:
        direction = "positive" if r > 0 else "negative"
        findings.append(f"'{a}' and '{b}' show a strong {direction} correlation (r = {r:.2f}).")
    return findings


# ---------------------------------------------------------------------------
# EDA / statistical helpers (added for the Analytics Dashboard upgrade)
# ---------------------------------------------------------------------------
def outlier_analysis(df: pd.DataFrame, column: str) -> Dict:
    """Detect potential outliers in a numeric column using the IQR method.

    Returns a dict with quartiles, IQR, bounds, outlier values/indices, count and %.
    Outliers are flagged as potential anomalies, not automatically incorrect values.
    """
    result: Dict = {
        "column": column,
        "q1": None,
        "q3": None,
        "iqr": None,
        "lower_bound": None,
        "upper_bound": None,
        "outlier_values": [],
        "outlier_indices": [],
        "count": 0,
        "pct": 0.0,
    }
    series = df[column].dropna()
    if series.empty:
        return result
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    mask = (series < lower) | (series > upper)
    outliers = series[mask]
    result.update(
        {
            "q1": q1,
            "q3": q3,
            "iqr": float(iqr),
            "lower_bound": float(lower),
            "upper_bound": float(upper),
            "outlier_values": outliers.tolist(),
            "outlier_indices": outliers.index.tolist(),
            "count": int(outliers.count()),
            "pct": float(outliers.count() / len(series) * 100) if len(series) else 0.0,
        }
    )
    return result


def all_outlier_analysis(df: pd.DataFrame) -> Dict[str, Dict]:
    """Run IQR outlier analysis on every numeric column with at least 2 non-null values."""
    numeric = [c for c in classify_columns(df)["numeric"] if df[c].notna().sum() >= 2]
    return {c: outlier_analysis(df, c) for c in numeric}


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation matrix for numeric columns with at least 2 non-null values."""
    numeric = [c for c in classify_columns(df)["numeric"] if df[c].notna().sum() >= 2]
    if len(numeric) < 2:
        return pd.DataFrame()
    return df[numeric].corr()


def top_categories(
    df: pd.DataFrame,
    cat_col: str,
    value_col: Optional[str] = None,
    agg: str = "count",
    top_n: int = 10,
) -> pd.DataFrame:
    """Top categories by count, sum, mean, min or max of an optional numeric column."""
    if value_col and value_col in df.columns:
        if agg == "count":
            result = df.groupby(cat_col).size().reset_index(name="value")
        elif agg == "sum":
            result = df.groupby(cat_col)[value_col].sum().reset_index(name="value")
        elif agg == "mean":
            result = df.groupby(cat_col)[value_col].mean().reset_index(name="value")
        elif agg == "min":
            result = df.groupby(cat_col)[value_col].min().reset_index(name="value")
        elif agg == "max":
            result = df.groupby(cat_col)[value_col].max().reset_index(name="value")
        else:
            result = df.groupby(cat_col)[value_col].sum().reset_index(name="value")
    else:
        result = df[cat_col].value_counts(dropna=False).reset_index()
        result.columns = [cat_col, "value"]
    return result.sort_values("value", ascending=False).head(top_n)


def missingness_insights(df: pd.DataFrame, threshold: float = 5.0) -> List[Dict]:
    """Columns whose missing percentage is at or above ``threshold`` percent."""
    insights: List[Dict] = []
    rows = len(df)
    if rows == 0:
        return insights
    for col in df.columns:
        missing = int(df[col].isna().sum())
        if missing == 0:
            continue
        pct = missing / rows * 100
        if pct >= threshold:
            insights.append(
                {"column": col, "missing": missing, "pct": float(pct)}
            )
    return sorted(insights, key=lambda x: x["pct"], reverse=True)


_FREQ_ALIASES = {"D": "D", "W": "W", "M": "ME", "Q": "QE", "Y": "YE"}


def time_series_agg(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: str = "M",
    agg: str = "sum",
) -> pd.DataFrame:
    """Aggregate a numeric column by a time frequency (D, W, M, Q, Y)."""
    pandas_freq = _FREQ_ALIASES.get(freq, freq)
    plot_df = df[[date_col, value_col]].dropna().sort_values(date_col)
    if plot_df.empty:
        return pd.DataFrame()
    plot_df = plot_df.set_index(date_col)
    agg_func = {"sum": "sum", "mean": "mean", "count": "count", "min": "min", "max": "max"}.get(
        agg, "sum"
    )
    result = getattr(plot_df[value_col].resample(pandas_freq), agg_func)()
    return result.reset_index()


"""Central configuration: app identity, navigation and colour palette."""

APP_NAME = "InsightIQ"
APP_FULL_NAME = "InsightIQ — AI-Powered Business Intelligence & Analytics Platform"
APP_TAGLINE = "Turn raw spreadsheets into clear business insight."
APP_VERSION = "0.1.0"

# File types accepted by the uploader (without the leading dot).
SUPPORTED_EXTENSIONS = ["csv", "xlsx"]

# (page name, icon) in sidebar order. The page name is also the navigation key.
NAV_ITEMS = [
    ("Overview", "🏠"),
    ("Upload Dataset", "📤"),
    ("Data Preview", "🔍"),
    ("Data Quality", "🛡️"),
    ("Data Cleaning Studio", "🧹"),
    ("Analytics Dashboard", "📊"),
    ("Reports", "📑"),
    ("Professional Reports", "📄"),
    ("Settings", "⚙️"),
]
PAGES = [name for name, _ in NAV_ITEMS]
PAGE_ICONS = dict(NAV_ITEMS)

# Colour palette (dark navy + blue theme).
COLORS = {
    "navy_900": "#0A1128",
    "navy_800": "#0F1A3A",
    "navy_700": "#16254F",
    "blue_500": "#3B82F6",
    "blue_400": "#60A5FA",
    "cyan": "#22D3EE",
    "text": "#E6EDF7",
    "muted": "#94A3B8",
    "grid": "rgba(148, 163, 184, 0.15)",
    "success": "#34D399",
    "warning": "#FBBF24",
    "danger": "#F87171",
}

# Colour sequence used by Plotly charts.
CHART_COLORWAY = [
    "#3B82F6",
    "#22D3EE",
    "#818CF8",
    "#34D399",
    "#FBBF24",
    "#F472B6",
    "#60A5FA",
    "#A78BFA",
]

# Default settings (mirrors src.state.DEFAULT_SETTINGS so config can provide
# get_setting/set_setting without creating a circular import).
DEFAULT_SETTINGS = {
    "preview_rows": 50,
    "max_categories": 15,
    "scatter_sample": 5000,
}


def get_setting(key: str):
    """Return a setting value from Streamlit session state, falling back to defaults."""
    import streamlit as st

    return st.session_state.get("settings", dict(DEFAULT_SETTINGS)).get(
        key, DEFAULT_SETTINGS[key]
    )


def set_setting(key: str, value) -> None:
    """Store a setting value in Streamlit session state."""
    import streamlit as st

    if "settings" not in st.session_state:
        st.session_state["settings"] = dict(DEFAULT_SETTINGS)
    st.session_state["settings"][key] = value

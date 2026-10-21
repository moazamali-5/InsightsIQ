"""Shared UI theme: custom CSS and reusable card/metric components."""

from __future__ import annotations

import streamlit as st

from src.config import APP_NAME, APP_FULL_NAME, APP_TAGLINE, COLORS, PAGE_ICONS

C = COLORS  # shorthand

INJECT_CSS = f"""
<style>
:root {{
  --navy-900: {C['navy_900']};
  --navy-800: {C['navy_800']};
  --navy-700: {C['navy_700']};
  --blue-500: {C['blue_500']};
  --blue-400: {C['blue_400']};
  --cyan: {C['cyan']};
  --text: {C['text']};
  --muted: {C['muted']};
  --grid: {C['grid']};
  --success: {C['success']};
  --warning: {C['warning']};
  --danger: {C['danger']};
}}

html, body, [class*="stApp"] {{
  background: var(--navy-900) !important;
  color: var(--text) !important;
}}

/* Hide Streamlit default chrome for a cleaner look. */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}
.stDeployButton {{visibility: hidden;}}
.stAppToolbar {{visibility: hidden;}}

h1, h2, h3, h4, h5, h6 {{
  color: var(--text) !important;
  letter-spacing: -0.02em;
}}
h1 {{ font-size: 2.25rem; line-height: 1.2; }}
h2 {{ font-size: 1.5rem; margin-top: 1.25rem; }}
h3 {{ font-size: 1.25rem; color: var(--blue-400); }}

p, li, label, .stMarkdown, .stText {{ color: var(--text) !important; }}
.small, .muted, .stCaption {{ color: var(--muted) !important; font-size: 0.875rem; }}

a {{ color: var(--blue-400); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* Primary buttons */
.stButton > button {{
  background: var(--blue-500) !important;
  color: white !important;
  border: none !important;
  border-radius: 8px !important;
  padding: 0.5rem 1rem !important;
  font-weight: 600 !important;
  width: 100% !important;
}}
.stButton > button:hover {{ background: var(--blue-400) !important; }}

/* Sidebar */
[data-testid="stSidebar"] {{
  background: var(--navy-800) !important;
  border-right: 1px solid var(--grid) !important;
}}
[data-testid="stSidebar"] .stRadio > div {{
  background: transparent !important;
}}
[data-testid="stSidebar"] label {{ color: var(--text) !important; }}
[data-testid="stSidebar"] [aria-checked="true"] {{
  background: var(--blue-500) !important;
  color: white !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}}

/* Cards */
.metric-card {{
  background: var(--navy-800);
  border: 1px solid var(--grid);
  border-radius: 12px;
  padding: 1.1rem 1rem;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}}
.metric-card .label {{ color: var(--muted); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
.metric-card .value {{ color: var(--text); font-size: 1.75rem; font-weight: 700; line-height: 1.2; }}
.metric-card .delta {{ font-size: 0.8rem; }}

.info-card {{
  background: var(--navy-800);
  border: 1px solid var(--grid);
  border-radius: 12px;
  padding: 1.25rem 1.25rem;
  margin-bottom: 1rem;
}}
.info-card h4 {{ margin-top: 0; color: var(--blue-400); font-size: 1.1rem; }}
.info-card p {{ margin: 0.5rem 0 0; color: var(--text); font-size: 0.95rem; line-height: 1.5; }}

.section-header {{
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 1.5rem 0 0.75rem;
}}
.section-badge {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: var(--navy-700);
  color: var(--blue-400);
  border-radius: 8px;
  font-size: 0.9rem;
}}

ul.tight {{ margin: 0.25rem 0 0; padding-left: 1.25rem; }}
ul.tight li {{ margin-bottom: 0.35rem; color: var(--text); }}
ul.tight li strong {{ color: var(--blue-400); }}

.stDataFrame {{ border: 1px solid var(--grid) !important; border-radius: 8px !important; }}
.stDataFrame [data-testid="stTable"] {{ border-radius: 8px !important; }}

.download-btn {{ margin-top: 0.5rem; }}
</style>
"""


def inject_theme() -> None:
    st.markdown(INJECT_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(
        f'<div class="section-header"><span class="section-badge">{PAGE_ICONS.get(title, "📄")}</span>'
        f'<h2 style="margin:0;">{title}</h2></div>',
        unsafe_allow_html=True,
    )
    if subtitle:
        st.markdown(f'<p class="muted">{subtitle}</p>', unsafe_allow_html=True)


def metric_card(label: str, value, delta: str | None = None, delta_color: str = "muted") -> None:
    delta_html = ""
    if delta:
        color = {"success": "var(--success)", "warning": "var(--warning)", "danger": "var(--danger)"}.get(
            delta_color, "var(--muted)"
        )
        delta_html = f'<div class="delta" style="color:{color}">{delta}</div>'
    st.markdown(
        f'<div class="metric-card">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        f'{delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def info_card(title: str, body: str) -> None:
    st.markdown(
        f'<div class="info-card"><h4>{title}</h4><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def app_header() -> None:
    st.markdown(
        f'<h1 style="margin:0; display:flex; align-items:center; gap:0.6rem;">'
        f'<span style="font-size:2rem;">🧠</span>{APP_NAME}</h1>'
        f'<p class="muted" style="margin-top:0.25rem;">{APP_TAGLINE}</p>',
        unsafe_allow_html=True,
    )

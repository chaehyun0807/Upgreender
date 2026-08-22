"""Shared design system (colors, cards, pills, chips) matching the
teammate's Upgreender mockup (upgreender_design.html). Every page calls
inject_theme() once near the top, then uses the helper functions below
instead of repeating inline styles."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root{
  --teal:#0F766E; --teal-dark:#0B5D57; --teal-tint:#E7F4F2; --teal-pale:#F3FAF9;
  --ink:#101312; --ink-soft:#3F4644; --muted:#6B726F; --faint:#9AA0A0;
  --border:#E7E7E4; --border-soft:#EFEFEC; --surface:#FFFFFF; --canvas:#FAFAF8;
  --amber:#B45309; --amber-tint:#FDF3E7; --red:#B3261E; --red-tint:#FBEAE9;
  --radius-lg:18px; --radius-md:12px; --radius-sm:8px;
  --shadow-sm: 0 1px 2px rgba(16,19,18,.04), 0 1px 1px rgba(16,19,18,.03);
}
html, body, [class*="css"] { font-family:'Pretendard','Manrope',-apple-system,sans-serif; }

.ug-card{
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg);
  box-shadow:var(--shadow-sm); padding:18px; margin-bottom:14px;
}
.ug-section-title{ font-size:14.5px; font-weight:800; letter-spacing:-.01em; margin:0 0 10px; color:var(--ink); }
.ug-eyebrow{ font-size:12px; font-weight:700; color:var(--teal); letter-spacing:.04em; text-transform:uppercase; margin:0 0 6px; }

.ug-pill{
  display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:700;
  padding:4px 9px; border-radius:20px; white-space:nowrap;
}
.ug-pill-good{ background:var(--teal-tint); color:var(--teal-dark); }
.ug-pill-warn{ background:var(--amber-tint); color:var(--amber); }
.ug-pill-bad{ background:var(--red-tint); color:var(--red); }
.ug-pill-neutral{ background:var(--canvas); color:var(--ink-soft); border:1px solid var(--border); }

.ug-chip{
  border:1px solid var(--border); background:var(--surface); color:var(--ink-soft);
  font-size:12.5px; font-weight:600; padding:6px 12px; border-radius:20px;
  display:inline-flex; align-items:center; gap:6px; margin:2px 6px 2px 0;
}
.ug-chip-active{ background:var(--teal); border-color:var(--teal); color:#fff; }

.ug-stat-line{
  display:flex; align-items:center; justify-content:space-between; padding:9px 0;
  font-size:13px; border-top:1px solid var(--border-soft);
}
.ug-stat-line .lbl{ color:var(--ink-soft); font-weight:600; }
.ug-stat-line .val{ font-weight:700; }
.ug-val-warn{ color:var(--red); }
.ug-val-good{ color:var(--teal-dark); }

.ug-row{ display:flex; align-items:center; gap:14px; }
.ug-icon-badge{
  flex:0 0 auto; width:40px; height:40px; border-radius:10px; display:flex;
  align-items:center; justify-content:center; font-size:16px;
}
.ug-title{ font-size:13.5px; font-weight:700; margin:0 0 2px; color:var(--ink); }
.ug-sub{ font-size:12px; color:var(--muted); margin:0; }

/* ── 기본 Streamlit 위젯을 목업 톤에 맞춤 (기능은 그대로, 색/모양만 조정) ── */
h1, h2, h3 { color:var(--ink) !important; letter-spacing:-.01em; }
p, li, .stMarkdown, .stCaption { color:var(--ink-soft); }

.stButton > button, .stFormSubmitButton > button {
  border-radius:10px; border:1px solid var(--border); font-weight:600;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background:var(--teal); border-color:var(--teal);
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
  background:var(--teal-dark); border-color:var(--teal-dark);
}

div[data-testid="stAlertContentInfo"], .stAlert:has(div[data-testid="stAlertContentInfo"]) {
  background:var(--teal-pale);
}
div[data-testid="stAlertContentSuccess"] { background:var(--teal-tint); }
div[data-testid="stAlertContentWarning"] { background:var(--amber-tint); }
div[data-testid="stAlertContentError"] { background:var(--red-tint); }

div[data-testid="stExpander"] {
  border:1px solid var(--border); border-radius:var(--radius-md); box-shadow:none;
}
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
  border:1px solid var(--border); border-radius:var(--radius-md); overflow:hidden;
}
div[data-testid="stMetric"] {
  background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-md); padding:10px 14px;
}
section[data-testid="stSidebar"] { background:var(--canvas); border-right:1px solid var(--border); }

/* ── 사이드바 내비게이션: 목업처럼 라운드 필 + 활성 항목 강조 ── */
div[data-testid="stSidebarNav"] { padding:8px 8px 4px; }
div[data-testid="stSidebarNavItems"] { gap:2px; }
div[data-testid="stSidebarNavLinkContainer"] { padding:0; }
a[data-testid="stSidebarNavLink"] {
  border-radius:10px; padding:9px 12px; gap:10px;
  font-size:14px; font-weight:600; color:var(--ink-soft) !important;
}
a[data-testid="stSidebarNavLink"] span { color:inherit !important; }
a[data-testid="stSidebarNavLink"]:hover { background:var(--border-soft); }
a[data-testid="stSidebarNavLink"][aria-current="page"] {
  background:var(--teal-tint); color:var(--teal-dark) !important;
}
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def pill(text: str, kind: str = "neutral") -> str:
    return f'<span class="ug-pill ug-pill-{kind}">{text}</span>'


def card_open(extra_style: str = "") -> str:
    return f'<div class="ug-card" style="{extra_style}">'


CARD_CLOSE = "</div>"


def chip(text: str, active: bool = False) -> str:
    cls = "ug-chip ug-chip-active" if active else "ug-chip"
    return f'<span class="{cls}">{text}</span>'

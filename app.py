import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from parser import parse_pdf
from analyzer import calculate_metrics, calculate_health_score, compare_months
from agent import run_analysis, chat_with_artha, get_client
from exporter import export_to_pdf, export_to_text

load_dotenv()

st.set_page_config(
    page_title="Artha — Personal Finance Agent",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SESSION_FILE = Path(__file__).parent / "session_history.json"

# ── Color palette ──────────────────────────────────────────────────────────────

LIGHT = {
    "bg": "#F4F6FA",
    "card": "#FFFFFF",
    "accent": "#1B2A4A",
    "text": "#1B2A4A",
    "secondary": "#3A4D6B",
    "good": "#1A7F4B",
    "bad": "#A32D2D",
    "border": "#E0E0E0",
    "input_bg": "#F4F6FA",
    "chat_bg": "#FFFFFF",
}

DARK = {
    "bg": "#12172B",
    "card": "#1E2540",
    "accent": "#4A7ABB",
    "text": "#E8EAF0",
    "secondary": "#9BA3B5",
    "good": "#2ECC71",
    "bad": "#E74C3C",
    "border": "#2E3650",
    "input_bg": "#1A2035",
    "chat_bg": "#1E2540",
}


def C():
    return DARK if st.session_state.get("dark_mode") else LIGHT


def inject_css():
    c = C()
    st.markdown(
        f"""
<style>
/* ── Page background with dot pattern ── */
.stApp {{
    background-color: {c['bg']} !important;
    background-image: radial-gradient(circle, rgba(27,42,74,0.12) 1px, transparent 1px) !important;
    background-size: 22px 22px !important;
}}
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section[data-testid="stMain"],
section[data-testid="stMain"] > div,
.block-container,
[data-testid="stMainBlockContainer"],
.appview-container,
.main {{
    background-color: transparent !important;
    background-image: none !important;
}}
[data-testid="stSidebar"] {{
    background-color: {c['card']} !important;
}}
/* ── Global text — catch everything Streamlit renders ── */
html, body {{
    color: {c['text']} !important;
}}
p, span, div, label,
.stMarkdown, .stMarkdown p,
[data-testid="stText"],
[data-testid="stCaption"],
[data-baseweb="caption"],
small, .caption,
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] span,
[class*="st-emotion-cache"] {{
    color: {c['text']} !important;
}}
h1, h2, h3, h4, h5, h6 {{
    color: {c['accent']} !important;
    font-size: revert !important;
}}
/* ── Buttons ── */
.stButton > button {{
    background-color: {c['accent']} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.45rem 1.1rem !important;
    transition: opacity 0.2s;
}}
.stButton > button:hover {{
    opacity: 0.85 !important;
    border: none !important;
}}
/* ── Outline button variant (class applied via container) ── */
.outline-btn .stButton > button {{
    background-color: transparent !important;
    color: {c['accent']} !important;
    border: 2px solid {c['accent']} !important;
}}
.outline-btn .stButton > button:hover {{
    background-color: {c['accent']} !important;
    color: #FFFFFF !important;
    opacity: 1 !important;
}}
/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput input,
.stSelectbox > div > div {{
    background-color: {c['input_bg']} !important;
    border: 1px solid {c['border']} !important;
    border-radius: 6px !important;
    color: {c['text']} !important;
}}
/* ── File uploader ── */
[data-testid="stFileUploader"] {{
    background-color: {c['card']} !important;
    border: 2px dashed {c['accent']} !important;
    border-radius: 10px !important;
    padding: 8px !important;
}}
[data-testid="stFileUploader"] *,
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] p {{
    color: {c['text']} !important;
    font-size: 14px !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"] * {{
    color: {c['text']} !important;
}}
/* ── Metrics ── */
[data-testid="metric-container"] {{
    background-color: {c['card']} !important;
    border: 1px solid {c['border']} !important;
    border-top: 3px solid {c['accent']} !important;
    border-radius: 10px !important;
    padding: 16px !important;
    box-shadow: 0 6px 24px rgba(27,42,74,0.12) !important;
}}
/* ── Chat input ── */
.stChatInput, [data-testid="stChatInput"] textarea {{
    background-color: {c['input_bg']} !important;
    border: 1px solid {c['border']} !important;
    color: {c['text']} !important;
}}
/* ── Multiselect ── */
.stMultiSelect > div {{
    background-color: {c['input_bg']} !important;
    border: 1px solid {c['border']} !important;
}}
/* ── Checkbox ── */
.stCheckbox label {{
    color: {c['secondary']} !important;
}}
/* ── Progress bar ── */
.stProgress > div > div {{
    border-radius: 999px !important;
}}
/* ── Expander ── */
[data-testid="stExpander"] {{
    background-color: {c['card']} !important;
    border: 1px solid {c['border']} !important;
    border-top: 3px solid {c['accent']} !important;
    border-radius: 8px !important;
    box-shadow: 0 6px 24px rgba(27,42,74,0.12) !important;
}}
/* ── Header branding (beats global div/span color reset) ── */
.artha-header-row {{
    position: relative;
    width: 100%;
    box-sizing: border-box;
    padding: clamp(20px, 3vw, 36px) clamp(12px, 3.5vw, 40px) clamp(22px, 3.2vw, 40px);
}}
.artha-brand-cluster {{
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    gap: clamp(16px, 3.5vw, 36px);
    flex-wrap: nowrap;
    width: 100%;
    max-width: 100%;
}}
.artha-logo-square {{
    width: clamp(56px, 11vw, 76px);
    height: clamp(56px, 11vw, 76px);
    background: #1B2A4A !important;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    align-self: flex-start;
    margin-top: clamp(2px, 0.6vw, 8px);
    box-shadow:
        0 2px 8px rgba(27, 42, 74, 0.18),
        0 0 0 1px rgba(255, 255, 255, 0.06) inset;
}}
.artha-logo-letter {{
    font-size: clamp(28px, 6.5vw, 40px);
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.03em;
    color: #FFFFFF !important;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.artha-brand-text {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    flex: 1;
    min-width: 0;
    gap: clamp(6px, 1.2vw, 12px);
}}
h1.artha-brand-title {{
    font-size: clamp(3rem, 6.2vw + 1.2rem, 7.25rem);
    font-weight: 900;
    letter-spacing: -0.04em;
    line-height: 0.97;
    color: {c['accent']} !important;
    margin: 0 !important;
    padding: 0;
    width: 100%;
    display: flex;
    justify-content: center;
    text-align: center;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.artha-brand-tagline {{
    font-size: clamp(1.2rem, 2.4vw + 0.5rem, 1.65rem);
    line-height: 1.45;
    text-align: center;
    color: #000000 !important;
    margin: 0;
    padding: 0;
    max-width: 36rem;
    font-style: normal;
    font-weight: 600;
    letter-spacing: -0.015em;
    opacity: 1;
}}
@media (max-width: 900px) {{
    .artha-brand-cluster {{
        flex-wrap: nowrap;
        align-items: center;
    }}
    h1.artha-brand-title {{
        letter-spacing: -0.032em;
    }}
}}
@media (max-width: 540px) {{
    .artha-brand-cluster {{
        flex-direction: column;
        align-items: flex-start;
        gap: 14px;
    }}
    .artha-logo-square {{
        margin-top: 0;
    }}
    .artha-brand-text {{
        width: 100%;
    }}
}}
/* ── Step card animations ── */
@keyframes pageFlip {{
  0%,100% {{ transform: rotateY(0deg); }}
  50%      {{ transform: rotateY(-25deg); }}
}}
@keyframes scanPulse {{
  0%,100% {{ transform: translate(0,0) scale(1); opacity:1; }}
  50%      {{ transform: translate(4px,4px) scale(1.08); opacity:0.85; }}
}}
@keyframes pulseRing {{
  0%   {{ r: 13; opacity: 0.6; }}
  100% {{ r: 22; opacity: 0; }}
}}
@keyframes typingDot {{
  0%,80%,100% {{ transform: translateY(0); opacity:0.4; }}
  40%          {{ transform: translateY(-5px); opacity:1; }}
}}
@keyframes floatCard {{
  0%,100% {{ transform: translateY(0); }}
  50%      {{ transform: translateY(-6px); }}
}}
.step-icon-wrap {{
  width:80px; height:80px;
  margin:0 auto 16px;
  animation: floatCard 3s ease-in-out infinite;
}}
.step-icon-wrap.s2 {{ animation-delay: 0.7s; }}
.step-icon-wrap.s3 {{ animation-delay: 1.4s; }}
.step-doc-page {{
  transform-origin: left center;
  animation: pageFlip 2.4s ease-in-out infinite;
}}
.step-mag {{
  animation: scanPulse 2s ease-in-out infinite;
  transform-origin: center;
}}
.pulse-ring {{
  animation: pulseRing 2s ease-out infinite;
  transform-origin: 34px 32px;
}}
.dot1 {{ animation: typingDot 1.2s ease-in-out infinite; animation-delay:0s; }}
.dot2 {{ animation: typingDot 1.2s ease-in-out infinite; animation-delay:0.2s; }}
.dot3 {{ animation: typingDot 1.2s ease-in-out infinite; animation-delay:0.4s; }}
.steps-label {{
  font-size: 12px !important;
  font-weight: 800 !important;
  color: {c['accent']} !important;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 0 0 6px 0;
}}
.steps-desc {{
  font-size: 15px !important;
  color: {c['accent']} !important;
  font-weight: 500;
  line-height: 1.5;
}}
/* ── Hide default Streamlit branding ── */
#MainMenu, footer, header[data-testid="stHeader"] {{
    visibility: hidden;
}}
/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; }}
::-webkit-scrollbar-track {{ background: {c['bg']}; }}
::-webkit-scrollbar-thumb {{ background: {c['border']}; border-radius: 3px; }}
</style>
""",
        unsafe_allow_html=True,
    )


# ── Session state init ─────────────────────────────────────────────────────────


def init_state():
    defaults = {
        "dark_mode": False,
        "onboarding_done": False,
        "checkin_done": False,
        "checkin_mood": "neutral",
        "parsed_dfs": {},          # month_key → DataFrame
        "file_names_done": set(),  # filenames already processed
        "metrics": None,
        "health_score": 0,
        "health_breakdown": {},
        "analysis": None,
        "chat_history": [],
        "selected_months": [],
        "emergency_fund": 0.0,
        "monthly_expenses": 0.0,
        "save_session": False,
        "session_loaded": False,
        "analysis_running": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()
inject_css()


# ── Helpers ────────────────────────────────────────────────────────────────────


def card(content_html, border_color=None, bg=None, padding="20px 24px"):
    c = C()
    bc = border_color or c["border"]
    bg_col = bg or c["card"]
    st.markdown(
        f'<div style="background:{bg_col};border:1px solid {bc};border-radius:10px;'
        f'padding:{padding};margin-bottom:16px;">{content_html}</div>',
        unsafe_allow_html=True,
    )


def fmt_dollar(v):
    return f"${abs(v):,.2f}"


def fmt_pct(v):
    return f"{v:.1f}%"


def month_label(month_key):
    year, month = month_key
    months = [
        "", "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    return f"{months[month]} {year}"


def api_key_ok():
    key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    return bool(key)


# ── API Key check ──────────────────────────────────────────────────────────────


def show_api_error():
    c = C()
    st.markdown(
        f"""
<div style="background:{c['card']};border:2px solid {c['bad']};border-radius:12px;padding:28px;margin:32px 0;">
  <h2 style="color:{c['bad']};margin:0 0 12px">⚠️ Anthropic API Key Missing</h2>
  <p style="color:{c['text']};font-size:15px;margin:0 0 16px">
    Artha uses Claude to analyze your finances. You need your own Anthropic API key (it's free to get started).
  </p>
  <p style="color:{c['text']};font-size:14px;margin:0 0 8px"><strong>To fix this in 2 minutes:</strong></p>
  <ol style="color:{c['secondary']};font-size:14px;line-height:1.8;">
    <li>Go to <strong>https://console.anthropic.com</strong> and create an account</li>
    <li>Click <strong>API Keys</strong> → <strong>Create Key</strong> and copy it</li>
    <li>In the <code>artha/</code> folder, create a file named <code>.env</code></li>
    <li>Add this line: <code>ANTHROPIC_API_KEY=your_key_here</code></li>
    <li>Save the file and run <code>streamlit run app.py</code> again</li>
  </ol>
  <p style="color:{c['secondary']};font-size:12px;margin:12px 0 0">
    Cost estimate: a typical analysis costs less than $0.02. You're billed per use, no subscription.
  </p>
</div>
""",
        unsafe_allow_html=True,
    )


# ── Top bar ────────────────────────────────────────────────────────────────────


def render_topbar():
    c = C()
    col_main, col_toggle = st.columns([14, 1])

    with col_main:
        st.markdown(
            f"""
<div class="artha-header-row">
  <div class="artha-brand-cluster">
    <div class="artha-logo-square">
      <span class="artha-logo-letter">A</span>
    </div>
    <div class="artha-brand-text">
      <h1 class="artha-brand-title">ARTHA!</h1>
      <p class="artha-brand-tagline">Your money has a story. Artha reads it.</p>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col_toggle:
        label = "☀️ Light" if st.session_state.dark_mode else "🌙 Dark"
        if st.button(label, key="toggle_dark"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.markdown(
        f'<hr style="border:none;border-top:1px solid {c["border"]};margin:0 0 clamp(20px, 3vw, 28px);">',
        unsafe_allow_html=True,
    )


# ── Emotional check-in ─────────────────────────────────────────────────────────


def render_checkin():
    c = C()
    st.markdown(
        f"""
<div style="background:{c['card']};border:1px solid {c['border']};border-radius:12px;
     padding:24px;margin-bottom:24px;text-align:center;">
  <p style="font-size:17px;font-weight:600;color:{c['text']};margin:0 0 16px;">
    How are you feeling about your finances this week?
  </p>
""",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("😰  Stressed", use_container_width=True, key="mood_stressed"):
            st.session_state.checkin_mood = "stressed"
            st.session_state.checkin_done = True
            st.rerun()
    with col2:
        if st.button("😐  Neutral", use_container_width=True, key="mood_neutral"):
            st.session_state.checkin_mood = "neutral"
            st.session_state.checkin_done = True
            st.rerun()
    with col3:
        if st.button("🙂  Okay", use_container_width=True, key="mood_okay"):
            st.session_state.checkin_mood = "okay"
            st.session_state.checkin_done = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ── Onboarding ─────────────────────────────────────────────────────────────────


def render_onboarding():
    c = C()
    accent = c['accent']
    card   = c['card']
    border = c['border']
    components.html(f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }}

  .wrap {{
    background: {card};
    border: 1px solid {border};
    border-top: 3px solid {accent};
    border-radius: 14px;
    padding: 40px 32px 36px;
    box-shadow: 0 6px 28px rgba(27,42,74,0.13);
  }}
  h2 {{
    color: {accent};
    text-align: center;
    font-size: 1.5rem;
    font-weight: 800;
    margin-bottom: 36px;
  }}
  .row {{
    display: flex;
    gap: 32px;
    flex-wrap: wrap;
    justify-content: center;
  }}
  .step {{
    flex: 1;
    min-width: 180px;
    text-align: center;
  }}
  .icon-wrap {{
    width: 80px;
    height: 80px;
    margin: 0 auto 16px;
  }}
  .label {{
    font-size: 11px;
    font-weight: 800;
    color: {accent};
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 6px;
  }}
  .desc {{
    font-size: 15px;
    color: {accent};
    font-weight: 500;
    line-height: 1.5;
  }}
  .footer {{
    text-align: center;
    font-size: 13px;
    color: {accent};
    margin-top: 32px;
    font-weight: 600;
    opacity: 0.7;
  }}

  /* float animation */
  @keyframes float1 {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-6px)}} }}
  @keyframes float2 {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-6px)}} }}
  @keyframes float3 {{ 0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-6px)}} }}
  .icon-wrap.s1 {{ animation: float1 3s ease-in-out infinite; }}
  .icon-wrap.s2 {{ animation: float2 3s ease-in-out infinite; animation-delay: 0.7s; }}
  .icon-wrap.s3 {{ animation: float3 3s ease-in-out infinite; animation-delay: 1.4s; }}

  /* page flip */
  @keyframes pageFlip {{ 0%,100%{{transform:rotateY(0)}} 50%{{transform:rotateY(-28deg)}} }}
  .doc-lines {{ transform-origin: left center; animation: pageFlip 2.4s ease-in-out infinite; }}

  /* magnifier scan */
  @keyframes scan {{ 0%,100%{{transform:translate(0,0)}} 50%{{transform:translate(5px,5px)}} }}
  .mag-glass {{ animation: scan 2s ease-in-out infinite; transform-origin: 34px 32px; }}
  @keyframes pulseRing {{ 0%{{stroke-width:1.5;opacity:0.6}} 100%{{stroke-width:0;opacity:0}} }}
  .pulse {{ animation: pulseRing 2s ease-out infinite; transform-box:fill-box; transform-origin:center; }}

  /* typing dots */
  @keyframes bounce {{ 0%,80%,100%{{transform:translateY(0);opacity:0.4}} 40%{{transform:translateY(-5px);opacity:1}} }}
  .d1 {{ animation: bounce 1.2s ease-in-out infinite; animation-delay: 0s; }}
  .d2 {{ animation: bounce 1.2s ease-in-out infinite; animation-delay: 0.2s; }}
  .d3 {{ animation: bounce 1.2s ease-in-out infinite; animation-delay: 0.4s; }}
</style>
</head>
<body>
<div class="wrap">
  <h2>Get started in 3 steps</h2>
  <div class="row">

    <div class="step">
      <div class="icon-wrap s1">
        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="80" height="80">
          <rect x="12" y="8" width="44" height="58" rx="6" fill="#EEF2FA" stroke="{accent}" stroke-width="2.5"/>
          <g class="doc-lines">
            <rect x="20" y="18" width="28" height="4" rx="2" fill="{accent}" opacity="0.3"/>
            <rect x="20" y="27" width="28" height="3" rx="1.5" fill="{accent}" opacity="0.22"/>
            <rect x="20" y="35" width="20" height="3" rx="1.5" fill="{accent}" opacity="0.22"/>
            <rect x="20" y="43" width="24" height="3" rx="1.5" fill="{accent}" opacity="0.17"/>
            <rect x="20" y="51" width="16" height="3" rx="1.5" fill="{accent}" opacity="0.17"/>
          </g>
          <circle cx="60" cy="60" r="14" fill="{accent}"/>
          <path d="M54 60 L58 64 L67 55" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="label">Step 1</div>
      <div class="desc">Upload your bank statement PDFs</div>
    </div>

    <div class="step">
      <div class="icon-wrap s2">
        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="80" height="80">
          <circle cx="34" cy="32" r="22" fill="#EEF2FA" stroke="{accent}" stroke-width="2.5"/>
          <circle class="pulse" cx="34" cy="32" r="22" fill="none" stroke="{accent}" stroke-width="3" opacity="0.4"/>
          <g class="mag-glass">
            <circle cx="34" cy="32" r="22" fill="none" stroke="{accent}" stroke-width="2.5"/>
            <line x1="50" y1="48" x2="66" y2="64" stroke="{accent}" stroke-width="5" stroke-linecap="round"/>
            <path d="M26 28 Q30 22 38 26" stroke="{accent}" stroke-width="2" stroke-linecap="round" opacity="0.45"/>
          </g>
        </svg>
      </div>
      <div class="label">Step 2</div>
      <div class="desc">Artha reads and analyzes your finances</div>
    </div>

    <div class="step">
      <div class="icon-wrap s3">
        <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" width="80" height="80">
          <rect x="6" y="10" width="56" height="42" rx="11" fill="{accent}"/>
          <polygon points="16,52 10,68 32,56" fill="{accent}"/>
          <circle class="d1" cx="24" cy="31" r="4.5" fill="white"/>
          <circle class="d2" cx="37" cy="31" r="4.5" fill="white"/>
          <circle class="d3" cx="50" cy="31" r="4.5" fill="white"/>
        </svg>
      </div>
      <div class="label">Step 3</div>
      <div class="desc">Ask Artha anything about your money</div>
    </div>

  </div>
  <p class="footer">🔒 No account needed. No data leaves your device. Ever.</p>
</div>
</body>
</html>
""", height=310)



# ── Upload section ─────────────────────────────────────────────────────────────


def render_upload():
    c = C()
    st.markdown(
        f"""
<div style="margin-bottom:8px;">
  <span style="background:#E8F5EE;color:{c['good']};border:1px solid {c['good']};
        border-radius:999px;padding:4px 14px;font-size:12px;font-weight:600;">
    🔒 Your file never leaves your device
  </span>
</div>
""",
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload your bank statements",
        type=["pdf"],
        accept_multiple_files=True,
        key="file_uploader",
        help="PDF format. One or more banks. One or more months.",
        label_visibility="visible",
    )
    st.markdown(
        f'<p style="font-size:12px;color:{c["secondary"]};margin-top:4px;">'
        "PDF format. One or more banks. One or more months.</p>",
        unsafe_allow_html=True,
    )

    return uploaded


# ── Process uploaded files ─────────────────────────────────────────────────────


def process_files(uploaded_files):
    """Parse new files and store results in session state."""
    if not uploaded_files:
        return

    errors = []
    new_parsed = False

    for f in uploaded_files:
        if f.name in st.session_state.file_names_done:
            continue

        with st.spinner(f"Reading {f.name}…"):
            df, err = parse_pdf(f)

        if err:
            errors.append((f.name, err))
        elif df is not None and not df.empty:
            month_key = (int(df["year"].iloc[0]), int(df["month"].iloc[0]))
            # Merge if same month already exists (multi-bank same month)
            if month_key in st.session_state.parsed_dfs:
                st.session_state.parsed_dfs[month_key] = pd.concat(
                    [st.session_state.parsed_dfs[month_key], df], ignore_index=True
                )
            else:
                st.session_state.parsed_dfs[month_key] = df
            st.session_state.file_names_done.add(f.name)
            new_parsed = True

    for fname, err in errors:
        c = C()
        st.markdown(
            f"""
<div style="background:#FFF5F5;border:1px solid {c['bad']};border-radius:8px;
     padding:16px;margin:8px 0;">
  <strong style="color:{c['bad']};">Could not read: {fname}</strong>
  <pre style="color:{c['secondary']};font-size:12px;white-space:pre-wrap;margin:8px 0 0;">{err}</pre>
</div>
""",
            unsafe_allow_html=True,
        )

    if new_parsed:
        all_keys = sorted(st.session_state.parsed_dfs.keys())
        st.session_state.selected_months = all_keys
        st.session_state.onboarding_done = True
        st.session_state.analysis = None  # Reset analysis on new data
        st.session_state.metrics = None


# ── Emergency fund sidebar inputs ──────────────────────────────────────────────


def render_ef_inputs():
    c = C()
    st.markdown(
        f'<p style="font-size:13px;color:{c["secondary"]};margin:0 0 4px;">'
        "Help Artha calculate your emergency fund runway:</p>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        ef = st.number_input(
            "💰 Savings balance ($)",
            min_value=0.0,
            value=float(st.session_state.emergency_fund),
            step=100.0,
            key="ef_input",
            help="Your current savings / checking balance that could cover emergencies",
        )
        st.session_state.emergency_fund = ef
    with col2:
        me = st.number_input(
            "📅 Monthly expenses ($)",
            min_value=0.0,
            value=float(st.session_state.monthly_expenses),
            step=100.0,
            key="me_input",
            help="Average monthly spend. Leave 0 to auto-detect from your statements.",
        )
        st.session_state.monthly_expenses = me


# ── Metric cards ───────────────────────────────────────────────────────────────


def render_metric_cards(metrics, health_score, health_breakdown):
    c = C()
    savings_rate = metrics.get("savings_rate", 0)
    em = metrics.get("emergency_months", 0)

    # Health score color
    if health_score >= 70:
        score_color = c["good"]
        score_label = "Strong"
    elif health_score >= 40:
        score_color = "#D4760A"
        score_label = "Needs work"
    else:
        score_color = c["bad"]
        score_label = "Critical"

    # Savings rate color
    if savings_rate > 20:
        sr_color = c["good"]
    elif savings_rate > 0:
        sr_color = "#D4760A"
    else:
        sr_color = c["bad"]

    # Emergency fund card
    if em < 3:
        ef_border = c["bad"]
        ef_bg = "#FFF5F5"
        ef_text = c["bad"]
        ef_badge = f'<span style="background:{c["bad"]};color:#fff;border-radius:4px;padding:2px 8px;font-size:11px;font-weight:700;">Fix this first</span>'
    elif em < 6:
        ef_border = "#D4760A"
        ef_bg = "#FFF8EE"
        ef_text = "#D4760A"
        ef_badge = ""
    else:
        ef_border = c["good"]
        ef_bg = "#F0FFF6"
        ef_text = c["good"]
        ef_badge = ""

    col1, col2, col3 = st.columns(3)

    with col1:
        progress_pct = min(health_score, 100)
        st.markdown(
            f"""
<div style="background:{c['card']};border:1px solid {c['border']};border-radius:10px;padding:20px;">
  <div style="font-size:12px;color:{c['secondary']};font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Health Score</div>
  <div style="font-size:42px;font-weight:800;color:{score_color};line-height:1.1;margin:8px 0 4px;">{health_score}</div>
  <div style="font-size:12px;color:{score_color};margin-bottom:10px;">{score_label}</div>
  <div style="background:{c['border']};border-radius:999px;height:6px;">
    <div style="width:{progress_pct}%;background:{score_color};height:6px;border-radius:999px;"></div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            f"""
<div style="background:{c['card']};border:1px solid {c['border']};border-radius:10px;padding:20px;">
  <div style="font-size:12px;color:{c['secondary']};font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">Savings Rate</div>
  <div style="font-size:42px;font-weight:800;color:{sr_color};line-height:1.1;margin:8px 0 4px;">{fmt_pct(savings_rate)}</div>
  <div style="font-size:12px;color:{c['secondary']};">
    Saved: {fmt_dollar(metrics.get('savings_amount', 0))} this period
  </div>
  <div style="font-size:11px;color:{c['secondary']};margin-top:6px;">Target: 20%+</div>
</div>
""",
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
<div style="background:{ef_bg};border:1px solid {ef_border};border-radius:10px;padding:20px;">
  <div style="font-size:12px;color:{ef_text};font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
    Emergency Fund &nbsp;{ef_badge}
  </div>
  <div style="font-size:42px;font-weight:800;color:{ef_text};line-height:1.1;margin:8px 0 4px;">
    {em:.1f}<span style="font-size:18px;font-weight:400;"> mo</span>
  </div>
  <div style="font-size:12px;color:{ef_text};">
    {fmt_dollar(metrics.get('emergency_fund_amount', 0))} saved &nbsp;|&nbsp; {fmt_dollar(metrics.get('monthly_expenses', 0))}/mo expenses
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)


# ── Emotional spending alert ───────────────────────────────────────────────────


def render_emotional_alert(metrics, all_metrics_by_month):
    c = C()
    spikes = metrics.get("spending_spikes", {})

    # Check upward trend in emotional categories across months
    emotional_cats = {"Food Delivery", "Shopping", "Dining Out"}
    trending_up = []
    if len(all_metrics_by_month) >= 2:
        sorted_months = sorted(all_metrics_by_month.keys())
        for cat in emotional_cats:
            vals = [
                all_metrics_by_month[m].get("category_totals", {}).get(cat, 0)
                for m in sorted_months
            ]
            if len(vals) >= 2 and vals[-1] > vals[-2] * 1.1:
                trending_up.append(cat)

    if not spikes and not trending_up:
        return

    alerts = []
    for day, avg in spikes.items():
        alerts.append(f"<strong>{day}</strong> spending runs {fmt_dollar(avg)}/day on average — that's a pattern worth noting.")
    for cat in trending_up:
        alerts.append(f"<strong>{cat}</strong> spending has been creeping up across your last statements.")

    st.markdown(
        f"""
<div style="background:#FFF8EE;border:2px solid #D4760A;border-radius:10px;padding:18px 22px;margin-bottom:16px;">
  <div style="font-size:13px;font-weight:700;color:#D4760A;margin-bottom:8px;">⚡ Spending Pattern Alert</div>
  {''.join(f'<p style="color:{c["text"]};font-size:14px;margin:4px 0;">{a}</p>' for a in alerts)}
</div>
""",
        unsafe_allow_html=True,
    )


# ── Analysis sections ──────────────────────────────────────────────────────────


def render_analysis(analysis, metrics):
    c = C()
    if not analysis:
        return

    def analysis_card(title, content, icon="", navy_bg=False):
        if not content:
            return
        bg = c["accent"] if navy_bg else c["card"]
        text_col = "#FFFFFF" if navy_bg else c["text"]
        border = c["accent"] if navy_bg else c["border"]
        st.markdown(
            f"""
<div style="background:{bg};border:1px solid {border};border-radius:10px;
     padding:22px 26px;margin-bottom:14px;">
  <div style="font-size:12px;font-weight:700;color:{'#AABBDD' if navy_bg else c['secondary']};
       text-transform:uppercase;letter-spacing:0.6px;margin-bottom:10px;">{icon} {title}</div>
  <div style="font-size:15px;color:{text_col};line-height:1.7;white-space:pre-wrap;">{content}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    analysis_card("Artha's Take", analysis.get("arthas_take", ""), "💬")
    analysis_card("What's Draining You", analysis.get("whats_draining_you", ""), "🔥")

    col1, col2 = st.columns(2)
    with col1:
        analysis_card("Spending Loop Alert", analysis.get("spending_loop_alert", ""), "⚡")
    with col2:
        analysis_card("What If...", analysis.get("what_if", ""), "🔮")

    analysis_card("One Thing to Fix This Month", analysis.get("one_thing_to_fix", ""), "🎯", navy_bg=True)
    analysis_card("Your Financial Priority Right Now", analysis.get("financial_priority", ""), "📌")


# ── Spending charts ────────────────────────────────────────────────────────────


def render_spending_chart(metrics):
    c = C()
    cat_totals = metrics.get("category_totals", {})
    if not cat_totals:
        return

    items = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
    cats = [i[0] for i in items]
    vals = [i[1] for i in items]

    fig = go.Figure(
        go.Bar(
            x=vals,
            y=cats,
            orientation="h",
            marker_color=c["accent"],
            text=[f"${v:,.0f}" for v in vals],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Spending by Category",
        paper_bgcolor=c["card"],
        plot_bgcolor=c["card"],
        font=dict(color=c["text"]),
        margin=dict(l=10, r=80, t=40, b=10),
        height=max(300, len(cats) * 34),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Multi-month comparison ─────────────────────────────────────────────────────


def render_multi_month(all_metrics_by_month, comp_df, trends):
    c = C()
    if comp_df is None or comp_df.empty or len(all_metrics_by_month) < 2:
        return

    st.markdown(
        f'<h3 style="color:{c["accent"]};margin:24px 0 12px;">Month-over-Month</h3>',
        unsafe_allow_html=True,
    )

    # Trajectory
    total_spendings = comp_df["total_spending"].tolist()
    if len(total_spendings) >= 2:
        pct_change = (total_spendings[-1] - total_spendings[0]) / max(total_spendings[0], 1) * 100
        if pct_change < -5:
            traj_label, traj_color = "Improving ↓", c["good"]
        elif pct_change > 5:
            traj_label, traj_color = "Increasing ↑", c["bad"]
        else:
            traj_label, traj_color = "Stable →", c["secondary"]

        st.markdown(
            f"""
<div style="display:inline-block;background:{c['card']};border:1px solid {traj_color};
     border-radius:999px;padding:6px 18px;margin-bottom:16px;">
  <span style="font-weight:700;color:{traj_color};font-size:14px;">
    Overall trajectory: {traj_label}
  </span>
</div>
""",
            unsafe_allow_html=True,
        )

    # Creeping up alerts
    if trends:
        for cat, trend in trends.items():
            if trend == "creeping_up":
                st.markdown(
                    f"""
<div style="display:inline-block;background:#FFF8EE;border:1px solid #D4760A;
     border-radius:999px;padding:4px 14px;margin:2px;font-size:13px;color:#D4760A;font-weight:600;">
  ↗ {cat} — creeping up
</div>
""",
                    unsafe_allow_html=True,
                )

    # Line chart — spending per category over months
    cats_in_comp = [col for col in comp_df.columns if col not in ("month", "total_spending")]
    top_cats = (
        comp_df[cats_in_comp].sum().sort_values(ascending=False).head(6).index.tolist()
    )

    if top_cats:
        fig = go.Figure()
        colors = ["#1B2A4A", "#1A7F4B", "#A32D2D", "#4A7ABB", "#D4760A", "#8E44AD"]
        for i, cat in enumerate(top_cats):
            fig.add_trace(
                go.Scatter(
                    x=comp_df["month"],
                    y=comp_df[cat],
                    name=cat,
                    mode="lines+markers",
                    line=dict(color=colors[i % len(colors)], width=2),
                    marker=dict(size=7),
                )
            )
        fig.update_layout(
            title="Spending per Category by Month",
            paper_bgcolor=c["card"],
            plot_bgcolor=c["card"],
            font=dict(color=c["text"]),
            legend=dict(bgcolor=c["card"]),
            margin=dict(l=10, r=10, t=40, b=10),
            height=380,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor=c["border"]),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Total spending line
    fig2 = go.Figure(
        go.Scatter(
            x=comp_df["month"],
            y=comp_df["total_spending"],
            mode="lines+markers+text",
            text=[f"${v:,.0f}" for v in comp_df["total_spending"]],
            textposition="top center",
            line=dict(color=c["accent"], width=3),
            marker=dict(size=9, color=c["accent"]),
            fill="tozeroy",
            fillcolor=f"rgba(27,42,74,0.07)",
        )
    )
    fig2.update_layout(
        title="Total Spending Over Time",
        paper_bgcolor=c["card"],
        plot_bgcolor=c["card"],
        font=dict(color=c["text"]),
        margin=dict(l=10, r=10, t=40, b=10),
        height=280,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor=c["border"]),
    )
    st.plotly_chart(fig2, use_container_width=True)


# ── Chat ───────────────────────────────────────────────────────────────────────


def render_chat(metrics):
    c = C()
    if not metrics:
        return

    st.markdown(
        f"""
<div style="background:{c['accent']};border-radius:10px 10px 0 0;padding:14px 22px;margin-top:24px;">
  <span style="font-size:16px;font-weight:700;color:#FFFFFF;">💬 Ask Artha anything</span>
</div>
""",
        unsafe_allow_html=True,
    )

    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.chat_history:
            is_user = msg["role"] == "user"
            label = "You" if is_user else "Artha"
            label_color = c["secondary"] if is_user else c["accent"]
            bubble_bg = c["input_bg"] if is_user else c["chat_bg"]
            border_col = c["border"]
            st.markdown(
                f"""
<div style="background:{bubble_bg};border:1px solid {border_col};border-radius:8px;
     padding:14px 18px;margin:8px 0;">
  <div style="font-size:11px;font-weight:700;color:{label_color};margin-bottom:6px;
       text-transform:uppercase;letter-spacing:0.4px;">{label}</div>
  <div style="font-size:14px;color:{c['text']};line-height:1.65;white-space:pre-wrap;">{msg['content']}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    st.markdown(
        f'<div style="background:{c["card"]};border:1px solid {c["border"]};'
        f'border-radius:0 0 10px 10px;padding:12px 16px;">',
        unsafe_allow_html=True,
    )
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "chat_input",
            placeholder="Ask Artha something about your money…",
            label_visibility="collapsed",
            key="chat_text_input",
        )
    with col_btn:
        send = st.button("Send", key="chat_send", use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    if send and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input.strip()})
        with st.spinner("Artha is thinking…"):
            try:
                reply = chat_with_artha(
                    user_input.strip(),
                    metrics,
                    st.session_state.chat_history[:-1],
                )
            except Exception as e:
                reply = f"Something went wrong: {str(e)}"
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()


# ── Export section ─────────────────────────────────────────────────────────────


def render_export(analysis, metrics, health_score):
    c = C()
    if not analysis or not metrics:
        return

    st.markdown(f'<hr style="border:none;border-top:1px solid {c["border"]};margin:28px 0 16px;">', unsafe_allow_html=True)
    st.markdown(
        f'<h3 style="color:{c["accent"]};margin-bottom:14px;">Export Your Report</h3>',
        unsafe_allow_html=True,
    )

    include_chat = st.checkbox(
        "Include chat history in export",
        value=False,
        key="include_chat_in_export",
    )

    col1, col2 = st.columns(2)
    with col1:
        try:
            pdf_bytes = export_to_pdf(
                analysis, metrics, health_score,
                chat_history=st.session_state.chat_history if include_chat else None,
                include_chat=include_chat,
            )
            st.download_button(
                "⬇ Export as PDF",
                data=pdf_bytes,
                file_name=f"artha_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="export_pdf_btn",
            )
        except Exception as e:
            st.error(f"PDF export failed: {e}")

    with col2:
        try:
            txt = export_to_text(
                analysis, metrics, health_score,
                chat_history=st.session_state.chat_history if include_chat else None,
                include_chat=include_chat,
            )
            st.download_button(
                "⬇ Export as Text",
                data=txt.encode("utf-8"),
                file_name=f"artha_report_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True,
                key="export_txt_btn",
            )
        except Exception as e:
            st.error(f"Text export failed: {e}")


# ── Session history ────────────────────────────────────────────────────────────


def load_session_history():
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_session_history(metrics, health_score, analysis):
    try:
        payload = {
            "date": datetime.now().isoformat(),
            "health_score": health_score,
            "savings_rate": metrics.get("savings_rate", 0),
            "total_spending": metrics.get("total_spending", 0),
            "total_income": metrics.get("total_income", 0),
            "emergency_months": metrics.get("emergency_months", 0),
            "arthas_take": (analysis or {}).get("arthas_take", ""),
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def render_session_history_banner():
    c = C()
    if st.session_state.session_loaded:
        return
    hist = load_session_history()
    if not hist:
        return

    try:
        date_str = datetime.fromisoformat(hist["date"]).strftime("%B %d, %Y")
    except Exception:
        date_str = "a previous session"

    st.markdown(
        f"""
<div style="background:{c['card']};border:1px solid {c['border']};border-radius:10px;
     padding:16px 22px;margin-bottom:20px;">
  <span style="color:{c['secondary']};font-size:14px;">
    👋 Welcome back. Your last session was on <strong style="color:{c['text']};">{date_str}</strong>
    &nbsp;(Health Score: <strong>{hist.get('health_score', '?')}</strong>).
  </span>
""",
        unsafe_allow_html=True,
    )
    col1, col2, _ = st.columns([1, 1, 4])
    with col1:
        if st.button("View summary", key="session_yes"):
            st.session_state.session_loaded = True
            with st.expander("Last session snapshot", expanded=True):
                st.write(f"**Health Score:** {hist.get('health_score')} / 100")
                st.write(f"**Savings Rate:** {hist.get('savings_rate', 0):.1f}%")
                st.write(f"**Total Spending:** ${hist.get('total_spending', 0):,.2f}")
                st.write(f"**Emergency Fund:** {hist.get('emergency_months', 0):.1f} months")
                if hist.get("arthas_take"):
                    st.write("**Artha's Take:**")
                    st.write(hist["arthas_take"])
    with col2:
        if st.button("Dismiss", key="session_no"):
            st.session_state.session_loaded = True
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# ── Main app ───────────────────────────────────────────────────────────────────


def main():
    c = C()
    render_topbar()

    if not st.session_state.checkin_done:
        render_checkin()
        return

    render_session_history_banner()

    if not st.session_state.onboarding_done:
        render_onboarding()

    # ── Upload ──
    st.markdown(
        f'<h3 style="color:{c["accent"]};margin-bottom:8px;">Upload Bank Statements</h3>',
        unsafe_allow_html=True,
    )
    uploaded_files = render_upload()
    process_files(uploaded_files)

    # No files yet
    if not st.session_state.parsed_dfs:
        return

    st.markdown(f'<hr style="border:none;border-top:1px solid {c["border"]};margin:20px 0;">', unsafe_allow_html=True)

    # ── Month selector (multi-month) ──
    all_keys = sorted(st.session_state.parsed_dfs.keys())
    if len(all_keys) > 1:
        month_options = {month_label(k): k for k in all_keys}
        selected_labels = st.multiselect(
            "Select months to include in analysis",
            options=list(month_options.keys()),
            default=list(month_options.keys()),
            key="month_selector",
        )
        selected_keys = [month_options[label] for label in selected_labels if label in month_options]
        if not selected_keys:
            selected_keys = all_keys
        st.session_state.selected_months = selected_keys
    else:
        st.session_state.selected_months = all_keys

    # Build combined DataFrame for selected months
    selected_dfs = [
        st.session_state.parsed_dfs[k]
        for k in st.session_state.selected_months
        if k in st.session_state.parsed_dfs
    ]
    if not selected_dfs:
        return

    combined_df = pd.concat(selected_dfs, ignore_index=True)

    # ── Emergency fund inputs ──
    render_ef_inputs()

    # ── Recalculate metrics if needed ──
    ef = st.session_state.emergency_fund
    me = st.session_state.monthly_expenses if st.session_state.monthly_expenses > 0 else None

    metrics = calculate_metrics(combined_df, emergency_fund_amount=ef, monthly_expenses=me)
    health_score, health_breakdown = calculate_health_score(metrics)
    st.session_state.metrics = metrics
    st.session_state.health_score = health_score
    st.session_state.health_breakdown = health_breakdown

    # ── Metric cards ──
    st.markdown(f'<h3 style="color:{c["accent"]};margin:16px 0 12px;">Your Financial Snapshot</h3>', unsafe_allow_html=True)
    render_metric_cards(metrics, health_score, health_breakdown)

    # ── Spending chart ──
    with st.expander("Spending Breakdown Chart", expanded=True):
        render_spending_chart(metrics)

    # ── Multi-month metrics per month ──
    all_metrics_by_month = {}
    for k in all_keys:
        df_m = st.session_state.parsed_dfs[k]
        all_metrics_by_month[k] = calculate_metrics(df_m, emergency_fund_amount=ef, monthly_expenses=me)

    # ── Emotional spending alert ──
    render_emotional_alert(metrics, all_metrics_by_month)

    # ── Claude analysis ──
    st.markdown(f'<h3 style="color:{c["accent"]};margin:20px 0 12px;">Artha\'s Analysis</h3>', unsafe_allow_html=True)

    if not api_key_ok():
        show_api_error()
    else:
        if st.session_state.analysis is None:
            if st.button("✨ Get Artha's Full Analysis", use_container_width=False, key="run_analysis_btn"):
                with st.spinner("Artha is reading your finances…"):
                    try:
                        analysis = run_analysis(
                            metrics,
                            health_score,
                            mood=st.session_state.checkin_mood,
                        )
                        st.session_state.analysis = analysis
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
        else:
            if st.button("🔄 Re-analyze", key="rerun_analysis_btn"):
                st.session_state.analysis = None
                st.rerun()

            render_analysis(st.session_state.analysis, metrics)

    # ── Multi-month comparison ──
    if len(all_keys) > 1:
        month_dfs = {
            month_label(k): st.session_state.parsed_dfs[k]
            for k in st.session_state.selected_months
            if k in st.session_state.parsed_dfs
        }
        if len(month_dfs) > 1:
            comp_df, trends = compare_months(month_dfs)
            render_multi_month(all_metrics_by_month, comp_df, trends)

    # ── Chat ──
    render_chat(metrics)

    # ── Export ──
    render_export(st.session_state.analysis, metrics, health_score)

    # ── Session saving ──
    st.markdown(f'<hr style="border:none;border-top:1px solid {c["border"]};margin:28px 0 8px;">', unsafe_allow_html=True)
    save_checked = st.checkbox(
        "Save this session for next time",
        value=st.session_state.save_session,
        key="save_session_checkbox",
    )
    st.session_state.save_session = save_checked

    if save_checked and st.session_state.analysis and metrics:
        save_session_history(metrics, health_score, st.session_state.analysis)
        st.markdown(
            f'<p style="font-size:12px;color:{c["good"]};">✓ Session saved locally.</p>',
            unsafe_allow_html=True,
        )

    st.markdown("<br><br>", unsafe_allow_html=True)


main()

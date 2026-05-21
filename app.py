import subprocess
import threading
import queue
import re
import json
import time
import shutil
import base64
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from itertools import groupby

import streamlit as st
import altair as alt
import pandas as pd

from config import (
    VAULT_PATH,
    VAULT_NAME,
    CLAUDE_CLI,
    DAILY_NOTES_DIR,
    RUNS_DIR,
    DRAFTS_AWAITING,
    SKILLS,
    RUN_TIMEOUT_SEC,
    PERMISSION_MODE,
    LIMITS,
    SESSION_META_DIR,
    CLAUDE_PLAN,
)
from data_sources import load_bookkeeping
import shopify_data
import plotly.graph_objects as go

st.set_page_config(page_title="Hailey's Hub", page_icon="◆", layout="wide")

# ═══════════════════════════════════════════════════════════
# GLOBAL RUNTIME (shared across reruns, lives in module scope)
# ═══════════════════════════════════════════════════════════


@st.cache_resource
def get_runtime():
    return {
        "proc": None,
        "buffer": [],           # raw stdout text chunks
        "text": "",             # accumulated assistant text (parsed)
        "phases": [],           # tool_use phase log
        "current_phase": None,  # latest phase label
        "cost_usd": None,
        "tokens_in": None,
        "tokens_out": None,
        "done": False,
        "cancelled": False,
        "error": None,
        "start_time": None,
    }


RT = get_runtime()


def reset_runtime():
    RT["proc"] = None
    RT["buffer"] = []
    RT["text"] = ""
    RT["phases"] = []
    RT["current_phase"] = None
    RT["cost_usd"] = None
    RT["tokens_in"] = None
    RT["tokens_out"] = None
    RT["done"] = False
    RT["cancelled"] = False
    RT["error"] = None
    RT["start_time"] = None


# ═══════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════

PREMIUM_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fraunces:ital,wght@0,400;0,500;1,400;1,500&display=swap');

:root {
    --bg:         #fde8f1;
    --bg-elev:    #ffffff;
    --bg-card:    #ffffff;
    --bg-card-hi: #fff5fa;
    --ink-deep:   #3d2a4f;          /* soft aubergine — used sparingly */
    --ring-soft:  rgba(26, 26, 46, 0.09);
    --ring-mid:   rgba(26, 26, 46, 0.18);
    --ring-hard:  #1a1a2e;
    --fg:         #1a1a2e;
    --fg-dim:     #4a4a60;
    --fg-mute:    #6f6f85;
    --accent:     #ec1e79;          /* hot magenta — primary */
    --accent-soft: rgba(236, 30, 121, 0.10);
    --accent-2:   #21c9e8;          /* cyan */
    --accent-3:   #a4e635;          /* lime */
    --accent-4:   #ffd633;          /* yellow */
    --accent-5:   #8b4cd6;          /* purple */
    --warn:       #ff9d3a;
    --danger:     #ff4d6d;          /* coral pink */
    --good:       #a4e635;          /* lime */

    /* legacy aliases (keep existing class selectors resolving) */
    --text:          var(--fg);
    --text-dim:      var(--fg-dim);
    --text-mute:     var(--fg-mute);
    --border:        var(--ring-soft);
    --border-strong: var(--ring-mid);
    --ring-warm:     var(--ring-soft);
    --ring-deep:     var(--ring-mid);
    --accent-glow:   rgba(236, 30, 121, 0.22);
    --coral:         #ff4d6d;
    --amber:         var(--warn);
}

html, body, [class*="css"] {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    color: var(--fg);
}

.stApp {
    background:
        linear-gradient(135deg,
            #fde8f1 0%,
            #e8f4ff 35%,
            #fff8e7 65%,
            #ebf9ee 100%);
    background-attachment: fixed;
}
body { background: var(--bg); }

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-weight: 500;
    letter-spacing: 0.02em;
    color: var(--fg);
    text-transform: uppercase;
}

.hero-title {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif !important;
    font-size: 2.8rem !important;
    font-weight: 600;
    letter-spacing: 0.05em;
    line-height: 1;
    color: var(--fg);
    margin: 0 0 0.5rem 0;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}
.hero-title em {
    font-style: normal;
    color: var(--accent);
    font-weight: 600;
    margin-left: 0;
}
.hero-title .hero-word { display: inline-block; color: var(--fg); }

.title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.2rem;
    flex-wrap: wrap;
    margin-bottom: 0.3rem;
}
.title-crumb {
    margin: 0;
    text-align: right;
    max-width: 60%;
}

/* Sprite-sheet mascot: 7 frames × 12x32, scaled 2× → 24x64 rendered */
.hero-title .mascot {
    display: inline-block;
    width: 24px;
    height: 64px;
    background-image: var(--idle);
    background-repeat: no-repeat;
    background-position: 0 0;
    background-size: 168px 64px;
    image-rendering: pixelated;
    image-rendering: crisp-edges;
    -ms-interpolation-mode: nearest-neighbor;
    vertical-align: middle;
    margin-right: 0.2em;
    margin-top: 0;
    filter: none;
    animation: robot-idle 0.85s steps(7) infinite;
    will-change: background-position, transform;
    transition: filter 0.2s ease;
    transform: translateY(-14px);
}
@keyframes robot-idle {
    from { background-position:    0  0; }
    to   { background-position: -168px 0; }
}
.hero-title .mascot:hover {
    background-image: var(--run);
    animation: robot-run 0.55s steps(7) infinite;
    filter: none;
    transform: translateY(0);
}
@keyframes robot-run {
    from { background-position:    0  0; }
    to   { background-position: -168px 0; }
}

/* Pixel mascot rows — Star Wars trio on left, LOTR trio on right of title. */
.mascot-pair {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    vertical-align: middle;
    margin: 0 0.6rem;
}
.tree-mascot {
    display: inline-block;
    width: 36px;
    height: 56px;
    vertical-align: middle;
    transform-origin: bottom center;
    image-rendering: pixelated;
    image-rendering: crisp-edges;
    -ms-interpolation-mode: nearest-neighbor;
    transform: translateY(-4px);
}
.mascot-pair .tree-mascot:nth-child(3n+1) {
    animation: mascot-sway-a 3.0s ease-in-out infinite;
}
.mascot-pair .tree-mascot:nth-child(3n+2) {
    animation: mascot-sway-b 3.0s ease-in-out infinite;
    animation-delay: -1s;
}
.mascot-pair .tree-mascot:nth-child(3n+3) {
    animation: mascot-sway-a 3.0s ease-in-out infinite;
    animation-delay: -2s;
}
.tree-mascot:hover {
    animation: tree-bounce 0.55s ease-in-out infinite !important;
}
@keyframes mascot-sway-a {
    0%, 100% { transform: translateY(-4px) rotate(-2deg); }
    50%      { transform: translateY(-4px) rotate(2deg); }
}
@keyframes mascot-sway-b {
    0%, 100% { transform: translateY(-4px) rotate(2deg); }
    50%      { transform: translateY(-4px) rotate(-2deg); }
}
@keyframes tree-bounce {
    0%, 100% { transform: translateY(-4px) rotate(-3deg); }
    50%      { transform: translateY(-7px) rotate(3deg); }
}

.caption-mono {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.62rem;
    color: var(--fg-mute);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

[data-testid="stStatusWidget"], [data-testid="stToolbar"],
#MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stHeader"], header[data-testid="stHeader"] {
    display: none !important;
    height: 0 !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    max-width: 1480px;
}

.cat-label, .chip-cat, .cpt-cat {
    color: var(--accent);
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.62rem;
    letter-spacing: 0.2em;
    font-weight: 500;
    text-transform: uppercase;
    margin: 0.8rem 0 0.5rem 0;
    padding: 0.35rem 0 0.35rem 0;
    border-bottom: 1px solid var(--ring-soft);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.cat-label::before, .cat-label::after,
.cpt-cat::before, .cpt-cat::after { content: none; }
.chip-cat, .cpt-cat.chip-cat {
    margin: 0.8rem 0 0.4rem 0;
    font-size: 0.58rem;
    letter-spacing: 0.22em;
}
.brand-ico {
    width: 12px;
    height: 12px;
    vertical-align: middle;
    margin-right: 0.35rem;
    display: inline-block;
    flex-shrink: 0;
}
.header-link-btn,
.header-link-btn:link,
.header-link-btn:visited {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: var(--bg-card);
    color: var(--fg-dim) !important;
    border: none;
    border-radius: 2px;
    padding: 0.4rem 0.7rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-weight: 500;
    font-size: 0.66rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: left;
    text-decoration: none !important;
    cursor: pointer;
    transition: box-shadow 0.12s, color 0.12s;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.header-link-btn:hover,
.header-link-btn:focus,
.header-link-btn:active {
    color: var(--accent) !important;
    text-decoration: none !important;
    outline: none;
    box-shadow: 0 0 0 1px var(--accent);
}
.header-link-btn * { text-decoration: none !important; }

/* Chip buttons (compact) */
[data-testid="stButton"] > button[kind="secondary"] {
    padding: 0.45rem 0.6rem;
    font-size: 0.72rem;
}
.stTextArea textarea {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif !important;
    font-size: 0.82rem !important;
    background: var(--bg-card) !important;
    color: var(--fg) !important;
    border: none !important;
    border-radius: 3px !important;
    line-height: 1.6 !important;
    padding: 0.75rem 0.9rem !important;
    box-shadow:
        0 0 0 1px var(--ring-mid),
        inset 0 1px 0 rgba(255, 255, 255, 0.5),
        0 2px 6px rgba(42, 40, 38, 0.05) !important;
    transition: box-shadow 0.15s ease !important;
}
.stTextArea textarea:hover {
    box-shadow:
        0 0 0 1px rgba(201, 100, 66, 0.40),
        0 4px 14px rgba(42, 40, 38, 0.08) !important;
}
.stTextArea textarea:focus {
    background: var(--bg-card) !important;
    box-shadow:
        0 0 0 1px var(--accent),
        0 0 0 4px rgba(201, 100, 66, 0.10),
        0 6px 18px rgba(42, 40, 38, 0.10) !important;
    outline: none !important;
}

.stButton > button, .stFormSubmitButton > button {
    background: var(--bg-card);
    color: var(--fg-dim);
    border: none;
    border-radius: 10px;
    padding: 0.6rem 0.9rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-weight: 500;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    transition: box-shadow 0.12s, color 0.12s, transform 0.12s;
    text-align: left;
    height: auto;
    white-space: normal;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    color: var(--accent);
    box-shadow: 0 0 0 1px var(--accent);
}
.stButton > button:active, .stFormSubmitButton > button:active {
    background: rgba(201, 100, 66, 0.1) !important;
    color: var(--accent) !important;
    box-shadow: 0 0 0 1px var(--accent) !important;
}
.stButton > button:disabled, .stFormSubmitButton > button:disabled {
    opacity: 0.35;
    color: var(--fg-mute);
    cursor: not-allowed;
}

.stTextInput > div > div > input {
    background: var(--bg-elev);
    color: var(--fg);
    border: none;
    border-radius: 3px;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.8rem;
    padding: 0.5rem 0.75rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.stTextInput > div > div > input:focus {
    box-shadow: 0 0 0 1px var(--accent);
    outline: none;
}
.stTextInput > div > div > input::placeholder { color: var(--fg-mute); }

pre, code, [data-testid="stCodeBlock"] {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif !important;
    font-size: 0.76rem !important;
    background: var(--bg-elev) !important;
    border: none !important;
    border-radius: 3px !important;
    color: var(--fg-dim) !important;
    line-height: 1.55 !important;
    box-shadow: 0 0 0 1px var(--ring-soft) !important;
}

hr {
    border: none !important;
    border-top: 1px solid var(--ring-soft) !important;
    margin: 0.9rem 0 !important;
}
hr.chapter {
    border: none !important;
    border-top: 1px solid var(--ring-soft) !important;
    height: 0 !important;
    background: none !important;
    margin: 1rem 0 !important;
    position: relative;
    overflow: visible;
}
hr.chapter::after { content: none; }

.hero-card {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.75rem 0.9rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
    min-height: 80px;
    position: relative;
    overflow: hidden;
}
.hero-card::before { content: none; }
.hero-card.running {
    box-shadow: 0 0 0 1px var(--accent);
    animation: hero-pulse 2.4s ease-in-out infinite;
}
.hero-card.running .hero-headline,
.hero-card.running .hero-label,
.hero-card.running .phase-line {
    color: #1a1a2e !important;
    opacity: 1 !important;
}
.hero-card.running .stream-output,
.hero-card.running pre.stream-output,
.hero-card.running pre.stream-output * {
    color: #000000 !important;
    opacity: 1 !important;
    -webkit-text-fill-color: #000000 !important;
    background: #ffffff !important;
    text-shadow: none !important;
    filter: none !important;
}
.hero-card.running .phase-line .phase-name {
    color: var(--accent) !important;
}
.hero-card.error {
    background: rgba(181, 51, 51, 0.05);
    box-shadow: 0 0 0 1px rgba(181, 51, 51, 0.55);
}
.hero-card.error .hero-label { color: var(--danger); }
.hero-card.error .hero-headline em { color: var(--danger); }
.error-detail {
    background: var(--bg-elev);
    border: none;
    border-radius: 2px;
    padding: 0.55rem 0.75rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.72rem;
    color: #e8b8b8;
    box-shadow: 0 0 0 1px rgba(181, 51, 51, 0.35);
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
    margin: 0.4rem 0;
    line-height: 1.5;
}
.error-hint {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.62rem;
    color: var(--fg-mute);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.skill-desc {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.62rem;
    color: var(--fg-mute);
    margin: -0.1rem 0 0.4rem 0.1rem;
    letter-spacing: 0.02em;
    line-height: 1.35;
    text-transform: uppercase;
}
@keyframes hero-pulse {
    0%, 100% { box-shadow: 0 0 0 1px var(--accent); }
    50%      { box-shadow: 0 0 0 1px var(--accent), 0 0 18px rgba(201, 100, 66, 0.28); }
}

.hero-label {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.62rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--fg-mute);
    margin-bottom: 0.3rem;
}
.hero-headline {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--fg);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    line-height: 1.2;
    margin: 0 0 0.3rem 0;
}
.hero-headline em { font-style: normal; color: var(--accent); }

.cursor-blink {
    display: inline-block;
    color: var(--accent);
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-weight: 400;
    margin-left: 0.35rem;
    line-height: 1;
    animation: cursor-blink 1.05s steps(2) infinite;
}
@keyframes cursor-blink {
    0%, 49%   { opacity: 1; }
    50%, 100% { opacity: 0; }
}

@keyframes pulse {
    0%, 100% { opacity: 0.4; }
    50%      { opacity: 1.0; }
}
.pulse-dot {
    width: 8px; height: 8px;
    background: var(--accent);
    border-radius: 50%;
    display: inline-block;
    margin-right: 0.5rem;
    vertical-align: middle;
    animation: pulse 1.1s ease-in-out infinite;
}
.pulse-dot.idle {
    background: var(--warn);
    animation: idle-pulse 2.8s ease-in-out infinite;
}
@keyframes idle-pulse {
    0%, 100% { opacity: 0.5; }
    50%      { opacity: 1; }
}
.pulse-dot.small { width: 6px; height: 6px; }

.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.7rem;
    background: transparent;
    border: none;
    border-radius: 2px;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.62rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--fg-dim);
    box-shadow: 0 0 0 1px var(--ring-soft);
    float: right;
    margin-top: 0.55rem;
}
.status-chip.running {
    color: var(--accent);
    background: rgba(201, 100, 66, 0.06);
    box-shadow: 0 0 0 1px var(--accent);
    animation: chip-pulse 2.4s ease-in-out infinite;
}
@keyframes chip-pulse {
    0%, 100% { box-shadow: 0 0 0 1px var(--accent); }
    50%      { box-shadow: 0 0 0 1px var(--accent), 0 0 10px rgba(201, 100, 66, 0.3); }
}

.activity-feed {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.6rem 0.8rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.74rem;
    color: var(--fg-dim);
    max-height: 500px;
    overflow-y: auto;
    line-height: 1.6;
}
.activity-feed h1, .activity-feed h2, .activity-feed h3 {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    color: var(--fg);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
.activity-feed p { margin: 0.2rem 0 !important; }
.activity-feed ul { padding-left: 1rem; }

.obsidian-link, .meta-link {
    display: inline-block;
    color: var(--accent);
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.66rem;
    text-decoration: none;
    padding: 0.25rem 0.55rem;
    margin: 0.2rem 0.3rem 0.1rem 0;
    border: none;
    border-radius: 2px;
    background: rgba(201, 100, 66, 0.05);
    box-shadow: 0 0 0 1px rgba(201, 100, 66, 0.3);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    transition: box-shadow 0.12s, background 0.12s;
}
.obsidian-link:hover, .meta-link:hover {
    background: rgba(201, 100, 66, 0.1);
    box-shadow: 0 0 0 1px var(--accent);
}
.meta-link {
    color: var(--fg-dim);
    background: transparent;
    box-shadow: 0 0 0 1px var(--ring-soft);
}

[data-testid="stForm"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(209, 207, 197, 0.12); border-radius: 0; }
::-webkit-scrollbar-thumb:hover { background: rgba(209, 207, 197, 0.22); }

.stream-output {
    background: var(--bg-elev);
    border: none;
    border-radius: 3px;
    padding: 0.7rem 0.9rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.72rem;
    color: var(--fg-dim);
    box-shadow: 0 0 0 1px var(--ring-soft);
    max-height: 340px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
    margin-top: 0.7rem;
    line-height: 1.6;
    letter-spacing: 0.005em;
}

/* Expander styling — used for SEO/AEO Pulse and other collapsible sections */
[data-testid="stExpander"] {
    background: var(--bg-card);
    border-radius: 4px;
    box-shadow: 0 0 0 1px var(--ring-soft);
    margin-bottom: 1rem;
    overflow: hidden;
}
[data-testid="stExpander"] details > summary {
    color: var(--fg) !important;
    background: rgba(33, 201, 232, 0.18) !important;   /* soft cyan */
    font-family: 'Outfit', system-ui, -apple-system, sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    padding: 0.55rem 0.85rem !important;
    border-radius: 4px 4px 0 0 !important;
}
[data-testid="stExpander"] details > summary:hover {
    background: rgba(33, 201, 232, 0.32) !important;
    color: var(--fg) !important;
}
[data-testid="stExpander"] details[open] > summary {
    border-radius: 4px 4px 0 0 !important;
    border-bottom: 1px solid rgba(33, 201, 232, 0.35) !important;
}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] *,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] {
    color: var(--fg) !important;
}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] h4 {
    color: var(--fg) !important;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    margin-top: 0.9rem !important;
    margin-bottom: 0.4rem !important;
}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] a {
    color: var(--accent) !important;
    text-decoration: underline;
}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] strong {
    color: var(--fg) !important;
    font-weight: 600;
}
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] li {
    color: var(--fg) !important;
    line-height: 1.6;
    font-size: 0.85rem;
    margin-bottom: 0.35rem;
}

/* Body-copy treatment for rendered markdown output (cockpit mono) */
.output-body + [data-testid="stMarkdownContainer"] p,
.output-body ~ [data-testid="stMarkdownContainer"] p,
.output-body + [data-testid="stMarkdownContainer"] *,
.output-body ~ [data-testid="stMarkdownContainer"] *,
.output-body + [data-testid="stMarkdownContainer"] td,
.output-body ~ [data-testid="stMarkdownContainer"] td,
.output-body + [data-testid="stMarkdownContainer"] th,
.output-body ~ [data-testid="stMarkdownContainer"] th {
    line-height: 1.55;
    font-size: 0.82rem;
    color: #1a1a2e !important;
    -webkit-text-fill-color: #1a1a2e !important;
    opacity: 1 !important;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
}

/* AGGRESSIVE override: force all rendered markdown text dark wherever it lives.
   Needed because Streamlit nests stMarkdownContainer deeper than the .output-body
   sibling selectors can reach. */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] td,
[data-testid="stMarkdownContainer"] th,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] strong,
[data-testid="stMarkdownContainer"] em,
[data-testid="stMarkdownContainer"] code,
[data-testid="stMarkdownContainer"] blockquote,
[data-testid="stMarkdownContainer"] ul,
[data-testid="stMarkdownContainer"] ol {
    color: #1a1a2e !important;
    -webkit-text-fill-color: #1a1a2e !important;
    opacity: 1 !important;
}
[data-testid="stMarkdownContainer"] a {
    color: #ec1e79 !important;
    -webkit-text-fill-color: #ec1e79 !important;
    opacity: 1 !important;
}
.output-body + [data-testid="stMarkdownContainer"] h1,
.output-body + [data-testid="stMarkdownContainer"] h2,
.output-body + [data-testid="stMarkdownContainer"] h3,
.output-body ~ [data-testid="stMarkdownContainer"] h1,
.output-body ~ [data-testid="stMarkdownContainer"] h2,
.output-body ~ [data-testid="stMarkdownContainer"] h3 {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: #1a1a2e !important;
    -webkit-text-fill-color: #1a1a2e !important;
    margin-top: 1rem;
    margin-bottom: 0.4rem;
}
.output-body + [data-testid="stMarkdownContainer"] li,
.output-body ~ [data-testid="stMarkdownContainer"] li {
    line-height: 1.5;
    margin-bottom: 0.25rem;
    color: #1a1a2e !important;
    -webkit-text-fill-color: #1a1a2e !important;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
}
.output-body + [data-testid="stMarkdownContainer"] a,
.output-body ~ [data-testid="stMarkdownContainer"] a {
    color: var(--accent) !important;
    -webkit-text-fill-color: var(--accent) !important;
}
.output-body + [data-testid="stMarkdownContainer"] blockquote,
.output-body ~ [data-testid="stMarkdownContainer"] blockquote {
    border-left: 2px solid var(--accent);
    padding-left: 0.8rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-style: normal;
    color: #1a1a2e !important;
    margin: 0.7rem 0;
}

.phase-line {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.68rem;
    color: var(--fg-dim);
    margin-top: 0.4rem;
    letter-spacing: 0.04em;
}
.phase-line .phase-name { color: var(--accent); }

.meta-row {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.66rem;
    color: var(--fg-mute);
    margin-top: 0.5rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.meta-row .meta-val { color: var(--fg-dim); }

/* Recent runs card wrapper */
.runs-card {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.55rem 0.75rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.runs-card .cat-label {
    margin: 0 0 0.35rem 0;
    padding: 0 0 0.35rem 0;
    border-bottom: 1px solid var(--ring-soft);
}
.run-list {
    display: flex;
    flex-direction: column;
    padding: 0;
    margin: 0;
}
.run-row {
    display: grid;
    grid-template-columns: 3.2rem 1fr auto;
    align-items: center;
    column-gap: 0.6rem;
    padding: 0.4rem 0.1rem;
    border-top: 1px solid var(--ring-soft);
    background: transparent;
}
.run-row:first-child { border-top: none; }
.run-row .run-time {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.62rem;
    color: var(--fg-mute);
    letter-spacing: 0.04em;
}
.run-row .run-label {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.76rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    color: var(--fg);
    line-height: 1.25;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.run-row:hover .run-label { color: var(--accent); }
.run-row a {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.6rem;
    color: var(--fg-mute);
    text-decoration: none;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    transition: color 0.12s;
}
.run-row a:hover { color: var(--accent); }

.approval-card {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.approval-card h4 {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.8rem;
    margin: 0 0 0.3rem 0;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.approval-card .approval-meta {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.64rem;
    color: var(--fg-mute);
    letter-spacing: 0.06em;
    margin-bottom: 0.4rem;
}

/* Danger button variant (cancel) */
.cancel-btn .stButton > button {
    background: rgba(181, 51, 51, 0.06) !important;
    box-shadow: 0 0 0 1px rgba(181, 51, 51, 0.35) !important;
    color: var(--danger) !important;
}
.cancel-btn .stButton > button:hover {
    background: rgba(181, 51, 51, 0.14) !important;
    box-shadow: 0 0 0 1px var(--danger) !important;
    color: #fff !important;
}

/* Quick-nav pill bar */
.quicknav {
    display: flex;
    gap: 0.35rem;
    flex-wrap: wrap;
    align-items: center;
    margin: 0 0 0.7rem 0;
}
.quicknav a {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.7rem;
    background: transparent;
    border: none;
    border-radius: 2px;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.66rem;
    font-weight: 500;
    color: var(--fg-dim);
    text-decoration: none;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    box-shadow: 0 0 0 1px var(--ring-soft);
    transition: box-shadow 0.12s, color 0.12s;
}
.quicknav a:hover {
    color: var(--accent);
    background: transparent;
    box-shadow: 0 0 0 1px var(--accent);
}
.quicknav a em, .quicknav .qn-icon {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-style: normal;
    font-weight: 500;
    color: var(--accent);
    font-size: 0.7rem;
    letter-spacing: 0.06em;
}

/* Claude code pill — terracotta-tinted + traveling-dot border pulse */
.quicknav a.qn-claude {
    position: relative;
    overflow: visible;
    padding: 0.4rem 0.85rem;
    color: var(--fg);
    box-shadow: 0 0 0 1px var(--accent), 0 0 0 3px rgba(201, 100, 66, 0.08);
    background: rgba(201, 100, 66, 0.04);
}
.quicknav a.qn-claude:hover {
    background: rgba(201, 100, 66, 0.09);
    box-shadow: 0 0 0 1px var(--accent), 0 0 12px rgba(201, 100, 66, 0.35);
}
.quicknav a.qn-claude .qn-arrow {
    color: var(--accent);
    margin-left: 0.15rem;
    font-size: 0.66rem;
    opacity: 0.85;
}
.quicknav a.qn-claude > span { position: relative; z-index: 1; }
.qn-pulse-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    overflow: visible;
    z-index: 0;
}

/* Status chip when embedded in quicknav — push to right edge */
.quicknav .qn-status {
    float: none !important;
    margin: 0 0 0 auto !important;
}

/* Metric tiles */
.metric-tile {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.55rem 0.75rem;
    min-height: 64px;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.metric-tile::before { content: none; }
.metric-label {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: var(--fg-mute);
    margin-bottom: 0.3rem;
}
.metric-value {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--fg);
    letter-spacing: 0.02em;
    line-height: 1.1;
}
.metric-value .unit {
    font-size: 0.72rem;
    color: var(--fg-mute);
    margin-left: 0.2rem;
}
.metric-value.highlight { color: var(--accent); }

/* MCP health strip */
.mcp-strip {
    display: flex;
    gap: 0.9rem;
    align-items: center;
    flex-wrap: wrap;
    margin: 0.4rem 0 0.8rem 0;
    padding: 0.45rem 0.75rem;
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.mcp-label {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: var(--accent);
    margin-right: 0.3rem;
    padding-right: 0.75rem;
    border-right: 1px solid var(--ring-soft);
}
.mcp-item {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.66rem;
    font-weight: 500;
    color: var(--fg-dim);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    transition: color 0.12s;
}
.mcp-item:hover { color: var(--accent); }
.mcp-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--fg-mute);
    flex-shrink: 0;
}
.mcp-dot.ready, .mcp-dot.connected {
    background: var(--accent);
    box-shadow: 0 0 4px rgba(201, 100, 66, 0.55);
}
.mcp-dot.needs_auth, .mcp-dot.needs-auth { background: var(--warn); }
.mcp-dot.failed, .mcp-dot.error { background: var(--danger); }
.mcp-dot.connecting {
    background: var(--fg-dim);
    animation: mcp-pulse 1.4s ease-in-out infinite;
}
@keyframes mcp-pulse {
    0%, 100% { opacity: 0.5; }
    50%      { opacity: 1; }
}

/* Chart container */
.chart-card, .cpt-chart-card {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.5rem 0.7rem 0.3rem;
    margin-bottom: 0.7rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
/* Parchment variant — stripped in cockpit (kept as no-op for compatibility) */
.chart-card.parchment {
    background: var(--bg-card);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    padding: 0.5rem 0.7rem 0.3rem;
    border-radius: 3px;
    box-shadow: 0 0 0 1px var(--ring-soft);
    margin: 0.3rem 0 0.7rem 0;
}
.chart-card.parchment .chart-title,
.chart-card.parchment .cpt-chart-title { color: var(--fg-dim); }
.chart-card.parchment .chart-title span,
.chart-card.parchment .cpt-chart-title span { color: var(--fg-mute) !important; }
.chart-card.mini-chart, .cpt-chart-card.mini-chart {
    padding: 0.4rem 0.6rem 0.25rem;
    border-radius: 3px;
    margin-top: 0.6rem;
}
.chart-title, .cpt-chart-title {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.66rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--fg-dim);
    margin-bottom: 0.3rem;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}
.chart-title em, .cpt-chart-title em {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-style: normal;
    font-weight: 500;
    color: var(--accent);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 0.66rem;
}
.chart-title span, .cpt-chart-title span {
    color: var(--fg-mute);
    font-size: 0.6rem;
    letter-spacing: 0.06em;
}

/* Inline SVG cumulative activity chart (replaces plotly) */
.activity-chart-wrap {
    position: relative;
    margin: 0.2rem 0 0.1rem;
    isolation: isolate;
}
.activity-chart-wrap::before {
    content: "";
    position: absolute;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    background-image:
        radial-gradient(ellipse 78% 62% at 50% 55%, rgba(201, 100, 66, 0.055) 0%, rgba(201, 100, 66, 0) 72%),
        linear-gradient(180deg, rgba(0, 0, 0, 0) 55%, rgba(0, 0, 0, 0.18) 100%),
        repeating-linear-gradient(90deg, transparent 0 59px, rgba(209, 207, 197, 0.05) 59px 60px),
        repeating-linear-gradient(0deg,  transparent 0 39px, rgba(209, 207, 197, 0.05) 39px 40px),
        repeating-linear-gradient(90deg, transparent 0 11px, rgba(209, 207, 197, 0.022) 11px 12px),
        repeating-linear-gradient(0deg,  transparent 0 7px,  rgba(209, 207, 197, 0.022) 7px 8px);
}
.activity-svg {
    display: block;
    width: 100%;
    height: 170px;
    overflow: visible;
    position: relative;
    z-index: 1;
}
.activity-axis {
    display: flex;
    justify-content: space-between;
    padding: 0.25rem 0.1rem 0.15rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.56rem;
    color: var(--fg-mute);
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

/* Gauge cards — htop-style hatched block bars */
.gauge-card, .cpt-gauge {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.55rem 0.75rem;
    min-height: 64px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 0 0 1px var(--ring-soft);
    transition: box-shadow 0.12s;
}
.gauge-card:hover, .cpt-gauge:hover { box-shadow: 0 0 0 1px var(--ring-mid); }
.gauge-card::before, .cpt-gauge::before { content: none; }
.gauge-header, .cpt-gauge-head {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-bottom: 0.28rem;
}
.gauge-label, .cpt-gauge-label { color: var(--fg-dim); }
.gauge-reset, .cpt-gauge-reset { color: var(--fg-mute); font-size: 0.56rem; letter-spacing: 0.08em; }
.gauge-track, .cpt-gauge-track {
    height: 10px;
    background: rgba(209, 207, 197, 0.08);
    border-radius: 0;
    overflow: hidden;
    margin-bottom: 0.35rem;
    position: relative;
}
.gauge-track::before, .cpt-gauge-track::before {
    content: "";
    position: absolute;
    inset: 0;
    background: repeating-linear-gradient(90deg, transparent 0 4px, var(--bg-card) 4px 5px);
    pointer-events: none;
    z-index: 2;
}
.gauge-fill, .cpt-gauge-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 0;
    transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: none;
}
.gauge-fill.warning, .cpt-gauge-fill.warning,
.cpt-gauge-fill.warn { background: var(--warn); box-shadow: none; }
.gauge-fill.danger, .cpt-gauge-fill.danger  { background: var(--danger); box-shadow: none; }
.gauge-stats, .cpt-gauge-stats {
    display: flex;
    align-items: baseline;
    gap: 0.3rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.9rem;
    letter-spacing: 0.02em;
    color: var(--fg);
}
.gauge-max, .cpt-gauge-max {
    font-size: 0.7rem;
    color: var(--fg-mute);
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
}
.gauge-sub, .cpt-gauge-sub {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.6rem;
    color: var(--fg-mute);
    margin-left: auto;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.gauge-delta, .cpt-gauge-delta {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.58rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-left: auto;
    padding: 0.1rem 0.45rem;
    border-radius: 2px;
    border: none;
    color: var(--fg-mute);
    background: transparent;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.gauge-delta.up, .cpt-gauge-delta.up         { color: var(--accent); box-shadow: 0 0 0 1px rgba(201, 100, 66, 0.40); background: rgba(201, 100, 66, 0.06); }
.gauge-delta.down, .cpt-gauge-delta.down     { color: var(--fg-dim); box-shadow: 0 0 0 1px var(--ring-soft); background: transparent; }
.gauge-delta.neutral, .cpt-gauge-delta.neutral { color: var(--fg-mute); }

/* ─── Cockpit forecast card ─── */
.cpt-forecast {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.6rem 0.8rem;
    margin-top: 0.6rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.cpt-forecast-head {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.78rem;
    color: var(--fg);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.25rem;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
}
.cpt-forecast-head em { font-style: normal; color: var(--accent); }
.cpt-forecast-sub {
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.58rem;
    color: var(--fg-mute);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.cpt-forecast-track {
    height: 18px;
    background: rgba(209, 207, 197, 0.06);
    box-shadow: inset 0 0 0 1px var(--ring-soft);
    position: relative;
    margin: 0.5rem 0 0.3rem;
}
.cpt-forecast-elapsed {
    position: absolute;
    left: 0; top: 0; bottom: 0;
    background: rgba(201, 100, 66, 0.35);
    border-right: 1px solid var(--accent);
}
.cpt-forecast-proj {
    position: absolute;
    top: 0; bottom: 0;
    background: repeating-linear-gradient(45deg,
        rgba(201, 100, 66, 0.12) 0 5px,
        rgba(201, 100, 66, 0.28) 5px 10px);
    border-right: 1px dashed var(--accent);
}
.cpt-forecast-now {
    position: absolute;
    top: -2px; bottom: -2px;
    width: 2px;
    background: var(--fg);
}
.cpt-forecast-legend {
    display: flex;
    gap: 0.9rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.56rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--fg-mute);
    margin-top: 0.3rem;
    flex-wrap: wrap;
}

/* Scheduled-routine rows under forecast */
.cpt-sched {
    margin-top: 0.7rem;
    padding-top: 0.55rem;
    border-top: 1px solid var(--ring-soft);
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}
.cpt-sched-row {
    display: grid;
    grid-template-columns: 3.2rem 1fr auto;
    align-items: baseline;
    column-gap: 0.6rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    font-size: 0.66rem;
    letter-spacing: 0.04em;
}
.cpt-sched-time {
    color: var(--accent);
    font-weight: 500;
}
.cpt-sched-label {
    color: var(--fg);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cpt-sched-in {
    color: var(--fg-mute);
    font-size: 0.58rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.cpt-forecast-legend em { font-style: normal; color: var(--fg-dim); }

/* ─── Cockpit vault pulse ─── */
.cpt-pulse-card {
    background: var(--bg-card);
    border: none;
    border-radius: 3px;
    padding: 0.55rem 0.75rem;
    margin-top: 0.6rem;
    box-shadow: 0 0 0 1px var(--ring-soft);
}
.cpt-pulse-card > .cpt-cat {
    margin: 0 0 0.35rem 0;
    padding-top: 0;
}
.cpt-pulse {
    display: grid;
    grid-template-columns: 4.6rem 1fr auto;
    gap: 0.5rem;
    align-items: center;
    padding: 0.35rem 0.1rem;
    border-top: 1px solid var(--ring-soft);
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
}
.cpt-pulse:first-of-type { border-top: none; }
.cpt-pulse-main { min-width: 0; }
.cpt-verb {
    font-size: 0.56rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0.12rem 0.4rem;
    border-radius: 2px;
    text-align: center;
    box-shadow: 0 0 0 1px var(--ring-soft);
    color: var(--fg-dim);
    font-weight: 500;
    display: inline-block;
}
.cpt-verb.created {
    color: var(--accent);
    box-shadow: 0 0 0 1px rgba(201, 100, 66, 0.35);
    background: rgba(201, 100, 66, 0.08);
}
.cpt-verb.appended {
    color: var(--warn);
    box-shadow: 0 0 0 1px rgba(217, 165, 102, 0.35);
    background: rgba(217, 165, 102, 0.06);
}
.cpt-verb.updated { color: var(--fg-dim); }
.cpt-verb.linked {
    color: var(--good);
    box-shadow: 0 0 0 1px rgba(143, 185, 122, 0.35);
    background: rgba(143, 185, 122, 0.06);
}
.cpt-pulse-name {
    color: var(--fg);
    font-size: 0.74rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    letter-spacing: 0.02em;
}
.cpt-pulse-dir {
    color: var(--fg-mute);
    font-size: 0.56rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cpt-pulse-ago {
    color: var(--fg-mute);
    font-size: 0.58rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

/* ─── Header bar — wraps the col row via :has() + hidden marker ─── */
[data-testid="stVerticalBlock"]:has(> div > .cpt-header-marker),
[data-testid="stHorizontalBlock"]:has(.cpt-header-marker) {
    padding: 0.3rem 0.7rem !important;
    box-shadow: 0 0 0 1px var(--ring-soft);
    border-radius: 3px;
    background: var(--bg-card);
    margin-bottom: 0.7rem !important;
    align-items: center;
}
.cpt-header-marker { display: none; }

/* ─── Skill chips (anchor-based, 4-column grid) ─── */
.cpt-skill-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.55rem;
    margin: 0 0 0.7rem 0;
}
@media (max-width: 1100px) {
    .cpt-skill-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 800px) {
    .cpt-skill-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.cpt-skill {
    background: var(--bg-card);
    box-shadow: 0 0 0 1px var(--ring-soft);
    border-radius: 10px;
    padding: 0.7rem 0.85rem;
    min-height: 4.6rem;
    font-family: 'Outfit', system-ui, -apple-system, sans-serif;
    text-align: left;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    transition: box-shadow 0.14s, transform 0.14s, color 0.14s;
    text-decoration: none !important;
    color: inherit;
    min-width: 0;
}
.cpt-skill:hover {
    box-shadow: 0 0 0 1.5px var(--accent);
    transform: translateY(-1px);
    text-decoration: none !important;
}
.cpt-skill.loaded { box-shadow: 0 0 0 1.5px var(--accent); }
.cpt-skill-name {
    color: var(--fg);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cpt-skill:hover .cpt-skill-name { color: var(--accent); }
.cpt-skill-desc {
    color: var(--fg-dim);
    font-size: 0.72rem;
    letter-spacing: 0.01em;
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: normal;
}

/* Reveal body after PREMIUM_CSS parses — overrides pre-hide from earlier inline style. */
body { opacity: 1; transition: opacity 0.18s ease-out; }
</style>
"""

# ═══════════════════════════════════════════════════════════
# BOOT ANIMATION CSS — injected only on first render of a session.
# Prevents animations replaying on every Streamlit rerun (button clicks etc).
# ═══════════════════════════════════════════════════════════
BOOT_ANIMATION_CSS = """
<style>
@keyframes boot-rise {
    0%   { opacity: 0; transform: translateY(28px) scale(0.96); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes boot-slide-l {
    0%   { opacity: 0; transform: translateX(-40px); }
    100% { opacity: 1; transform: translateX(0); }
}
@keyframes boot-slide-r {
    0%   { opacity: 0; transform: translateX(40px); }
    100% { opacity: 1; transform: translateX(0); }
}
.title-row {
    animation: boot-rise 0.75s cubic-bezier(0.22, 1, 0.36, 1) 0s both;
}
.quicknav {
    animation: boot-rise 0.75s cubic-bezier(0.22, 1, 0.36, 1) 0.18s both;
}
[data-testid="stColumn"]:nth-of-type(1) .gauge-card,
[data-testid="column"]:nth-of-type(1) .gauge-card {
    animation: boot-slide-l 1.45s cubic-bezier(0.22, 1, 0.36, 1) 0.55s both;
}
[data-testid="stColumn"]:nth-of-type(2) .gauge-card,
[data-testid="column"]:nth-of-type(2) .gauge-card {
    animation: boot-rise 1.45s cubic-bezier(0.22, 1, 0.36, 1) 0.80s both;
}
[data-testid="stColumn"]:nth-of-type(3) .gauge-card,
[data-testid="column"]:nth-of-type(3) .gauge-card {
    animation: boot-slide-r 1.45s cubic-bezier(0.22, 1, 0.36, 1) 0.55s both;
}
.chart-card {
    animation: boot-rise 0.85s cubic-bezier(0.22, 1, 0.36, 1) 0.55s both;
}
.mcp-strip {
    animation: boot-rise 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.95s both;
}
</style>
"""

# Hide body + Streamlit chrome immediately — PREMIUM_CSS reveals body via fade once parsed.
# Kills the brief flash of unstyled cards + Deploy button before CSS attaches.
st.markdown(
    "<style>"
    "body{opacity:0}"
    '[data-testid="stToolbar"],[data-testid="stStatusWidget"],[data-testid="stHeader"],'
    '[data-testid="stDecoration"],#MainMenu,footer,header{display:none!important;height:0!important}'
    "</style>",
    unsafe_allow_html=True,
)
st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

# Boot animations only on fresh page mount — not on every Streamlit rerun (button clicks).
# Session state persists per tab; fresh Ctrl+R creates a new session → animation replays.
if not st.session_state.get("_boot_animated"):
    st.session_state._boot_animated = True
    st.markdown(BOOT_ANIMATION_CSS, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════


def html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@st.cache_resource
def _asset_data_url(filename: str) -> str:
    p = Path(__file__).parent / "assets" / filename
    if not p.exists():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


MASCOT_IDLE_URL = _asset_data_url("robot-idle-normalized.png")
MASCOT_RUN_URL = _asset_data_url("robot-run-normalized.png")
# 7 frames per row, 12×32 px each → sheet is 84×32 native.
MASCOT_FRAMES = 7
MASCOT_FRAME_W = 12
MASCOT_FRAME_H = 32
MASCOT_SCALE = 3  # rendered at 36×96 px (scaled 3×)


PHASE_LABELS = {
    "Read": "reading file",
    "Write": "writing file",
    "Edit": "editing file",
    "MultiEdit": "editing file",
    "Bash": "running command",
    "Glob": "finding files",
    "Grep": "searching code",
    "Task": "delegating subagent",
    "Agent": "spawning agent",
    "TodoWrite": "tracking tasks",
    "WebFetch": "fetching page",
    "WebSearch": "searching web",
    "NotebookEdit": "editing notebook",
    "Skill": "invoking skill",
    "ToolSearch": "searching tools",
    "EnterPlanMode": "entering plan mode",
    "ExitPlanMode": "exiting plan mode",
    "EnterWorktree": "entering worktree",
    "ExitWorktree": "exiting worktree",
    "ScheduleWakeup": "scheduling wakeup",
    "SendMessage": "sending message",
    "TaskCreate": "creating task",
    "TaskUpdate": "updating task",
    "TaskGet": "reading task",
    "TaskList": "listing tasks",
    "TaskStop": "stopping task",
    "TaskOutput": "reading task output",
    "AskUserQuestion": "asking question",
    "PushNotification": "sending notification",
    "RemoteTrigger": "triggering remote",
    "Monitor": "monitoring process",
    "CronCreate": "creating schedule",
    "CronDelete": "deleting schedule",
    "CronList": "listing schedules",
    "TeamCreate": "creating team",
    "TeamDelete": "deleting team",
}


def pretty_phase(name: str) -> str:
    if not name:
        return "starting"
    if name in PHASE_LABELS:
        return PHASE_LABELS[name]
    if name.startswith("mcp__"):
        parts = name.split("__")
        if len(parts) >= 3:
            service = parts[1].replace("_", " ")
            action = "__".join(parts[2:]).replace("_", " ")
            return f"{service} · {action}"
    # CamelCase → spaced, lowercase
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", name).lower()
    return spaced or name


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return s or "run"


def today_daily_note() -> Path:
    return DAILY_NOTES_DIR / f"{date.today().isoformat()}.md"


def read_activity() -> str:
    note = today_daily_note()
    if not note.exists():
        return "_No activity yet today._"
    return note.read_text(encoding="utf-8", errors="replace")


def log_run(label: str, ok: bool):
    note = today_daily_note()
    note.parent.mkdir(parents=True, exist_ok=True)
    if not note.exists():
        note.write_text(f"# {date.today().isoformat()}\n\n## Runs\n\n", encoding="utf-8")
    status = "OK" if ok else "ERR"
    stamp = datetime.now().strftime("%H:%M")
    with note.open("a", encoding="utf-8") as f:
        f.write(f"- {stamp} [{status}] {label}\n")


def save_run_output(label: str, prompt: str, output: str, meta: dict | None = None) -> Path:
    today_str = date.today().isoformat()
    now = datetime.now().strftime("%H-%M")
    day_dir = RUNS_DIR / today_str
    day_dir.mkdir(parents=True, exist_ok=True)
    path = day_dir / f"{now}-{slugify(label)}.md"
    meta_block = ""
    if meta:
        for k, v in meta.items():
            if v is not None:
                meta_block += f"{k}: {v}\n"
    body = (
        f"---\nskill: {label}\ntime: {datetime.now().isoformat(timespec='seconds')}\n"
        f"{meta_block}---\n\n"
        f"**Prompt**\n\n```\n{prompt}\n```\n\n"
        f"**Output**\n\n{output}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def obsidian_uri(vault_path: Path) -> str:
    rel = vault_path.relative_to(VAULT_PATH).as_posix()
    return f"obsidian://open?vault={quote(VAULT_NAME)}&file={quote(rel)}"


def open_claude_terminal() -> None:
    wt = Path(r"C:\Users\Chase\AppData\Local\Microsoft\WindowsApps\wt.exe")
    if wt.exists():
        subprocess.Popen(
            [str(wt), "-d", str(VAULT_PATH), str(CLAUDE_CLI)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        subprocess.Popen(
            ["cmd.exe", "/k", f'cd /d "{VAULT_PATH}" && "{CLAUDE_CLI}"'],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )


def list_recent_runs(limit: int = 10):
    if not RUNS_DIR.exists():
        return []
    files = sorted(RUNS_DIR.glob("*/*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def list_runs_last_n_days(days: int = 7):
    """Return all run markdown files modified in the last `days` days, newest first."""
    if not RUNS_DIR.exists():
        return []
    cutoff = time.time() - (days * 86400)
    files = []
    for p in RUNS_DIR.glob("*/*.md"):
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if mtime >= cutoff:
            files.append((p, mtime))
    files.sort(key=lambda t: t[1], reverse=True)
    return [p for p, _ in files]


def parse_run_file(path: Path) -> dict:
    """Parse a saved run file. Returns {skill, time, output, prompt_short, meta}."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"skill": path.stem, "output": "(unreadable)", "time": None, "prompt_short": "", "meta": {}}
    # Strip frontmatter
    skill = path.stem
    when = None
    meta: dict = {}
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end > 0:
            fm = text[4:end]
            body = text[end + 5:]
            for line in fm.splitlines():
                if ": " in line:
                    k, v = line.split(": ", 1)
                    meta[k.strip()] = v.strip()
            skill = meta.get("skill", skill)
            when = meta.get("time")
    # Split prompt and output sections
    prompt_short = ""
    output = body.strip()
    if "**Output**" in body:
        prompt_part, _, output_part = body.partition("**Output**")
        output = output_part.strip()
        if "**Prompt**" in prompt_part:
            _, _, prompt_body = prompt_part.partition("**Prompt**")
            prompt_short = prompt_body.strip().lstrip("`").strip()[:200]
    return {"skill": skill, "time": when, "output": output, "prompt_short": prompt_short, "meta": meta}


def list_awaiting_approvals():
    if not DRAFTS_AWAITING.exists():
        return []
    return sorted(DRAFTS_AWAITING.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def list_vault_pulse(limit: int = 6):
    """Recent vault .md changes, sorted by mtime desc. Verb inferred from mtime-vs-ctime delta."""
    if not VAULT_PATH.exists():
        return []
    skip_parts = {".obsidian", ".trash", "node_modules", ".git"}
    files = []
    for p in VAULT_PATH.rglob("*.md"):
        if any(part in skip_parts for part in p.parts):
            continue
        try:
            st_ = p.stat()
        except OSError:
            continue
        files.append((p, st_))
    files.sort(key=lambda t: t[1].st_mtime, reverse=True)
    files = files[:limit]

    now = time.time()
    out = []
    for p, st_ in files:
        age = now - st_.st_mtime
        # verb inference: created if mtime ~= ctime (within 2 min),
        # linked if file contains wiki-links and was touched recently,
        # appended if touched in last 10 min, else updated.
        created_delta = abs(st_.st_mtime - st_.st_ctime)
        has_wikilink = False
        if age < 900:
            try:
                has_wikilink = "[[" in p.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                pass
        if created_delta < 120:
            verb = "created"
        elif has_wikilink and age < 300:
            verb = "linked"
        elif age < 600:
            verb = "appended"
        else:
            verb = "updated"
        try:
            rel = p.relative_to(VAULT_PATH).as_posix()
        except ValueError:
            rel = p.name
        directory = str(Path(rel).parent).replace("\\", "/")
        if directory == ".":
            directory = "vault"
        out.append({
            "verb": verb,
            "name": p.stem,
            "dir": directory,
            "age_sec": int(age),
            "path": p,
        })
    return out


def fmt_ago(sec: int) -> str:
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}m"
    if sec < 86400:
        return f"{sec // 3600}h"
    return f"{sec // 86400}d"


# ─── Metrics / chart data / MCP cache ───

CACHE_DIR = Path(__file__).parent / ".cache"
MCP_CACHE = CACHE_DIR / "mcp.json"
RATE_CACHE = CACHE_DIR / "rate_limits.json"

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")[:2500]
    meta = {"file": path.name, "path": str(path)}
    m = _FRONTMATTER_RE.match(text)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
    return meta


def scan_runs(days: int = 30) -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    cutoff = date.today() - timedelta(days=days)
    out = []
    for day_dir in RUNS_DIR.iterdir():
        if not day_dir.is_dir():
            continue
        try:
            d = date.fromisoformat(day_dir.name)
        except ValueError:
            continue
        if d < cutoff:
            continue
        for f in day_dir.glob("*.md"):
            meta = _parse_frontmatter(f)
            meta["date"] = d.isoformat()
            out.append(meta)
    return out


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def calc_metrics() -> dict:
    runs = scan_runs(30)
    today_str = date.today().isoformat()
    month_str = date.today().strftime("%Y-%m")
    runs_today = sum(1 for r in runs if r.get("date") == today_str)
    cost_month = sum(
        _to_float(r.get("cost_usd"))
        for r in runs if (r.get("date") or "").startswith(month_str)
    )
    tokens_30d = sum(
        _to_int(r.get("tokens_in")) + _to_int(r.get("tokens_out"))
        for r in runs
    )
    approvals = len(list_awaiting_approvals())
    return {
        "runs_today": runs_today,
        "cost_month": cost_month,
        "tokens_30d": tokens_30d,
        "approvals": approvals,
    }


def runs_per_day(days: int = 14) -> pd.DataFrame:
    today = date.today()
    counts = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    for r in scan_runs(days):
        if r.get("date") in counts:
            counts[r["date"]] += 1
    df = pd.DataFrame([{"date": k, "runs": v} for k, v in counts.items()])
    df["date"] = pd.to_datetime(df["date"])
    return df


def tokens_per_day(days: int = 14) -> pd.DataFrame:
    today = date.today()
    buckets = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    for m in _read_session_metas():
        t = _parse_session_time(m)
        if t is None:
            continue
        k = t.date().isoformat()
        if k in buckets:
            buckets[k] += int(m.get("input_tokens") or 0) + int(m.get("output_tokens") or 0)
    df = pd.DataFrame([{"date": k, "tokens": v} for k, v in buckets.items()])
    df["date"] = pd.to_datetime(df["date"])
    return df


def compute_delta(current: float, prior: float, threshold_pct: float = 5.0) -> tuple[str, float, str]:
    if prior <= 0 and current <= 0:
        return ("·", 0.0, "neutral")
    if prior <= 0:
        return ("▲", 100.0, "up")
    pct = (current - prior) / prior * 100.0
    if abs(pct) < threshold_pct:
        return ("·", pct, "neutral")
    return (("▲", pct, "up") if pct > 0 else ("▼", pct, "down"))


def activity_cumulative(days: int = 30, backfill_demo: bool = True) -> pd.DataFrame:
    """Daily count of (scan_runs + routines ledger) → cumulative sum.

    backfill_demo seeds synthetic activity on empty early days so the cumulative
    curve ramps smoothly instead of flatlining at 0 until recent spike.
    """
    import random
    today = date.today()
    per_day = {(today - timedelta(days=i)).isoformat(): 0 for i in range(days - 1, -1, -1)}
    for r in scan_runs(days):
        d = r.get("date")
        if d in per_day:
            per_day[d] += 1
    ledger = _load_routines_ledger()
    for d in per_day:
        per_day[d] += int(ledger.get(d, 0))

    if backfill_demo:
        keys = list(per_day.keys())
        n = len(keys)
        rng = random.Random(0xA6E8)
        for i, k in enumerate(keys):
            if per_day[k] == 0 and i < n - 3:
                t = i / max(1, n - 1)
                base = 1.8 + t * 6.0
                jitter = rng.uniform(-1.2, 1.6)
                per_day[k] = max(1, int(round(base + jitter)))

    df = pd.DataFrame(
        [{"date": k, "day_count": v} for k, v in per_day.items()]
    )
    df["date"] = pd.to_datetime(df["date"])
    df["cumulative"] = df["day_count"].cumsum()
    return df


def delta_window(metas: list[dict], cur_start: datetime, cur_end: datetime,
                 pri_start: datetime, pri_end: datetime) -> tuple[int, int]:
    cur = pri = 0
    for m in metas:
        t = _parse_session_time(m)
        if t is None:
            continue
        tot = int(m.get("input_tokens") or 0) + int(m.get("output_tokens") or 0)
        if cur_start <= t < cur_end:
            cur += tot
        elif pri_start <= t < pri_end:
            pri += tot
    return cur, pri


def save_mcp_state(servers: list):
    CACHE_DIR.mkdir(exist_ok=True)
    try:
        MCP_CACHE.write_text(json.dumps(servers), encoding="utf-8")
    except Exception:
        pass


def load_mcp_state() -> list:
    if MCP_CACHE.exists():
        try:
            return json.loads(MCP_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_rate_limit(event: dict):
    """Persist latest rate_limit_info keyed by rateLimitType."""
    CACHE_DIR.mkdir(exist_ok=True)
    info = event.get("rate_limit_info") or {}
    kind = info.get("rateLimitType")
    if not kind:
        return
    data = load_rate_limits()
    data[kind] = {
        "status": info.get("status"),
        "resets_at": info.get("resetsAt"),
        "overage_status": info.get("overageStatus"),
        "overage_resets_at": info.get("overageResetsAt"),
        "is_using_overage": info.get("isUsingOverage"),
        "captured_at": int(time.time()),
    }
    try:
        RATE_CACHE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def load_rate_limits() -> dict:
    if RATE_CACHE.exists():
        try:
            return json.loads(RATE_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def fmt_time_until(ts: int) -> str:
    if not ts:
        return "—"
    delta = int(ts - time.time())
    if delta <= 0:
        return "now"
    h = delta // 3600
    m = (delta % 3600) // 60
    if h > 24:
        d = h // 24
        h = h % 24
        return f"{d}d {h}h"
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m}m"


def _read_session_metas() -> list[dict]:
    """Read all Claude Code per-session usage meta files."""
    if not SESSION_META_DIR.exists():
        return []
    out = []
    for f in SESSION_META_DIR.glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            if "start_time" in d and ("input_tokens" in d or "output_tokens" in d):
                out.append(d)
        except Exception:
            continue
    return out


def _parse_session_time(d: dict) -> datetime | None:
    t = d.get("start_time")
    if not t:
        return None
    try:
        if t.endswith("Z"):
            t = t.replace("Z", "+00:00")
        dt = datetime.fromisoformat(t)
        return dt.replace(tzinfo=None)  # naive local
    except Exception:
        return None


def calc_usage_windows() -> dict:
    """Aggregate Claude Code session token usage across 5h, 7d, today windows."""
    now = datetime.now()
    five_h_ago = now - timedelta(hours=5)
    seven_d_ago = now - timedelta(days=7)
    today_start = datetime.combine(date.today(), datetime.min.time())

    metas = _read_session_metas()

    def agg(metas_list, since):
        in_tok = out_tok = sessions = 0
        for m in metas_list:
            t = _parse_session_time(m)
            if t is None or t < since:
                continue
            in_tok += int(m.get("input_tokens") or 0)
            out_tok += int(m.get("output_tokens") or 0)
            sessions += 1
        return {"input": in_tok, "output": out_tok, "total": in_tok + out_tok, "sessions": sessions}

    # Local dashboard button runs (manual)
    runs_today = [r for r in scan_runs(2) if r.get("date") == date.today().isoformat()]
    cost_today = sum(_to_float(r.get("cost_usd")) for r in runs_today)

    # Routine runs today — cloud routines, tracked via local ledger
    routine_count = count_routines_today()

    return {
        "five_hour": agg(metas, five_h_ago),
        "weekly": agg(metas, seven_d_ago),
        "today": {
            **agg(metas, today_start),
            "routines": routine_count,
            "cost": cost_today,
            "runs": len(runs_today),
        },
    }


# ─── Routine run ledger ───
ROUTINES_LEDGER = CACHE_DIR / "routines.json"


def _load_routines_ledger() -> dict:
    if ROUTINES_LEDGER.exists():
        try:
            return json.loads(ROUTINES_LEDGER.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_routines_ledger(data: dict):
    CACHE_DIR.mkdir(exist_ok=True)
    ROUTINES_LEDGER.write_text(json.dumps(data), encoding="utf-8")


def count_routines_today() -> int:
    today_str = date.today().isoformat()
    return int(_load_routines_ledger().get(today_str, 0))


def increment_routine_count():
    today_str = date.today().isoformat()
    data = _load_routines_ledger()
    data[today_str] = int(data.get(today_str, 0)) + 1
    _save_routines_ledger(data)


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def fmt_cost(c: float) -> str:
    if c >= 100:
        return f"${c:.0f}"
    if c >= 10:
        return f"${c:.1f}"
    return f"${c:.2f}"


# ═══════════════════════════════════════════════════════════
# BACKGROUND RUNNER — parses stream-json events from claude CLI
# ═══════════════════════════════════════════════════════════


def _parse_event(evt: dict):
    """Mutate RT based on one stream-json event."""
    t = evt.get("type")
    if t == "assistant":
        msg = evt.get("message", {})
        for block in msg.get("content", []):
            btype = block.get("type")
            if btype == "text":
                RT["text"] += block.get("text", "")
            elif btype == "tool_use":
                name = block.get("name", "tool")
                RT["phases"].append(name)
                RT["current_phase"] = name
    elif t == "user":
        # tool results; don't need full content
        pass
    elif t == "result":
        RT["cost_usd"] = evt.get("total_cost_usd") or evt.get("cost_usd")
        usage = evt.get("usage", {})
        RT["tokens_in"] = usage.get("input_tokens")
        RT["tokens_out"] = usage.get("output_tokens")
        if evt.get("subtype") != "success":
            RT["error"] = evt.get("result") or evt.get("subtype")
    elif t == "system":
        sub = evt.get("subtype")
        if sub == "init":
            RT["current_phase"] = "initializing"
            servers = evt.get("mcp_servers")
            if servers:
                save_mcp_state(servers)
    elif t == "rate_limit_event":
        save_rate_limit(evt)


def _run_skill_bg(prompt: str):
    """Subprocess runner (runs in background thread). Populates RT."""
    try:
        proc = subprocess.Popen(
            [
                str(CLAUDE_CLI),
                "-p",
                prompt,
                "--permission-mode",
                PERMISSION_MODE,
                "--output-format",
                "stream-json",
                "--verbose",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(VAULT_PATH),
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
        RT["proc"] = proc

        for line in iter(proc.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            RT["buffer"].append(line)
            try:
                evt = json.loads(line)
                _parse_event(evt)
            except json.JSONDecodeError:
                # plaintext line (maybe error before JSON starts)
                RT["text"] += line + "\n"

        proc.wait(timeout=RUN_TIMEOUT_SEC)
        if proc.returncode != 0 and not RT.get("error"):
            stderr_text = proc.stderr.read() if proc.stderr else ""
            RT["error"] = f"exit {proc.returncode}: {stderr_text[:500]}"
    except Exception as e:
        RT["error"] = str(e)
    finally:
        RT["done"] = True
        RT["proc"] = None


def start_skill_run(label: str, prompt: str):
    reset_runtime()
    RT["start_time"] = time.time()
    thread = threading.Thread(target=_run_skill_bg, args=(prompt,), daemon=True)
    thread.start()
    st.session_state.running = True
    st.session_state.active_skill = label
    st.session_state.active_prompt = prompt
    st.session_state.last_error = None


def cancel_current_run():
    proc = RT.get("proc")
    if proc:
        try:
            proc.terminate()
            time.sleep(0.2)
            if proc.poll() is None:
                proc.kill()
        except Exception:
            pass
    RT["cancelled"] = True
    RT["error"] = "cancelled by user"
    RT["done"] = True


def finalize_run_if_done(label: str, prompt: str):
    """Called when RT['done']==True. Persists output, resets session state."""
    if RT.get("cancelled"):
        st.session_state.last_output = "(cancelled)"
        st.session_state.last_saved_path = None
        st.session_state.last_error = None
    elif RT.get("error"):
        st.session_state.last_error = str(RT["error"])
        st.session_state.last_output = RT.get("text", "").strip()
        st.session_state.last_saved_path = None
        log_run(label, ok=False)
    else:
        output = RT.get("text", "").strip() or "(no text output)"
        st.session_state.last_output = output
        meta = {
            "cost_usd": RT.get("cost_usd"),
            "tokens_in": RT.get("tokens_in"),
            "tokens_out": RT.get("tokens_out"),
            "phases": ", ".join(RT.get("phases", [])) or None,
        }
        saved = save_run_output(label, prompt, output, meta=meta)
        st.session_state.last_saved_path = str(saved)
        st.session_state.last_cost = RT.get("cost_usd")
        st.session_state.last_tokens = (RT.get("tokens_in"), RT.get("tokens_out"))
        log_run(label, ok=True)

    st.session_state.running = False
    st.session_state.active_skill = None


# ═══════════════════════════════════════════════════════════
# FIRST-RUN WIZARD
# ═══════════════════════════════════════════════════════════

if not VAULT_PATH.exists():
    st.markdown('<h1 class="hero-title">Hailey\'s <em>Hub</em></h1>', unsafe_allow_html=True)
    st.error(f"Vault not found: `{VAULT_PATH}`")
    st.markdown(
        "**Setup required.** Edit `config.py` and set:\n\n"
        "- `VAULT_PATH` → your Obsidian vault directory\n"
        "- `VAULT_NAME` → vault name as Obsidian shows it\n"
        "- `CLAUDE_CLI` → path to `claude.exe`\n\n"
        "Then reload this page."
    )
    st.stop()

if not CLAUDE_CLI.exists():
    st.error(f"Claude CLI not found at `{CLAUDE_CLI}`. Check config.py.")
    st.stop()


# ═══════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════

defaults = {
    "running": False,
    "last_output": "",
    "last_label": "",
    "last_saved_path": None,
    "last_prompt": None,
    "last_cost": None,
    "last_tokens": None,
    "last_error": None,
    "active_skill": None,
    "active_prompt": None,
    "skill_search": "",
    "output_view_md": True,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ═══════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════

st.markdown('<div class="cpt-header-marker"></div>', unsafe_allow_html=True)

# Terminal launch via query-param (claude code pill in quicknav)
_action_q = st.query_params.get("action")
if _action_q == "terminal":
    try:
        open_claude_terminal()
        st.toast("Terminal opened at vault.", icon="✅")
    except Exception as e:
        st.toast(f"Failed: {e}", icon="⚠️")
    # Preserve brand when clearing the action param
    _saved_brand = st.query_params.get("brand")
    st.query_params.clear()
    if _saved_brand:
        st.query_params["brand"] = _saved_brand

# ─── STAR WARS TRIO (left of title) ───

# Yoda — green sage with pointy ears
_yoda_svg = (
    '<svg class="tree-mascot" viewBox="0 0 18 28" '
    'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
    # ears
    '<rect x="2" y="2" width="2" height="4" fill="#7ec850"/>'
    '<rect x="14" y="2" width="2" height="4" fill="#7ec850"/>'
    # head
    '<rect x="4" y="4" width="10" height="2" fill="#a4e635"/>'
    '<rect x="2" y="6" width="14" height="6" fill="#a4e635"/>'
    '<rect x="4" y="12" width="10" height="2" fill="#a4e635"/>'
    # highlights
    '<rect x="4" y="4" width="2" height="2" fill="#c8ff5e"/>'
    '<rect x="2" y="6" width="2" height="2" fill="#c8ff5e"/>'
    # shadows
    '<rect x="14" y="8" width="2" height="2" fill="#7dc432"/>'
    '<rect x="12" y="12" width="2" height="2" fill="#7dc432"/>'
    # eyes
    '<rect x="6" y="8" width="2" height="2" fill="#1a1a2e"/>'
    '<rect x="10" y="8" width="2" height="2" fill="#1a1a2e"/>'
    # robe
    '<rect x="4" y="14" width="10" height="2" fill="#8b6f47"/>'
    '<rect x="2" y="16" width="14" height="6" fill="#a08359"/>'
    '<rect x="14" y="16" width="2" height="6" fill="#6e573a"/>'
    '<rect x="0" y="22" width="18" height="2" fill="#a08359"/>'
    '<rect x="0" y="24" width="18" height="2" fill="#6e573a"/>'
    '</svg>'
)

# R2-D2 — astromech droid (white + blue dome)
_r2d2_svg = (
    '<svg class="tree-mascot" viewBox="0 0 18 28" '
    'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
    # dome top (white)
    '<rect x="6" y="2" width="6" height="2" fill="#e8e8e8"/>'
    '<rect x="4" y="4" width="10" height="2" fill="#e8e8e8"/>'
    '<rect x="2" y="6" width="14" height="2" fill="#e8e8e8"/>'
    # dome eye (blue lens)
    '<rect x="8" y="6" width="2" height="2" fill="#2d6cc8"/>'
    '<rect x="8" y="6" width="1" height="1" fill="#5aa5ff"/>'
    # dome shadow
    '<rect x="14" y="6" width="2" height="2" fill="#b8b8b8"/>'
    '<rect x="12" y="4" width="2" height="2" fill="#b8b8b8"/>'
    # neck divider
    '<rect x="2" y="8" width="14" height="1" fill="#7a7a7a"/>'
    # body (white with blue panels)
    '<rect x="2" y="9" width="14" height="11" fill="#f0f0f0"/>'
    # blue accent panels
    '<rect x="4" y="10" width="4" height="2" fill="#2d6cc8"/>'
    '<rect x="10" y="10" width="4" height="2" fill="#2d6cc8"/>'
    # round port
    '<rect x="7" y="13" width="4" height="3" fill="#7a7a7a"/>'
    '<rect x="8" y="14" width="2" height="1" fill="#1a1a2e"/>'
    # rectangular grilles
    '<rect x="4" y="17" width="4" height="1" fill="#7a7a7a"/>'
    '<rect x="10" y="17" width="4" height="1" fill="#7a7a7a"/>'
    # body shadow
    '<rect x="14" y="9" width="2" height="11" fill="#c8c8c8"/>'
    # legs
    '<rect x="3" y="20" width="3" height="6" fill="#d8d8d8"/>'
    '<rect x="12" y="20" width="3" height="6" fill="#d8d8d8"/>'
    # leg shadows
    '<rect x="5" y="20" width="1" height="6" fill="#a8a8a8"/>'
    '<rect x="14" y="20" width="1" height="6" fill="#a8a8a8"/>'
    # feet
    '<rect x="2" y="26" width="5" height="2" fill="#5a5a5a"/>'
    '<rect x="11" y="26" width="5" height="2" fill="#5a5a5a"/>'
    '</svg>'
)

# Darth Vader — black helmet + cape, red lightsaber
_vader_svg = (
    '<svg class="tree-mascot" viewBox="0 0 18 28" '
    'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
    # helmet top
    '<rect x="5" y="2" width="8" height="2" fill="#1a1a1a"/>'
    '<rect x="3" y="4" width="12" height="2" fill="#1a1a1a"/>'
    '<rect x="2" y="6" width="14" height="6" fill="#1a1a1a"/>'
    # helmet highlights
    '<rect x="3" y="4" width="2" height="2" fill="#2a2a2a"/>'
    '<rect x="2" y="6" width="2" height="2" fill="#2a2a2a"/>'
    # red eye slits
    '<rect x="5" y="8" width="3" height="1" fill="#ff2d3a"/>'
    '<rect x="10" y="8" width="3" height="1" fill="#ff2d3a"/>'
    # mouth grille
    '<rect x="6" y="10" width="6" height="1" fill="#3a3a3a"/>'
    '<rect x="7" y="11" width="4" height="1" fill="#5a5a5a"/>'
    # neck
    '<rect x="6" y="12" width="6" height="2" fill="#1a1a1a"/>'
    # cape shoulders
    '<rect x="2" y="14" width="14" height="2" fill="#0a0a0a"/>'
    # chest panel (silver/grey)
    '<rect x="6" y="16" width="6" height="3" fill="#5a5a6a"/>'
    # control buttons (red/green)
    '<rect x="7" y="17" width="1" height="1" fill="#ff2d3a"/>'
    '<rect x="9" y="17" width="1" height="1" fill="#a4e635"/>'
    # cape
    '<rect x="2" y="16" width="4" height="10" fill="#0a0a0a"/>'
    '<rect x="12" y="16" width="4" height="10" fill="#0a0a0a"/>'
    '<rect x="0" y="22" width="18" height="4" fill="#0a0a0a"/>'
    # red lightsaber hilt + blade (right side)
    '<rect x="15" y="14" width="2" height="2" fill="#888888"/>'
    '<rect x="15" y="2" width="2" height="12" fill="#ff2d3a"/>'
    '<rect x="15" y="2" width="1" height="12" fill="#ffaab0"/>'
    '</svg>'
)

# ─── LORD OF THE RINGS TRIO (right of title) ───

# Gandalf — grey wizard with pointy hat
_gandalf_svg = (
    '<svg class="tree-mascot" viewBox="0 0 18 28" '
    'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
    # pointed hat
    '<rect x="8" y="0" width="2" height="2" fill="#3a3a4a"/>'
    '<rect x="6" y="2" width="6" height="2" fill="#4a4a60"/>'
    '<rect x="6" y="2" width="2" height="2" fill="#3a3a4a"/>'
    '<rect x="4" y="4" width="10" height="2" fill="#4a4a60"/>'
    # hat brim
    '<rect x="2" y="6" width="14" height="2" fill="#3a3a4a"/>'
    '<rect x="2" y="6" width="2" height="2" fill="#2a2a3a"/>'
    # face skin
    '<rect x="6" y="8" width="6" height="4" fill="#e8c7a0"/>'
    # eyes
    '<rect x="7" y="9" width="1" height="1" fill="#1a1a2e"/>'
    '<rect x="10" y="9" width="1" height="1" fill="#1a1a2e"/>'
    # white beard
    '<rect x="4" y="12" width="10" height="2" fill="#f5f5f0"/>'
    '<rect x="2" y="14" width="14" height="4" fill="#f5f5f0"/>'
    '<rect x="4" y="18" width="10" height="2" fill="#f5f5f0"/>'
    # beard shadow
    '<rect x="14" y="14" width="2" height="4" fill="#d4d4cf"/>'
    # grey robe
    '<rect x="2" y="20" width="14" height="4" fill="#7a8492"/>'
    '<rect x="0" y="24" width="18" height="2" fill="#7a8492"/>'
    '<rect x="0" y="26" width="18" height="2" fill="#5a6472"/>'
    '<rect x="14" y="20" width="2" height="4" fill="#5a6472"/>'
    # staff
    '<rect x="16" y="2" width="1" height="22" fill="#6e4a2a"/>'
    '</svg>'
)

# Frodo — hobbit with curly brown hair, green cloak
_frodo_svg = (
    '<svg class="tree-mascot" viewBox="0 0 18 28" '
    'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
    # curly brown hair
    '<rect x="5" y="2" width="8" height="2" fill="#6e3a1a"/>'
    '<rect x="3" y="4" width="12" height="2" fill="#6e3a1a"/>'
    '<rect x="2" y="6" width="14" height="2" fill="#6e3a1a"/>'
    # hair curls (lighter highlights)
    '<rect x="4" y="4" width="2" height="2" fill="#8b5028"/>'
    '<rect x="8" y="2" width="2" height="2" fill="#8b5028"/>'
    '<rect x="12" y="4" width="2" height="2" fill="#8b5028"/>'
    # face (pale skin)
    '<rect x="4" y="8" width="10" height="4" fill="#f0d4ad"/>'
    # blue eyes (Frodo is famous for them)
    '<rect x="6" y="9" width="2" height="2" fill="#2d6cc8"/>'
    '<rect x="10" y="9" width="2" height="2" fill="#2d6cc8"/>'
    '<rect x="6" y="9" width="1" height="1" fill="#5aa5ff"/>'
    '<rect x="10" y="9" width="1" height="1" fill="#5aa5ff"/>'
    # small mouth
    '<rect x="8" y="11" width="2" height="1" fill="#a85e3a"/>'
    # green elven cloak
    '<rect x="4" y="12" width="10" height="2" fill="#3a6a3a"/>'
    '<rect x="2" y="14" width="14" height="8" fill="#4d8a4d"/>'
    '<rect x="14" y="14" width="2" height="8" fill="#2a5a2a"/>'
    # cloak fold (gold ring brooch — Frodo wears one)
    '<rect x="8" y="14" width="2" height="2" fill="#e8c14a"/>'
    '<rect x="8" y="15" width="1" height="1" fill="#a8800a"/>'
    # cloak bottom flare
    '<rect x="0" y="22" width="18" height="4" fill="#4d8a4d"/>'
    '<rect x="0" y="26" width="18" height="2" fill="#2a5a2a"/>'
    '</svg>'
)

# Gollum — pale grey, big eyes, loincloth
_gollum_svg = (
    '<svg class="tree-mascot" viewBox="0 0 18 28" '
    'xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">'
    # bald head (pale greenish-grey)
    '<rect x="6" y="4" width="6" height="2" fill="#a8a89a"/>'
    '<rect x="4" y="6" width="10" height="6" fill="#a8a89a"/>'
    # head highlights/shadow
    '<rect x="4" y="6" width="2" height="2" fill="#c0c0b2"/>'
    '<rect x="12" y="8" width="2" height="4" fill="#888878"/>'
    # giant white eyes (Gollum's signature)
    '<rect x="5" y="8" width="3" height="3" fill="#ffffff"/>'
    '<rect x="10" y="8" width="3" height="3" fill="#ffffff"/>'
    # blue/cyan pupils (lit from within)
    '<rect x="6" y="9" width="1" height="1" fill="#5aa5ff"/>'
    '<rect x="11" y="9" width="1" height="1" fill="#5aa5ff"/>'
    # snarly mouth
    '<rect x="6" y="11" width="6" height="1" fill="#5a4a3a"/>'
    '<rect x="7" y="11" width="1" height="1" fill="#ffffff"/>'
    '<rect x="10" y="11" width="1" height="1" fill="#ffffff"/>'
    # scrawny neck
    '<rect x="7" y="12" width="4" height="2" fill="#a8a89a"/>'
    # bony shoulders + arms hugging
    '<rect x="4" y="14" width="10" height="2" fill="#a8a89a"/>'
    # ribcage body
    '<rect x="5" y="16" width="8" height="6" fill="#a8a89a"/>'
    # rib shadows
    '<rect x="6" y="17" width="6" height="1" fill="#888878"/>'
    '<rect x="6" y="19" width="6" height="1" fill="#888878"/>'
    # body shadow
    '<rect x="11" y="16" width="2" height="6" fill="#888878"/>'
    # ragged loincloth
    '<rect x="4" y="22" width="10" height="3" fill="#6e573a"/>'
    '<rect x="5" y="25" width="2" height="1" fill="#6e573a"/>'
    '<rect x="11" y="25" width="2" height="1" fill="#6e573a"/>'
    # crouched legs
    '<rect x="5" y="25" width="3" height="3" fill="#a8a89a"/>'
    '<rect x="10" y="25" width="3" height="3" fill="#a8a89a"/>'
    '</svg>'
)

_mascot_html_left = (
    f'<span class="mascot-pair">{_yoda_svg}{_r2d2_svg}{_vader_svg}</span>'
)
_mascot_html_right = (
    f'<span class="mascot-pair">{_gandalf_svg}{_frodo_svg}{_gollum_svg}</span>'
)
st.markdown(
    '<div class="title-row">'
    '<h1 class="hero-title">'
    f'{_mascot_html_left}'
    '<span class="hero-word">Hailey\'s</span>'
    '<em>Hub</em>'
    f'{_mascot_html_right}'
    '</h1>'
    f'<div class="caption-mono title-crumb">vault · {VAULT_PATH.name} · plan · {CLAUDE_PLAN} · permission · {PERMISSION_MODE}</div>'
    '</div>',
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
# BRAND SWITCHER — Wild Oak Trail · Sandalwood AI · Popcorn & Prayers
# ═══════════════════════════════════════════════════════════

BRANDS = {
    "wot": {
        "label": "Wild Oak Trail",
        "tagline": "e-commerce · shopify",
        "accent": "var(--accent-3)",   # lime green
    },
    "sandalwood": {
        "label": "Sandalwood AI",
        "tagline": "content · research · AI radar",
        "accent": "var(--accent-5)",   # purple
    },
    "popcorn": {
        "label": "Popcorn & Prayers",
        "tagline": "Christian movie reviews",
        "accent": "var(--accent)",     # hot magenta
    },
}

if "active_brand" not in st.session_state:
    st.session_state.active_brand = "wot"

# Allow ?brand=... query param to set the brand
_brand_q = st.query_params.get("brand")
if _brand_q and _brand_q in BRANDS:
    st.session_state.active_brand = _brand_q

_active_brand = st.session_state.active_brand

st.markdown(
    '<style>'
    '.brand-switcher { display: flex; gap: 0.5rem; margin: 0.4rem 0 1rem 0; }'
    '.brand-pill { flex: 1; display: block; padding: 0.85rem 1rem; border-radius: 14px; '
    '  background: var(--bg-card); box-shadow: 0 0 0 1px var(--ring-soft); '
    '  text-decoration: none !important; color: var(--fg); text-align: center; '
    "  font-family: 'Outfit', system-ui, sans-serif; "
    '  transition: box-shadow 0.14s, transform 0.14s; }'
    '.brand-pill:hover { box-shadow: 0 0 0 1.5px var(--accent); transform: translateY(-1px); }'
    '.brand-pill.active { box-shadow: 0 0 0 2px var(--pill-accent, var(--accent)); '
    '  background: linear-gradient(180deg, var(--bg-card) 0%, var(--bg-card-hi) 100%); }'
    '.brand-pill-name { display: block; font-weight: 600; font-size: 1rem; '
    '  letter-spacing: 0.02em; color: var(--pill-accent, var(--fg)); }'
    '.brand-pill-tag { display: block; font-size: 0.7rem; color: var(--fg-mute); '
    '  letter-spacing: 0.04em; text-transform: lowercase; margin-top: 0.15rem; }'
    '</style>'
    '<div class="brand-switcher">'
    + "".join(
        f'<a class="brand-pill{" active" if key == _active_brand else ""}" '
        f'href="?brand={key}" target="_self" '
        f'style="--pill-accent: {meta["accent"]};">'
        f'<span class="brand-pill-name">{html_escape(meta["label"])}</span>'
        f'<span class="brand-pill-tag">{html_escape(meta["tagline"])}</span>'
        f'</a>'
        for key, meta in BRANDS.items()
    )
    + '</div>',
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
# QUICK-NAV PILLS  (claude code · vault · daily · runs · drafts · [status])
# ═══════════════════════════════════════════════════════════

today_note = today_daily_note()
today_runs_dir = RUNS_DIR / date.today().isoformat()

vault_uri = f"obsidian://open?vault={quote(VAULT_NAME)}"
daily_note_uri = obsidian_uri(today_note) if today_note.exists() else vault_uri
runs_folder_uri = f"obsidian://open?vault={quote(VAULT_NAME)}&file={quote('dashboard-runs')}"
drafts_folder_uri = f"obsidian://open?vault={quote(VAULT_NAME)}&file={quote('drafts/awaiting')}"

if st.session_state.running:
    _active = st.session_state.active_skill or "skill"
    _status_html = (
        f'<div class="status-chip running qn-status">'
        f'<span class="pulse-dot small"></span>{_active}</div>'
    )
else:
    _status_html = (
        '<div class="status-chip qn-status">'
        '<span class="pulse-dot idle small"></span>idle</div>'
    )

st.markdown(
    f"""
    <div class="quicknav">
        <a class="qn-claude" href="?brand={_active_brand}&action=terminal" target="_self">
            <span class="qn-icon">◆</span>claude code<span class="qn-arrow">↗</span>
        </a>
        <a href="{vault_uri}" target="_blank"><span class="qn-icon">✱</span>vault</a>
        <a href="{daily_note_uri}" target="_blank"><span class="qn-icon">§</span>daily note</a>
        <a href="{runs_folder_uri}" target="_blank"><span class="qn-icon">¶</span>runs folder</a>
        <a href="{drafts_folder_uri}" target="_blank"><span class="qn-icon">※</span>drafts</a>
        {_status_html}
    </div>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════
# BOOKKEEPING STAT CARDS  (was: usage gauges)
# ═══════════════════════════════════════════════════════════

usage = calc_usage_windows()
rate_limits = load_rate_limits()
metrics = calc_metrics()


def _gauge_class(pct: float) -> str:
    if pct >= 90:
        return "danger"
    if pct >= 70:
        return "warning"
    return ""


def render_gauge(
    label: str,
    reset_label: str,
    used: float,
    limit: float,
    stat_primary: str,
    stat_max: str,
    stat_sub: str,
    delta: tuple[str, float, str] | None = None,
) -> str:
    pct = min(100.0, (used / limit * 100.0) if limit else 0.0)
    klass = _gauge_class(pct)
    delta_html = ""
    if delta is not None:
        arrow, pct_d, dklass = delta
        dtxt = f'{arrow} {abs(pct_d):.0f}%' if dklass != "neutral" else '· flat'
        delta_html = f'<span class="gauge-delta {dklass}">{dtxt}</span>'
    return (
        f'<div class="gauge-card">'
        f'<div class="gauge-header">'
        f'<span class="gauge-label">{label}</span>'
        f'<span class="gauge-reset">{reset_label}</span>'
        f'</div>'
        f'<div class="gauge-track">'
        f'<div class="gauge-fill {klass}" style="width:{pct:.1f}%"></div>'
        f'</div>'
        f'<div class="gauge-stats">'
        f'<span>{stat_primary}</span>'
        f'<span class="gauge-max">/ {stat_max}</span>'
        f'<span class="gauge-sub">{stat_sub}</span>'
        f'{delta_html}'
        f'</div>'
        f'</div>'
    )


five_h_reset = (rate_limits.get("five_hour") or {}).get("resets_at")
week_reset = (rate_limits.get("weekly") or {}).get("resets_at")

five_h_tokens = usage["five_hour"]["total"]
week_tokens = usage["weekly"]["total"]
routines_today = usage["today"]["routines"]
today_runs = usage["today"]["runs"]
today_cost = usage["today"]["cost"]

_metas_cache = _read_session_metas()
_now = datetime.now()
_5h_cur, _5h_pri = delta_window(
    _metas_cache,
    _now - timedelta(hours=5), _now,
    _now - timedelta(hours=10), _now - timedelta(hours=5),
)
_wk_cur, _wk_pri = delta_window(
    _metas_cache,
    _now - timedelta(days=7), _now,
    _now - timedelta(days=14), _now - timedelta(days=7),
)
_rt_ledger = _load_routines_ledger()
_rt_today = int(_rt_ledger.get(date.today().isoformat(), 0))
_rt_yday = int(_rt_ledger.get((date.today() - timedelta(days=1)).isoformat(), 0))
_5h_delta = compute_delta(_5h_cur, _5h_pri)
_wk_delta = compute_delta(_wk_cur, _wk_pri)
_rt_delta = compute_delta(_rt_today, _rt_yday)

def render_stat_card(
    label: str,
    sub_label: str,
    value_str: str,
    is_negative: bool,
    sub_text: str,
    accent_var: str = "var(--accent)",
    min_height: str | None = None,
) -> str:
    color = "var(--danger)" if is_negative else accent_var
    style_attr = (
        f' style="min-height: {min_height}; display: flex; flex-direction: column; justify-content: space-between;"'
        if min_height else ''
    )
    return (
        f'<div class="gauge-card"{style_attr}>'
        f'<div class="gauge-header">'
        f'<span class="gauge-label">{label}</span>'
        f'<span class="gauge-reset">{sub_label}</span>'
        f'</div>'
        f"<div style=\"font-family: 'Outfit', system-ui, -apple-system, sans-serif; font-size: 1.6rem; "
        f"font-weight: 600; color: {color}; padding: 0.45rem 0 0.35rem 0; "
        f"letter-spacing: -0.02em; line-height: 1.1;\">"
        f'{value_str}'
        f'</div>'
        f'<div class="gauge-stats">'
        f'<span class="gauge-sub">{sub_text}</span>'
        f'</div>'
        f'</div>'
    )


def _fmt_money(v) -> str:
    if v is None:
        return "—"
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.0f}"


_bk = load_bookkeeping()
_ytd = _bk.get("ytd") or {}
_monthly = _bk.get("monthly") or {}
_cur_month_name = _bk.get("current_month_name") or datetime.now().strftime("%B")
_last_full_month_name = _bk.get("last_full_month_name") or ""
_cur_month = _monthly.get(_cur_month_name) or {}
_last_full_month = _monthly.get(_last_full_month_name) or {}

if _active_brand == "wot":
    _bk_h1, _bk_h2 = st.columns([5, 1], gap="small")
    with _bk_h1:
        _as_of = _bk.get("as_of", "—")
        st.markdown(
            f'<div class="cat-label" style="display: flex; align-items: baseline; gap: 0.7rem;">'
            f'<span>bookkeeping</span>'
            f'<span style="font-weight: normal; color: var(--fg-mute); text-transform: lowercase; '
            f'font-size: 0.7rem;">as of · {_as_of}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with _bk_h2:
        if st.button("↻ refresh", key="refresh_bookkeeping"):
            with st.spinner("pulling sheet..."):
                try:
                    import importlib
                    import refresh_bookkeeping as _rb
                    importlib.reload(_rb)
                    _rb.main()
                    st.rerun()
                except Exception as _e:
                    st.error(f"refresh failed: {_e}")

    with st.expander("show net income figures", expanded=False):
        m1, m2, m3 = st.columns(3, gap="small")
        with m1:
            _v = _ytd.get("net", 0.0)
            _m = _ytd.get("margin_pct")
            st.markdown(
                render_stat_card(
                    f"net income · ytd {_bk.get('year', '')}",
                    f"{_ytd.get('orders', 0)} orders",
                    _fmt_money(_v),
                    is_negative=(_v < 0),
                    sub_text=f"margin {_m:.1f}%" if _m is not None else "margin —",
                    accent_var="var(--accent-5)",   # purple
                ),
                unsafe_allow_html=True,
            )
        with m2:
            _v = _last_full_month.get("net", 0.0)
            _m = _last_full_month.get("margin_pct")
            st.markdown(
                render_stat_card(
                    f"net income · {_last_full_month_name.lower()} (last full)",
                    f"{_last_full_month.get('orders', 0)} orders",
                    _fmt_money(_v),
                    is_negative=(_v < 0),
                    sub_text=f"margin {_m:.1f}%" if _m is not None else "margin —",
                    accent_var="var(--accent-2)",   # cyan
                ),
                unsafe_allow_html=True,
            )
        with m3:
            _v = _cur_month.get("net", 0.0)
            _m = _cur_month.get("margin_pct")
            st.markdown(
                render_stat_card(
                    f"net income · {_cur_month_name.lower()} (in progress)",
                    f"{_cur_month.get('orders', 0)} orders so far",
                    _fmt_money(_v),
                    is_negative=(_v < 0),
                    sub_text=f"margin {_m:.1f}%" if _m is not None else "margin —",
                    accent_var="var(--accent)",     # hot magenta
                ),
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# SHOPIFY — live commerce metrics
# ═══════════════════════════════════════════════════════════

if _active_brand == "wot":
    if shopify_data.is_configured():
        _sh_h1, _sh_h2 = st.columns([5, 1], gap="small")
        with _sh_h1:
            st.markdown(
                '<div class="cat-label" style="display: flex; align-items: baseline; gap: 0.7rem;">'
                '<span>shopify</span>'
                '<span style="font-weight: normal; color: var(--fg-mute); text-transform: lowercase; '
                'font-size: 0.7rem;">live · wild-oak-trail.myshopify.com</span>'
                '</div>',
                unsafe_allow_html=True,
            )
        with _sh_h2:
            if st.button("↻ refresh", key="refresh_shopify"):
                shopify_data.fetch_revenue_window.clear()
                shopify_data.fetch_recent_orders.clear()
                shopify_data.fetch_top_products_mtd.clear()
                shopify_data.fetch_top_landing_pages_7d.clear()
                st.rerun()

        try:
            _today = shopify_data.fetch_today()
            _mtd = shopify_data.fetch_mtd()
            _shopify_err = None
        except Exception as _e:
            _today = {"orders": 0, "gross": 0.0, "aov": 0.0}
            _mtd = {"orders": 0, "gross": 0.0, "aov": 0.0}
            _shopify_err = str(_e)

        if _shopify_err:
            st.markdown(
                f'<div style="color: var(--danger); font-size: 0.85rem; padding: 0.4rem 0;">'
                f'shopify api error: {html_escape(_shopify_err)}</div>',
                unsafe_allow_html=True,
            )
        else:
            try:
                _landing = shopify_data.fetch_top_landing_pages_7d(limit=10)
                _landing_err = None
            except Exception as _le:
                _landing = []
                _landing_err = str(_le)

            s1, s2, s3 = st.columns(3, gap="small")
            with s2:
                st.markdown(
                    render_stat_card(
                        "today's revenue",
                        f"{_today['orders']} orders",
                        _fmt_money(_today["gross"]),
                        is_negative=False,
                        sub_text=f"aov ${_today['aov']:,.0f}" if _today["orders"] else "no orders yet",
                        accent_var="var(--accent-2)",
                        min_height="6.2rem",
                    ),
                    unsafe_allow_html=True,
                )
            with s3:
                st.markdown(
                    render_stat_card(
                        f"month to date · {_cur_month_name.lower()}",
                        f"{_mtd['orders']} orders",
                        _fmt_money(_mtd["gross"]),
                        is_negative=False,
                        sub_text=f"aov ${_mtd['aov']:,.0f}" if _mtd["orders"] else "no orders yet",
                        accent_var="var(--accent)",
                        min_height="6.2rem",
                    ),
                    unsafe_allow_html=True,
                )

            with s1:
                _quotes = [
                    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
                    ("It always seems impossible until it's done.", "Nelson Mandela"),
                    ("Success is not final, failure is not fatal.", "Winston Churchill"),
                    ("Done is better than perfect.", ""),
                    ("Small steps, every day.", ""),
                    ("Great things never come from comfort zones.", ""),
                    ("Action is the foundational key to all success.", "Pablo Picasso"),
                    ("You are doing better than you think.", ""),
                    ("Trust the process.", ""),
                    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
                ]
                _n = len(_quotes)
                _cycle = _n * 20  # 20s per quote
                _quote_items = []
                for idx, (text, author) in enumerate(_quotes):
                    attribution = f'<span style="opacity:0.7; font-size:0.78rem;"> — {html_escape(author)}</span>' if author else ""
                    _quote_items.append(
                        f'<div class="quote-item" style="animation-delay: {idx * 20}s;">'
                        f'"{html_escape(text)}"{attribution}'
                        f'</div>'
                    )
                _quotes_html = (
                    f'<style>'
                    f'.quote-card {{ position: relative; min-height: 6.2rem; }}'
                    f'.quote-stage {{ position: relative; height: 4.2rem; }}'
                    f'.quote-item {{'
                    f'  position: absolute; inset: 0;'
                    f'  display: flex; align-items: center; justify-content: center;'
                    f'  text-align: center; padding: 0 0.3rem;'
                    f"  font-family: 'Fraunces', Georgia, serif;"
                    f'  font-size: 1.05rem; line-height: 1.35;'
                    f'  color: var(--accent-5);'
                    f'  font-style: italic;'
                    f'  font-weight: 400;'
                    f'  opacity: 0;'
                    f'  animation: quote-rotate {_cycle}s infinite;'
                    f'}}'
                    f'@keyframes quote-rotate {{'
                    f'  0%   {{ opacity: 0; transform: translateY(4px); }}'
                    f'  0.5% {{ opacity: 1; transform: translateY(0); }}'
                    f'  9.5% {{ opacity: 1; transform: translateY(0); }}'
                    f'  10%  {{ opacity: 0; transform: translateY(-4px); }}'
                    f'  100% {{ opacity: 0; }}'
                    f'}}'
                    f'</style>'
                    f'<div class="gauge-card quote-card">'
                    f'<div class="gauge-header">'
                    f'<span class="gauge-label">daily fuel</span>'
                    f'<span class="gauge-reset">rotates · 20s</span>'
                    f'</div>'
                    f'<div class="quote-stage">'
                    f'{"".join(_quote_items)}'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(_quotes_html, unsafe_allow_html=True)

            @st.dialog("recent orders · last 10", width="large")
            def _show_recent_orders():
                try:
                    recent = shopify_data.fetch_recent_orders(limit=10)
                    if recent:
                        df = pd.DataFrame([
                            {
                                "order": r["order"],
                                "customer": r["customer"],
                                "total": f"${r['total']:,.2f}",
                                "payment": r["financial"] or "—",
                                "fulfillment": r["fulfillment"] or "—",
                                "when": r["created_at"][:16].replace("T", " ") if r["created_at"] else "",
                            }
                            for r in recent
                        ])
                        st.dataframe(df, hide_index=True, width='stretch')
                    else:
                        st.markdown(
                            '<div style="color: var(--fg-dim); font-size: 0.85rem;">no orders found.</div>',
                            unsafe_allow_html=True,
                        )
                except Exception as _de:
                    st.error(f"failed to load recent orders: {_de}")

            _tp_title = f"top products · {_cur_month_name.lower()} mtd"

            @st.dialog(_tp_title, width="large")
            def _show_top_products():
                try:
                    top = shopify_data.fetch_top_products_mtd(limit=10)
                    if top:
                        df = pd.DataFrame([
                            {
                                "product": r["title"],
                                "units": r["units"],
                                "revenue": f"${r['revenue']:,.2f}",
                            }
                            for r in top
                        ])
                        st.dataframe(df, hide_index=True, width='stretch')
                    else:
                        st.markdown(
                            '<div style="color: var(--fg-dim); font-size: 0.85rem;">no sales this month yet.</div>',
                            unsafe_allow_html=True,
                        )
                except Exception as _de:
                    st.error(f"failed to load top products: {_de}")

            @st.dialog("top landing pages · last 7 days", width="large")
            def _show_landing_pages():
                if _landing_err and not _landing:
                    if "read_reports" in (_landing_err or ""):
                        st.markdown(
                            '<div style="color: var(--fg-dim); font-size: 0.85rem;">'
                            'analytics scope not yet granted. re-install the app to approve '
                            '<code>read_reports</code> — see chat for the install URL.</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.error(f"failed to load landing pages: {_landing_err}")
                elif _landing:
                    df = pd.DataFrame([
                        {
                            "rank": i + 1,
                            "landing page": r.get("path") or "/",
                            "sessions": int(r.get("sessions", 0)),
                        }
                        for i, r in enumerate(_landing)
                    ])
                    st.dataframe(df, hide_index=True, width='stretch')
                else:
                    st.markdown(
                        '<div style="color: var(--fg-dim); font-size: 0.85rem;">no traffic data in the last 7 days.</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
            b1, b2, b3 = st.columns(3, gap="small")
            with b1:
                if st.button("recent orders · last 10", key="btn_recent_orders", width='stretch'):
                    _show_recent_orders()
            with b2:
                if st.button(f"top products · {_cur_month_name.lower()} mtd", key="btn_top_products", width='stretch'):
                    _show_top_products()
            with b3:
                if st.button("top landing pages · last 7 days", key="btn_landing_pages", width='stretch'):
                    _show_landing_pages()

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# NET INCOME CHART — by month, current year
# ═══════════════════════════════════════════════════════════

if _active_brand == "wot":
    _months_order = ["January", "February", "March", "April", "May", "June",
                     "July", "August", "September", "October", "November", "December"]
    _short_months = ["jan", "feb", "mar", "apr", "may", "jun",
                     "jul", "aug", "sep", "oct", "nov", "dec"]
    _net_vals = [_monthly.get(m, {}).get("net", 0.0) for m in _months_order]
    _pos_color = "#a4e635"   # lime — positive months
    _neg_color = "#ff4d6d"   # coral pink — negative months
    _bar_colors = [_pos_color if v >= 0 else _neg_color for v in _net_vals]

    _profit_fig = go.Figure()
    _profit_fig.add_trace(go.Bar(
        x=_short_months,
        y=_net_vals,
        marker=dict(color=_bar_colors, line=dict(width=0)),
        hovertemplate="<b>%{x}</b><br>$%{y:,.2f}<extra></extra>",
        name="net income",
    ))
    _profit_fig.update_layout(
        height=280,
        margin=dict(l=50, r=20, t=10, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, system-ui, sans-serif", size=10, color="#5a5a70"),
        showlegend=False,
        bargap=0.32,
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#ec1e79",
            font=dict(family="Outfit, system-ui, sans-serif", color="#1a1a2e", size=10),
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showline=False,
            tickfont=dict(color="#5a5a70", size=10),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(26, 26, 46, 0.06)",
            zeroline=True,
            zerolinecolor="rgba(26, 26, 46, 0.18)",
            tickprefix="$",
            tickformat=",.0f",
            tickfont=dict(color="#5a5a70", size=10),
        ),
    )

    _ytd_net = _ytd.get("net", 0)
    _ytd_str = f"${_ytd_net:,.0f}" if _ytd_net >= 0 else f"-${abs(_ytd_net):,.0f}"

    with st.expander(f"show net income chart · {_bk.get('year', '')}", expanded=False):
        st.markdown(
            f'<div class="chart-card">'
            f'<div class="chart-title">net income · {_bk.get("year", "")} '
            f'<span>· ytd {_ytd_str}</span></div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(_profit_fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# SEO + AEO PULSE — latest news, refreshed by the SEO/AEO News skill
# ═══════════════════════════════════════════════════════════

if _active_brand == "wot":
    _news_file = RUNS_DIR / "seo-aeo-news.md"
    _news_text = ""
    _news_mtime = None
    if _news_file.exists():
        _news_text = _news_file.read_text().strip()
        _news_mtime = datetime.fromtimestamp(_news_file.stat().st_mtime)

    _news_header_sub = (
        f"updated · {_news_mtime.strftime('%b %d · %H:%M')}"
        if _news_mtime else
        "no data yet — run the SEO/AEO News skill below"
    )

    _expander_label = f"seo + aeo pulse  ·  {_news_header_sub}"
    with st.expander(_expander_label, expanded=False):
        if _news_text:
            st.markdown(_news_text)
        else:
            st.markdown(
                '<div style="color: var(--fg-dim); font-size: 0.85rem; padding: 0.2rem 0;">'
                'no news fetched yet — click the <strong>SEO/AEO News</strong> button below to pull the latest.'
                '</div>',
                unsafe_allow_html=True,
            )


if _active_brand == "sandalwood":
    # ─── AI News Pulse (same pattern, separate file) ───
    _ai_news_file = RUNS_DIR / "ai-news.md"
    _ai_news_text = ""
    _ai_news_mtime = None
    if _ai_news_file.exists():
        _ai_news_text = _ai_news_file.read_text().strip()
        _ai_news_mtime = datetime.fromtimestamp(_ai_news_file.stat().st_mtime)

    _ai_news_sub = (
        f"updated · {_ai_news_mtime.strftime('%b %d · %H:%M')}"
        if _ai_news_mtime else
        "no data yet — run the AI News skill below"
    )
    _ai_expander_label = f"ai news pulse  ·  {_ai_news_sub}"
    with st.expander(_ai_expander_label, expanded=False):
        if _ai_news_text:
            st.markdown(_ai_news_text)
        else:
            st.markdown(
                '<div style="color: var(--fg-dim); font-size: 0.85rem; padding: 0.2rem 0;">'
                'no news fetched yet — click the <strong>AI News</strong> button below to pull the latest.'
                '</div>',
                unsafe_allow_html=True,
            )


if _active_brand == "sandalwood":
    # ─── GitHub Trending Pulse (same pattern) ───
    _gh_file = RUNS_DIR / "github-trending.md"
    _gh_text = ""
    _gh_mtime = None
    if _gh_file.exists():
        _gh_text = _gh_file.read_text().strip()
        _gh_mtime = datetime.fromtimestamp(_gh_file.stat().st_mtime)

    _gh_sub = (
        f"updated · {_gh_mtime.strftime('%b %d · %H:%M')}"
        if _gh_mtime else
        "no data yet — run the GitHub Trending skill below"
    )
    _gh_expander_label = f"github trending  ·  {_gh_sub}"
    with st.expander(_gh_expander_label, expanded=False):
        if _gh_text:
            st.markdown(_gh_text)
        else:
            st.markdown(
                '<div style="color: var(--fg-dim); font-size: 0.85rem; padding: 0.2rem 0;">'
                'no trending data yet — click the <strong>GitHub Trending</strong> button below to fetch '
                'the latest. Uses GitHub\'s public search API (no key needed).'
                '</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


if _active_brand == "popcorn":
    # ═══════════════════════════════════════════════════════════
    # POPCORN & PRAYERS — Christian movie review brand
    # ═══════════════════════════════════════════════════════════

    st.markdown(
        '<div class="cat-label">'
        '<span>popcorn & prayers</span>'
        '<span style="font-weight: normal; color: var(--fg-mute); text-transform: lowercase; '
        'font-size: 0.7rem;">christian movie review brand</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ─── Movie Trending Pulse ───
    _mt_file = RUNS_DIR / "popcorn-trending.md"
    _mt_text = ""
    _mt_mtime = None
    if _mt_file.exists():
        _mt_text = _mt_file.read_text().strip()
        _mt_mtime = datetime.fromtimestamp(_mt_file.stat().st_mtime)

    _mt_sub = (
        f"updated · {_mt_mtime.strftime('%b %d · %H:%M')}"
        if _mt_mtime else
        "no data yet — run the Movie Trending skill below"
    )
    _mt_expander_label = f"movie trending  ·  {_mt_sub}"
    with st.expander(_mt_expander_label, expanded=False):
        if _mt_text:
            st.markdown(_mt_text)
        else:
            st.markdown(
                '<div style="color: var(--fg-dim); font-size: 0.85rem; padding: 0.2rem 0;">'
                'no movie data yet — click the <strong>Movie Trending</strong> button below to pull '
                "what's hot in theaters and streaming, with faith/family content notes."
                '</div>',
                unsafe_allow_html=True,
            )


    # ─── Movie Controversies Pulse ───
    _mc_file = RUNS_DIR / "popcorn-controversies.md"
    _mc_text = ""
    _mc_mtime = None
    if _mc_file.exists():
        _mc_text = _mc_file.read_text().strip()
        _mc_mtime = datetime.fromtimestamp(_mc_file.stat().st_mtime)

    _mc_sub = (
        f"updated · {_mc_mtime.strftime('%b %d · %H:%M')}"
        if _mc_mtime else
        "no data yet — run the Movie Controversies skill below"
    )
    _mc_expander_label = f"movie controversies  ·  {_mc_sub}"
    with st.expander(_mc_expander_label, expanded=False):
        if _mc_text:
            st.markdown(_mc_text)
        else:
            st.markdown(
                '<div style="color: var(--fg-dim); font-size: 0.85rem; padding: 0.2rem 0;">'
                'no controversy data yet — click the <strong>Movie Controversies</strong> button below '
                'to pull current debates and reactions with a faith perspective angle.'
                '</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# MCP HEALTH STRIP
# ═══════════════════════════════════════════════════════════

mcp_servers = load_mcp_state()
if mcp_servers:
    items_html = '<span class="mcp-label">integrations</span>'
    for s in mcp_servers:
        name = s.get("name", "?").replace("claude.ai ", "").replace("plugin:", "")
        status = (s.get("status") or "unknown").lower().replace("-", "_")
        items_html += (
            f'<span class="mcp-item">'
            f'<span class="mcp-dot {status}"></span>'
            f'{html_escape(name)}'
            f'</span>'
        )
    st.markdown(f'<div class="mcp-strip">{items_html}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# LAYOUT
# ═══════════════════════════════════════════════════════════

st.markdown('<hr class="chapter" />', unsafe_allow_html=True)

col_main, col_side = st.columns([2.6, 1], gap="large")


# ——— SIDEBAR COLUMN: recent runs ———
with col_side:
    runs = list_recent_runs(8)
    card_html = '<div class="runs-card"><div class="cat-label">recent runs</div>'
    if not runs:
        card_html += '<div style="color: var(--text-mute); font-size: 0.8rem; padding: 0.4rem 0 0.5rem 0;">no runs yet</div>'
    else:
        card_html += '<div class="run-list">'
        for r in runs:
            mtime = datetime.fromtimestamp(r.stat().st_mtime)
            label = r.stem.split("-", 2)[-1].replace("-", " ")
            uri = obsidian_uri(r)
            card_html += (
                f'<div class="run-row">'
                f'<span class="run-time">{mtime.strftime("%H:%M")}</span>'
                f'<span class="run-label">{html_escape(label)}</span>'
                f'<a href="{uri}" target="_blank">open ↗</a>'
                f'</div>'
            )
        card_html += '</div>'
    card_html += '</div>'
    st.markdown(card_html, unsafe_allow_html=True)

    # Mini 7-day runs bar chart (bottom-right "dead space" filler)
    df_7 = activity_cumulative(7)
    _bar_labels = df_7["date"].dt.strftime("%a").tolist()
    _bar_vals = df_7["day_count"].tolist()
    _bar_total = int(sum(_bar_vals))

    st.markdown(
        '<div class="chart-card mini-chart">'
        '<div class="chart-title">last <em>seven</em> days '
        f'<span>· {_bar_total} runs</span></div>',
        unsafe_allow_html=True,
    )
    _barfig = go.Figure()
    _barfig.add_trace(
        go.Bar(
            x=_bar_labels,
            y=_bar_vals,
            marker=dict(color="#ec1e79", line=dict(width=0)),
            hovertemplate="<b>%{x}</b><br>%{y} runs<extra></extra>",
        )
    )
    _barfig.update_layout(
        height=120,
        margin=dict(l=20, r=20, t=10, b=28),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit, system-ui, sans-serif", size=9, color="#5a5a70"),
        showlegend=False,
        bargap=0.32,
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#ec1e79",
            font=dict(family="Outfit, system-ui, sans-serif", color="#1a1a2e", size=10),
        ),
        xaxis=dict(
            showgrid=False, zeroline=False, showline=False,
            tickfont=dict(color="#5a5a70", size=9),
        ),
        yaxis=dict(
            showgrid=False, zeroline=False, showline=False, showticklabels=False,
        ),
    )
    st.plotly_chart(_barfig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # ——— Forecast card (5-hour burn projection) ———
    _cap = LIMITS["five_hour_tokens"]
    _used = five_h_tokens
    _remaining = max(0, _cap - _used)
    _reset_in_sec = max(0, int(five_h_reset - time.time())) if five_h_reset else 0
    _reset_in_min = _reset_in_sec // 60
    _window_min = 300  # 5h
    _elapsed_min = max(1, _window_min - _reset_in_min) if _reset_in_min else 1
    _burn_per_min = (_used / _elapsed_min) if _elapsed_min > 0 else 0
    _exhaust_in_min = int(_remaining / _burn_per_min) if _burn_per_min > 0 else None
    _will_exhaust = _exhaust_in_min is not None and _exhaust_in_min < _reset_in_min

    _elapsed_pct = min(100, _elapsed_min / _window_min * 100)
    if _will_exhaust and _exhaust_in_min is not None:
        _proj_end_min = _elapsed_min + _exhaust_in_min
    else:
        _proj_end_min = _window_min
    _proj_pct = max(_elapsed_pct, min(100, _proj_end_min / _window_min * 100))
    _proj_left = _elapsed_pct
    _proj_width = max(0, _proj_pct - _elapsed_pct)
    _now_pct = _elapsed_pct

    if _will_exhaust and _exhaust_in_min is not None:
        _hit = (datetime.now() + timedelta(minutes=_exhaust_in_min)).strftime("%H:%M")
        _headline = f'cap at <em>{_hit}</em>'
    else:
        _headline = 'under cap <em>this window</em>'
    _sub = (
        f'burn · {fmt_tokens(int(_burn_per_min))}/min'
        if _burn_per_min > 0 else 'burn · idle'
    )

    # Next scheduled routines — hardcoded schedule until real cron wired in
    _scheduled = [
        ("17:00", "evening digest"),
        ("22:00", "vault compact"),
        ("09:00", "morning brief"),
    ]
    _now_dt = datetime.now()
    _sched_rows = []
    for hhmm, label in _scheduled:
        _h, _m = [int(x) for x in hhmm.split(":")]
        _next = _now_dt.replace(hour=_h, minute=_m, second=0, microsecond=0)
        if _next <= _now_dt:
            _next = _next + timedelta(days=1)
        _sched_rows.append((_next, hhmm, label))
    _sched_rows.sort(key=lambda r: r[0])
    _sched_html = '<div class="cpt-sched">'
    for dt, hhmm, label in _sched_rows[:2]:
        _sched_html += (
            '<div class="cpt-sched-row">'
            f'<span class="cpt-sched-time">{hhmm}</span>'
            f'<span class="cpt-sched-label">{label}</span>'
            f'<span class="cpt-sched-in">in {fmt_time_until(int(dt.timestamp()))}</span>'
            '</div>'
        )
    _sched_html += '</div>'

    st.markdown(
        '<div class="cpt-forecast">'
        f'<div class="cpt-forecast-head">forecast · 5h'
        f'<span class="cpt-forecast-sub">{_sub}</span></div>'
        f'<div class="cpt-forecast-head" '
        'style="font-size:0.7rem;color:var(--fg-dim);margin-bottom:0;">'
        f'{_headline}</div>'
        '<div class="cpt-forecast-track">'
        f'<div class="cpt-forecast-elapsed" style="width:{_elapsed_pct:.1f}%"></div>'
        f'<div class="cpt-forecast-proj" '
        f'style="left:{_proj_left:.1f}%;width:{_proj_width:.1f}%"></div>'
        f'<div class="cpt-forecast-now" style="left:{_now_pct:.1f}%"></div>'
        '</div>'
        '<div class="cpt-forecast-legend">'
        '<span><em>█</em> elapsed</span>'
        '<span><em>▨</em> projected</span>'
        '<span><em>│</em> now</span>'
        f'<span>resets · {fmt_time_until(five_h_reset)}</span>'
        '</div>'
        f'{_sched_html}'
        '</div>',
        unsafe_allow_html=True,
    )

    # ——— Vault pulse ———
    pulse_items = list_vault_pulse(6)
    if pulse_items:
        pulse_html = '<div class="cpt-pulse-card"><div class="cpt-cat">vault pulse</div>'
        for it in pulse_items:
            try:
                uri = obsidian_uri(it["path"])
            except Exception:
                uri = "#"
            pulse_html += (
                '<div class="cpt-pulse">'
                f'<span class="cpt-verb {it["verb"]}">{it["verb"]}</span>'
                '<div class="cpt-pulse-main">'
                f'<div class="cpt-pulse-name">'
                f'<a href="{uri}" target="_blank" '
                'style="color:inherit;text-decoration:none;">'
                f'{html_escape(it["name"])}</a></div>'
                f'<div class="cpt-pulse-dir">{html_escape(it["dir"])}</div>'
                '</div>'
                f'<span class="cpt-pulse-ago">{fmt_ago(it["age_sec"])}</span>'
                '</div>'
            )
        pulse_html += '</div>'
        st.markdown(pulse_html, unsafe_allow_html=True)



# ——— MAIN COLUMN ———
with col_main:
    hero_slot = st.empty()

    def render_hero_error():
        err = st.session_state.last_error or "unknown error"
        label = (st.session_state.last_label or "skill").lower()
        hero_slot.markdown(
            f'<div class="hero-card error">'
            f'<div class="hero-label">failed · {html_escape(label)}</div>'
            f'<h2 class="hero-headline">run failed <em>·</em></h2>'
            f'<pre class="error-detail">{html_escape(err)}</pre>'
            f'<div class="error-hint">check logs or click ↻ rerun below</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    def render_hero_idle():
        if st.session_state.last_output:
            last = st.session_state.last_label
            saved_link = ""
            if st.session_state.last_saved_path:
                saved = Path(st.session_state.last_saved_path)
                uri = obsidian_uri(saved)
                rel = saved.relative_to(VAULT_PATH).as_posix()
                saved_link = (
                    f'<a class="obsidian-link" href="{uri}" target="_blank">◆ open in obsidian · {rel}</a>'
                )

            meta_html = ""
            if st.session_state.last_cost is not None:
                cost = st.session_state.last_cost
                tok_in, tok_out = st.session_state.last_tokens or (None, None)
                parts = [f'<span class="meta-val">${cost:.4f}</span>']
                if tok_in is not None:
                    parts.append(f'<span class="meta-val">{tok_in} in</span>')
                if tok_out is not None:
                    parts.append(f'<span class="meta-val">{tok_out} out</span>')
                meta_html = f'<div class="meta-row">{" · ".join(parts)}</div>'

            hero_slot.markdown(
                f'<div class="hero-card">'
                f'<div class="hero-label">last run · {last.lower()}</div>'
                f'<h2 class="hero-headline">complete <em>·</em></h2>'
                f'{saved_link}'
                f'{meta_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        # else: no output and no run in progress — render nothing (skip the
        # idle "run a skill to begin" placeholder card)

    def _clear_output():
        st.session_state.last_output = ""
        st.session_state.last_error = None
        st.session_state.last_saved_path = None
        st.session_state.last_cost = None
        st.session_state.last_tokens = None
        st.session_state.last_label = ""
        st.session_state.last_prompt = None

    # Rendered output (markdown) for last run
    def render_last_output():
        has_content = st.session_state.last_output or st.session_state.last_error
        if has_content and not st.session_state.running:
            with st.container():
                col_view, col_rerun, col_toggle, col_clear = st.columns([3, 1, 0.7, 0.7])
                with col_view:
                    st.markdown(
                        '<div class="caption-mono" style="margin-top:0.8rem;">output</div>',
                        unsafe_allow_html=True,
                    )
                with col_rerun:
                    if st.session_state.last_prompt and st.button(
                        "↻ rerun", key="btn_rerun", use_container_width=True
                    ):
                        start_skill_run(st.session_state.last_label, st.session_state.last_prompt)
                        st.rerun()
                with col_toggle:
                    view_toggle = st.toggle(
                        "md",
                        value=st.session_state.output_view_md,
                        key="view_toggle",
                        help="toggle markdown / raw",
                    )
                    st.session_state.output_view_md = view_toggle
                with col_clear:
                    st.button(
                        "✕",
                        key="btn_clear_output",
                        use_container_width=True,
                        help="clear output",
                        on_click=_clear_output,
                    )

                st.markdown('<div class="output-body">', unsafe_allow_html=True)
                if st.session_state.output_view_md:
                    st.markdown(st.session_state.last_output)
                else:
                    st.code(st.session_state.last_output, language="markdown")
                st.markdown('</div>', unsafe_allow_html=True)

    # ——— RUNNING STATE: live fragment ———
    if st.session_state.running:
        @st.fragment(run_every=0.4)
        def live_hero_fragment():
            elapsed = int(time.time() - (RT.get("start_time") or time.time()))
            phase = RT.get("current_phase") or "starting"
            text_preview = RT.get("text", "")[-2500:]
            phase_log = RT.get("phases", [])
            phase_log_html = ""
            if phase_log:
                last_phases = phase_log[-6:]
                phase_log_html = (
                    f'<div class="phase-line">phases · '
                    + " → ".join(
                        f'<span class="phase-name">{html_escape(pretty_phase(p))}</span>'
                        for p in last_phases
                    )
                    + "</div>"
                )

            preview_html = (
                f'<pre class="stream-output">{html_escape(text_preview)}</pre>'
                if text_preview else ""
            )

            label = st.session_state.active_skill or "skill"
            hero_slot.markdown(
                f'<div class="hero-card running">'
                f'<div class="hero-label"><span class="pulse-dot small"></span>'
                f'running · {elapsed}s · {html_escape(pretty_phase(phase))}</div>'
                f'<h2 class="hero-headline">{html_escape(label.lower())} <em>·</em></h2>'
                f'{phase_log_html}'
                f'{preview_html}'
                f'</div>',
                unsafe_allow_html=True,
            )

            if RT.get("done"):
                finalize_run_if_done(
                    st.session_state.active_skill or "skill",
                    st.session_state.active_prompt or "",
                )
                st.rerun(scope="app")

        live_hero_fragment()

        # Cancel button
        st.markdown('<div class="cancel-btn">', unsafe_allow_html=True)
        if st.button("✕ cancel run", key="btn_cancel", use_container_width=False):
            cancel_current_run()
            finalize_run_if_done(
                st.session_state.active_skill or "skill",
                st.session_state.active_prompt or "",
            )
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        if st.session_state.last_error:
            render_hero_error()
        else:
            render_hero_idle()
        render_last_output()

        # ——— 7-DAY SKILL HISTORY (expandable) ———
        _history_runs = list_runs_last_n_days(7)
        _hist_count = len(_history_runs)
        _hist_label = (
            f"skill history · last 7 days  ·  {_hist_count} run{'s' if _hist_count != 1 else ''}"
            if _hist_count
            else "skill history · last 7 days  ·  no runs yet"
        )
        with st.expander(_hist_label, expanded=False):
            if not _history_runs:
                st.markdown(
                    '<div style="color: var(--fg-dim); font-size: 0.85rem;">'
                    'no skill runs in the last 7 days. once you run a skill, the output '
                    'will be saved here automatically.'
                    '</div>',
                    unsafe_allow_html=True,
                )
            else:
                for _run_path in _history_runs:
                    _parsed = parse_run_file(_run_path)
                    _when_dt = datetime.fromtimestamp(_run_path.stat().st_mtime)
                    _when_str = _when_dt.strftime("%b %d · %H:%M")
                    _skill = _parsed["skill"]
                    _uri = obsidian_uri(_run_path)
                    _inner_label = f"{_when_str}  ·  {_skill}"
                    with st.expander(_inner_label, expanded=False):
                        if _parsed["prompt_short"]:
                            st.markdown(
                                f'<div style="color: var(--fg-mute); font-size: 0.72rem; '
                                f'text-transform: uppercase; letter-spacing: 0.08em; '
                                f'margin-bottom: 0.3rem;">prompt</div>'
                                f'<div style="color: var(--fg-dim); font-size: 0.78rem; '
                                f'background: var(--bg-elev); padding: 0.5rem 0.7rem; '
                                f'border-radius: 4px; margin-bottom: 0.6rem; font-family: monospace;">'
                                f'{html_escape(_parsed["prompt_short"])}{"..." if len(_parsed["prompt_short"]) >= 200 else ""}'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                        st.markdown(
                            f'<div style="color: var(--fg-mute); font-size: 0.72rem; '
                            f'text-transform: uppercase; letter-spacing: 0.08em; '
                            f'margin-bottom: 0.3rem;">output</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(_parsed["output"])
                        st.markdown(
                            f'<div style="margin-top: 0.6rem;">'
                            f'<a href="{_uri}" target="_blank" style="color: var(--accent); '
                            f'font-size: 0.78rem;">◆ open in obsidian ↗</a>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

    # ——— UNIFIED PROMPT + SKILL CHIPS (hidden during run — takeover UX) ———
    if "prompt_input_widget" not in st.session_state:
        st.session_state.prompt_input_widget = ""
    if "last_chip_label" not in st.session_state:
        st.session_state.last_chip_label = None

    def _load_chip(template: str, label: str):
        st.session_state.prompt_input_widget = template
        st.session_state.last_chip_label = label

    def _clear_prompt():
        st.session_state.prompt_input_widget = ""
        st.session_state.last_chip_label = None

    clicked = None

    # Query-param chip loader: <a href="?skill=Label"> → load template
    _skill_q = st.query_params.get("skill")
    if _skill_q and not st.session_state.running:
        for _s in SKILLS:
            if _s["label"] == _skill_q:
                st.session_state.prompt_input_widget = _s["prompt_template"]
                st.session_state.last_chip_label = _s["label"]
                break
        # Preserve the active brand when clearing the skill param
        st.query_params.clear()
        st.query_params["brand"] = _active_brand

    if not st.session_state.running:
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="cpt-cat">prompt</div>', unsafe_allow_html=True)
        with st.form(key="form_unified", clear_on_submit=False, border=False):
            prompt_val = st.text_area(
                "prompt",
                placeholder="type any prompt, or pick a skill below to load a template…",
                label_visibility="collapsed",
                key="prompt_input_widget",
                height=120,
            )
            b1, b2 = st.columns([3, 1])
            with b1:
                submit = st.form_submit_button(
                    "run →",
                    use_container_width=True,
                )
            with b2:
                cleared = st.form_submit_button(
                    "clear",
                    use_container_width=True,
                    on_click=_clear_prompt,
                )
            if submit:
                text = (prompt_val or "").strip()
                if not text:
                    st.warning("prompt empty")
                elif "{input}" in text:
                    st.warning("replace {input} placeholder before running")
                else:
                    label = st.session_state.last_chip_label or "Ad-hoc"
                    clicked = {"label": label, "prompt": text}

        # Skill chips — cpt-skill anchor grid grouped by category
        st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
        # Filter skills by active brand (showing brand-specific + shared)
        _brand_skills = [
            s for s in SKILLS
            if s.get("brand") in (_active_brand, "shared")
        ]
        skills_sorted = sorted(_brand_skills, key=lambda s: s.get("category", "other"))
        _active = st.session_state.last_chip_label
        for category, group in groupby(skills_sorted, key=lambda s: s.get("category", "other")):
            group_list = list(group)
            grid_html = (
                f'<div class="cpt-cat chip-cat">{html_escape(category)}</div>'
                '<div class="cpt-skill-grid">'
            )
            for skill in group_list:
                loaded = " loaded" if skill["label"] == _active else ""
                grid_html += (
                    f'<a class="cpt-skill{loaded}" '
                    f'href="?brand={_active_brand}&skill={quote(skill["label"])}" target="_self" '
                    f'title="{html_escape(skill["description"])}">'
                    f'<span class="cpt-skill-name">{html_escape(skill["label"])}</span>'
                    f'<span class="cpt-skill-desc">{html_escape(skill["description"])}</span>'
                    '</a>'
                )
            grid_html += '</div>'
            st.markdown(grid_html, unsafe_allow_html=True)

        # Trigger run
        if clicked:
            st.session_state.last_label = clicked["label"]
            st.session_state.last_prompt = clicked["prompt"]
            start_skill_run(clicked["label"], clicked["prompt"])
            st.rerun()

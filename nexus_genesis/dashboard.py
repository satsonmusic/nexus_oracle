import base64
import asyncio
import os
import streamlit as st
import streamlit.components.v1 as components
from core.orchestrator import create_nexus_graph

# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="NEXUS GENESIS // SATSON",
    layout="wide",
    page_icon="🧬",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# FULL VISUAL INJECTION — War Room / Intel Ops aesthetic
# ---------------------------------------------------------------------------
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;900&family=Share+Tech+Mono&family=Rajdhani:wght@300;400;600&display=swap" rel="stylesheet">

<style>
/* ── ROOT VARIABLES ─────────────────────────────────────── */
:root {
    --bg-void:    #050810;
    --bg-panel:   #090d1a;
    --bg-card:    #0d1220;
    --bg-hover:   #111827;
    --cyan:       #00e5ff;
    --cyan-dim:   #0099bb;
    --amber:      #ffb300;
    --green:      #00e676;
    --red:        #ff1744;
    --purple:     #aa00ff;
    --text-primary:   #e0f0ff;
    --text-secondary: #5a7a99;
    --text-muted:     #2a3a50;
    --border:     rgba(0,229,255,0.12);
    --border-hot: rgba(0,229,255,0.45);
    --glow-cyan:  0 0 20px rgba(0,229,255,0.3), 0 0 60px rgba(0,229,255,0.1);
    --glow-amber: 0 0 20px rgba(255,179,0,0.4);
}

/* ── GLOBAL RESET ───────────────────────────────────────── */
.stApp {
    background: var(--bg-void) !important;
    font-family: 'Rajdhani', sans-serif !important;
}

/* Animated grid background */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
    animation: gridPulse 8s ease-in-out infinite;
}

@keyframes gridPulse {
    0%, 100% { opacity: 0.6; }
    50%       { opacity: 1.0; }
}

/* Scanline overlay */
.stApp::after {
    content: '';
    position: fixed;
    inset: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,0,0,0.15) 2px,
        rgba(0,0,0,0.15) 4px
    );
    pointer-events: none;
    z-index: 0;
}

/* ── MAIN CONTENT ───────────────────────────────────────── */
.main .block-container {
    padding: 1.5rem 2rem 2rem !important;
    max-width: 100% !important;
    position: relative;
    z-index: 1;
}

/* ── HEADER INJECTION ───────────────────────────────────── */
header[data-testid="stHeader"] {
    background: rgba(5,8,16,0.95) !important;
    border-bottom: 1px solid var(--border) !important;
    backdrop-filter: blur(10px);
}

/* ── SIDEBAR ────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: var(--bg-panel) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .block-container {
    padding: 1.5rem 1rem !important;
}
section[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
}
section[data-testid="stSidebar"] .stSlider > div > div {
    background: var(--bg-card) !important;
}
section[data-testid="stSidebar"] .stSlider [data-baseweb="slider"] div[role="slider"] {
    background: var(--cyan) !important;
    box-shadow: var(--glow-cyan) !important;
}

/* ── TEXT ELEMENTS ──────────────────────────────────────── */
h1, h2, h3, p, label, .stMarkdown {
    color: var(--text-primary) !important;
    font-family: 'Rajdhani', sans-serif !important;
}

/* ── TEXT AREA ──────────────────────────────────────────── */
.stTextArea label {
    color: var(--cyan) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
}
.stTextArea textarea {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    color: var(--text-primary) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.9rem !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
    caret-color: var(--cyan) !important;
}
.stTextArea textarea:focus {
    border-color: var(--cyan) !important;
    box-shadow: var(--glow-cyan) !important;
    outline: none !important;
}

/* ── FILE UPLOADER ──────────────────────────────────────── */
.stFileUploader label {
    color: var(--cyan) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
}
.stFileUploader > div {
    background: var(--bg-card) !important;
    border: 1px dashed var(--border-hot) !important;
    border-radius: 4px !important;
    transition: border-color 0.3s !important;
}
.stFileUploader > div:hover {
    border-color: var(--cyan) !important;
    box-shadow: var(--glow-cyan) !important;
}

/* ── BUTTONS ────────────────────────────────────────────── */
.stButton > button {
    background: transparent !important;
    border: 1px solid var(--cyan) !important;
    border-radius: 2px !important;
    color: var(--cyan) !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s ease !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button::before {
    content: '';
    position: absolute;
    inset: 0;
    background: var(--cyan);
    opacity: 0;
    transition: opacity 0.2s;
}
.stButton > button:hover {
    background: rgba(0,229,255,0.08) !important;
    box-shadow: var(--glow-cyan) !important;
    transform: translateY(-1px) !important;
}
.stButton > button:active {
    transform: translateY(0) scale(0.98) !important;
}

/* ── METRICS ────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-left: 3px solid var(--cyan) !important;
    border-radius: 2px !important;
    padding: 1rem !important;
}
[data-testid="stMetricLabel"] {
    color: var(--text-secondary) !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    color: var(--cyan) !important;
    font-family: 'Orbitron', sans-serif !important;
    font-size: 1.6rem !important;
    text-shadow: var(--glow-cyan) !important;
}

/* ── ALERTS ─────────────────────────────────────────────── */
.stAlert {
    background: var(--bg-card) !important;
    border-radius: 2px !important;
    font-family: 'Share Tech Mono', monospace !important;
    font-size: 0.85rem !important;
}
div[data-baseweb="notification"] {
    border-radius: 2px !important;
}

/* ── SUCCESS ─────────────────────────────────────────────── */
.stSuccess {
    background: rgba(0,230,118,0.05) !important;
    border: 1px solid rgba(0,230,118,0.3) !important;
    color: var(--green) !important;
}

/* ── WARNING ─────────────────────────────────────────────── */
.stWarning {
    background: rgba(255,179,0,0.05) !important;
    border: 1px solid rgba(255,179,0,0.3) !important;
    color: var(--amber) !important;
}

/* ── ERROR ───────────────────────────────────────────────── */
.stError {
    background: rgba(255,23,68,0.05) !important;
    border: 1px solid rgba(255,23,68,0.3) !important;
    color: var(--red) !important;
}

/* ── CODE BLOCKS ─────────────────────────────────────────── */
.stCode, code, pre {
    background: var(--bg-void) !important;
    border: 1px solid var(--border) !important;
    border-radius: 2px !important;
    font-family: 'Share Tech Mono', monospace !important;
    color: var(--cyan) !important;
}

/* ── DIVIDER ─────────────────────────────────────────────── */
hr {
    border-color: var(--border) !important;
    margin: 1.5rem 0 !important;
}

/* ── CUSTOM SCROLLBAR ────────────────────────────────────── */
::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-void); }
::-webkit-scrollbar-thumb { background: var(--cyan-dim); border-radius: 2px; }

/* ── ANIMATIONS ──────────────────────────────────────────── */
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes pulse-border {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0,229,255,0.2); }
    50%       { box-shadow: 0 0 0 6px rgba(0,229,255,0); }
}

/* ── LOG ENTRIES ─────────────────────────────────────────── */
.log-entry {
    animation: fadeInUp 0.3s ease forwards;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: var(--text-secondary);
    padding: 0.25rem 0;
    border-bottom: 1px solid var(--text-muted);
}
.log-entry strong { color: var(--cyan); }

/* Slider track color */
[data-baseweb="slider"] [data-testid="stSlider"] {
    accent-color: var(--cyan) !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.markdown("""
<div style="
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0 1.5rem;
    border-bottom: 1px solid rgba(0,229,255,0.12);
    margin-bottom: 1.5rem;
">
    <div style="display: flex; align-items: baseline; gap: 1.2rem;">
        <span style="
            font-family: 'Orbitron', sans-serif;
            font-size: 1.6rem;
            font-weight: 900;
            color: #00e5ff;
            letter-spacing: 0.1em;
            text-shadow: 0 0 30px rgba(0,229,255,0.6), 0 0 60px rgba(0,229,255,0.2);
        ">NEXUS GENESIS</span>
        <span style="
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.7rem;
            color: rgba(0,229,255,0.4);
            letter-spacing: 0.3em;
            padding: 2px 8px;
            border: 1px solid rgba(0,229,255,0.15);
            border-radius: 2px;
        ">v2.0 // SOVEREIGN</span>
    </div>
    <div style="display: flex; align-items: center; gap: 1.5rem;">
        <div style="
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.65rem;
            color: rgba(0,229,255,0.35);
            letter-spacing: 0.2em;
            text-align: right;
        ">
            OPERATOR<br>
            <span style="
                font-family: 'Orbitron', sans-serif;
                font-size: 0.85rem;
                font-weight: 600;
                color: #ffb300;
                text-shadow: 0 0 15px rgba(255,179,0,0.5);
                letter-spacing: 0.25em;
            ">SATSON</span>
        </div>
        <div style="
            width: 8px; height: 8px;
            border-radius: 50%;
            background: #00e676;
            box-shadow: 0 0 12px rgba(0,230,118,0.8);
            animation: blink 2s ease-in-out infinite;
        "></div>
    </div>
</div>

<style>
@keyframes blink {
    0%, 100% { opacity: 1; box-shadow: 0 0 12px rgba(0,230,118,0.8); }
    50%       { opacity: 0.3; box-shadow: 0 0 4px rgba(0,230,118,0.2); }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# INSTRUCTIONS BANNER
# ---------------------------------------------------------------------------
st.markdown("""
<div style="
    background: rgba(0,229,255,0.02);
    border: 1px solid rgba(0,229,255,0.08);
    border-left: 3px solid #ffb300;
    border-radius: 2px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 1.2rem;
    display: flex;
    gap: 1.5rem;
    align-items: flex-start;
">
    <div style="flex:1;">
        <div style="font-family:'Orbitron',sans-serif;font-size:0.62rem;font-weight:600;letter-spacing:0.25em;color:#ffb300;margin-bottom:0.5rem;">// OPERATOR BRIEFING</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.72rem;color:rgba(0,229,255,0.6);line-height:1.7;">
            This is <span style="color:#00e5ff;">NEXUS GENESIS</span> — a 14-node sovereign AI research engine.
            It does not chat. It <em>thinks</em>: planning, verifying, peer-reviewing, and formally proving before delivering a verdict.
            Expect 2–4 minutes per run. Ask it hard questions.
        </div>
    </div>
    <div style="min-width:220px;">
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:rgba(255,179,0,0.5);letter-spacing:0.15em;margin-bottom:0.4rem;">SUGGESTED DIRECTIVES</div>
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.62rem;color:rgba(0,229,255,0.35);line-height:1.9;">
            → Compare RAG vs fine-tuning for my domain<br>
            → Write a Python class with full error handling<br>
            → Analyze causal impact of X on Y<br>
            → Design a scalable microservices architecture<br>
            → Audit this code for security vulnerabilities
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SESSION STATE BOOTSTRAP
# ---------------------------------------------------------------------------
if "app" not in st.session_state:
    st.session_state.app = create_nexus_graph()
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "nexus_session_001"
if "status_log" not in st.session_state:
    st.session_state.status_log = []
if "nexus_running" not in st.session_state:
    st.session_state.nexus_running = False
if "route_mode" not in st.session_state:
    st.session_state.route_mode = None   # "SOVEREIGN" | "QUICK" | "CODE"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []   # [{role, content}]
if "quick_answer" not in st.session_state:
    st.session_state.quick_answer = ""

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 1.5rem;">
        <div style="
            font-family: 'Orbitron', sans-serif;
            font-size: 0.65rem;
            font-weight: 600;
            letter-spacing: 0.3em;
            color: rgba(0,229,255,0.5);
            text-transform: uppercase;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(0,229,255,0.08);
        ">System Status</div>
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <div style="width:6px;height:6px;border-radius:50%;background:#00e676;box-shadow:0 0 8px #00e676;"></div>
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:#5a7a99;letter-spacing:0.1em;">ORCHESTRATOR ONLINE</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <div style="width:6px;height:6px;border-radius:50%;background:#00e676;box-shadow:0 0 8px #00e676;"></div>
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:#5a7a99;letter-spacing:0.1em;">KNOWLEDGE GRAPH READY</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <div style="width:6px;height:6px;border-radius:50%;background:#00e676;box-shadow:0 0 8px #00e676;"></div>
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:#5a7a99;letter-spacing:0.1em;">EMPIRICAL EYE ARMED</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:6px;height:6px;border-radius:50%;background:#ffb300;box-shadow:0 0 8px #ffb300;"></div>
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.7rem;color:#5a7a99;letter-spacing:0.1em;">AWAITING DIRECTIVE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="
        font-family: 'Orbitron', sans-serif;
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.3em;
        color: rgba(0,229,255,0.5);
        text-transform: uppercase;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid rgba(0,229,255,0.08);
    ">Mission Parameters</div>
    """, unsafe_allow_html=True)

    max_iters      = st.slider("MAX EVOLUTIONARY ROUNDS", 1, 5, 3)
    min_confidence = st.slider("MIN CONFIDENCE GATE", 0.0, 1.0, 0.75)

    st.markdown("""
    <div style="
        margin-top: 2rem;
        padding: 0.75rem;
        border: 1px solid rgba(0,229,255,0.08);
        border-radius: 2px;
        background: rgba(0,229,255,0.02);
    ">
        <div style="
            font-family: 'Share Tech Mono', monospace;
            font-size: 0.6rem;
            color: rgba(0,229,255,0.2);
            letter-spacing: 0.15em;
            line-height: 1.8;
        ">
            PROJECT-12 // NEXUS ORACLE<br>
            PHASE 2: INTELLIGENCE ACTIVE<br>
            BUILT BY SATSON<br>
            CLASSIFICATION: SOVEREIGN
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-family:'Orbitron',sans-serif;font-size:0.6rem;font-weight:600;
        letter-spacing:0.25em;color:rgba(255,179,0,0.6);margin-bottom:0.75rem;">
        INTELLIGENCE FEED</div>
    """, unsafe_allow_html=True)

    try:
        import sys as _sys
        _sys.path.insert(0, str(__file__).replace("dashboard.py",""))
        from nexus_intelligence import get_recent_signals, get_signal_stats
        stats   = get_signal_stats()
        signals = get_recent_signals(limit=5)

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Signals", stats["total"])
        with col_b:
            st.metric("Triggered", stats["triggered"])

        if signals:
            for sig in signals[:4]:
                color = "#ffb300" if sig["triggered"] else "rgba(0,229,255,0.4)"
                st.markdown(f"""
                <div style="padding:5px 0;border-bottom:1px solid rgba(0,229,255,0.05);">
                    <div style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;
                        color:{color};letter-spacing:0.08em;line-height:1.6;">
                        [{sig['score']:.2f}] {(sig['title'] or sig['url'])[:40]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.58rem;
                color:rgba(0,229,255,0.15);letter-spacing:0.1em;">
                No signals yet.<br>Run: python nexus_intelligence.py watch
            </div>
            """, unsafe_allow_html=True)
    except ImportError:
        st.markdown("""
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.58rem;
            color:rgba(0,229,255,0.15);letter-spacing:0.1em;">
            Place nexus_intelligence.py in project root to activate.
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ASYNC RUNNER — with live UI feed
# ---------------------------------------------------------------------------
NODE_MESSAGES = {
    "llmpick":        ("⚡", "#00e5ff",  "Selecting optimal model for this session..."),
    "tom":            ("🧠", "#7c5cbf",  "Profiling your cognitive state & user model..."),
    "load_balancer":  ("⚖",  "#0097a7",  "Calibrating urgency and cognitive mode..."),
    "visual_parser":  ("👁",  "#6a1b9a",  "Parsing visual intelligence..."),
    "privacy":        ("🛡",  "#e65100",  "Scrubbing sensitive data from context..."),
    "broadcast":      ("📡", "#00838f",  "Broadcasting to global workspace..."),
    "visionary":      ("🔭", "#00b0ff",  "Drafting sovereign research plan..."),
    "diagnostics":    ("🔬", "#00c853",  "Running hallucination diagnostics..."),
    "coder":          ("⚙",  "#0288d1",  "Modifying system state — writing code..."),
    "testing":        ("🧪", "#f9a825",  "Executing evolutionary unit tests..."),
    "skeptic":        ("🔍", "#e53935",  "Performing global peer review..."),
    "judge":          ("⚖",  "#ffd600",  "Enforcing formal rigor & constitutional law..."),
    "risk":           ("🚨", "#ff6d00",  "Evaluating decision risk gate..."),
    "commander":      ("🎯", "#aa00ff",  "Synthesising strategic status report..."),
    "manifesto":      ("📜", "#00e5ff",  "Generating sovereign dossier..."),
    "memory_surgeon": ("💾", "#aa00ff",  "Updating your cognitive profile..."),
    "evolution":      ("🧬", "#76ff03",  "Proposing system evolution..."),
}

def _render_live_feed(log: list, current_node: str = "", error: str = "") -> str:
    """Build the HTML for the live feed panel."""
    rows = ""
    for entry in log:
        is_err = "❌" in entry
        clean  = entry.replace("✅","").replace("❌","").replace("**","").strip()
        key    = clean.split()[0].lower() if clean else ""
        icon, color, msg = NODE_MESSAGES.get(key, ("▶", "#00e5ff", clean))
        status_color = "#ff1744" if is_err else color
        rows += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:7px 0;
            border-bottom:1px solid rgba(0,229,255,0.05);
            animation:fadeIn 0.3s ease forwards;">
          <span style="font-size:0.85rem;min-width:20px;text-align:center;">{icon}</span>
          <div style="flex:1;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;
                color:{status_color};letter-spacing:0.1em;text-transform:uppercase;">{key.upper()}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.65rem;
                color:{status_color}99;line-height:1.4;">{msg}</div>
          </div>
          <span style="font-size:0.6rem;color:{status_color};opacity:0.6;">{"❌" if is_err else "✓"}</span>
        </div>"""

    # Active node pulsing at bottom
    if current_node:
        icon, color, msg = NODE_MESSAGES.get(current_node.lower(), ("▶", "#00e5ff", "Processing..."))
        rows += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:7px 0;
            animation:pulse 1s ease-in-out infinite;">
          <span style="font-size:0.85rem;min-width:20px;text-align:center;">{icon}</span>
          <div style="flex:1;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;
                color:{color};letter-spacing:0.1em;text-transform:uppercase;">{current_node.upper()}</div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.65rem;
                color:{color}cc;line-height:1.4;">{msg}</div>
          </div>
          <span style="font-size:0.7rem;color:{color};">●</span>
        </div>"""

    if error:
        rows += f"""
        <div style="padding:8px;background:rgba(255,23,68,0.05);border:1px solid rgba(255,23,68,0.2);
            border-radius:2px;margin-top:6px;">
          <span style="font-family:'Share Tech Mono',monospace;font-size:0.62rem;color:#ff1744;">{error}</span>
        </div>"""

    return f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
      *{{box-sizing:border-box;}} body{{margin:0;padding:6px 4px;background:transparent;}}
      @keyframes fadeIn{{from{{opacity:0;transform:translateX(-6px)}}to{{opacity:1;transform:translateX(0)}}}}
      @keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}
    </style>
    <div style="max-height:360px;overflow-y:auto;">{rows if rows else
        '<div style="font-family:Share Tech Mono,monospace;font-size:0.62rem;color:rgba(0,229,255,0.15);padding:2rem;text-align:center;">NEXUS STANDING BY...</div>'
    }</div>"""


async def run_nexus(inputs: dict | None, live_placeholder=None):
    try:
        async for event in st.session_state.app.astream(
            inputs, config=config, stream_mode="updates"
        ):
            for node_name, node_data in event.items():
                st.session_state.status_log.append(f"✅ **{node_name.upper()}**")
                if node_name == "judge" and node_data and node_data.get("judge_verdict"):
                    st.session_state["judge_verdict"] = node_data["judge_verdict"]
                # ── LIVE UPDATE — write directly to placeholder ──────────
                if live_placeholder is not None:
                    html = _render_live_feed(
                        st.session_state.status_log,
                        current_node="",
                    )
                    live_placeholder.markdown(
                        f'<div style="background:rgba(0,229,255,0.02);border:1px solid rgba(0,229,255,0.08);'
                        f'border-radius:2px;padding:0.5rem;">{html}</div>',
                        unsafe_allow_html=True
                    )
    except Exception as e:
        st.session_state.status_log.append(f"❌ Engine error: {e}")
        if live_placeholder is not None:
            live_placeholder.markdown(
                f'<div style="color:#ff1744;font-family:Share Tech Mono,monospace;font-size:0.7rem;">'
                f'ENGINE ERROR: {e}</div>',
                unsafe_allow_html=True
            )

# ---------------------------------------------------------------------------
# SMART ROUTER — classifies prompt before touching the pipeline
# ---------------------------------------------------------------------------
def classify_prompt(task: str) -> dict:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    import json, re as _re
    router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    prompt = (
        "You are a prompt router for a sovereign AI research engine. "
        "Classify the prompt into ONE mode:\n"
        "SOVEREIGN: deep research, causal analysis, architecture decisions, scientific verification.\n"
        "CODE: needs working executable code (write X in Python, build X, create X).\n"
        "QUICK: simple fact, lookup, current event, definition.\n"
        "Return ONLY JSON: {\"mode\": \"SOVEREIGN\"|\"QUICK\"|\"CODE\", \"reason\": \"one sentence\"}"
    )
    try:
        response = router_llm.invoke([SystemMessage(content=prompt), HumanMessage(content=f"Classify: {task}")])
        data = json.loads(_re.search(r"\{.*\}", response.content, _re.DOTALL).group())
        return {"mode": data.get("mode", "SOVEREIGN"), "reason": data.get("reason", "")}
    except Exception:
        return {"mode": "SOVEREIGN", "reason": "Classification failed — defaulting to full pipeline."}


def run_quick_response(task: str, mode: str) -> str:
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    if mode == "CODE":
        sys_prompt = (
            "You are an expert software engineer. Deliver a complete, working implementation. "
            "No placeholders. Include all imports, clear inline comments, and a usage example at the bottom. "
            "Use markdown code blocks."
        )
    else:
        sys_prompt = (
            "You are a concise research assistant. Answer directly and accurately. Be brief but complete."
        )
        try:
            from langchain_tavily import TavilySearch
            web_ctx = TavilySearch(max_results=2).invoke(task[:120])
            task = task + "\n\nWeb context: " + str(web_ctx)
        except Exception:
            pass
    try:
        return llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=task)]).content
    except Exception as e:
        return f"Error generating response: {e}"


# ---------------------------------------------------------------------------
# APPROVAL CALLBACKS
# ---------------------------------------------------------------------------
def approve_and_continue():
    st.session_state.app.update_state(
        config, {"approval_granted": True, "proposed_edit": None}
    )
    asyncio.run(run_nexus(None))
    st.session_state.nexus_running = False

def reject_and_clear():
    st.session_state.status_log.append("🚫 Edit rejected.")
    st.session_state.nexus_running = False
    st.session_state.thread_id = f"nexus_{os.urandom(4).hex()}"

# ---------------------------------------------------------------------------
# MAIN LAYOUT
# ---------------------------------------------------------------------------
# Task input
st.markdown("""
<div style="
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.3em;
    color: rgba(0,229,255,0.5);
    text-transform: uppercase;
    margin-bottom: 0.4rem;
">// DIRECTIVE INPUT</div>
""", unsafe_allow_html=True)

task_input = st.text_area(
    "ENTER RESEARCH DIRECTIVE:",
    placeholder="e.g., Analyse the causal relationship between training compute and model capability...",
    height=110,
    label_visibility="collapsed"
)

uploaded_file = st.file_uploader(
    "// ATTACH VISUAL INTELLIGENCE (PNG · JPG)",
    type=["png", "jpg", "jpeg"],
    label_visibility="visible"
)
if uploaded_file:
    st.session_state["uploaded_image_base64"] = base64.b64encode(
        uploaded_file.getvalue()
    ).decode("utf-8")
    col_img, _ = st.columns([1, 3])
    with col_img:
        st.image(uploaded_file, caption="VISUAL INTEL INGESTED", use_container_width=True)

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

col1, col2 = st.columns([1.1, 0.9])

# Live feed placeholder — written to during pipeline execution
if "live_feed_placeholder" not in st.session_state:
    st.session_state.live_feed_placeholder = None

# ---------------------------------------------------------------------------
# LEFT — LIVE FEED (during run) or EVOLUTION DISPLAY (idle/done)
# ---------------------------------------------------------------------------
with col1:
    # Section header
    is_running_now = st.session_state.get("nexus_running", False)
    header_label = "Live Intelligence Feed" if is_running_now else "System Evolution"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.8rem;">
        <span style="font-family:'Orbitron',sans-serif;font-size:0.7rem;font-weight:600;
            letter-spacing:0.25em;color:rgba(0,229,255,0.7);text-transform:uppercase;">
            {header_label}</span>
        <div style="flex:1;height:1px;background:rgba(0,229,255,0.08);"></div>
        {"<span style='font-family:Share Tech Mono,monospace;font-size:0.55rem;color:#00e676;letter-spacing:0.15em;animation:blink 1s infinite;'>● LIVE</span>" if is_running_now else ""}
    </div>
    """, unsafe_allow_html=True)

    # Create the live feed placeholder — this gets written to mid-run
    live_feed = st.empty()
    st.session_state.live_feed_placeholder = live_feed

    # Show live feed content if we have a log OR are running
    if st.session_state.status_log or is_running_now:
        feed_html = _render_live_feed(st.session_state.status_log)
        live_feed.markdown(
            f'<div style="background:rgba(0,229,255,0.02);border:1px solid rgba(0,229,255,0.08);'
            f'border-radius:2px;padding:0.5rem;">{feed_html}</div>',
            unsafe_allow_html=True
        )
    else:
        # Idle — show the chip→robot sprite below the placeholder
        live_feed.empty()

    TOTAL_NODES = 14
    NODE_ORDER  = ["TOM","LOAD_BALANCER","VISUAL_PARSER","PRIVACY","BROADCAST",
                   "VISIONARY","DIAGNOSTICS","CODER","TESTING","SKEPTIC",
                   "JUDGE","MANIFESTO","MEMORY_SURGEON","EVOLUTION"]
    NODE_LABELS = {"TOM":"Theory of Mind","LOAD_BALANCER":"Load Balancer",
                   "VISUAL_PARSER":"Visual Cortex","PRIVACY":"Armor",
                   "BROADCAST":"Consciousness","VISIONARY":"Visionary",
                   "DIAGNOSTICS":"Ego","CODER":"Architect","TESTING":"Sandbox",
                   "SKEPTIC":"Skeptic","JUDGE":"Judge","MANIFESTO":"Manifesto",
                   "MEMORY_SURGEON":"Memory Surgeon","EVOLUTION":"Genesis"}

    completed = [e.replace("✅","").replace("**","").strip().split()[0]
                 for e in st.session_state.status_log if "✅" in e]
    # count unique nodes completed (cap at 14)
    seen = []
    for n in completed:
        key = n.upper()
        if key in NODE_ORDER and key not in seen:
            seen.append(key)
    pct = min(100, int(len(seen) / TOTAL_NODES * 100))
    last_node = NODE_LABELS.get(seen[-1], seen[-1]) if seen else "STANDBY"
    is_done   = pct >= 100 or ("EVOLUTION" in seen)

    components.html(f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@700&display=swap');
      *{{box-sizing:border-box;}} body{{margin:0;padding:8px 4px;background:transparent;}}
      @keyframes idleBob{{0%,100%{{transform:translateY(0)}} 50%{{transform:translateY(-5px)}}}}
      @keyframes blink2{{0%,88%,100%{{transform:scaleY(1)}} 94%{{transform:scaleY(0.1)}}}}
      @keyframes chipPulse{{0%,100%{{opacity:0.6}} 50%{{opacity:1}}}}
      @keyframes glowPulse{{0%,100%{{filter:drop-shadow(0 0 4px #00e5ff)}} 50%{{filter:drop-shadow(0 0 12px #00e5ff)}}}}
      @keyframes laugh{{0%{{transform:rotate(-8deg)translateY(0)}}25%{{transform:rotate(8deg)translateY(-4px)}}50%{{transform:rotate(-5deg)translateY(0)}}75%{{transform:rotate(5deg)translateY(-3px)}}100%{{transform:rotate(-8deg)translateY(0)}}}}
      @keyframes pointArm{{0%,100%{{transform:translateX(0)}}50%{{transform:translateX(7px)}}}}
      @keyframes barShine{{0%{{background-position:200% center}}100%{{background-position:-200% center}}}}
      .bob{{animation:idleBob 2.5s ease-in-out infinite;}}
      .eyes{{animation:blink2 4s ease-in-out infinite;transform-origin:center;}}
      .chip-pulse{{animation:chipPulse 1.5s ease-in-out infinite;}}
      .glow{{animation:glowPulse 2s ease-in-out infinite;}}
      .laugh-body{{animation:laugh 0.5s ease-in-out infinite;transform-origin:bottom center;}}
      .point{{animation:pointArm 0.6s ease-in-out infinite;}}
      .bar-fill{{
        height:100%;border-radius:2px;
        background:linear-gradient(90deg,#00e5ff,#7c5cbf,#00e5ff);
        background-size:200% 100%;
        animation:barShine 2s linear infinite;
        transition:width 0.5s ease;
      }}
    </style>

    <div style="display:flex;flex-direction:column;align-items:center;gap:16px;padding:8px 0 4px;">

      <!-- EVOLUTION STAGE LABEL -->
      <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;letter-spacing:0.25em;color:rgba(0,229,255,0.3);text-transform:uppercase;">
        {'GENESIS COMPLETE' if is_done else ('EVOLVING...' if pct > 0 else 'AWAITING DIRECTIVE')}
      </div>

      <!-- SPRITE: chips at 0%, partial at 1-99%, full robot at 100% -->
      {'<!-- DONE: celebration robot --><div class="laugh-body">' if is_done else ('<div class="bob">' if pct > 0 else '<div class="bob chip-pulse glow">')}
        <svg width="120" height="150" viewBox="0 0 120 150" xmlns="http://www.w3.org/2000/svg">

          <!-- ═══ MICROCHIP BASE (always visible, fades as robot emerges) ═══ -->
          <g opacity="{max(0.05, 1 - pct/100 * 1.4)}">
            <!-- chip body -->
            <rect x="35" y="45" width="50" height="50" rx="4" fill="#0d1220" stroke="#00e5ff" stroke-width="1.5"/>
            <!-- chip grid lines -->
            <line x1="35" y1="61" x2="85" y2="61" stroke="#00e5ff" stroke-width="0.4" opacity="0.4"/>
            <line x1="35" y1="70" x2="85" y2="70" stroke="#00e5ff" stroke-width="0.4" opacity="0.4"/>
            <line x1="35" y1="79" x2="85" y2="79" stroke="#00e5ff" stroke-width="0.4" opacity="0.4"/>
            <line x1="51" y1="45" x2="51" y2="95" stroke="#00e5ff" stroke-width="0.4" opacity="0.4"/>
            <line x1="60" y1="45" x2="60" y2="95" stroke="#00e5ff" stroke-width="0.4" opacity="0.4"/>
            <line x1="69" y1="45" x2="69" y2="95" stroke="#00e5ff" stroke-width="0.4" opacity="0.4"/>
            <!-- chip pins left -->
            <line x1="20" y1="53" x2="35" y2="53" stroke="#00e5ff" stroke-width="1.2"/><rect x="14" y="51" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <line x1="20" y1="63" x2="35" y2="63" stroke="#00e5ff" stroke-width="1.2"/><rect x="14" y="61" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <line x1="20" y1="73" x2="35" y2="73" stroke="#00e5ff" stroke-width="1.2"/><rect x="14" y="71" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <line x1="20" y1="83" x2="35" y2="83" stroke="#00e5ff" stroke-width="1.2"/><rect x="14" y="81" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <!-- chip pins right -->
            <line x1="85" y1="53" x2="100" y2="53" stroke="#00e5ff" stroke-width="1.2"/><rect x="100" y="51" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <line x1="85" y1="63" x2="100" y2="63" stroke="#00e5ff" stroke-width="1.2"/><rect x="100" y="61" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <line x1="85" y1="73" x2="100" y2="73" stroke="#00e5ff" stroke-width="1.2"/><rect x="100" y="71" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <line x1="85" y1="83" x2="100" y2="83" stroke="#00e5ff" stroke-width="1.2"/><rect x="100" y="81" width="6" height="4" rx="1" fill="#00e5ff" opacity="0.7"/>
            <!-- chip core label -->
            <text x="60" y="73" text-anchor="middle" font-family="monospace" font-size="7" fill="#00e5ff" opacity="0.8">NEXUS</text>
          </g>

          <!-- ═══ ROBOT EMERGES (opacity grows with pct) ═══ -->
          <g opacity="{min(1.0, pct/100 * 1.5)}">
            <!-- Head -->
            <rect x="38" y="8" width="44" height="36" rx="8" fill="#0d1220" stroke="{'#76ff03' if is_done else '#00e5ff'}" stroke-width="1.8"/>
            <!-- Eyes -->
            <g class="eyes">
              <rect x="46" y="19" width="9" height="9" rx="2" fill="{'#76ff03' if is_done else '#00e5ff'}"/>
              <rect x="65" y="19" width="9" height="9" rx="2" fill="{'#76ff03' if is_done else '#00e5ff'}"/>
            </g>
            <!-- Mouth: smile if done, neutral if running -->
            {'<path d="M48 35 Q60 43 72 35" fill="none" stroke="#76ff03" stroke-width="2" stroke-linecap="round"/>' if is_done else '<rect x="50" y="34" width="20" height="3" rx="1.5" fill="#00e5ff" opacity="0.6"/>'}
            <!-- Neck -->
            <rect x="54" y="44" width="12" height="7" fill="#0d1220" stroke="{'#76ff03' if is_done else '#00e5ff'}" stroke-width="1"/>
            <!-- Body -->
            <rect x="28" y="51" width="64" height="40" rx="6" fill="#0d1220" stroke="{'#76ff03' if is_done else '#ffb300'}" stroke-width="1.8"/>
            <!-- Chest badge -->
            <rect x="47" y="60" width="26" height="20" rx="3" fill="{'#76ff0322' if is_done else '#ffb30022'}" stroke="{'#76ff03' if is_done else '#ffb300'}" stroke-width="1"/>
            <text x="60" y="74" text-anchor="middle" font-family="monospace" font-size="10" fill="{'#76ff03' if is_done else '#ffb300'}" font-weight="700">S</text>
            <!-- Arms -->
            {'<g class="point"><rect x="4" y="52" width="24" height="14" rx="4" fill="#0d1220" stroke="#76ff03" stroke-width="1.5"/><rect x="92" y="52" width="24" height="10" rx="4" fill="#0d1220" stroke="#76ff03" stroke-width="1.5"/><rect x="114" y="53" width="10" height="6" rx="2" fill="#0d1220" stroke="#76ff03" stroke-width="1"/></g>' if is_done else '<rect x="6" y="52" width="22" height="30" rx="5" fill="#0d1220" stroke="#00e5ff" stroke-width="1.5"/><rect x="92" y="52" width="22" height="30" rx="5" fill="#0d1220" stroke="#00e5ff" stroke-width="1.5"/>'}
            <!-- Legs -->
            <rect x="35" y="91" width="18" height="26" rx="5" fill="#0d1220" stroke="{'#76ff03' if is_done else '#00e5ff'}" stroke-width="1.5"/>
            <rect x="67" y="91" width="18" height="26" rx="5" fill="#0d1220" stroke="{'#76ff03' if is_done else '#00e5ff'}" stroke-width="1.5"/>
            <!-- Progress dots on body (light up per node) -->
            {''.join([f'<circle cx="{33 + (i%7)*8}" cy="{117 + (i//7)*8}" r="2.5" fill="{"#00e5ff" if i < len(seen) else "#0d1220"}" stroke="#00e5ff" stroke-width="0.8" opacity="0.7"/>' for i in range(14)])}
          </g>
        </svg>
      </div>

      <!-- CURRENT NODE LABEL -->
      <div style="font-family:'Share Tech Mono',monospace;font-size:0.68rem;color:rgba(0,229,255,0.7);letter-spacing:0.15em;text-align:center;">
        {'ALL NODES COMPLETE' if is_done else last_node.upper()}
      </div>

      <!-- PROGRESS BAR -->
      <div style="width:85%;max-width:280px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
          <span style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;color:rgba(0,229,255,0.3);letter-spacing:0.15em;">PIPELINE PROGRESS</span>
          <span style="font-family:'Orbitron',monospace;font-size:0.6rem;color:{'#76ff03' if is_done else '#00e5ff'};font-weight:700;">{pct}%</span>
        </div>
        <div style="height:6px;background:rgba(0,229,255,0.08);border-radius:3px;border:1px solid rgba(0,229,255,0.12);overflow:hidden;">
          <div class="bar-fill" style="width:{pct}%;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:5px;">
          <span style="font-family:'Share Tech Mono',monospace;font-size:0.5rem;color:rgba(0,229,255,0.2);">{len(seen)}/{TOTAL_NODES} NODES</span>
          <span style="font-family:'Share Tech Mono',monospace;font-size:0.5rem;color:rgba(0,229,255,0.2);">{'SOVEREIGN' if is_done else 'PROCESSING'}</span>
        </div>
      </div>

    </div>
    """, height=420)

# ---------------------------------------------------------------------------
# RIGHT — DECISION CENTER
# ---------------------------------------------------------------------------
with col2:
    st.markdown("""
    <div style="
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 0.8rem;
    ">
        <span style="
            font-family: 'Orbitron', sans-serif;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.25em;
            color: rgba(0,229,255,0.7);
            text-transform: uppercase;
        ">Decision Center</span>
        <div style="flex:1; height:1px; background: rgba(0,229,255,0.08);"></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        current      = st.session_state.app.get_state(config)
        state_values = current.values if current else {}
    except Exception:
        state_values = {}

    # Merge session-captured verdict into state_values for display
    if st.session_state.get("judge_verdict") and not state_values.get("judge_verdict"):
        state_values["judge_verdict"] = st.session_state["judge_verdict"]

    pending_edit = state_values.get("proposed_edit")

    if pending_edit:
        st.markdown("""
        <div style="
            background: rgba(255,179,0,0.04);
            border: 1px solid rgba(255,179,0,0.25);
            border-left: 3px solid #ffb300;
            border-radius: 2px;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
        ">
            <span style="
                font-family: 'Orbitron', sans-serif;
                font-size: 0.65rem;
                font-weight: 600;
                letter-spacing: 0.25em;
                color: #ffb300;
            ">⚠ SAFETY GATE TRIGGERED</span><br>
            <span style="
                font-family: 'Share Tech Mono', monospace;
                font-size: 0.72rem;
                color: rgba(255,179,0,0.6);
            ">NEXUS REQUESTING FILE MODIFICATION — HUMAN AUTHORIZATION REQUIRED</span>
        </div>
        """, unsafe_allow_html=True)

        st.code(pending_edit, language="python")
        c1, c2 = st.columns(2)
        with c1:
            st.button("✅ APPROVE & WRITE", on_click=approve_and_continue, use_container_width=True)
        with c2:
            st.button("❌ TERMINATE", on_click=reject_and_clear, use_container_width=True)

    else:
        current_mode = st.session_state.get("route_mode")
        quick_ans    = st.session_state.get("quick_answer", "")

        if current_mode in ("CODE", "QUICK") and quick_ans:
            # ── CODE / QUICK: show delivery confirmation, not a score ──────
            icon  = "⌨" if current_mode == "CODE" else "⚡"
            label = "CODE DELIVERED" if current_mode == "CODE" else "ANSWER RETRIEVED"
            color = "#ffb300" if current_mode == "CODE" else "#00e676"
            st.markdown(f"""
            <div style="background:{color}08;border:1px solid {color}33;border-left:3px solid {color};
                border-radius:2px;padding:1rem 1.25rem;margin-bottom:1rem;
                display:flex;align-items:center;justify-content:space-between;">
                <div>
                    <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;
                        color:{color}66;letter-spacing:0.2em;margin-bottom:4px;">DIRECT RESPONSE</div>
                    <div style="font-family:'Orbitron',sans-serif;font-size:0.75rem;font-weight:600;
                        color:{color};letter-spacing:0.15em;text-shadow:0 0 15px {color};">{label}</div>
                </div>
                <div style="font-family:'Orbitron',sans-serif;font-size:2rem;font-weight:900;
                    color:{color};text-shadow:0 0 30px {color};">{icon}</div>
            </div>
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.62rem;
                color:rgba(0,229,255,0.25);line-height:1.8;padding:0 0.25rem;">
                No pipeline required for this prompt type.<br>
                Scroll down to see your {'code' if current_mode=='CODE' else 'answer'} in the Direct Response panel.<br>
                Use the chat box below it for follow-ups.
            </div>
            """, unsafe_allow_html=True)

        elif current_mode == "SOVEREIGN":
            # ── SOVEREIGN: show full score verdict as before ───────────────
            score = state_values.get("confidence_score", 0.0)
            if score:
                verdict_color = "#00e676" if score >= min_confidence else "#ff1744"
                verdict_text  = "VERIFIED & ARCHIVED" if score >= min_confidence else "REJECTED — RE-PLANNING"
                st.markdown(f"""
                <div style="background:rgba(0,229,255,0.02);border:1px solid rgba(0,229,255,0.1);
                    border-left:3px solid {verdict_color};border-radius:2px;
                    padding:1rem 1.25rem;margin-bottom:1rem;
                    display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;
                            color:rgba(0,229,255,0.3);letter-spacing:0.2em;margin-bottom:4px;">SOVEREIGN VERDICT</div>
                        <div style="font-family:'Orbitron',sans-serif;font-size:0.75rem;font-weight:600;
                            color:{verdict_color};letter-spacing:0.15em;
                            text-shadow:0 0 15px {verdict_color};">{verdict_text}</div>
                    </div>
                    <div style="font-family:'Orbitron',sans-serif;font-size:2.2rem;font-weight:900;
                        color:{verdict_color};text-shadow:0 0 30px {verdict_color};
                        letter-spacing:0.05em;">{score:.2f}</div>
                </div>
                """, unsafe_allow_html=True)

        # Celebration sprite — only for SOVEREIGN success
        _score_for_sprite = state_values.get("confidence_score", 0.0)
        if current_mode == "SOVEREIGN" and _score_for_sprite and not st.session_state.nexus_running:
            score = _score_for_sprite
            if score >= min_confidence:
                # Laughing/pointing celebration sprite
                components.html("""
                <style>
                  body{margin:0;padding:0;background:transparent;}
                  @keyframes laugh{0%{transform:rotate(-8deg) translateY(0)}25%{transform:rotate(8deg) translateY(-4px)}50%{transform:rotate(-6deg) translateY(0)}75%{transform:rotate(6deg) translateY(-3px)}100%{transform:rotate(-8deg) translateY(0)}}
                  @keyframes point{0%,100%{transform:translateX(0)}50%{transform:translateX(6px)}}
                  @keyframes celebGlow{0%,100%{opacity:0.3}50%{opacity:0.8}}
                  .body-laugh{animation:laugh 0.5s ease-in-out infinite;transform-origin:bottom center;}
                  .point-arm{animation:point 0.6s ease-in-out infinite;}
                </style>
                <div style="display:flex;align-items:center;justify-content:center;padding:0.5rem;gap:12px;">
                  <svg class="body-laugh" width="56" height="72" viewBox="0 0 56 72" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="28" cy="15" r="12" fill="#0d1220" stroke="#76ff03" stroke-width="1.5"/>
                    <rect x="22" y="10" width="4" height="5" rx="1" fill="#76ff03"/>
                    <rect x="30" y="10" width="4" height="5" rx="1" fill="#76ff03"/>
                    <path d="M21 20 Q28 26 35 20" fill="none" stroke="#76ff03" stroke-width="1.5" stroke-linecap="round"/>
                    <rect x="12" y="27" width="32" height="22" rx="4" fill="#0d1220" stroke="#76ff03" stroke-width="1.5"/>
                    <text x="28" y="42" text-anchor="middle" font-family="monospace" font-size="9" fill="#ffb300" font-weight="700">✓</text>
                    <rect x="4"  y="28" width="8" height="14" rx="3" fill="#0d1220" stroke="#76ff03" stroke-width="1"/>
                    <g class="point-arm"><rect x="44" y="28" width="10" height="8" rx="3" fill="#0d1220" stroke="#76ff03" stroke-width="1"/><rect x="52" y="29" width="6" height="4" rx="2" fill="#0d1220" stroke="#76ff03" stroke-width="1"/></g>
                    <rect x="17" y="49" width="8" height="14" rx="3" fill="#0d1220" stroke="#76ff03" stroke-width="1"/>
                    <rect x="31" y="49" width="8" height="14" rx="3" fill="#0d1220" stroke="#76ff03" stroke-width="1"/>
                    <circle cx="28" cy="38" r="20" fill="none" stroke="#76ff03" stroke-width="0.5" opacity="0.15" style="animation:celebGlow 1s ease-in-out infinite;"/>
                  </svg>
                  <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;color:#76ff03;letter-spacing:0.15em;line-height:1.8;">MISSION<br>COMPLETE<br><span style="color:rgba(118,255,3,0.4);font-size:0.5rem;">DOSSIER ARCHIVED</span></div>
                </div>
                """, height=110)

        # Route badge — show current mode
        if st.session_state.route_mode:
            mode_colors = {"SOVEREIGN": "#00e5ff", "CODE": "#ffb300", "QUICK": "#00e676"}
            mode_icons  = {"SOVEREIGN": "⚗", "CODE": "⌨", "QUICK": "⚡"}
            mc = mode_colors.get(st.session_state.route_mode, "#00e5ff")
            mi = mode_icons.get(st.session_state.route_mode, "◆")
            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:0.5rem;padding:6px 10px;
                background:{mc}11;border:1px solid {mc}44;border-radius:2px;">
                <span style="color:{mc};font-size:0.9rem;">{mi}</span>
                <span style="font-family:'Share Tech Mono',monospace;font-size:0.65rem;color:{mc};letter-spacing:0.1em;">
                    MODE: {st.session_state.route_mode}
                </span>
            </div>
            """, unsafe_allow_html=True)

        # Launch button
        st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🚀 LAUNCH INVESTIGATION", use_container_width=True):
            if not task_input.strip():
                st.error("DIRECTIVE REQUIRED — enter a research task.")
            else:
                # ── SMART ROUTING ──────────────────────────────────────────
                with st.spinner("Routing prompt..."):
                    route = classify_prompt(task_input)

                st.session_state.route_mode    = route["mode"]
                st.session_state.quick_answer  = ""
                st.session_state.status_log    = []
                st.session_state.nexus_running = True

                if route["mode"] in ("QUICK", "CODE"):
                    # Fast path — no pipeline, no Z3, no Judge, no false rejections
                    spinner_msg = "Generating code..." if route["mode"] == "CODE" else "Fetching answer..."
                    with st.spinner(spinner_msg):
                        answer = run_quick_response(task_input, route["mode"])
                    st.session_state.quick_answer  = answer
                    st.session_state.nexus_running = False
                    # Clear any stale pipeline state so the Decision Center
                    # does not show a leftover sovereign score
                    st.session_state["judge_verdict"] = ""
                    try:
                        # Reset the checkpointer thread so old verdicts don't bleed through
                        st.session_state.thread_id = f"nexus_{os.urandom(4).hex()}"
                    except Exception:
                        pass
                else:
                    # Full sovereign pipeline
                    initial_state = {
                        "task": task_input, "plan": [], "research_notes": [],
                        "uncertainty_flags": [], "visual_context": None,
                        "user_profile": {}, "global_workspace": None,
                        "cognitive_mode": "EXPLAIN", "urgency_level": 0.0,
                        "iterations": 0, "max_iterations": max_iters,
                        "min_confidence": min_confidence, "confidence_score": 0.0,
                        "proposed_edit": None, "approval_granted": False,
                        "judge_verdict": "",
                    }
                    asyncio.run(run_nexus(
                        initial_state,
                        live_placeholder=st.session_state.get("live_feed_placeholder")
                    ))
                    st.session_state.nexus_running = False

                st.session_state["last_task"] = task_input
                st.rerun()

        # Node status grid
        st.markdown("""
        <div style="margin-top: 1.5rem;">
            <div style="
                font-family: 'Share Tech Mono', monospace;
                font-size: 0.6rem;
                letter-spacing: 0.2em;
                color: rgba(0,229,255,0.2);
                margin-bottom: 0.75rem;
                text-transform: uppercase;
            ">// Pipeline Topology</div>
        </div>
        """, unsafe_allow_html=True)

        active_nodes = [e.replace("✅", "").replace("**", "").strip()
                        for e in st.session_state.status_log if "✅" in e]
        error_nodes  = [e.replace("❌", "").strip()
                        for e in st.session_state.status_log if "❌" in e]

        all_nodes = [
            "TOM", "LOAD_BALANCER", "VISUAL_PARSER", "PRIVACY",
            "BROADCAST", "VISIONARY", "DIAGNOSTICS", "CODER",
            "TESTING", "SKEPTIC", "JUDGE", "MANIFESTO",
            "MEMORY_SURGEON", "EVOLUTION"
        ]

        node_html = '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px;">'
        for node in all_nodes:
            if any(node in a.upper() for a in active_nodes):
                dot_color = "#00e676"
                text_color = "#5a7a99"
                bg = "rgba(0,230,118,0.04)"
                border = "rgba(0,230,118,0.15)"
            elif any(node in e.upper() for e in error_nodes):
                dot_color = "#ff1744"
                text_color = "#5a7a99"
                bg = "rgba(255,23,68,0.04)"
                border = "rgba(255,23,68,0.15)"
            else:
                dot_color = "rgba(0,229,255,0.1)"
                text_color = "rgba(0,229,255,0.15)"
                bg = "transparent"
                border = "rgba(0,229,255,0.05)"

            node_html += f"""
            <div style="
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 5px 8px;
                background: {bg};
                border: 1px solid {border};
                border-radius: 2px;
            ">
                <div style="
                    width: 5px; height: 5px;
                    border-radius: 50%;
                    background: {dot_color};
                    box-shadow: 0 0 6px {dot_color};
                    flex-shrink: 0;
                "></div>
                <span style="
                    font-family: 'Share Tech Mono', monospace;
                    font-size: 0.58rem;
                    color: {text_color};
                    letter-spacing: 0.08em;
                ">{node}</span>
            </div>
            """
        node_html += "</div>"
        components.html(f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
            * {{ box-sizing: border-box; }}
            body {{ margin: 0; padding: 0; background: transparent; }}
        </style>
        {node_html}
        """, height=280, scrolling=False)

# ---------------------------------------------------------------------------
# COMPANION CHAT PANEL — direct answer + persistent chat
# ---------------------------------------------------------------------------

quick_answer = st.session_state.get("quick_answer", "")
route_mode   = st.session_state.get("route_mode", None)
chat_history = st.session_state.get("chat_history", [])

if quick_answer or chat_history:
    st.markdown("""
    <div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid rgba(0,229,255,0.08);">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.8rem;">
            <span style="font-family:'Orbitron',sans-serif;font-size:0.7rem;font-weight:600;
                letter-spacing:0.25em;color:rgba(0,229,255,0.7);text-transform:uppercase;">
                Direct Response</span>
            <div style="flex:1;height:1px;background:rgba(0,229,255,0.08);"></div>
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;
                color:rgba(0,229,255,0.25);letter-spacing:0.15em;">
                COMPANION TO THE DOSSIER</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show the direct answer from the last run
    if quick_answer:
        mode_label = {"CODE": "⌨ CODE OUTPUT", "QUICK": "⚡ QUICK ANSWER", "SOVEREIGN": "◆ DIRECT SUMMARY"}.get(route_mode, "◆ RESPONSE")
        mode_color = {"CODE": "#ffb300", "QUICK": "#00e676", "SOVEREIGN": "#00e5ff"}.get(route_mode, "#00e5ff")
        st.markdown(f"""
        <div style="background:{mode_color}08;border:1px solid {mode_color}22;
            border-left:3px solid {mode_color};border-radius:2px;
            padding:0.6rem 1rem;margin-bottom:0.75rem;">
            <span style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;
                color:{mode_color};letter-spacing:0.15em;">{mode_label}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(quick_answer)

    # Persistent follow-up chat
    if chat_history:
        st.markdown("---")
        for msg in chat_history:
            role_label = "SATSON" if msg["role"] == "user" else "NEXUS"
            role_color = "#ffb300" if msg["role"] == "user" else "#00e5ff"
            align      = "flex-end" if msg["role"] == "user" else "flex-start"
            br         = "12px 12px 4px 12px" if msg["role"] == "user" else "12px 12px 12px 4px"
            st.markdown(f"""
            <div style="display:flex;justify-content:{align};margin-bottom:8px;">
              <div style="max-width:80%;">
                <div style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;
                    color:{role_color}88;margin-bottom:3px;
                    text-align:{'right' if msg['role']=='user' else 'left'};">{role_label}</div>
                <div style="background:{role_color}10;border:1px solid {role_color}33;
                    border-radius:{br};padding:8px 12px;
                    font-family:'Share Tech Mono',monospace;font-size:0.75rem;
                    color:{role_color}cc;line-height:1.6;">{msg["content"]}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

# Follow-up chat input — always visible after first run
if route_mode:
    follow_up = st.chat_input("Ask a follow-up question or request a code change...")
    if follow_up:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage
        # Build context from previous quick answer
        ctx = quick_answer[:500] if quick_answer else "No prior context."
        follow_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        sys_prompt = (
            f"You are the Nexus companion AI. The user has been working on: '{st.session_state.get('last_task','')}'. "
            f"Prior response context: {ctx} "
            "Answer follow-up questions directly. For code requests, provide complete runnable code."
        )
        try:
            resp = follow_llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=follow_up)])
            st.session_state.chat_history.append({"role": "user",      "content": follow_up})
            st.session_state.chat_history.append({"role": "assistant", "content": resp.content})
        except Exception as e:
            st.session_state.chat_history.append({"role": "assistant", "content": f"Error: {e}"})
        st.rerun()

# ---------------------------------------------------------------------------
# BREAKOUT GAME (shows while pipeline is running) + JUDGE VERDICT ROBOT
# ---------------------------------------------------------------------------

verdict_text = state_values.get("judge_verdict", "") or st.session_state.get("judge_verdict", "")
is_running   = st.session_state.get("nexus_running", False)

game_col, verdict_col = st.columns([1.2, 0.8])

with game_col:
    st.markdown("""
    <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;letter-spacing:0.2em;color:rgba(0,229,255,0.25);margin-bottom:0.5rem;">// KEEP BUSY WHILE NEXUS THINKS</div>
    """, unsafe_allow_html=True)
    components.html("""
        <style>
          body{margin:0;padding:0;background:#050810;overflow:hidden;}
          canvas{display:block;margin:0 auto;}
          #msg{font-family:'Share Tech Mono',monospace;font-size:11px;color:#00e5ff;text-align:center;letter-spacing:0.15em;margin-top:4px;height:16px;}
        </style>
        <canvas id="c" width="380" height="200"></canvas>
        <div id="msg">← → MOVE &nbsp;|&nbsp; SPACE LAUNCH</div>
        <script>
        const cv=document.getElementById('c'),ctx=cv.getContext('2d');
        const W=380,H=200;
        let bx=W/2,by=H-30,bdx=2.8,bdy=-2.8,launched=false;
        const pw=60,ph=8;let px=(W-pw)/2,py=H-14;
        const BR=5,BC=8,BW=36,BH=10,BPAD=6;
        let bricks=[];
        const COLS=['#00e5ff','#7c5cbf','#ffb300','#00e676','#ff1744'];
        for(let r=0;r<BR;r++)for(let col=0;col<BC;col++)bricks.push({x:10+col*(BW+BPAD),y:22+r*(BH+BPAD),alive:true,c:COLS[r%COLS.length]});
        let score=0,lives=3,keys={};
        document.addEventListener('keydown',e=>{keys[e.key]=true;if(e.key===' '){launched=true;}});
        document.addEventListener('keyup',e=>{keys[e.key]=false;});
        function reset(){bx=px+pw/2;by=H-30;bdx=2.8;bdy=-2.8;launched=false;}
        function draw(){
          ctx.fillStyle='#050810';ctx.fillRect(0,0,W,H);
          // paddle
          ctx.fillStyle='#00e5ff';ctx.fillRect(px,py,pw,ph);
          ctx.strokeStyle='#00e5ff88';ctx.strokeRect(px,py,pw,ph);
          // ball
          ctx.beginPath();ctx.arc(bx,by,6,0,Math.PI*2);ctx.fillStyle='#ffb300';ctx.fill();
          ctx.strokeStyle='#ffb30066';ctx.stroke();
          // bricks
          bricks.forEach(b=>{
            if(!b.alive)return;
            ctx.fillStyle=b.c+'33';ctx.fillRect(b.x,b.y,BW,BH);
            ctx.strokeStyle=b.c;ctx.strokeRect(b.x,b.y,BW,BH);
          });
          // hud
          ctx.fillStyle='rgba(0,229,255,0.25)';
          ctx.font='10px Share Tech Mono,monospace';
          ctx.fillText('SCR:'+score,8,14);
          ctx.fillText('LIVES:'+lives,W-70,14);
        }
        function update(){
          if(!launched){bx=px+pw/2;return;}
          bx+=bdx;by+=bdy;
          if(bx<6||bx>W-6)bdx*=-1;
          if(by<6){bdy*=-1;}
          if(by>H-14-6&&by<H-14+6&&bx>px&&bx<px+pw){bdy*=-1;bdx+=((bx-px-pw/2)/pw)*1.5;}
          if(by>H){lives--;if(lives<=0){lives=3;score=0;bricks.forEach(b=>b.alive=true);}reset();}
          bricks.forEach(b=>{
            if(!b.alive)return;
            if(bx>b.x-6&&bx<b.x+BW+6&&by>b.y-6&&by<b.y+BH+6){b.alive=false;bdy*=-1;score+=10;}
          });
          if(bricks.every(b=>!b.alive)){bricks.forEach(b=>b.alive=true);bdx*=1.05;bdy*=1.05;}
        }
        function loop(){
          if(keys['ArrowLeft']&&px>0)px-=5;
          if(keys['ArrowRight']&&px<W-pw)px+=5;
          update();draw();requestAnimationFrame(loop);
        }
        loop();
        </script>
    """, height=230)

with verdict_col:
    if verdict_text:
        st.markdown("""
        <div style="font-family:'Share Tech Mono',monospace;font-size:0.6rem;letter-spacing:0.2em;color:rgba(0,229,255,0.25);margin-bottom:0.5rem;">// JUDGE VERDICT DEBRIEF</div>
        """, unsafe_allow_html=True)
        components.html(f"""
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
          body{{margin:0;padding:0;background:transparent;}}
          @keyframes idleBob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
          @keyframes blink3{{0%,85%,100%{{transform:scaleY(1)}}92%{{transform:scaleY(0.1)}}}}
          @keyframes bubblePop{{from{{opacity:0;transform:scale(0.9)}}to{{opacity:1;transform:scale(1)}}}}
          .sprite2{{animation:idleBob 3s ease-in-out infinite;display:inline-block;}}
          .eyes2{{animation:blink3 5s ease-in-out infinite;display:inline-block;transform-origin:center;}}
        </style>
        <div style="display:flex;align-items:flex-start;gap:10px;padding:0.5rem;">
          <div class="sprite2" style="flex-shrink:0;">
            <svg width="44" height="56" viewBox="0 0 44 56" xmlns="http://www.w3.org/2000/svg">
              <rect x="12" y="2" width="20" height="18" rx="5" fill="#0d1220" stroke="#ffd600" stroke-width="1.5"/>
              <g class="eyes2"><rect x="16" y="8" width="4" height="4" rx="1" fill="#ffd600"/><rect x="24" y="8" width="4" height="4" rx="1" fill="#ffd600"/></g>
              <rect x="18" y="16" width="8" height="2" rx="1" fill="#ffd600" opacity="0.5"/>
              <rect x="20" y="20" width="4" height="4" fill="#0d1220" stroke="#ffd600" stroke-width="1"/>
              <rect x="10" y="24" width="24" height="16" rx="3" fill="#0d1220" stroke="#ffd600" stroke-width="1.5"/>
              <text x="22" y="36" text-anchor="middle" font-family="monospace" font-size="7" fill="#ffd600" font-weight="700">JD</text>
              <rect x="2" y="25" width="8" height="12" rx="2" fill="#0d1220" stroke="#ffd600" stroke-width="1"/>
              <rect x="34" y="25" width="8" height="12" rx="2" fill="#0d1220" stroke="#ffd600" stroke-width="1"/>
              <rect x="13" y="40" width="7" height="12" rx="2" fill="#0d1220" stroke="#ffd600" stroke-width="1"/>
              <rect x="24" y="40" width="7" height="12" rx="2" fill="#0d1220" stroke="#ffd600" stroke-width="1"/>
            </svg>
          </div>
          <div style="animation:bubblePop 0.3s ease forwards;">
            <div style="font-family:'Share Tech Mono',monospace;font-size:0.55rem;color:rgba(255,214,0,0.5);margin-bottom:4px;letter-spacing:0.1em;">SUPREME JUDGE</div>
            <div style="background:rgba(255,214,0,0.06);border:1px solid rgba(255,214,0,0.25);border-radius:2px 10px 10px 10px;padding:8px 12px;font-family:'Share Tech Mono',monospace;font-size:0.68rem;color:rgba(255,214,0,0.8);line-height:1.6;max-width:280px;">{verdict_text}</div>
          </div>
        </div>
        """, height=200)

# ---------------------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------------------
st.markdown("""
<div style="
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid rgba(0,229,255,0.06);
    display: flex;
    align-items: center;
    justify-content: space-between;
">
    <span style="
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.6rem;
        color: rgba(0,229,255,0.1);
        letter-spacing: 0.2em;
    ">NEXUS GENESIS // PROJECT-11 // SOVEREIGN AI RESEARCH ENGINE</span>
    <span style="
        font-family: 'Orbitron', sans-serif;
        font-size: 0.6rem;
        font-weight: 600;
        color: rgba(255,179,0,0.25);
        letter-spacing: 0.3em;
    ">SATSON</span>
</div>
""", unsafe_allow_html=True)
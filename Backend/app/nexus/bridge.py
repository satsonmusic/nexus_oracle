"""
app/nexus/bridge.py — Phase 4: Nexus Genesis ↔ Jarvis FastAPI Bridge
=====================================================================
Imports the Nexus pipeline from its Desktop location and exposes it
as an async generator that yields node events over WebSocket.

Place this file in: C:\\Users\\scott\\Desktop\\Jarvis\\Backend\\app\\nexus\\bridge.py
Also create:        C:\\Users\\scott\\Desktop\\Jarvis\\Backend\\app\\nexus\\__init__.py
"""

import sys
import asyncio
import os
import uuid
import json
from pathlib import Path
from datetime import datetime
from typing import AsyncGenerator, Optional

# ---------------------------------------------------------------------------
# PATH BRIDGE — import Nexus Genesis from Desktop without moving files
# ---------------------------------------------------------------------------
NEXUS_ROOT = Path(os.environ.get("NEXUS_ROOT", "/app/nexus_genesis"))
if str(NEXUS_ROOT) not in sys.path:
    sys.path.insert(0, str(NEXUS_ROOT))

# Lazy pipeline loader - imported on first use, not at startup
_create_nexus_graph = None
NEXUS_AVAILABLE = False

def _load_pipeline():
    global _create_nexus_graph, NEXUS_AVAILABLE
    if _create_nexus_graph is not None:
        return True
    print("[ NEXUS BRIDGE ] Attempting to load pipeline...")
    import traceback as _tb
    try:
        if str(NEXUS_ROOT) not in sys.path:
            sys.path.insert(0, str(NEXUS_ROOT))
        print(f"[ NEXUS BRIDGE ] NEXUS_ROOT={NEXUS_ROOT}, exists={NEXUS_ROOT.exists()}")
        from core.orchestrator import create_nexus_graph as _cng
        _create_nexus_graph = _cng
        NEXUS_AVAILABLE = True
        print("[ NEXUS BRIDGE ] Pipeline loaded from", NEXUS_ROOT)
        return True
    except BaseException as e:
        NEXUS_AVAILABLE = False
        print(f"[ NEXUS BRIDGE ] FAILED: {type(e).__name__}: {e}")
        _tb.print_exc()
        return False

# ---------------------------------------------------------------------------
# SESSION REGISTRY — tracks active pipeline runs
# ---------------------------------------------------------------------------
# session_id → {"status", "events", "task", "started_at", "dossier_path"}
_sessions: dict = {}


def create_session(task: str) -> str:
    session_id = str(uuid.uuid4())[:8]
    _sessions[session_id] = {
        "status":     "pending",
        "events":     [],
        "task":       task,
        "started_at": datetime.utcnow().isoformat(),
        "dossier_path": None,
        "score":      None,
        "verdict":    None,
        "judge_verdict": "",
    }
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    return _sessions.get(session_id)


def get_dossier(session_id: str) -> Optional[str]:
    """Read the dossier MD from disk for a completed session."""
    session = _sessions.get(session_id)
    if not session:
        return None
    path = session.get("dossier_path")
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    # Fallback: find latest dossier in output folder
    output_dir = NEXUS_ROOT / "output"
    if output_dir.exists():
        dossiers = sorted(output_dir.glob("Dossier_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if dossiers:
            return dossiers[0].read_text(encoding="utf-8")
    return None


# ---------------------------------------------------------------------------
# NODE PERSONALITY MAP — what each node does in plain English
# ---------------------------------------------------------------------------
NODE_INFO = {
    "llmpick":        {"icon": "⚡", "label": "LlmPick",        "msg": "Selecting optimal model for this session"},
    "tom":            {"icon": "🧠", "label": "Theory of Mind",  "msg": "Profiling cognitive state and user model"},
    "load_balancer":  {"icon": "⚖",  "label": "Load Balancer",  "msg": "Calibrating urgency and cognitive mode"},
    "visual_parser":  {"icon": "👁",  "label": "Visual Cortex",  "msg": "Parsing visual intelligence"},
    "privacy":        {"icon": "🛡",  "label": "Armor",          "msg": "Scrubbing sensitive data from context"},
    "broadcast":      {"icon": "📡", "label": "Consciousness",   "msg": "Broadcasting to global workspace"},
    "visionary":      {"icon": "🔭", "label": "Visionary",       "msg": "Drafting sovereign research plan"},
    "diagnostics":    {"icon": "🔬", "label": "Ego/Diagnostics", "msg": "Running hallucination diagnostics"},
    "coder":          {"icon": "⚙",  "label": "Architect",       "msg": "Modifying system state"},
    "testing":        {"icon": "🧪", "label": "Sandbox",         "msg": "Executing evolutionary unit tests"},
    "skeptic":        {"icon": "🔍", "label": "Skeptic",         "msg": "Performing global peer review"},
    "judge":          {"icon": "⚖",  "label": "Supreme Judge",   "msg": "Enforcing formal rigor"},
    "risk":           {"icon": "🚨", "label": "Risk Gate",        "msg": "Evaluating decision risk tier"},
    "commander":      {"icon": "🎯", "label": "Commander",       "msg": "Synthesising strategic status report"},
    "manifesto":      {"icon": "📜", "label": "Manifesto",       "msg": "Generating sovereign dossier"},
    "memory_surgeon": {"icon": "💾", "label": "Memory Surgeon",  "msg": "Updating cognitive profile"},
    "evolution":      {"icon": "🧬", "label": "Genesis",         "msg": "Proposing system evolution"},
}

TOTAL_NODES = 14
NODE_ORDER = [
    "llmpick", "tom", "load_balancer", "visual_parser", "privacy",
    "broadcast", "visionary", "diagnostics", "coder", "testing",
    "skeptic", "judge", "risk", "commander", "manifesto",
    "memory_surgeon", "evolution",
]


# ---------------------------------------------------------------------------
# PIPELINE RUNNER — async generator yielding SSE-style JSON events
# ---------------------------------------------------------------------------
async def run_nexus_stream(
    task: str,
    session_id: str,
    max_iterations: int = 3,
    min_confidence: float = 0.75,
) -> AsyncGenerator[dict, None]:
    """
    Runs the Nexus pipeline and yields JSON-serialisable event dicts.
    Each event has: type, node, icon, label, msg, pct, timestamp
    """
    session = _sessions.get(session_id)
    if not session:
        yield {"type": "error", "msg": "Session not found"}
        return

    session["status"] = "running"
    completed_nodes = []

    if not _load_pipeline():
        yield {
            "type":  "error",
            "node":  "system",
            "msg":   "Nexus pipeline not available — check NEXUS_ROOT path",
            "pct":   0,
            "ts":    datetime.utcnow().isoformat(),
        }
        session["status"] = "error"
        return

    # Yield a start event
    yield {
        "type":    "start",
        "node":    "system",
        "icon":    "🧬",
        "label":   "Nexus Oracle",
        "msg":     f"Initialising sovereign pipeline for: {task[:80]}",
        "pct":     0,
        "ts":      datetime.utcnow().isoformat(),
        "session": session_id,
    }

    try:
        if not _load_pipeline():
            yield {"type": "error", "node": "system", "msg": "Pipeline failed to load", "pct": 0, "ts": datetime.utcnow().isoformat()}
            return
        app_graph = _create_nexus_graph()
        config    = {"configurable": {"thread_id": f"jarvis_{session_id}"}}

        initial_state = {
            "task":              task,
            "plan":              [],
            "research_notes":    [],
            "uncertainty_flags": [],
            "visual_context":    None,
            "user_profile":      {},
            "global_workspace":  None,
            "cognitive_mode":    "EXPLAIN",
            "urgency_level":     0.0,
            "iterations":        0,
            "max_iterations":    max_iterations,
            "min_confidence":    min_confidence,
            "confidence_score":  0.0,
            "proposed_edit":     None,
            "approval_granted":  False,
            "judge_verdict":     "",
        }

        async for event in app_graph.astream(
            initial_state, config=config, stream_mode="updates"
        ):
            for node_name, node_data in event.items():
                info = NODE_INFO.get(node_name.lower(), {
                    "icon": "▶", "label": node_name.upper(), "msg": "Processing..."
                })

                # Track unique completions for progress
                key = node_name.lower()
                if key not in completed_nodes:
                    completed_nodes.append(key)

                pct = min(100, int(len(completed_nodes) / TOTAL_NODES * 100))

                # Capture judge verdict
                if node_name == "judge" and node_data:
                    verdict = node_data.get("judge_verdict", "")
                    if verdict:
                        session["judge_verdict"] = verdict
                    score = node_data.get("confidence_score")
                    if score is not None:
                        session["score"] = score

                ev = {
                    "type":   "node_complete",
                    "node":   node_name,
                    "icon":   info["icon"],
                    "label":  info["label"],
                    "msg":    info["msg"],
                    "pct":    pct,
                    "ts":     datetime.utcnow().isoformat(),
                }

                # Attach score/verdict when judge fires
                if node_name == "judge":
                    ev["score"]        = session.get("score")
                    ev["judge_verdict"] = session.get("judge_verdict", "")

                session["events"].append(ev)
                yield ev

                # Small yield to event loop so FastAPI can flush the WebSocket
                await asyncio.sleep(0)

        # Pipeline complete
        session["status"] = "complete"
        session["verdict"] = "VERIFIED" if (session.get("score") or 0) >= min_confidence else "REVIEWED"

        # Find dossier path
        output_dir = NEXUS_ROOT / "output"
        if output_dir.exists():
            dossiers = sorted(
                output_dir.glob("Dossier_*.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if dossiers:
                session["dossier_path"] = str(dossiers[0])

        yield {
            "type":         "complete",
            "node":         "system",
            "icon":         "✅",
            "label":        "Pipeline Complete",
            "msg":          "Sovereign dossier archived",
            "pct":          100,
            "ts":           datetime.utcnow().isoformat(),
            "score":        session.get("score"),
            "verdict":      session.get("verdict"),
            "judge_verdict": session.get("judge_verdict", ""),
            "dossier_url":  f"/nexus/dossier/{session_id}",
        }

    except Exception as e:
        session["status"] = "error"
        yield {
            "type":  "error",
            "node":  "system",
            "msg":   f"Pipeline error: {str(e)}",
            "pct":   int(len(completed_nodes) / TOTAL_NODES * 100),
            "ts":    datetime.utcnow().isoformat(),
        }


# ---------------------------------------------------------------------------
# INTELLIGENCE FEED — proxy to Phase 2 WebSum signals
# ---------------------------------------------------------------------------
def get_intelligence_signals(limit: int = 10) -> list:
    """Returns recent signals from Phase 2 watcher."""
    try:
        if str(NEXUS_ROOT) not in sys.path:
            sys.path.insert(0, str(NEXUS_ROOT))
        from nexus_intelligence import get_recent_signals, get_signal_stats
        signals = get_recent_signals(limit=limit)
        stats   = get_signal_stats()
        return {"signals": signals, "stats": stats}
    except Exception as e:
        return {"signals": [], "stats": {"total": 0, "triggered": 0, "avg_score": 0.0}, "error": str(e)}


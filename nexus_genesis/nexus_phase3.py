"""
nexus_phase3.py — Phase 3: Decision Layer
==========================================
Wires Commander, LlmPick, and DecisionRiskEval into the Nexus pipeline
without modifying any of the original source files.

Place this file in: C:\\Users\\scott\\Desktop\\nexus_genesis\\

What each module contributes:
  LlmPick        → global model router — replaces hardcoded gpt-4o everywhere
  Commander      → strategic synthesis node — runs after Judge
  DecisionRiskEval → risk adjudicator — gates the Commander output

Import this module in nodes.py and orchestrator.py to activate Phase 3.
"""

import sys
import json
import importlib.util
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# PATH REGISTRY — where each repo lives on disk
# ---------------------------------------------------------------------------
REPO_PATHS = {
    "llmpick":       Path(r"C:\Users\scott\LlmPick\router.py"),
    "commander":     Path(r"C:\Users\scott\Commander\control_tower.py"),
    "decision_risk": Path(r"C:\Users\scott\DecisionMaker\risk_engine.py"),
}


# Key-specific fallback paths — each module only falls back to its own alternatives
_FALLBACKS = {
    "llmpick": [
        Path(r"C:\Users\scott\LlmPick\router.py"),
        Path(r"C:\Users\scott\llmpick\llmpick.py"),
        Path(r"C:\Users\scott\LLMPick\llmpick.py"),
    ],
    "commander": [
        Path(r"C:\Users\scott\Commander\control_tower.py"),
        Path(r"C:\Users\scott\commander\control_tower.py"),
        Path(r"C:\Users\scott\Commander\commander.py"),
    ],
    "decision_risk": [
        Path(r"C:\Users\scott\DecisionMaker\risk_engine.py"),
        Path(r"C:\Users\scott\DecisionRiskEval\decision_risk_eval.py"),
        Path(r"C:\Users\scott\decisionmaker\risk_engine.py"),
    ],
}


def _load_module(key: str) -> Optional[object]:
    """Dynamically import a module from its absolute path."""
    path = REPO_PATHS.get(key)
    if path is None or not path.exists():
        # Try key-specific fallbacks only — never cross-load another module
        for alt in _FALLBACKS.get(key, []):
            if alt.exists():
                path = alt
                break
        else:
            print(f"[ PHASE3 ] WARNING: {key} not found — module disabled")
            return None

    try:
        spec   = importlib.util.spec_from_file_location(key, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"[ PHASE3 ] {key} loaded from {path}")
        return module
    except Exception as e:
        print(f"[ PHASE3 ] WARNING: Could not load {key}: {e}")
        return None


# Load all three modules at import time
_llmpick    = _load_module("llmpick")
_commander  = _load_module("commander")
_decisionrisk = _load_module("decision_risk")


# ---------------------------------------------------------------------------
# LLMPICK INTEGRATION — global model router
# ---------------------------------------------------------------------------

# Real 2025/2026 model catalog mapped to your existing LlmPick ModelSpec
NEXUS_MODEL_CATALOG = None

def _build_catalog():
    """Build the model catalog using LlmPick's ModelSpec dataclass."""
    if _llmpick is None:
        return None
    # Support both ModelSpec (llmpick.py) and any alias in router.py
    spec_cls = None
    for attr in ("ModelSpec", "Model", "ModelDef", "LLMSpec"):
        if hasattr(_llmpick, attr):
            spec_cls = getattr(_llmpick, attr)
            break
    if spec_cls is None:
        print(f"[ LLMPICK ] WARNING: no ModelSpec class found in module — available: {[x for x in dir(_llmpick) if not x.startswith('_')]}")
        return None
    M = spec_cls
    return [
        # name, provider, family, version, quality(1-3), latency_ms, cost_cents, failure_rate
        M("gpt-4o-mini",       "OpenAI",    "GPT",    "4o-mini", 2,  400, 0.02, 0.02),
        M("gpt-4o",            "OpenAI",    "GPT",    "4o",      3,  800, 0.50, 0.03),
        M("claude-sonnet-4-6", "Anthropic", "Claude", "4.6",     3,  700, 0.40, 0.02),
        M("claude-haiku-4-5",  "Anthropic", "Claude", "haiku",   2,  300, 0.05, 0.02),
        M("gemini-1.5-flash",  "Google",    "Gemini", "1.5",     2,  350, 0.07, 0.04),
        M("gemini-1.5-pro",    "Google",    "Gemini", "1.5-pro", 3,  900, 0.35, 0.04),
    ]


def pick_model(quality: str = "med", max_latency_ms: int = 1500,
               max_cost_cents: float = 1.0, deny: list = None) -> str:
    """
    Returns the best model name string for the given constraints.
    Falls back to 'gpt-4o' if LlmPick is unavailable.

    quality:        'low' | 'med' | 'high'
    max_latency_ms: hard upper bound on expected latency
    max_cost_cents: hard upper bound on cost per 1k tokens
    deny:           list of model name substrings to exclude
    """
    global NEXUS_MODEL_CATALOG
    if _llmpick is None:
        return "gpt-4o"  # safe fallback

    if NEXUS_MODEL_CATALOG is None:
        NEXUS_MODEL_CATALOG = _build_catalog()
    if not NEXUS_MODEL_CATALOG:
        return "gpt-4o"

    try:
        # Support both choose_candidates (llmpick.py) and route/select (router.py)
        router_fn = None
        for fn in ("choose_candidates", "route", "select", "pick"):
            if hasattr(_llmpick, fn):
                router_fn = getattr(_llmpick, fn)
                break
        if router_fn is None:
            print(f"[ LLMPICK ] No routing function found — available: {[x for x in dir(_llmpick) if not x.startswith('_')]}")
            return "gpt-4o"
        candidates = router_fn(
            models=NEXUS_MODEL_CATALOG,
            quality=quality,
            latency_ms=max_latency_ms,
            max_cost_cents=max_cost_cents,
            deny=deny or [],
        )
        if candidates:
            chosen = candidates[0]
            print(f"[ LLMPICK ] Routed to: {chosen.name} "
                  f"(q={chosen.quality} lat={chosen.latency_ms}ms "
                  f"cost={chosen.cost_cents}¢)")
            return chosen.name
        return "gpt-4o"
    except Exception as e:
        print(f"[ LLMPICK ] Routing error: {e} — using gpt-4o")
        return "gpt-4o"


def get_llm(quality: str = "med", max_latency_ms: int = 1500,
            max_cost_cents: float = 1.0, deny: list = None,
            temperature: float = 0.0):
    """
    Returns a LangChain ChatOpenAI instance wired to the best-fit model.
    Drop-in replacement for hardcoded ChatOpenAI(model="gpt-4o").

    Usage in nodes.py:
        from nexus_phase3 import get_llm
        judge_llm = get_llm(quality="high", temperature=0.0)
    """
    from langchain_openai import ChatOpenAI
    model_name = pick_model(quality, max_latency_ms, max_cost_cents, deny)
    return ChatOpenAI(model=model_name, temperature=temperature)


# ---------------------------------------------------------------------------
# COMMANDER INTEGRATION — strategic synthesis node
# ---------------------------------------------------------------------------

def run_commander_synthesis(state: dict) -> dict:
    """
    Converts the Nexus pipeline state into Commander's Update format,
    runs the status rollup, and returns a strategic synthesis string.

    Called by commander_node() in nodes.py.
    """
    if _commander is None:
        return {"commander_report": "Commander module unavailable."}

    from datetime import date
    import io

    try:
        # Build synthetic Update rows from pipeline state
        plan      = (state.get("plan") or [""])[-1]
        flags     = state.get("uncertainty_flags") or []
        score     = state.get("confidence_score", 0.0)
        task      = state.get("task", "Unknown task")
        mode      = state.get("cognitive_mode", "EXPLAIN")

        # Determine status from confidence score
        if score >= 0.75:
            status = "Green"
        elif score >= 0.4:
            status = "Yellow"
        else:
            status = "Red"

        # Synthetic update row matching Commander's Update dataclass
        updates = [
            _commander.Update(
                program="Nexus Oracle",
                workstream=mode,
                owner="SATSON",
                status=status,
                milestone=task[:80],
                due_date=date.today(),
                last_update=date.today(),
                blockers="; ".join([f for f in flags if "FAIL" in f or "Error" in f])[:200] or "None",
                notes=plan[:300],
            )
        ]

        report = _commander.render_status_md(updates, date.today(), stale_days=1, due_soon_days=1)
        print("[ COMMANDER ] Strategic synthesis complete")
        return {"commander_report": report}

    except Exception as e:
        print(f"[ COMMANDER ] Synthesis error: {e}")
        return {"commander_report": f"Commander synthesis failed: {e}"}


# ---------------------------------------------------------------------------
# DECISIONRISKEVAL INTEGRATION — risk adjudicator gate
# ---------------------------------------------------------------------------

def run_risk_evaluation(state: dict) -> dict:
    """
    Evaluates the pipeline state for risk signals using DecisionRiskEval's
    scoring logic. Returns a risk assessment dict with severity, urgency,
    signals, and a tiered approval decision.

    Tiered HITL gate:
      severity < 30  → AUTO_APPROVE  (low risk, no human needed)
      severity 30-60 → CONFIRM       (show warning, require click)
      severity > 60  → BLOCK         (hard stop, escalation packet generated)
    """
    if _decisionrisk is None:
        return {"risk_assessment": {"tier": "AUTO_APPROVE", "severity": 0,
                                    "signals": [], "recommendation": "Risk module unavailable."}}

    from datetime import date, timedelta

    try:
        score     = state.get("confidence_score", 0.5)
        flags     = state.get("uncertainty_flags") or []
        task      = state.get("task", "")
        plan      = (state.get("plan") or [""])[-1]

        # Build a synthetic Milestone from pipeline state
        slip_count = len([f for f in flags if "FAIL" in f])
        status_str = "red" if score < 0.3 else ("yellow" if score < 0.75 else "green")

        m = _decisionrisk.Milestone(
            program="Nexus Oracle",
            workstream=state.get("cognitive_mode", "EXPLAIN"),
            owner="SATSON",
            name=task[:80],
            due_date=date.today(),
            status=status_str,
            last_update=date.today(),
            slip_count=slip_count,
        )

        escalation = _decisionrisk.score_milestone(m, date.today(), stale_days=1)

        if escalation is None:
            # No escalation triggered — low risk
            assessment = {
                "tier":           "AUTO_APPROVE",
                "severity":       0,
                "urgency":        0,
                "signals":        [],
                "recommendation": "No risk signals detected. Safe to proceed.",
                "confidence":     100,
            }
        else:
            sev = escalation.severity
            if sev > 60:
                tier = "BLOCK"
            elif sev > 30:
                tier = "CONFIRM"
            else:
                tier = "AUTO_APPROVE"

            assessment = {
                "tier":           tier,
                "severity":       sev,
                "urgency":        escalation.urgency,
                "signals":        escalation.signals,
                "recommendation": escalation.recommendation,
                "confidence":     escalation.confidence,
            }

        print(f"[ RISK ] Tier: {assessment['tier']} | Severity: {assessment['severity']}")
        return {"risk_assessment": assessment}

    except Exception as e:
        print(f"[ RISK ] Evaluation error: {e}")
        return {"risk_assessment": {"tier": "CONFIRM", "severity": 50,
                                    "signals": [f"Evaluation error: {e}"],
                                    "recommendation": "Manual review recommended."}}


# ---------------------------------------------------------------------------
# CONVENIENCE: PHASE 3 STATUS CHECK
# ---------------------------------------------------------------------------

def phase3_status() -> dict:
    """Returns which Phase 3 modules are loaded. Call on startup."""
    return {
        "llmpick":     _llmpick is not None,
        "commander":   _commander is not None,
        "decisionrisk": _decisionrisk is not None,
    }


if __name__ == "__main__":
    print("=== NEXUS PHASE 3 STATUS ===")
    status = phase3_status()
    for module, loaded in status.items():
        icon = "✓" if loaded else "✗"
        print(f"  [{icon}] {module}")

    print("\n=== LLMPICK TEST ===")
    print(f"  High quality model:  {pick_model('high')}")
    print(f"  Fast cheap model:    {pick_model('low', max_latency_ms=500, max_cost_cents=0.1)}")
    print(f"  No OpenAI:           {pick_model('med', deny=['openai'])}")

    print("\n=== RISK TEST ===")
    test_state = {
        "task": "Analyze system architecture",
        "plan": ["Implement a new caching layer"],
        "uncertainty_flags": ["FAIL: unit test failed", "FAIL: Z3 proof failed"],
        "confidence_score": 0.15,
        "cognitive_mode": "DIRECTIVE",
    }
    result = run_risk_evaluation(test_state)
    print(f"  Risk tier: {result['risk_assessment']['tier']}")
    print(f"  Signals:   {result['risk_assessment']['signals']}")
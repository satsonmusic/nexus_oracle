from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from core.state import NexusState
from core.nodes import (
    visual_node,
    tom_node,
    privacy_node,
    load_balancer_node,
    broadcast_node,
    visionary_node,
    diagnostics_node,
    coder_node,
    testing_node,
    skeptic_node,
    judge_node,
    critic_node,
    repair_node,
    manifesto_node,
    memory_surgeon_node,
    evolution_node,
    # Phase 3 — Decision Layer
    llmpick_node,
    commander_node,
    risk_node,
)

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
MAX_REPAIR_ITERATIONS = 2      # hard cap — prevents cost explosion
TARGET_SCORE          = 0.85   # exit repair loop early if met


# ---------------------------------------------------------------------------
# ROUTING LOGIC
# ---------------------------------------------------------------------------

def route_after_risk(state: NexusState) -> str:
    tier = state.get("risk_tier", "AUTO_APPROVE")
    if tier == "BLOCK":
        print("!!! RISK GATE: BLOCKED — routing to manifesto !!!")
        return "manifesto"
    return "commander"


def route_after_coder(state: NexusState) -> str:
    if state.get("proposed_edit"):
        return "testing"
    return "skeptic"


def route_after_judge(state: NexusState) -> str:
    """
    Phase 2 routing — Judge v2 aware.

    Score >= TARGET or iterations exhausted  → proceed to risk/manifesto
    action == REPAIR or REJECTED             → route to Critic for surgical fix
    action == REVIEWED (score 0.50-0.84)     → one repair pass if iterations remain
    action == ACCEPTED (score >= 0.85)       → proceed immediately
    """
    score      = state.get("confidence_score", 0.0)
    iterations = state.get("iterations", 0)
    action     = state.get("judge_action", "REVIEWED")

    print(f"--- [ ROUTER: score={score:.2f} action={action} iter={iterations}/{MAX_REPAIR_ITERATIONS} ] ---")

    # Always exit if target met or iterations exhausted
    if score >= TARGET_SCORE or iterations >= MAX_REPAIR_ITERATIONS:
        return "manifesto"

    # Route to Critic-Repair for anything below ACCEPTED
    if action in ("REPAIR", "REJECTED", "REVIEWED"):
        return "critic"

    return "manifesto"


def route_after_repair(state: NexusState) -> str:
    """After repair, always re-score with Judge."""
    return "judge"


# ---------------------------------------------------------------------------
# GRAPH FACTORY
# ---------------------------------------------------------------------------

def create_nexus_graph():
    """
    Phase 2: 16-node Sovereign Pipeline with Critic-Repair Loop.
    New flow: Judge → Critic → Repair → Judge (up to MAX_REPAIR_ITERATIONS)
    """
    workflow     = StateGraph(NexusState)
    checkpointer = MemorySaver()

    # ── 1. Register all nodes ──────────────────────────────────────────────
    workflow.add_node("llmpick",        llmpick_node)
    workflow.add_node("tom",            tom_node)
    workflow.add_node("load_balancer",  load_balancer_node)
    workflow.add_node("visual_parser",  visual_node)
    workflow.add_node("privacy",        privacy_node)
    workflow.add_node("broadcast",      broadcast_node)
    workflow.add_node("visionary",      visionary_node)
    workflow.add_node("diagnostics",    diagnostics_node)
    workflow.add_node("coder",          coder_node)
    workflow.add_node("testing",        testing_node)
    workflow.add_node("skeptic",        skeptic_node)
    workflow.add_node("judge",          judge_node)
    workflow.add_node("critic",         critic_node)       # Phase 2
    workflow.add_node("repair",         repair_node)       # Phase 2
    workflow.add_node("risk",           risk_node)
    workflow.add_node("commander",      commander_node)
    workflow.add_node("manifesto",      manifesto_node)
    workflow.add_node("memory_surgeon", memory_surgeon_node)
    workflow.add_node("evolution",      evolution_node)

    # ── 2. Entry point ────────────────────────────────────────────────────
    workflow.set_entry_point("llmpick")

    # ── 3. Psychology & Perception ────────────────────────────────────────
    workflow.add_edge("llmpick",       "tom")
    workflow.add_edge("tom",           "load_balancer")
    workflow.add_edge("load_balancer", "visual_parser")

    # ── 4. Armor ──────────────────────────────────────────────────────────
    workflow.add_edge("visual_parser", "privacy")
    workflow.add_edge("privacy",       "broadcast")

    # ── 5. Conscious Deliberation ─────────────────────────────────────────
    workflow.add_edge("broadcast",   "visionary")
    workflow.add_edge("visionary",   "diagnostics")
    workflow.add_edge("diagnostics", "coder")

    # ── 6. Technical Validation ───────────────────────────────────────────
    workflow.add_conditional_edges(
        "coder",
        route_after_coder,
        {"testing": "testing", "skeptic": "skeptic"}
    )
    workflow.add_edge("testing", "skeptic")
    workflow.add_edge("skeptic", "judge")

    # ── 7. Phase 2: Critic-Repair Loop ────────────────────────────────────
    workflow.add_conditional_edges(
        "judge",
        route_after_judge,
        {
            "critic":   "critic",    # needs repair
            "manifesto": "risk",     # good enough — proceed
        }
    )
    workflow.add_edge("critic", "repair")
    workflow.add_edge("repair", "judge")   # re-score after repair

    # ── 8. Phase 3: Risk Gate → Commander → Manifesto ─────────────────────
    workflow.add_conditional_edges(
        "risk",
        route_after_risk,
        {"commander": "commander", "manifesto": "manifesto"}
    )
    workflow.add_edge("commander",      "manifesto")

    # ── 9. Legacy & Evolution ─────────────────────────────────────────────
    workflow.add_edge("manifesto",      "memory_surgeon")
    workflow.add_edge("memory_surgeon", "evolution")
    workflow.add_edge("evolution",      END)

    return workflow.compile(checkpointer=checkpointer)
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
    manifesto_node,
    memory_surgeon_node,
    evolution_node,
    # Phase 3 — Decision Layer
    llmpick_node,
    commander_node,
    risk_node,
)


# ---------------------------------------------------------------------------
# ROUTING LOGIC
# ---------------------------------------------------------------------------

def route_after_risk(state: NexusState) -> str:
    """
    After risk evaluation:
      AUTO_APPROVE → commander (proceed directly)
      CONFIRM      → commander (proceed, but dashboard shows warning)
      BLOCK        → manifesto (hard stop — surface findings without executing)
    """
    tier = state.get("risk_tier", "AUTO_APPROVE")
    if tier == "BLOCK":
        print("!!! RISK GATE: BLOCKED — routing to manifesto !!!")
        return "manifesto"
    return "commander"


def route_after_coder(state: NexusState) -> str:
    """
    If the Architect produced a proposed file edit, pause for human approval
    by routing to testing (sandbox runs before the human sees the code).
    Otherwise — simulation result, direct execution, or any other output —
    skip testing and go straight to the Skeptic.

    NOTE: Never route back to diagnostics here. diagnostics → coder is a
    one-way feed; returning to diagnostics from coder creates an infinite loop.
    """
    if state.get("proposed_edit"):
        return "testing"
    return "skeptic"


def route_after_judge(state: NexusState) -> str:
    """
    After the Judge scores the plan:
      - Score is high enough OR iterations exhausted → write the dossier.
      - Iterations remaining                         → loop back and re-plan.
    """
    score         = state.get("confidence_score", 0.0)
    iterations    = state.get("iterations", 0)
    max_iters     = state.get("max_iterations", 3)
    min_confidence = state.get("min_confidence", 0.75)

    if score >= min_confidence or iterations >= max_iters:
        return "manifesto"
    return "visionary"


# ---------------------------------------------------------------------------
# GRAPH FACTORY
# ---------------------------------------------------------------------------

def create_nexus_graph():
    """
    Compiles the 14-node Sovereign Pipeline for Nexus Genesis.
    Flow: Psychology -> Senses -> Armor -> Consciousness -> Thinking -> Validation -> Legacy
    """
    workflow    = StateGraph(NexusState)
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
    workflow.add_node("manifesto",      manifesto_node)
    workflow.add_node("memory_surgeon", memory_surgeon_node)
    workflow.add_node("evolution",      evolution_node)
    # Phase 3
    workflow.add_node("risk",           risk_node)
    workflow.add_node("commander",      commander_node)

    # ── 2. Entry point ────────────────────────────────────────────────────
    workflow.set_entry_point("llmpick")

    # ── 2.5 LlmPick — model selection before anything else ────────────────
    workflow.add_edge("llmpick",       "tom")

    # ── 3. Psychology & Perception ────────────────────────────────────────
    workflow.add_edge("tom",           "load_balancer")
    workflow.add_edge("load_balancer", "visual_parser")

    # ── 4. Armor (scrub after eyes, before brain) ─────────────────────────
    workflow.add_edge("visual_parser", "privacy")
    workflow.add_edge("privacy",       "broadcast")

    # ── 5. Conscious Deliberation ─────────────────────────────────────────
    workflow.add_edge("broadcast",   "visionary")
    workflow.add_edge("visionary",   "diagnostics")
    workflow.add_edge("diagnostics", "coder")

    # ── 6. Technical Validation ───────────────────────────────────────────
    # Coder: branch on whether a file edit needs sandboxing first
    workflow.add_conditional_edges(
        "coder",
        route_after_coder,
        {
            "testing": "testing",
            "skeptic": "skeptic",
        }
    )
    # Testing always rejoins at skeptic
    workflow.add_edge("testing", "skeptic")
    workflow.add_edge("skeptic", "judge")

    # ── 6.5 Phase 3: Risk Gate → Commander → Manifesto ──────────────────
    workflow.add_conditional_edges(
        "judge",
        route_after_judge,
        {
            "visionary": "visionary",
            "manifesto": "risk",      # Always route through risk gate first
        }
    )
    workflow.add_conditional_edges(
        "risk",
        route_after_risk,
        {
            "commander": "commander",
            "manifesto": "manifesto",
        }
    )
    workflow.add_edge("commander",      "manifesto")

    # ── 7. Legacy & Evolution ─────────────────────────────────────────────
    workflow.add_edge("manifesto",      "memory_surgeon")
    workflow.add_edge("memory_surgeon", "evolution")
    workflow.add_edge("evolution",      END)

    return workflow.compile(checkpointer=checkpointer)
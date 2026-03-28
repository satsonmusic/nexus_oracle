from typing import TypedDict, List, Optional


class NexusState(TypedDict, total=False):
    # Core task
    task:               str
    plan:               List[str]
    research_notes:     List[str]
    uncertainty_flags:  List[str]

    # Perception
    visual_context:     Optional[str]

    # Psychology
    user_profile:       dict
    global_workspace:   Optional[str]
    cognitive_mode:     str
    urgency_level:      float

    # Loop control
    iterations:         int
    max_iterations:     int
    min_confidence:     float
    confidence_score:   float

    # Judge
    judge_verdict:      str
    judge_violations:   List[str]   # violations fed back to Visionary

    # Phase 3 — Decision Layer
    selected_model:     str          # LlmPick: best model for this session
    commander_report:   str          # Commander: strategic synthesis MD
    risk_tier:          str          # Risk: AUTO_APPROVE | CONFIRM | BLOCK
    risk_assessment:    dict         # Risk: full assessment dict

    # Architect / Safety Gate
    proposed_edit:      Optional[str]
    approval_granted:   bool

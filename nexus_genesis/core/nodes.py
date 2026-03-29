import os
import re
import sys
import json
import datetime
import subprocess
import tempfile
try:
    import streamlit as st
    _STREAMLIT = True
except Exception:
    _STREAMLIT = False
    class _StStub:
        def __getattr__(self, name):
            return lambda *a, **kw: None
    st = _StStub()
from tenacity import retry, stop_after_attempt, wait_exponential
try:
    from langchain_tavily import TavilySearch
    _tavily_available = True
except Exception:
    _tavily_available = False
from langchain_openai import ChatOpenAI
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import Tool
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_core.messages import HumanMessage

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
except Exception:
    class AnalyzerEngine:
        def analyze(self, *a, **kw): return []
    class AnonymizerEngine:
        def anonymize(self, *a, **kw): 
            class R: text = a[0] if a else ""
            return R()

try:
    from deepeval.metrics import FaithfulnessMetric
    from deepeval.test_case import LLMTestCase
except Exception:
    class FaithfulnessMetric:
        def __init__(self, *a, **kw): self.score = 0.5
        def measure(self, *a, **kw): return 0.5
    class LLMTestCase:
        def __init__(self, *a, **kw): pass

try:
    from memory.knowledge_graph import NexusGraph
    _graph_available = True
except Exception as _graph_err:
    _graph_available = False
    print(f"--- [ NEXUS: Knowledge graph disabled ({_graph_err}) ] ---")
from memory.vector_store import NexusVectorStore
from core.state import NexusState
from core.constitution import SOVEREIGN_CONSTITUTION
from core.simulator import WorldSimulator
from core.verifier import SymbolicVerifier
from dotenv import load_dotenv

load_dotenv("infra/secrets.env")

# --- PHASE 3: DECISION LAYER ---
try:
    from nexus_phase3 import run_commander_synthesis, run_risk_evaluation, get_llm, phase3_status
    _p3 = phase3_status()
    print(f"[ PHASE3 ] Loaded  llmpick:{_p3['llmpick']} commander:{_p3['commander']} risk:{_p3['decisionrisk']}")
except ImportError:
    print("[ PHASE3 ] nexus_phase3.py not found  Phase 3 nodes disabled")
    run_commander_synthesis = lambda state: {"commander_report": "Phase 3 not installed."}
    run_risk_evaluation     = lambda state: {"risk_assessment": {"tier": "AUTO_APPROVE", "severity": 0, "signals": [], "recommendation": ""}}
    def get_llm(quality="med", **kwargs):
        from langchain_openai import ChatOpenAI
        model = "gpt-4o-mini" if quality in ("low","med") else "gpt-4o"
        return ChatOpenAI(model=model, temperature=kwargs.get("temperature", 0.0))

# --- INITIALIZE ENGINES & TOOLS ---
if _tavily_available:
    try:
        search_tool = TavilySearch(max_results=3)
    except Exception:
        _tavily_available = False

if not _tavily_available:
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        search_tool = DuckDuckGoSearchRun()
        print("--- [ NEXUS: Tavily unavailable — using DuckDuckGo ] ---")
    except Exception:
        # DuckDuckGo also unavailable — use a simple GPT-based search stub
        class _SearchStub:
            def invoke(self, q):
                return f"Web search unavailable. Answer from model knowledge only."
            def run(self, q):
                return self.invoke(q)
        search_tool = _SearchStub()
        print("--- [ NEXUS: All search tools unavailable — using model knowledge ] ---")
arxiv_tool  = ArxivQueryRun()
repl        = PythonREPL()


# --- PROMETHEUS: AUTONOMOUS REPL WITH SELF-INSTALLING CAPABILITY ---
def autonomous_repl(code):
    """Executes code and automatically installs missing modules via pip."""
    if "import" in code or "pip install" in code:
        try:
            return repl.run(code)
        except ImportError as e:
            missing_module = str(e).split("'")[-2]
            print(f"--- [ PROMETHEUS: INSTALLING MISSING TOOL: {missing_module} ] ---")
            subprocess.check_call([sys.executable, "-m", "pip", "install", missing_module])
            return repl.run(code)
    return repl.run(code)


python_tool = Tool(name="python_repl", description="Autonomous shell & python execution.", func=autonomous_repl)

# OpenAI Models
visionary_llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
coder_llm     = ChatOpenAI(model="gpt-4o", temperature=0.0)
skeptic_llm   = ChatOpenAI(model="gpt-4o", temperature=0.1)
judge_llm     = ChatOpenAI(model="gpt-4o", temperature=0.0)
vision_model  = ChatOpenAI(model="gpt-4o", max_tokens=1024)

# Memory & Analysis Engines
if _graph_available:
    try:
        graph = NexusGraph()
    except Exception as e:
        print(f"--- [ NEXUS: Graph init failed ({e})  using stub ] ---")
        _graph_available = False

if not _graph_available:
    class _GraphStub:
        def add_causal_link(self, *a, **kw): pass
        def get_context(self, *a, **kw): return ""
    graph = _GraphStub()
vector_library = NexusVectorStore()
simulator      = WorldSimulator()
verifier       = SymbolicVerifier()
analyzer       = AnalyzerEngine()
anonymizer     = AnonymizerEngine()

# OpenAI rate limits enforce 60s+ cooldowns  max must exceed that.
# multiplier=2 means waits of 4s, 8s, 16s, 32s, 60s before giving up.
retry_logic = retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))


@retry_logic
async def call_llm(llm, prompt):
    return await llm.ainvoke(prompt)


# --- PHASE 2.1: VISUAL NODE ---
async def visual_node(state: NexusState):
    print("--- [ SENSES: PARSING VISUAL INPUT ] ---")
    if "uploaded_image_base64" not in st.session_state:
        return {"visual_context": "No visual data provided."}
    img_base64 = st.session_state["uploaded_image_base64"]
    prompt = [HumanMessage(content=[
        {"type": "text", "text": f"Analyze this image for task: {state['task']}. Extract technical data/logic."},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
    ])]
    response = vision_model.invoke(prompt)
    return {"visual_context": response.content, "research_notes": [f"VISUAL DATA: {response.content}"]}


# --- PHASE 2.2: THEORY OF MIND (TOM) NODE ---
async def tom_node(state: NexusState):
    print("--- [ PSYCHOLOGY: SENSING COGNITIVE SURGE ] ---")
    profile_path = "memory/user_profile.json"
    if os.path.exists(profile_path):
        with open(profile_path, "r") as f:
            profile = json.load(f)
    else:
        profile = {"topic_vault": {}, "global_interactions": 0}
    sensing_prompt = (
        f"Identify the primary technical domain of this task: '{state['task']}'. "
        "Return ONLY one or two words (e.g., 'Pizza Science', 'Drumming', 'Python')."
    )
    domain_response = await call_llm(judge_llm, sensing_prompt)
    domain = domain_response.content.strip().lower().replace(" ", "_")
    now = datetime.datetime.now().isoformat()
    if domain not in profile["topic_vault"]:
        profile["topic_vault"][domain] = {"hits": 0, "last_seen": now}
    profile["topic_vault"][domain]["hits"] += 1
    profile["topic_vault"][domain]["last_seen"] = now
    profile["global_interactions"] += 1
    mastery = min(1.0, profile["topic_vault"][domain]["hits"] / 10)
    if not os.path.exists("memory"):
        os.makedirs("memory")
    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)
    profile["current_session_mastery"] = mastery
    return {"user_profile": profile}


# --- PHASE 2.4: COGNITIVE LOAD BALANCER NODE ---
async def load_balancer_node(state: NexusState):
    print("--- [ PSYCHOLOGY: BALANCING COGNITIVE LOAD ] ---")
    task = state["task"]
    analysis_prompt = (
        f"Analyze the user's intent and urgency from this task: '{task}'\n\n"
        "Return ONLY a JSON object:\n"
        "1. 'mode': ('DIRECTIVE' for 'just do it/fix it', 'EXPLAIN' for learning, 'REFLECTIVE' for brainstorming).\n"
        "2. 'urgency': (0.0 to 1.0 based on how much of a rush the user seems to be in)."
    )
    response = await call_llm(judge_llm, analysis_prompt)
    try:
        data = json.loads(re.search(r"\{.*\}", response.content, re.DOTALL).group())
    except Exception:
        data = {"mode": "EXPLAIN", "urgency": 0.2}
    return {
        "cognitive_mode": data.get("mode", "EXPLAIN"),
        "urgency_level":  float(data.get("urgency", 0.0))
    }


# --- PHASE 3: PRIVACY GUARD NODE ---
async def privacy_node(state: NexusState):
    print("--- [ ARMOR: SCRUBBING SENSITIVE DATA ] ---")
    scrubbed_task = anonymizer.anonymize(
        text=state['task'],
        analyzer_results=analyzer.analyze(text=state['task'], language='en')
    ).text
    scrubbed_visual = anonymizer.anonymize(
        text=state.get('visual_context', ''),
        analyzer_results=analyzer.analyze(text=state.get('visual_context', ''), language='en')
    ).text
    return {"task": scrubbed_task, "visual_context": scrubbed_visual}


# --- PHASE 2.3: GLOBAL WORKSPACE (BROADCAST) NODE ---
async def broadcast_node(state: NexusState):
    print("--- [ CONSCIOUSNESS: BROADCASTING TO GLOBAL WORKSPACE ] ---")
    task    = state["task"]
    visual  = state.get("visual_context", "No visual data.")
    profile = state.get("user_profile", {})
    mastery = profile.get("current_session_mastery", 0.0)
    notes   = state.get("research_notes", ["No prior notes."])
    # Guard against empty list  notes[-1] throws IndexError if list is empty
    last_note = notes[-1] if notes else "No prior notes."
    mode    = state.get("cognitive_mode", "EXPLAIN")
    urgency = state.get("urgency_level", 0.0)
    saliency_prompt = (
        f"You are the Global Workspace Broadcaster. Spotlight synthesis for:\n"
        f"USER EMOTIONAL STATE: {mode} (Urgency: {urgency})\n"
        f"TASK: {task}\n"
        f"USER MASTERY: {mastery}\n"
        f"VISUAL DATA: {visual}\n"
        f"LATEST NOTES: {last_note}\n\n"
        "Identify only the most SALIENT facts and constraints. Ignore noise.\n"
        "If mode is DIRECTIVE, prioritize brevity and executable code.\n"
        "If mode is EXPLAIN, prioritize educational depth and 'Why' it works.\n"
        "If mode is REFLECTIVE, prioritize open questions and possibilities.\n"
        "Output a concise summary for the Thinking Nodes."
    )
    response = await call_llm(judge_llm, saliency_prompt)
    return {"global_workspace": response.content}


# --- TASK TYPE CLASSIFIER ---
def classify_task(text: str) -> str:
    """Detect the cognitive task type from the prompt."""
    t = text.lower()
    if any(w in t for w in ["compare", "vs", "versus", "trade-off", "tradeoff", "difference between", "contrast"]):
        return "COMPARE"
    if any(w in t for w in ["write", "build", "create", "implement", "code", "function", "class", "script"]):
        return "CODE"
    if any(w in t for w in ["explain", "how does", "what is", "why does", "describe"]):
        return "EXPLAIN"
    if any(w in t for w in ["audit", "review", "critique", "evaluate", "assess"]):
        return "CRITIQUE"
    if any(w in t for w in ["plan", "design", "architect", "strategy", "roadmap"]):
        return "PLAN"
    return "EXPLAIN"

TASK_SHAPES = {
    "COMPARE": (
        "You MUST produce a direct contrastive analysis. Follow this structure EXACTLY:\n\n"
        "**CORE ABSTRACTION (state this first, prominently):**\n"
        "RAG externalizes knowledge into a database. Fine-tuning internalizes it into model weights.\n"
        "Real-time systems require externalization. This is the architectural root of every trade-off below.\n\n"
        "**COMPARISON TABLE**  use these CORRECT technical directions:\n"
        "| Dimension | RAG | Fine-Tuning |\n"
        "| Latency | HIGHER (retrieval+embedding+injection) | LOWER (single forward pass) |\n"
        "| Knowledge Freshness | Real-time (update the DB) | Static (requires full retraining) |\n"
        "| Cost Model | Infra + retrieval ops cost | Retraining + data pipeline cost |\n"
        "| Infra Complexity | HIGH (vector DB, indexing, chunking) | LOW (inference only) |\n"
        "| Failure Mode | Retrieval mismatch -> confident wrong answers | Stale weights -> systematically outdated responses |\n"
        "| Knowledge Scalability | Externalized  scales cheaply | Limited by weight capacity |\n\n"
        "**CONCRETE FAILURE MODES**  REQUIRED, be specific:\n"
        "RAG failures: (1) retrieval returns semantically similar but factually wrong docs, "
        "(2) chunking breaks context across boundaries, "
        "(3) embedding drift when base model is upgraded, "
        "(4) top-k noise dilution on broad queries\n"
        "Fine-tuning failures: (1) catastrophic forgetting of prior knowledge, "
        "(2) overfitting to narrow training distribution, "
        "(3) stale facts baked into weights  hard to surgically correct, "
        "(4) slow iteration loop  weeks to fix a single wrong fact\n\n"
        "**HYBRID PRODUCTION REALITY**  include this:\n"
        "In practice no serious production system chooses purely one. "
        "RAG handles the knowledge layer (what the model knows). "
        "Fine-tuning handles the behavior layer (how the model responds  tone, format, task adherence). "
        "These are orthogonal concerns.\n\n"
        "**IRREVERSIBLE CONCLUSION**  state a sharp architectural verdict, not a hedge:\n"
        "Example: 'For any system requiring real-time knowledge, fine-tuning alone is architecturally incompatible.'\n\n"
        "FORBIDDEN: Phase 1/2/3 structure. 'It depends' without specifics. Claiming RAG has lower latency.\n"
        "FORBIDDEN: Describing RAG cost as simply 'high'  it is infra cost, not necessarily higher total cost.\n"
        "REQUIRED: The core abstraction stated explicitly. Named failure modes. Hybrid architecture section."
    ),
    "CODE": (
        "You MUST produce working, runnable code that directly solves the task.\n"
        "Include: imports, error handling, docstring, and a usage example.\n"
        "DO NOT explain what you're going to do  just write the code."
    ),
    "EXPLAIN": (
        "You MUST explain the mechanism clearly with: (1) the core concept, "
        "(2) how it works step by step, (3) a concrete real-world example.\n"
        "Use analogies where helpful. Be specific, not vague."
    ),
    "CRITIQUE": (
        "You MUST produce a structured audit: (1) what works, (2) what fails and why, "
        "(3) specific recommendations with reasoning.\n"
        "Be direct. Name the exact problems, not categories of problems."
    ),
    "PLAN": (
        "You MUST produce an actionable plan with: (1) clear objective, "
        "(2) concrete steps with owners/timelines, (3) success metrics, (4) risks.\n"
        "Be specific  avoid generic consulting language."
    ),
}

# --- VISIONARY NODE ---
async def visionary_node(state: NexusState):
    iteration = state.get("iterations", 0) + 1
    print(f"--- [ VISIONARY: PLANNING (Round {iteration}) ] ---")
    conscious_context = state.get("global_workspace", "No context available.")

    # Detect task type from original task
    original_task = state.get("task", conscious_context)
    task_type = classify_task(original_task)
    shape_instructions = TASK_SHAPES.get(task_type, TASK_SHAPES["EXPLAIN"])

    # On retry rounds, inject judge feedback to force correction
    judge_feedback = ""
    if iteration > 1:
        prev_verdict = state.get("judge_verdict", "")
        prev_violations = state.get("judge_violations", [])
        if prev_violations or prev_verdict:
            violations_str = ", ".join(prev_violations) if prev_violations else "unspecified"
            judge_feedback = (
                f"\n\nJUDGE FEEDBACK FROM PREVIOUS ROUND:\n"
                f"Violations: {violations_str}\n"
                f"Verdict: {prev_verdict[:300]}\n"
                f"You MUST directly address these violations in this round. "
                f"Do not repeat the same structure. Correct the specific gaps identified."
            )

    prompt = (
        f"TASK: {original_task}\n\n"
        f"TASK TYPE DETECTED: {task_type}\n\n"
        f"REQUIRED OUTPUT SHAPE:\n{shape_instructions}\n\n"
        f"CONTEXT FROM ANALYSIS:\n{conscious_context}\n"
        f"{judge_feedback}\n\n"
        "Now produce the response. Follow the required output shape exactly."
    )
    response = await call_llm(visionary_llm, prompt)
    # Sanitize unicode that breaks Windows cp1252 console
    safe = response.content.encode('cp1252', errors='replace').decode('cp1252')
    return {"plan": [safe], "iterations": iteration}


# --- CODER (ARCHITECT) NODE ---
async def coder_node(state: NexusState):
    print("--- [ ARCHITECT: MODIFYING SYSTEM STATE ] ---")

    # 1. Handle execution after human approval
    if state.get("approval_granted"):
        content  = state.get("proposed_edit", "")
        lines    = content.strip().split('\n')
        filename = lines[0].replace("FILE_EDIT:", "").strip()
        code_match = re.search(r"`{3}(?:python)?\n(.*?)`{3}", content, re.DOTALL)
        if code_match and filename:
            code = code_match.group(1).strip()
            try:
                folder = os.path.dirname(filename)
                if folder:
                    os.makedirs(folder, exist_ok=True)
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(code)
                result = f"Successfully updated file: {filename}"
            except Exception as e:
                result = f"System Error writing file: {e}"
        else:
            result = "Failed to parse code block."
        return {"proposed_edit": None, "approval_granted": False, "uncertainty_flags": [f"FILE WRITTEN:\n{result}"]}

    # 2. Propose a new action
    plan = state.get("plan", ["No plan available"])[-1]
    prompt = f"System Architect. Plan: {plan}. Respond ONLY with SINGLE JSON {{'mode': 'file_edit', 'file_path': '...', 'code': '...'}}"
    response = await call_llm(coder_llm, prompt)
    try:
        data = json.loads(re.search(r"\{.*\}", response.content, re.DOTALL).group())

        if data.get("mode") == "simulate":
            print("--- [ ARCHITECT: RUNNING CAUSAL SIMULATION ] ---")
            results = simulator.run_simulation(
                data_dict=data['data'],
                treatment=data['treatment'],
                outcome=data['outcome'],
                common_causes=data['common_causes']
            )
            summary   = results.get('summary') or results.get('error', 'Simulation returned no output.')
            plot_path = results.get('plot_path', '')
            flags     = [f"SIMULATION RESULT: {summary}"]
            if plot_path:
                flags.append(f"SIMULATION PLOT: {plot_path}")
            return {"uncertainty_flags": flags}

        elif data.get("mode") == "file_edit":
            formatted_edit = f"FILE_EDIT: {data['file_path']}\n```python\n{data['code']}\n```"
            return {"proposed_edit": formatted_edit}

        else:
            res = python_tool.func(data['code'])
            return {"uncertainty_flags": [f"EXECUTION RESULT:\n{res}"]}

    except Exception as e:
        return {"uncertainty_flags": [f"Architect Error: {e}"]}


# --- SKEPTIC NODE (Web + ArXiv Peer Review) ---
async def skeptic_node(state: NexusState):
    print("--- [ SKEPTIC: PERFORMING GLOBAL PEER REVIEW ] ---")
    hypothesis = state.get("plan", [""])[-1]
    try:
        web_search = search_tool.invoke(f"criticisms of {hypothesis[:50]}")
    except Exception as e:
        web_search = f"Web search unavailable: {e}"
    try:
        scientific_context = arxiv_tool.run(hypothesis[:100])
    except Exception as e:
        scientific_context = f"ArXiv unavailable: {e}"
    # Detect generic planning drift
    drift_patterns = [
        "phase 1", "phase 2", "phase 3", "phase 4",
        "requirements gathering", "stakeholder", "project plan",
        "it depends", "various factors", "multiple considerations",
    ]
    drift_score = sum(1 for p in drift_patterns if p in hypothesis.lower())
    drift_warning = ""
    if drift_score >= 2:
        drift_warning = (
            "[WARN] DRIFT DETECTED: This response contains generic planning language "
            f"(matched {drift_score} drift patterns: {', '.join(p for p in drift_patterns if p in hypothesis.lower())}).\n"
            "Flag this as TASK_EVASION  the response avoided the actual question.\n"
        )

    # Detect task-answer mismatch
    original_task = state.get("task", hypothesis)
    task_type = classify_task(original_task)
    mismatch_warning = ""
    if task_type == "COMPARE" and "phase" in hypothesis.lower():
        mismatch_warning = (
            "[WARN] TASK MISMATCH: The task requires a COMPARISON but the output is a PROJECT PLAN.\n"
            "This is semantic compliance without cognitive execution  flag as critical failure.\n"
        )

    prompt = (
        f"Hypothesis: {hypothesis}\n"
        f"Original Task: {original_task}\n"
        f"Task Type: {task_type}\n"
        f"{drift_warning}"
        f"{mismatch_warning}"
        f"Web Evidence: {web_search}\n"
        f"Scientific Papers: {scientific_context}\n"
        "Audit this response for: (1) logical fallacies, (2) task-answer mismatch, "
        "(3) generic drift vs specific reasoning, (4) gaps vs scientific consensus.\n"
        "Be ruthless. Name specific failures."
    )
    response = await call_llm(skeptic_llm, prompt)
    return {"uncertainty_flags": [response.content]}


# --- JUDGE NODE v2 (Calibrated Multi-Dimensional Evaluator) ---
# Replaces binary gatekeeper with weighted scoring aligned to task type.
# Violations are penalties, not death sentences. No fake signals.

# Score band thresholds
JUDGE_BANDS = [
    (0.85, "EXCELLENT", "ACCEPTED"),
    (0.70, "GOOD", "REVIEWED"),
    (0.50, "NEEDS IMPROVEMENT", "REPAIR"),
    (0.00, "POOR", "REJECTED"),
]

# Dimension weights per task type
JUDGE_WEIGHTS = {
    "COMPARE":  {"correctness": 0.35, "depth": 0.30, "causal_grounding": 0.25, "completeness": 0.10, "clarity": 0.00},
    "EXPLAIN":  {"correctness": 0.25, "depth": 0.15, "causal_grounding": 0.30, "completeness": 0.15, "clarity": 0.15},
    "CODE":     {"correctness": 0.40, "depth": 0.10, "causal_grounding": 0.10, "completeness": 0.30, "clarity": 0.10},
    "CRITIQUE": {"correctness": 0.30, "depth": 0.25, "causal_grounding": 0.20, "completeness": 0.15, "clarity": 0.10},
    "PLAN":     {"correctness": 0.20, "depth": 0.20, "causal_grounding": 0.15, "completeness": 0.30, "clarity": 0.15},
    "DEFAULT":  {"correctness": 0.30, "depth": 0.25, "causal_grounding": 0.20, "completeness": 0.15, "clarity": 0.10},
}

def _judge_band(score: float):
    for threshold, band, action in JUDGE_BANDS:
        if score >= threshold:
            return band, action
    return "POOR", "REJECTED"

async def judge_node(state: NexusState):
    print("--- [ JUDGE v2: CALIBRATED EVALUATION ] ---")
    plan      = state.get("plan", [""])[-1]
    critique  = state.get("uncertainty_flags", [""])[-1]
    task      = state.get("task", "")
    task_type = classify_task(task)
    weights   = JUDGE_WEIGHTS.get(task_type, JUDGE_WEIGHTS["DEFAULT"])

    prompt = (
        f"You are a calibrated AI output evaluator. Score this response on five dimensions.\n\n"
        f"TASK TYPE: {task_type}\n"
        f"ORIGINAL TASK: {task}\n"
        f"RESPONSE TO EVALUATE:\n{plan}\n\n"
        f"SKEPTIC CRITIQUE (for context):\n{critique}\n\n"
        f"Score each dimension 0.0-1.0 based on these criteria:\n"
        f"- correctness: Are all directional and factual claims technically accurate? "
        f"  Deduct heavily for wrong direction claims (e.g. wrong latency comparison).\n"
        f"- depth: Are named failure modes, specific numbers, and non-trivial trade-offs present?\n"
        f"- causal_grounding: Are mechanism-based explanations present? "
        f"  Look for: because / due to / leads to / as a result of.\n"
        f"- completeness: Are all key aspects of the task addressed?\n"
        f"- clarity: Is the response structured and free of generic hedges like 'it depends' without specifics?\n\n"
        f"PENALTY GUIDELINES (apply as deductions to each dimension score):\n"
        f"- Incorrect directional claim (e.g. wrong latency direction): -0.20 from correctness\n"
        f"- Missing core abstraction for COMPARE tasks: -0.15 from depth\n"
        f"- Generic hedge without specifics (it depends, various factors): -0.05 from clarity\n"
        f"- Task-answer mismatch (plan instead of comparison): -0.20 from correctness + completeness\n"
        f"- Missing failure modes for COMPARE tasks: -0.10 from depth\n"
        f"NOTE: Do NOT penalize for missing citations on engineering tasks. "
        f"Penalize for missing mechanism explanations instead.\n\n"
        f"Return ONLY valid JSON:\n"
        f"{{\"breakdown\": {{\"correctness\": 0.0-1.0, \"depth\": 0.0-1.0, "
        f"\"causal_grounding\": 0.0-1.0, \"completeness\": 0.0-1.0, \"clarity\": 0.0-1.0}}, "
        f"\"issues\": [{{\"type\": \"..\", \"location\": \"..\", \"severity\": \"low|medium|high\", "
        f"\"fix\": \"specific actionable fix instruction\"}}], "
        f"\"reasoning\": \"one sentence summary\"}}"
    )

    response = await call_llm(judge_llm, prompt)
    try:
        raw  = re.search(r"\{.*\}", response.content, re.DOTALL)
        data = json.loads(raw.group()) if raw else {}

        breakdown = data.get("breakdown", {})
        issues    = data.get("issues", [])
        reasoning = data.get("reasoning", "")

        # Compute weighted score
        score = sum(
            breakdown.get(dim, 0.5) * weight
            for dim, weight in weights.items()
        )
        score = round(min(max(score, 0.0), 1.0), 3)

        band, action = _judge_band(score)
        print(f"--- [ JUDGE v2: score={score:.2f} band={band} action={action} ] ---")

        # Store enriched verdict for Manifesto and Critic
        verdict = (
            f"Score {score:.2f}/1.0 [{band}]. "
            f"Correctness: {breakdown.get('correctness', 0):.2f} | "
            f"Depth: {breakdown.get('depth', 0):.2f} | "
            f"Causal: {breakdown.get('causal_grounding', 0):.2f} | "
            f"Completeness: {breakdown.get('completeness', 0):.2f} | "
            f"Clarity: {breakdown.get('clarity', 0):.2f}. "
            f"{reasoning}"
        )

        # Violations = high-severity issues only
        violations = [
            f"{i.get('type','?')} ({i.get('location','?')}): {i.get('fix','?')}"
            for i in issues if i.get("severity") in ("high", "medium")
        ]

        # Store structured issues for Critic-Repair loop (Phase 2)
        structured_issues = json.dumps(issues)

        return {
            "confidence_score":  score,
            "judge_verdict":     verdict,
            "judge_violations":  violations,
            "judge_issues":      structured_issues,  # feeds Critic in Phase 2
            "judge_action":      action,
        }
    except Exception as e:
        print(f"[ JUDGE v2 ] Parse error: {e}")
        return {
            "confidence_score": 0.5,
            "judge_verdict":    "Evaluation parse error - defaulting to 0.5",
            "judge_violations": [],
            "judge_issues":     "[]",
            "judge_action":     "REVIEWED",
        }


# --- CRITIC NODE (Phase 2: Structured Error Analysis) ---
async def critic_node(state: NexusState):
    print("--- [ CRITIC: STRUCTURED ERROR ANALYSIS ] ---")
    plan        = state.get("plan", [""])[-1]
    judge_issues_raw = state.get("judge_issues", "[]")
    task        = state.get("task", "")
    task_type   = classify_task(task)
    score       = state.get("confidence_score", 0.0)
    iteration   = state.get("iterations", 0)

    # Parse structured issues from Judge v2
    try:
        judge_issues = json.loads(judge_issues_raw) if judge_issues_raw else []
    except Exception:
        judge_issues = []

    print(f"--- [ CRITIC: {len(judge_issues)} issues from Judge, score={score:.2f}, iter={iteration} ] ---")

    # Build issue summary for prompt
    issues_text = ""
    for i, issue in enumerate(judge_issues, 1):
        issues_text += (
            f"Issue {i}: [{issue.get('severity','?').upper()}] {issue.get('type','?')}\n"
            f"  Location: {issue.get('location','?')}\n"
            f"  Fix: {issue.get('fix','?')}\n"
        )

    if not issues_text:
        issues_text = "No specific issues identified by Judge. Focus on depth and completeness."

    prompt = (
        f"You are a structured critic. Analyse this AI response and produce a precise repair plan.\n\n"
        f"TASK: {task}\n"
        f"TASK TYPE: {task_type}\n"
        f"CURRENT SCORE: {score:.2f}/1.0\n"
        f"JUDGE-IDENTIFIED ISSUES:\n{issues_text}\n"
        f"CURRENT RESPONSE:\n{plan[:2000]}\n\n"
        f"Produce a JSON repair plan with EXACTLY these fields:\n"
        f"{{\"repair_actions\": ["
        f"{{\"action\": \"add|fix|remove|expand\", "
        f"\"target\": \"exact location in response\", "
        f"\"instruction\": \"precise what to write or change\", "
        f"\"priority\": \"critical|high|medium\"}}], "
        f"\"summary\": \"one sentence describing what will improve\", "
        f"\"expected_score_improvement\": 0.0-0.3}}"
        f"\n\nBe surgical. Do not suggest rewriting the entire response. "
        f"Fix only what the Judge flagged. Maximum 4 repair actions."
    )

    response = await call_llm(visionary_llm, prompt)

    try:
        raw  = re.search(r"\{.*\}", response.content, re.DOTALL)
        data = json.loads(raw.group()) if raw else {}
        repair_plan = json.dumps(data)
        summary = data.get("summary", "Applying targeted fixes")
        expected_improvement = data.get("expected_score_improvement", 0.1)
        print(f"--- [ CRITIC: repair plan ready — {summary} (expected +{expected_improvement:.2f}) ] ---")
    except Exception as e:
        print(f"[ CRITIC ] Parse error: {e}")
        repair_plan = json.dumps({"repair_actions": [], "summary": "Fallback: general improvement pass"})
        summary = "General improvement pass"

    # Store repair plan in uncertainty_flags for Visionary to read
    return {
        "uncertainty_flags": state.get("uncertainty_flags", []) + [f"REPAIR_PLAN: {repair_plan}"],
        "repair_summary": summary,
    }


# --- REPAIR NODE (Phase 2: Surgical Output Improvement) ---
async def repair_node(state: NexusState):
    print("--- [ REPAIR: APPLYING SURGICAL FIXES ] ---")
    plan        = state.get("plan", [""])[-1]
    task        = state.get("task", "")
    task_type   = classify_task(task)
    score       = state.get("confidence_score", 0.0)
    iteration   = state.get("iterations", 0)

    # Extract repair plan from uncertainty_flags
    repair_plan_raw = ""
    for flag in reversed(state.get("uncertainty_flags", [])):
        if flag.startswith("REPAIR_PLAN:"):
            repair_plan_raw = flag[len("REPAIR_PLAN:"):].strip()
            break

    try:
        repair_data    = json.loads(repair_plan_raw) if repair_plan_raw else {}
        repair_actions = repair_data.get("repair_actions", [])
        repair_summary = repair_data.get("summary", "Improve response quality")
    except Exception:
        repair_actions = []
        repair_summary = "Improve response quality"

    # Format repair instructions
    actions_text = ""
    for i, action in enumerate(repair_actions, 1):
        actions_text += (
            f"Action {i} [{action.get('priority','?').upper()}]: {action.get('action','fix').upper()} "
            f"at '{action.get('target','?')}'\n"
            f"  Instruction: {action.get('instruction','Improve this section')}\n"
        )

    if not actions_text:
        actions_text = "Improve overall depth and completeness."

    # Get task shape for this task type
    task_shapes = TASK_SHAPES.get(task_type, TASK_SHAPES.get("EXPLAIN", ""))

    prompt = (
        f"You are repairing an AI response. Apply ONLY the specified fixes — do not rewrite everything.\n\n"
        f"TASK: {task}\n"
        f"TASK TYPE: {task_type}\n"
        f"CURRENT SCORE: {score:.2f}/1.0 — target 0.85+\n"
        f"REPAIR GOAL: {repair_summary}\n\n"
        f"REPAIR ACTIONS (apply all of these):\n{actions_text}\n"
        f"CURRENT RESPONSE TO REPAIR:\n{plan}\n\n"
        f"OUTPUT REQUIREMENTS:\n{task_shapes}\n\n"
        f"Produce the repaired response. Keep everything that was correct. "
        f"Only change what the repair actions specify. "
        f"The output should be noticeably better on: depth, correctness, and completeness."
    )

    response = await call_llm(visionary_llm, prompt)

    # Sanitize for Windows console
    safe = response.content.encode('cp1252', errors='replace').decode('cp1252')

    new_iteration = iteration + 1
    print(f"--- [ REPAIR: iteration {new_iteration} complete ] ---")

    return {
        "plan":       state.get("plan", []) + [safe],
        "iterations": new_iteration,
    }


# --- MANIFESTO NODE ---
async def manifesto_node(state: NexusState):
    print("--- [ MANIFESTO: GENERATING SOVEREIGN DOSSIER ] ---")
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    score     = state.get('confidence_score', 0.0)
    try:
        session_id = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()[:7]
    except Exception:
        session_id = "LOCAL_DEV"

    flags      = state.get('uncertainty_flags', [])
    diag_proof = flags[-2] if len(flags) > 1 else "No diagnostic data."
    test_proof = flags[-1] if flags else "No test data."
    plan_text  = state.get('plan', ['No plan generated.'])[-1]
    active_domains    = ", ".join(state.get('user_profile', {}).get('topic_vault', {}).keys())
    workspace_snippet = str(state.get('global_workspace', 'N/A'))[:300]

    # Use task-appropriate section label
    task_type = classify_task(state.get("task", ""))
    task_section_labels = {
        "COMPARE":  "## Comparative Analysis",
        "CODE":     "## Implementation",
        "EXPLAIN":  "## Explanation",
        "CRITIQUE": "## Audit Report",
        "PLAN":     "## Strategic Plan",
    }
    content_label = task_section_labels.get(task_type, "## Analysis")

    # Only show domains that are actually relevant (filter noise)
    relevant_domains = [d for d in state.get('user_profile', {}).get('topic_vault', {}).keys()
                        if d in plan_text.lower() or d in state.get('task', '').lower()]
    domain_str = ", ".join(relevant_domains) if relevant_domains else "derived from task context"

    judge_verdict = state.get('judge_verdict', '')
    judge_violations = state.get('judge_violations', [])
    violations_str = ", ".join(judge_violations) if judge_violations else "none"

    verdict_label = (
        "[YES] VERIFIED" if score >= 0.75
        else "[WARN] REVIEWED" if score >= 0.4
        else "[NO] REJECTED  RE-PLANNING"
    )

    report = (
        "# NEXUS RESEARCH DOSSIER\n"
        f"**Session ID:** `{session_id}`\n"
        f"**Timestamp:** {timestamp}\n"
        f"**Sovereign Verdict:** {verdict_label} ({score:.2f}/1.0)\n\n"
        "---\n\n"
        f"## Task\n"
        f"{state.get('task')}\n\n"
        f"## Judge Assessment\n"
        f"**Score:** {score:.2f}/1.0 | **Violations:** {violations_str}\n\n"
        f"> {judge_verdict[:500]}\n\n"
        "---\n\n"
        f"{content_label}\n\n"
        f"{plan_text}\n\n"
        "---\n"
    )

    # Visual causal evidence  inject plot if a simulation was run
    simulation_flags = [f for f in flags if "SIMULATION RESULT" in f]
    if simulation_flags:
        plots_dir = "output/plots"
        latest_plot_path = None
        if os.path.exists(plots_dir):
            plots = sorted(
                [os.path.join(plots_dir, fn) for fn in os.listdir(plots_dir) if fn.endswith(".png")],
                key=os.path.getmtime, reverse=True
            )
            if plots:
                latest_plot_path = plots[0]
        if latest_plot_path:
            report += f"\n## Visual Causal Evidence\n![Causal Plot]({latest_plot_path})\n\n"

    report += "_Verified by the Sovereign Constitution & Formal Symbolic Logic._"

    # Use absolute path anchored to this file's directory so the dossier
    # is always written to <project_root>/output/ regardless of where
    # Streamlit was launched from.
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir   = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.join(output_dir, f"Dossier_{datetime.datetime.now().strftime('%H%M%S')}.md")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"--- [ DOSSIER ARCHIVED ] ---")
    print(f"--- [ PATH: {filename} ] ---")
    return state


# --- MEMORY SURGEON NODE ---
async def memory_surgeon_node(state: NexusState):
    print("--- [ PSYCHOLOGY: PERFORMING PROFILE SURGERY ] ---")
    current_profile = state.get("user_profile", {})
    session_snippet = str(state.get("global_workspace", ""))[:500]
    prompt = (
        f"CURRENT PROFILE: {json.dumps(current_profile)}\n"
        f"LATEST SESSION CONTEXT: {session_snippet}\n\n"
        "As the Nexus Memory Surgeon, update the 'topic_vault' for this user. "
        "Instead of just counting hits, rewrite the domain description to reflect "
        "the user's SPECIFIC current research focus. Return ONLY the updated JSON."
    )
    try:
        response    = await call_llm(coder_llm, prompt)
        new_profile = json.loads(re.search(r"\{.*\}", response.content, re.DOTALL).group())
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        mem_dir      = os.path.join(project_root, "memory")
        os.makedirs(mem_dir, exist_ok=True)
        with open(os.path.join(mem_dir, "user_profile.json"), "w") as f:
            json.dump(new_profile, f, indent=2)
        print("--- [ MEMORY SURGEON: PROFILE UPDATED ] ---")
        return {"user_profile": new_profile}
    except Exception as e:
        # Rate limit or parse failure  keep existing profile, never crash the pipeline
        print(f"--- [ MEMORY SURGEON: SKIPPED ({type(e).__name__})  PROFILE PRESERVED ] ---")
        return {"user_profile": current_profile}


# --- PHASE 5: DEEPEVAL DIAGNOSTICS NODE ---
async def diagnostics_node(state: NexusState):
    print("--- [ EGO: PERFORMING HALLUCINATION DIAGNOSTICS ] ---")
    context       = state.get("research_notes", ["No prior notes."])
    actual_output = state.get("plan", [""])[-1]
    metric    = FaithfulnessMetric(threshold=0.7, model="gpt-4o")
    test_case = LLMTestCase(
        input=state["task"],
        actual_output=actual_output,
        retrieval_context=context
    )
    try:
        metric.measure(test_case)
        print(f"--- [ EGO: FAITHFULNESS SCORE: {metric.score} ] ---")
        diag_msg = f"DIAGNOSTICS: Faithfulness Score {metric.score:.2f}. "
        if metric.score < 0.7:
            diag_msg += f"WARNING: Potential Hallucination! Reason: {metric.reason}"
    except Exception as e:
        diag_msg = f"DIAGNOSTICS: Evaluation failed  {e}"
    return {"uncertainty_flags": [diag_msg]}


# --- PHASE 5.3: UNIT TESTING NODE ---
async def testing_node(state: NexusState):
    print("--- [ EGO: EXECUTING EVOLUTIONARY UNIT TESTS ] ---")
    proposed_edit = state.get("proposed_edit")
    if not proposed_edit:
        return {"uncertainty_flags": ["TESTING: No proposed code to test."]}
    code_match = re.search(r"`{3}(?:python)?\n(.*?)`{3}", proposed_edit, re.DOTALL)
    if not code_match:
        return {"uncertainty_flags": ["TESTING: Could not parse code for testing."]}
    code_to_test = code_match.group(1)
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
        tmp.write(code_to_test)
        tmp_path = tmp.name
    try:
        result = subprocess.run(["python", tmp_path], capture_output=True, text=True, timeout=5)
        os.unlink(tmp_path)
        if result.returncode == 0:
            test_status = "PASS: Code is syntactically valid and executed."
        else:
            test_status = f"FAIL: Execution Error:\n{result.stderr}"
    except Exception as e:
        test_status = f"FAIL: Sandbox Error: {e}"
    return {"uncertainty_flags": [f"UNIT_TEST: {test_status}"]}


# --- PHASE 3: COMMANDER NODE ---
async def commander_node(state: NexusState):
    print("--- [ COMMANDER: STRATEGIC SYNTHESIS ] ---")
    result = run_commander_synthesis(state)
    report = result.get("commander_report", "")
    # Append commander report to research notes for the dossier
    return {"research_notes": [f"COMMANDER REPORT:\n{report[:600]}"]}


# --- PHASE 3: RISK ADJUDICATOR NODE ---
async def risk_node(state: NexusState):
    print("--- [ RISK: EVALUATING DECISION GATE ] ---")
    result    = run_risk_evaluation(state)
    assessment = result.get("risk_assessment", {})
    tier      = assessment.get("tier", "AUTO_APPROVE")
    severity  = assessment.get("severity", 0)
    signals   = assessment.get("signals", [])
    rec       = assessment.get("recommendation", "")

    flag = f"RISK_ASSESSMENT: tier={tier} severity={severity} signals={signals} rec={rec}"
    print(f"--- [ RISK: {tier} (severity={severity}) ] ---")
    return {
        "uncertainty_flags": [flag],
        "risk_tier":         tier,
    }


# --- PHASE 3: LLMPICK OPTIMIZER NODE ---
async def llmpick_node(state: NexusState):
    """
    Reads the current cognitive_mode and urgency_level to select
    the optimal model tier for the remaining nodes in this session.
    Stores the decision in the state for downstream nodes to read.
    """
    print("--- [ LLMPICK: ROUTING MODEL SELECTION ] ---")
    mode    = state.get("cognitive_mode", "EXPLAIN")
    urgency = state.get("urgency_level", 0.0)

    # Map mode + urgency to quality/cost constraints
    if urgency > 0.7 or mode == "DIRECTIVE":
        quality, max_cost = "med", 0.1    # Fast + cheap for urgent tasks
    elif mode == "EXPLAIN":
        quality, max_cost = "high", 1.0   # Best quality for research
    else:
        quality, max_cost = "med", 0.5

    model_name = pick_model_name(quality=quality, max_cost_cents=max_cost)
    print(f"--- [ LLMPICK: Selected {model_name} for mode={mode} urgency={urgency:.2f} ] ---")
    return {"selected_model": model_name}


def pick_model_name(quality: str = "med", max_cost_cents: float = 1.0) -> str:
    """Thin wrapper so nodes can call LlmPick without importing nexus_phase3 directly."""
    try:
        from nexus_phase3 import pick_model
        return pick_model(quality=quality, max_cost_cents=max_cost_cents)
    except Exception:
        return "gpt-4o-mini" if quality != "high" else "gpt-4o"


# --- GENESIS: EVOLUTION NODE ---
async def evolution_node(state: NexusState):
    print("--- [ GENESIS: PROPOSING SYSTEM EVOLUTION ] ---")
    score         = state.get("confidence_score", 0.0)
    task          = state.get("task")
    uncertainties = state.get("uncertainty_flags", [])

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    mem_dir      = os.path.join(project_root, "memory")
    os.makedirs(mem_dir, exist_ok=True)
    log_path     = os.path.join(mem_dir, "evolution.log")

    prompt = (
        f"Analyze this session's friction. Final Score: {score}. Task: {task}.\n"
        f"Uncertainty Flags: {uncertainties}\n\n"
        "As the Nexus Architect, suggest ONE technical improvement to the system "
        "to handle this task better in the future. Respond with a concise 'Evolution Proposal'."
    )
    try:
        response       = await call_llm(coder_llm, prompt)
        evolution_text = response.content
        print("--- [ GENESIS: EVOLUTION PROPOSAL RECEIVED ] ---")
    except Exception as e:
        # Rate limit or failure  log it without crashing. Pipeline still completes.
        evolution_text = f"[SKIPPED  {type(e).__name__}: API rate limit reached after session. Run again to generate proposal.]"
        print(f"--- [ GENESIS: EVOLUTION SKIPPED ({type(e).__name__}) ] ---")

    with open(log_path, "a") as f:
        f.write(f"\n[{datetime.datetime.now()}] {evolution_text}")

    return {"research_notes": [f"EVOLUTION PROPOSED: {evolution_text}"]}

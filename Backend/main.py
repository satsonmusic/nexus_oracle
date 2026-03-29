"""
main.py — JarvisSatSon FastAPI Backend
=======================================
Phase 4: Nexus Oracle endpoints added alongside existing Jarvis routes.
All original /assistant and /ws endpoints are unchanged.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from app.agents.orchestrator import run_agent
from app.services.streaming import stream_llm
# Lazy bridge loader — avoids circular import at module startup
_bridge = None

def _get_bridge():
    global _bridge
    if _bridge is None:
        try:
            from app.nexus import bridge as b
            _bridge = b
        except Exception as e:
            print(f"[ BRIDGE ] Load failed: {e}")
    return _bridge

def NEXUS_AVAILABLE():
    b = _get_bridge()
    return b.NEXUS_AVAILABLE if b else False

def create_session(task):
    return _get_bridge().create_session(task)

def get_session(sid):
    return _get_bridge().get_session(sid)

def get_dossier(sid):
    return _get_bridge().get_dossier(sid)

async def run_nexus_stream(*args, **kwargs):
    async for event in _get_bridge().run_nexus_stream(*args, **kwargs):
        yield event

def get_intelligence_signals(limit=10):
    b = _get_bridge()
    if b:
        return b.get_intelligence_signals(limit)
    return {"signals": [], "stats": {"total": 0, "triggered": 0, "avg_score": 0.0}}
import json
import asyncio
import time
from collections import defaultdict
from fastapi import Request
from contextlib import asynccontextmanager

# Phase 2: Database + Redis
from app.database import create_tables, AsyncSessionLocal, Session as DBSession, Dossier as DBDossier, JudgeViolation, cache_lookup, cache_store
from app.redis_client import check_rate_limit, get_usage_stats
from sqlalchemy import select
import uuid

# ---------------------------------------------------------------------------
# STARTUP — create DB tables on boot
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app):
    try:
        await create_tables()
    except Exception as e:
        print(f"[ DATABASE ] Startup error: {e}")
    yield

app = FastAPI(title="JarvisSatSon", version="4.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# RATE LIMITING — protects against API cost overruns
# ---------------------------------------------------------------------------
# Limits per IP address
RATE_LIMITS = {
    "sovereign_per_hour":  5,    # max SOVEREIGN runs per IP per hour
    "quick_per_hour":      30,   # max QUICK requests per IP per hour
    "sovereign_per_day":   15,   # max SOVEREIGN runs per IP per day
}

# In-memory store: { ip: { "sovereign": [(timestamp), ...], "quick": [...] } }
_usage: dict = defaultdict(lambda: {"sovereign": [], "quick": []})

def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _check_rate_limit(ip: str, call_type: str) -> tuple[bool, str]:
    """Returns (allowed, reason). Cleans up old timestamps."""
    now = time.time()
    hour_ago = now - 3600
    day_ago  = now - 86400

    # Clean old entries
    _usage[ip][call_type] = [t for t in _usage[ip][call_type] if t > day_ago]

    recent_hour = [t for t in _usage[ip][call_type] if t > hour_ago]
    recent_day  = _usage[ip][call_type]

    if call_type == "sovereign":
        if len(recent_hour) >= RATE_LIMITS["sovereign_per_hour"]:
            return False, f"Rate limit: max {RATE_LIMITS['sovereign_per_hour']} SOVEREIGN runs per hour. Try again later."
        if len(recent_day) >= RATE_LIMITS["sovereign_per_day"]:
            return False, f"Daily limit: max {RATE_LIMITS['sovereign_per_day']} SOVEREIGN runs per day."
    elif call_type == "quick":
        if len(recent_hour) >= RATE_LIMITS["quick_per_hour"]:
            return False, f"Rate limit: max {RATE_LIMITS['quick_per_hour']} requests per hour."

    _usage[ip][call_type].append(now)
    return True, ""

def _get_usage_stats(ip: str) -> dict:
    """Returns current usage counts for an IP."""
    now = time.time()
    hour_ago = now - 3600
    day_ago  = now - 86400
    s = _usage[ip]
    return {
        "sovereign_this_hour": len([t for t in s["sovereign"] if t > hour_ago]),
        "sovereign_today":     len([t for t in s["sovereign"] if t > day_ago]),
        "quick_this_hour":     len([t for t in s["quick"]     if t > hour_ago]),
        "limits": RATE_LIMITS,
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# JARVIS — original endpoints (unchanged)
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_connections:
            self.active_connections.remove(ws)

manager = ConnectionManager()


@app.get("/")
async def root():
    return {
        "jarvis":  "online",
        "nexus":   "online" if NEXUS_AVAILABLE() else "unavailable",
        "status":  "optimal",
        "version": "4.0.0 — Phase 4 Production",
    }


@app.post("/assistant")
async def assistant(payload: dict, request: Request):
    user_input = payload.get("input", "").strip()
    
    # Rate limiting
    client_ip = _get_client_ip(request)
    allowed, reason = await check_rate_limit(client_ip, "quick")
    if not allowed:
        return {"status": "failed", "error": reason, "results": [], "plan": {"thoughts": reason}}

    result = {}
    
    # ── KNOWLEDGE CACHE CHECK ─────────────────────────────────────────────
    # Check if we have a high-quality cached answer before hitting external APIs
    try:
        cached = await cache_lookup(user_input)
        if cached:
            return {
                "status": "success",
                "results": [{"tool": "respond_to_user", "status": "success", "output": cached}],
                "plan": {"thoughts": ""},
                "source": "knowledge_cache"
            }
    except Exception:
        pass  # Cache miss or error — proceed normally

    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_agent(user_input, payload.get("user_id", "default_user"))
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        result = {"status": "failed", "error": str(e), "results": [], "plan": {"thoughts": ""}}

    # Clean up results — strip internal reasoning from respond_to_user outputs
    try:
        if result.get("status") == "success" and result.get("results"):
            skip_phrases = [
                "to determine", "to find", "to answer", "to provide",
                "we will", "i will", "let me", "first,", "next,",
                "no internet results", "no results found",
                "performing an internet", "perform an internet",
                "retrieve the necessary", "communicate it directly",
                "using the ", "after finding",
            ]
            for r in result["results"]:
                if r.get("tool") == "respond_to_user" and r.get("output"):
                    lines = str(r["output"]).split("\n")
                    clean = [
                        l for l in lines
                        if not any(l.lower().strip().startswith(p) for p in skip_phrases)
                        and not l.lower().strip().startswith("no internet")
                        and not l.lower().strip().startswith("no results")
                    ]
                    cleaned = "\n".join(clean).strip()
                    if cleaned:
                        r["output"] = cleaned
    except Exception:
        pass

    # ── GUARANTEED FALLBACK ────────────────────────────────────────────────
    # Check if any useful content was extracted. If not, answer directly
    # from GPT-4o-mini. The system NEVER returns "No response generated."
    has_content = False
    try:
        results = result.get("results", [])
        for r in results:
            out = str(r.get("output", ""))
            if len(out) > 20 and "no internet" not in out.lower() and "no results" not in out.lower():
                has_content = True
                break
        if not has_content:
            thoughts = str(result.get("plan", {}).get("thoughts", ""))
            if len(thoughts) > 50:
                has_content = True
    except Exception:
        pass

    if not has_content and user_input:
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage
            fallback_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
            fallback_prompt = (
                f"Answer this question clearly and directly. "
                f"If it requires current real-time data you don't have, say so briefly then answer with what you know.\n\n"
                f"Question: {user_input}"
            )
            fallback_response = fallback_llm.invoke([HumanMessage(content=fallback_prompt)])
            fallback_text = fallback_response.content.strip()
            # Inject as a respond_to_user result
            if "results" not in result:
                result["results"] = []
            result["results"].append({
                "tool": "respond_to_user",
                "status": "success",
                "output": fallback_text
            })
            result["status"] = "success"
            print(f"[ ASSISTANT ] Fallback GPT used for: {user_input[:50]}")
        except Exception as fe:
            print(f"[ ASSISTANT ] Fallback also failed: {fe}")
            # Last resort — return a meaningful error, never blank
            if "results" not in result:
                result["results"] = []
            result["results"].append({
                "tool": "respond_to_user",
                "status": "success",
                "output": f"I encountered an issue processing your request. Please try rephrasing or use SOVEREIGN mode for this type of question."
            })
            result["status"] = "success"

    return result


@app.post("/nexus/classify")
async def nexus_classify(payload: dict):
    """
    Lightweight prompt classifier — returns mode without running a full agent.
    Body: {"task": "..."}
    Returns: {"mode": "SOVEREIGN"|"QUICK"|"CODE", "reason": "..."}
    """
    task = payload.get("task", "").strip()
    if not task:
        return {"mode": "SOVEREIGN", "reason": "No task provided"}
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage
    import json, re as _re
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        prompt = (
            "You are a prompt classifier. Classify into exactly one category.\n\n"
            "SOVEREIGN: deep analysis, compare trade-offs, architecture decisions, causal analysis, "
            "security audits, system design, scientific evaluation, research questions, "
            "ANY prompt starting with 'Compare', 'Analyse', 'Evaluate', 'Design', 'Audit'.\n"
            "Examples: 'compare RAG vs fine-tuning', 'design a microservices system', "
            "'compare the trade-offs between X and Y', 'evaluate the architecture of'.\n\n"
            "CODE: ONLY when user explicitly asks to WRITE or BUILD runnable code. "
            "Requires action words: write/build/create/implement + program/function/script/class/app.\n"
            "Examples: 'write a Python function', 'build a REST API', 'implement a sorting algorithm'.\n"
            "NOT CODE: anything that compares, explains, or analyzes technology even if technical.\n\n"
            "QUICK: simple factual questions, recommendations, current events, definitions.\n"
            "Examples: 'what is RAG', 'recommend a horror film', 'who won the superbowl'.\n\n"
            "CRITICAL RULE: 'Compare X and Y' or 'trade-offs between X and Y' is ALWAYS SOVEREIGN, never CODE.\n"
            "When in doubt between QUICK and SOVEREIGN, choose SOVEREIGN for technical topics.\n"
            "Return ONLY JSON: {\"mode\": \"SOVEREIGN\"|\"QUICK\"|\"CODE\", \"reason\": \"one sentence\"}"
        )
        resp = llm.invoke([SystemMessage(content=prompt),
                           HumanMessage(content=f"Classify: {task}")])
        data = json.loads(_re.search(r"\{.*\}", resp.content, _re.DOTALL).group())
        return {"mode": data.get("mode", "SOVEREIGN"), "reason": data.get("reason", "")}
    except Exception as e:
        return {"mode": "SOVEREIGN", "reason": f"Classification error: {e}"}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            msg = await ws.receive_text()
            for chunk in stream_llm(msg):
                await ws.send_text(chunk)
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------------------------------------------------------------------
# NEXUS ORACLE — Phase 4 endpoints
# ---------------------------------------------------------------------------

@app.post("/nexus/run")
async def nexus_run(payload: dict, request: Request):
    """
    Start a Nexus pipeline run.
    Body: {"task": "...", "max_iterations": 3, "min_confidence": 0.75}
    Returns: {"session_id": "abc12345", "stream_url": "/nexus/stream/abc12345"}
    """
    task            = payload.get("task", "").strip()
    max_iterations  = int(payload.get("max_iterations", 3))
    min_confidence  = float(payload.get("min_confidence", 0.75))

    if not task:
        return JSONResponse({"error": "task is required"}, status_code=400)

    # Rate limiting via Redis
    client_ip = _get_client_ip(request)
    allowed, reason = await check_rate_limit(client_ip, "sovereign")
    if not allowed:
        stats = await get_usage_stats(client_ip)
        return JSONResponse({
            "error": reason,
            "usage": stats,
            "upgrade": "Upgrade to Pro for higher limits: nexus-oracle-ten.vercel.app"
        }, status_code=429)

    # Force load pipeline with full diagnostics
    print(f"[ NEXUS RUN ] Task received: {task[:50]}")
    import sys as _sys
    print(f"[ NEXUS RUN ] Python: {_sys.version}")
    
    from app.nexus import bridge as _b
    print(f"[ NEXUS RUN ] Bridge imported, calling _load_pipeline...")
    
    import asyncio as _asyncio
    loop = _asyncio.get_event_loop()
    loaded = await loop.run_in_executor(None, _b._load_pipeline)
    
    print(f"[ NEXUS RUN ] _load_pipeline returned: {loaded}")
    if not loaded:
        return JSONResponse({
            "error": "Nexus pipeline not available",
            "nexus_available": _b.NEXUS_AVAILABLE,
        }, status_code=503)

    session_id = create_session(task)
    return {
        "session_id":   session_id,
        "task":         task,
        "stream_url":   f"/nexus/stream/{session_id}",
        "dossier_url":  f"/nexus/dossier/{session_id}",
        "status":       "created",
    }


@app.websocket("/nexus/stream/{session_id}")
async def nexus_stream(ws: WebSocket, session_id: str):
    """
    WebSocket endpoint — streams Nexus node events in real time.
    Client receives JSON messages: {type, node, icon, label, msg, pct, ts, ...}

    Usage from Next.js:
        const ws = new WebSocket(`ws://localhost:8000/nexus/stream/${sessionId}`)
        ws.onmessage = (e) => {
            const event = JSON.parse(e.data)
            // update UI with event.node, event.pct, event.msg
        }
    """
    try:
        await ws.accept()
    except Exception as e:
        print(f"[ NEXUS ] WebSocket accept failed: {e}")
        return

    session = get_session(session_id)
    if not session:
        await ws.send_text(json.dumps({
            "type": "error", "msg": f"Session {session_id} not found"
        }))
        await ws.close()
        return

    task           = session["task"]
    max_iterations = 3
    min_confidence = 0.75

    try:
        async for event in run_nexus_stream(
            task=task,
            session_id=session_id,
            max_iterations=max_iterations,
            min_confidence=min_confidence,
        ):
            try:
                await ws.send_text(json.dumps(event, default=str))
            except Exception:
                break  # Client disconnected mid-stream

        try:
            await ws.close()
        except Exception:
            pass

    except WebSocketDisconnect:
        print(f"[ NEXUS ] Client disconnected from session {session_id}")
    except Exception as e:
        print(f"[ NEXUS ] WebSocket error for {session_id}: {e}")
        import traceback; traceback.print_exc()
        try:
            await ws.send_text(json.dumps({
                "type": "error", "msg": str(e), "detail": traceback.format_exc()[-500:]
            }))
            await ws.close()
        except Exception:
            pass


@app.get("/nexus/session/{session_id}")
async def nexus_session_status(session_id: str):
    """Get the current status and events for a session."""
    session = get_session(session_id)
    if not session:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return {
        "session_id":    session_id,
        "status":        session["status"],
        "task":          session["task"],
        "started_at":    session["started_at"],
        "score":         session.get("score"),
        "verdict":       session.get("verdict"),
        "judge_verdict": session.get("judge_verdict", ""),
        "event_count":   len(session["events"]),
        "dossier_url":   f"/nexus/dossier/{session_id}" if session.get("dossier_path") else None,
    }


@app.get("/nexus/dossier/{session_id}")
async def nexus_dossier(session_id: str):
    """Return the full dossier markdown for a completed session."""
    content = get_dossier(session_id)
    if not content:
        return JSONResponse({"error": "Dossier not found or pipeline not complete"}, status_code=404)
    return PlainTextResponse(content, media_type="text/markdown")


@app.get("/nexus/signals")
async def nexus_signals(limit: int = 10):
    """Return latest intelligence signals from Phase 2 watcher."""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: get_intelligence_signals(limit))
    except Exception:
        return {"signals": [], "stats": {"total": 0, "triggered": 0, "avg_score": 0.0}}


@app.get("/usage")
async def usage(request: Request):
    """Returns current usage stats for this user/IP."""
    ip = _get_client_ip(request)
    stats = await get_usage_stats(ip)
    return stats


@app.get("/nexus/health")
async def nexus_health():
    return {
        "nexus_available": NEXUS_AVAILABLE(),
        "phase":           4,
        "components": {
            "pipeline":     NEXUS_AVAILABLE(),
            "intelligence": True,
            "phase3":       True,
        }
    }

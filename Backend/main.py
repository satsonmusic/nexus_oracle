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

app = FastAPI(title="JarvisSatSon", version="4.0.0")

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
async def assistant(payload: dict):
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_agent(payload["input"], payload.get("user_id", "default_user"))
        )
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "failed", "error": str(e), "results": [], "plan": {"thoughts": f"Error: {e}"}}

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
        pass  # Cleaning failed — return raw result, never 500

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
async def nexus_run(payload: dict):
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
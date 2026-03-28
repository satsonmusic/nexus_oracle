"use client";

import { useState, useEffect, useRef, useCallback } from "react";

// ---------------------------------------------------------------------------
// TYPES
// ---------------------------------------------------------------------------
interface NexusEvent {
  type: string;
  node: string;
  icon: string;
  label: string;
  msg: string;
  pct: number;
  ts: string;
  score?: number;
  verdict?: string;
  judge_verdict?: string;
  dossier_url?: string;
  session?: string;
}

interface Signal {
  url: string;
  title: string;
  score: number;
  triggered: number;
  detected_at: string;
}

// ---------------------------------------------------------------------------
// CONFIG
// ---------------------------------------------------------------------------
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE  = API_BASE.replace("http", "ws").replace("https", "wss");

// ---------------------------------------------------------------------------
// WAR ROOM PAGE
// ---------------------------------------------------------------------------
export default function WarRoomPage() {
  const [task, setTask]               = useState("");
  const [sessionId, setSessionId]     = useState<string | null>(null);
  const [events, setEvents]           = useState<NexusEvent[]>([]);
  const [pct, setPct]                 = useState(0);
  const [status, setStatus]           = useState<"idle"|"running"|"complete"|"error">("idle");
  const [score, setScore]             = useState<number | null>(null);
  const [verdict, setVerdict]         = useState<string | null>(null);
  const [judgeVerdict, setJudgeVerdict] = useState<string>("");
  const [dossier, setDossier]         = useState<string | null>(null);
  const [signals, setSignals]         = useState<Signal[]>([]);
  const [mode, setMode]               = useState<"SOVEREIGN"|"CODE"|"QUICK">("SOVEREIGN");
  const [quickAnswer, setQuickAnswer] = useState<string>("");

  const wsRef       = useRef<WebSocket | null>(null);
  const feedRef     = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Fetch intelligence signals on mount
  useEffect(() => {
    fetch(`${API_BASE}/nexus/signals?limit=5`)
      .then(r => r.json())
      .then(d => setSignals(d.signals || []))
      .catch(() => {});
  }, []);

  // Auto-scroll feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [events]);

  // ---------------------------------------------------------------------------
  // ROUTE PROMPT
  // ---------------------------------------------------------------------------
  const classifyPrompt = useCallback(async (t: string): Promise<"SOVEREIGN"|"CODE"|"QUICK"> => {
    try {
      const r = await fetch(`${API_BASE}/assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: `Classify this prompt into one word — SOVEREIGN (deep research/analysis), CODE (write code), or QUICK (simple fact). Reply with ONLY the word. Prompt: "${t}"` })
      });
      const d = await r.json();
      const raw = (d.plan?.thoughts || "").toUpperCase();
      if (raw.includes("CODE")) return "CODE";
      if (raw.includes("QUICK")) return "QUICK";
      return "SOVEREIGN";
    } catch {
      return "SOVEREIGN";
    }
  }, []);

  // ---------------------------------------------------------------------------
  // LAUNCH
  // ---------------------------------------------------------------------------
  const handleLaunch = useCallback(async () => {
    if (!task.trim() || status === "running") return;

    setEvents([]);
    setPct(0);
    setScore(null);
    setVerdict(null);
    setJudgeVerdict("");
    setDossier(null);
    setQuickAnswer("");
    setStatus("running");

    const detectedMode = await classifyPrompt(task);
    setMode(detectedMode);

    // CODE / QUICK — direct Jarvis response, no pipeline
    if (detectedMode !== "SOVEREIGN") {
      try {
        const r = await fetch(`${API_BASE}/assistant`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input: task })
        });
        const d = await r.json();
        const thoughts = d.plan?.thoughts || "";
        const results  = (d.results || []).map((s: any) => s.output || "").join("\n\n");
        setQuickAnswer((thoughts + "\n\n" + results).trim());
      } catch (e) {
        setQuickAnswer("Error: " + String(e));
      }
      setStatus("complete");
      return;
    }

    // SOVEREIGN — full Nexus pipeline via WebSocket
    try {
      const r = await fetch(`${API_BASE}/nexus/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task, max_iterations: 3, min_confidence: 0.75 })
      });
      const d = await r.json();
      if (d.error) { setStatus("error"); return; }

      const sid = d.session_id;
      setSessionId(sid);

      // Open WebSocket and stream events
      const ws = new WebSocket(`${WS_BASE}/nexus/stream/${sid}`);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const ev: NexusEvent = JSON.parse(e.data);
        if (ev.type === "error") {
          setStatus("error");
          setEvents(prev => [...prev, ev]);
          return;
        }
        setEvents(prev => [...prev, ev]);
        setPct(ev.pct);
        if (ev.type === "complete") {
          setStatus("complete");
          if (ev.score !== undefined && ev.score !== null) setScore(ev.score);
          if (ev.verdict) setVerdict(ev.verdict);
          if (ev.judge_verdict) setJudgeVerdict(ev.judge_verdict);
          // Fetch dossier
          if (ev.dossier_url) {
            fetch(`${API_BASE}${ev.dossier_url}`)
              .then(r => r.text())
              .then(setDossier)
              .catch(() => {});
          }
        }
        if (ev.score !== undefined && ev.score !== null) setScore(ev.score);
        if (ev.judge_verdict) setJudgeVerdict(ev.judge_verdict);
      };

      ws.onerror = () => setStatus("error");
      ws.onclose = () => {
        if (status === "running") setStatus("complete");
      };

    } catch (e) {
      setStatus("error");
    }
  }, [task, status, classifyPrompt]);

  // Cleanup WebSocket on unmount
  useEffect(() => () => wsRef.current?.close(), []);

  // ---------------------------------------------------------------------------
  // UI HELPERS
  // ---------------------------------------------------------------------------
  const modeColor: Record<string, string> = {
    SOVEREIGN: "#00e5ff", CODE: "#ffb300", QUICK: "#00e676"
  };
  const modeIcon: Record<string, string> = {
    SOVEREIGN: "⚗", CODE: "⌨", QUICK: "⚡"
  };
  const verdictColor = score !== null
    ? (score >= 0.75 ? "#00e676" : score >= 0.4 ? "#ffb300" : "#ff1744")
    : "#00e5ff";

  // ---------------------------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------------------------
  return (
    <div style={{
      minHeight: "100vh",
      background: "#050810",
      fontFamily: "'Share Tech Mono', monospace",
      color: "#e0f0ff",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* Grid background */}
      <div style={{
        position: "fixed", inset: 0, pointerEvents: "none",
        backgroundImage: "linear-gradient(rgba(0,229,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(0,229,255,0.03) 1px,transparent 1px)",
        backgroundSize: "40px 40px",
      }} />

      <div style={{ position: "relative", zIndex: 1, padding: "1.5rem 2rem" }}>

        {/* ── HEADER ──────────────────────────────────────────────────────── */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          paddingBottom: "1.2rem", marginBottom: "1.5rem",
          borderBottom: "1px solid rgba(0,229,255,0.12)",
        }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: "1rem" }}>
            <span style={{
              fontFamily: "'Orbitron', sans-serif", fontSize: "1.5rem",
              fontWeight: 900, color: "#00e5ff", letterSpacing: "0.1em",
              textShadow: "0 0 30px rgba(0,229,255,0.5)",
            }}>NEXUS ORACLE</span>
            <span style={{
              fontSize: "0.6rem", color: "rgba(0,229,255,0.4)",
              letterSpacing: "0.3em", padding: "2px 8px",
              border: "1px solid rgba(0,229,255,0.15)",
            }}>v4.0 // PRODUCTION</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
            <span style={{ fontSize: "0.6rem", color: "rgba(0,229,255,0.3)", letterSpacing: "0.2em", textAlign: "right" }}>
              OPERATOR<br />
              <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.8rem", fontWeight: 700, color: "#ffb300" }}>SATSON</span>
            </span>
            <div style={{
              width: 8, height: 8, borderRadius: "50%",
              background: status === "running" ? "#ffb300" : "#00e676",
              boxShadow: `0 0 12px ${status === "running" ? "#ffb300" : "#00e676"}`,
            }} />
          </div>
        </div>

        {/* ── OPERATOR BRIEFING ───────────────────────────────────────────── */}
        <div style={{
          background: "rgba(0,229,255,0.02)", border: "1px solid rgba(0,229,255,0.08)",
          borderLeft: "3px solid #ffb300", padding: "0.8rem 1.2rem",
          marginBottom: "1.2rem", display: "flex", gap: "1.5rem",
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: "0.58rem", letterSpacing: "0.25em", color: "#ffb300", marginBottom: "0.4rem" }}>
              // OPERATOR BRIEFING
            </div>
            <div style={{ fontSize: "0.68rem", color: "rgba(0,229,255,0.6)", lineHeight: 1.7 }}>
              NEXUS GENESIS — 14-node sovereign AI research engine. Not a chatbot. Ask it hard questions.
            </div>
          </div>
          <div style={{ minWidth: 220 }}>
            <div style={{ fontSize: "0.55rem", letterSpacing: "0.15em", color: "rgba(255,179,0,0.5)", marginBottom: "0.3rem" }}>
              SUGGESTED DIRECTIVES
            </div>
            {[
              "Compare RAG vs fine-tuning architectures",
              "Design a scalable microservices system",
              "Audit this code for security flaws",
              "Write a Python class with full error handling",
            ].map(s => (
              <div key={s} onClick={() => setTask(s)}
                style={{ fontSize: "0.58rem", color: "rgba(0,229,255,0.3)", lineHeight: 1.9, cursor: "pointer" }}
                onMouseEnter={e => (e.currentTarget.style.color = "rgba(0,229,255,0.7)")}
                onMouseLeave={e => (e.currentTarget.style.color = "rgba(0,229,255,0.3)")}>
                → {s}
              </div>
            ))}
          </div>
        </div>

        {/* ── MAIN GRID ───────────────────────────────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "1.5rem", marginBottom: "1.5rem" }}>

          {/* LEFT — LIVE FEED */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: "0.8rem" }}>
              <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.65rem", fontWeight: 600, color: "rgba(0,229,255,0.7)", letterSpacing: "0.25em" }}>
                {status === "running" ? "LIVE INTELLIGENCE FEED" : "SYSTEM EVOLUTION"}
              </span>
              <div style={{ flex: 1, height: 1, background: "rgba(0,229,255,0.08)" }} />
              {status === "running" && (
                <span style={{ fontSize: "0.55rem", color: "#00e676", letterSpacing: "0.15em", animation: "pulse 1s infinite" }}>● LIVE</span>
              )}
            </div>

            {/* Progress bar */}
            <div style={{ marginBottom: "1rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: "0.52rem", color: "rgba(0,229,255,0.3)", letterSpacing: "0.15em" }}>PIPELINE PROGRESS</span>
                <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.58rem", color: pct === 100 ? "#76ff03" : "#00e5ff", fontWeight: 700 }}>{pct}%</span>
              </div>
              <div style={{ height: 6, background: "rgba(0,229,255,0.08)", borderRadius: 3, border: "1px solid rgba(0,229,255,0.12)", overflow: "hidden" }}>
                <div style={{
                  height: "100%", width: `${pct}%`, borderRadius: 3,
                  background: pct === 100
                    ? "linear-gradient(90deg,#76ff03,#00e676)"
                    : "linear-gradient(90deg,#00e5ff,#7c5cbf,#00e5ff)",
                  backgroundSize: "200% 100%",
                  transition: "width 0.4s ease",
                  animation: status === "running" ? "shimmer 2s linear infinite" : "none",
                }} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                <span style={{ fontSize: "0.48rem", color: "rgba(0,229,255,0.2)" }}>{events.filter(e => e.type === "node_complete").length}/14 NODES</span>
                <span style={{ fontSize: "0.48rem", color: "rgba(0,229,255,0.2)" }}>{status.toUpperCase()}</span>
              </div>
            </div>

            {/* Feed panel */}
            <div ref={feedRef} style={{
              height: 320, overflowY: "auto", padding: "0.5rem",
              background: "rgba(0,229,255,0.02)", border: "1px solid rgba(0,229,255,0.08)",
              borderRadius: 2,
            }}>
              {events.length === 0 ? (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "rgba(0,229,255,0.15)", fontSize: "0.62rem", letterSpacing: "0.2em" }}>
                  NEXUS STANDING BY...
                </div>
              ) : events.map((ev, i) => (
                <div key={i} style={{
                  display: "flex", alignItems: "flex-start", gap: 10,
                  padding: "6px 0", borderBottom: "1px solid rgba(0,229,255,0.04)",
                  animation: "slideIn 0.25s ease forwards",
                }}>
                  <span style={{ fontSize: "1rem", minWidth: 22, textAlign: "center" }}>{ev.icon || "▶"}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{
                      fontSize: "0.58rem", letterSpacing: "0.1em",
                      color: ev.type === "error" ? "#ff1744" : ev.type === "complete" ? "#76ff03" : "#00e5ff",
                      textTransform: "uppercase",
                    }}>{ev.label || ev.node}</div>
                    <div style={{ fontSize: "0.62rem", color: "rgba(0,229,255,0.5)", lineHeight: 1.4 }}>{ev.msg}</div>
                  </div>
                  <span style={{
                    fontSize: "0.6rem",
                    color: ev.type === "error" ? "#ff1744" : ev.type === "complete" ? "#76ff03" : "rgba(0,229,255,0.4)"
                  }}>{ev.type === "error" ? "❌" : "✓"}</span>
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT — DECISION CENTER */}
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: "0.8rem" }}>
              <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.65rem", fontWeight: 600, color: "rgba(0,229,255,0.7)", letterSpacing: "0.25em" }}>
                DECISION CENTER
              </span>
              <div style={{ flex: 1, height: 1, background: "rgba(0,229,255,0.08)" }} />
            </div>

            {/* Verdict panel */}
            {score !== null && (
              <div style={{
                background: `${verdictColor}08`, border: `1px solid ${verdictColor}33`,
                borderLeft: `3px solid ${verdictColor}`, padding: "1rem 1.25rem",
                marginBottom: "1rem", display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <div>
                  <div style={{ fontSize: "0.58rem", color: "rgba(0,229,255,0.3)", letterSpacing: "0.2em", marginBottom: 4 }}>SOVEREIGN VERDICT</div>
                  <div style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.72rem", fontWeight: 600, color: verdictColor, letterSpacing: "0.15em" }}>
                    {score >= 0.75 ? "VERIFIED & ARCHIVED" : score >= 0.4 ? "REVIEWED" : "REJECTED — RE-PLANNING"}
                  </div>
                </div>
                <div style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "2.2rem", fontWeight: 900, color: verdictColor }}>{score.toFixed(2)}</div>
              </div>
            )}

            {/* Mode badge */}
            {mode && (
              <div style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "5px 10px", marginBottom: "0.5rem",
                background: `${modeColor[mode]}11`, border: `1px solid ${modeColor[mode]}44`,
              }}>
                <span style={{ color: modeColor[mode], fontSize: "0.9rem" }}>{modeIcon[mode]}</span>
                <span style={{ fontSize: "0.62rem", color: modeColor[mode], letterSpacing: "0.1em" }}>MODE: {mode}</span>
              </div>
            )}

            {/* Input */}
            <div style={{ fontSize: "0.6rem", letterSpacing: "0.3em", color: "rgba(0,229,255,0.5)", marginBottom: "0.4rem" }}>
              // DIRECTIVE INPUT
            </div>
            <textarea
              ref={textareaRef}
              value={task}
              onChange={e => setTask(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && e.ctrlKey) handleLaunch(); }}
              placeholder="Enter research directive... (Ctrl+Enter to launch)"
              rows={4}
              style={{
                width: "100%", background: "#0d1220", border: "1px solid rgba(0,229,255,0.2)",
                color: "#e0f0ff", fontFamily: "'Share Tech Mono',monospace", fontSize: "0.85rem",
                padding: "0.6rem", resize: "none", outline: "none", borderRadius: 2,
                marginBottom: "0.5rem", boxSizing: "border-box",
              }}
              onFocus={e => (e.target.style.borderColor = "#00e5ff")}
              onBlur={e => (e.target.style.borderColor = "rgba(0,229,255,0.2)")}
            />

            <button
              onClick={handleLaunch}
              disabled={status === "running" || !task.trim()}
              style={{
                width: "100%", padding: "0.7rem", background: "transparent",
                border: `1px solid ${status === "running" ? "rgba(0,229,255,0.2)" : "#00e5ff"}`,
                color: status === "running" ? "rgba(0,229,255,0.3)" : "#00e5ff",
                fontFamily: "'Orbitron',sans-serif", fontSize: "0.68rem", fontWeight: 600,
                letterSpacing: "0.2em", cursor: status === "running" ? "not-allowed" : "pointer",
                transition: "all 0.2s", borderRadius: 2,
              }}
              onMouseEnter={e => { if (status !== "running") (e.currentTarget.style.background = "rgba(0,229,255,0.08)"); }}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              {status === "running" ? "🔄 NEXUS PROCESSING..." : "🚀 LAUNCH INVESTIGATION"}
            </button>

            {/* Judge robot verdict */}
            {judgeVerdict && status === "complete" && (
              <div style={{ marginTop: "1rem", padding: "0.75rem", background: "rgba(255,214,0,0.04)", border: "1px solid rgba(255,214,0,0.2)", borderRadius: 2 }}>
                <div style={{ fontSize: "0.55rem", color: "rgba(255,214,0,0.5)", letterSpacing: "0.1em", marginBottom: 5 }}>⚖ SUPREME JUDGE</div>
                <div style={{ fontSize: "0.65rem", color: "rgba(255,214,0,0.8)", lineHeight: 1.6 }}>{judgeVerdict}</div>
              </div>
            )}

            {/* Pipeline topology */}
            <div style={{ marginTop: "1rem" }}>
              <div style={{ fontSize: "0.55rem", letterSpacing: "0.2em", color: "rgba(0,229,255,0.2)", marginBottom: "0.6rem" }}>// PIPELINE TOPOLOGY</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 5 }}>
                {["TOM","LOAD_BALANCER","VISUAL_PARSER","PRIVACY","BROADCAST","VISIONARY","DIAGNOSTICS","CODER","TESTING","SKEPTIC","JUDGE","MANIFESTO","MEMORY_SURGEON","EVOLUTION"].map(n => {
                  const done = events.some(e => e.node.toUpperCase() === n && e.type === "node_complete");
                  return (
                    <div key={n} style={{
                      display: "flex", alignItems: "center", gap: 5, padding: "4px 7px",
                      background: done ? "rgba(0,230,118,0.04)" : "transparent",
                      border: `1px solid ${done ? "rgba(0,230,118,0.15)" : "rgba(0,229,255,0.05)"}`,
                    }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", background: done ? "#00e676" : "rgba(0,229,255,0.1)", flexShrink: 0 }} />
                      <span style={{ fontSize: "0.52rem", color: done ? "#5a7a99" : "rgba(0,229,255,0.15)", letterSpacing: "0.06em" }}>{n}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ── QUICK ANSWER / CODE PANEL ────────────────────────────────────── */}
        {quickAnswer && (
          <div style={{ marginBottom: "1.5rem", padding: "1rem", background: `${modeColor[mode]}06`, border: `1px solid ${modeColor[mode]}22`, borderLeft: `3px solid ${modeColor[mode]}` }}>
            <div style={{ fontSize: "0.58rem", color: modeColor[mode], letterSpacing: "0.15em", marginBottom: "0.6rem" }}>
              {mode === "CODE" ? "⌨ CODE OUTPUT" : "⚡ QUICK ANSWER"}
            </div>
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.8rem", color: "rgba(224,240,255,0.85)", fontFamily: "'Share Tech Mono',monospace", lineHeight: 1.6 }}>
              {quickAnswer}
            </pre>
          </div>
        )}

        {/* ── DOSSIER ─────────────────────────────────────────────────────── */}
        {dossier && (
          <div style={{ marginBottom: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: "0.8rem" }}>
              <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.65rem", fontWeight: 600, color: "rgba(0,229,255,0.7)", letterSpacing: "0.25em" }}>SOVEREIGN DOSSIER</span>
              <div style={{ flex: 1, height: 1, background: "rgba(0,229,255,0.08)" }} />
              <span style={{ fontSize: "0.55rem", color: "rgba(0,229,255,0.25)", letterSpacing: "0.15em" }}>ARCHIVED</span>
            </div>
            <div style={{ background: "rgba(0,229,255,0.02)", border: "1px solid rgba(0,229,255,0.08)", padding: "1rem 1.5rem", maxHeight: 400, overflowY: "auto" }}>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.75rem", color: "rgba(0,229,255,0.6)", fontFamily: "'Share Tech Mono',monospace", lineHeight: 1.7 }}>
                {dossier}
              </pre>
            </div>
          </div>
        )}

        {/* ── INTELLIGENCE FEED ────────────────────────────────────────────── */}
        {signals.length > 0 && (
          <div style={{ marginBottom: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: "0.8rem" }}>
              <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.65rem", fontWeight: 600, color: "rgba(255,179,0,0.7)", letterSpacing: "0.25em" }}>INTELLIGENCE FEED</span>
              <div style={{ flex: 1, height: 1, background: "rgba(255,179,0,0.08)" }} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px,1fr))", gap: 8 }}>
              {signals.map((s, i) => (
                <div key={i} style={{
                  padding: "0.6rem 0.8rem", background: "rgba(255,179,0,0.02)",
                  border: `1px solid ${s.triggered ? "rgba(255,179,0,0.25)" : "rgba(0,229,255,0.08)"}`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ fontSize: "0.6rem", color: s.triggered ? "#ffb300" : "rgba(0,229,255,0.4)", letterSpacing: "0.1em" }}>
                      {s.triggered ? "● ORACLE FIRED" : "○ SIGNAL"}
                    </span>
                    <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.6rem", color: "#ffb300" }}>{s.score.toFixed(2)}</span>
                  </div>
                  <div style={{ fontSize: "0.62rem", color: "rgba(0,229,255,0.5)", lineHeight: 1.4 }}>{(s.title || s.url).slice(0, 50)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── FOOTER ──────────────────────────────────────────────────────── */}
        <div style={{ borderTop: "1px solid rgba(0,229,255,0.06)", paddingTop: "1rem", display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: "0.55rem", color: "rgba(0,229,255,0.1)", letterSpacing: "0.2em" }}>
            NEXUS ORACLE // PROJECT-12 // PHASE 4 PRODUCTION // JARVIS BACKBONE
          </span>
          <span style={{ fontFamily: "'Orbitron',sans-serif", fontSize: "0.55rem", color: "rgba(255,179,0,0.25)", letterSpacing: "0.3em" }}>SATSON</span>
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;900&family=Share+Tech+Mono&display=swap');
        @keyframes shimmer { 0%{background-position:200% center} 100%{background-position:-200% center} }
        @keyframes slideIn { from{opacity:0;transform:translateX(-8px)} to{opacity:1;transform:translateX(0)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #050810; }
        ::-webkit-scrollbar-thumb { background: #0099bb; border-radius: 2px; }
      `}</style>
    </div>
  );
}

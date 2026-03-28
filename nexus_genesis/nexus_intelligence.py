"""
nexus_intelligence.py — Phase 2: Intelligence Layer
====================================================
Sits on top of WebSum's pipeline.py without modifying it.

Three capabilities added:
  1. LLM Summariser   — replaces heuristic TF-IDF with gpt-4o-mini
  2. Signal Watcher   — polls a feed list on a schedule, scores relevance
  3. Oracle Trigger   — fires the Nexus pipeline when a signal crosses threshold

Place this file in: C:\\Users\\scott\\Desktop\\nexus_genesis\\
Run standalone:     python nexus_intelligence.py watch
Or import from dashboard / any other module.
"""

import sys
import json
import time
import sqlite3
import threading
import asyncio
import importlib.util
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
load_dotenv("infra/secrets.env")


# ---------------------------------------------------------------------------
# CONNECT TO WEBSUM — import pipeline.py from its original location
# ---------------------------------------------------------------------------
WEBSUM_PATH = Path(r"C:\Users\scott\WebSum\pipeline.py")
WEBSUM_DB   = Path(r"C:\Users\scott\WebSum\pipeline.sqlite")

def _load_pipeline():
    """Dynamically import WebSum's pipeline.py without moving it."""
    spec   = importlib.util.spec_from_file_location("pipeline", WEBSUM_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

try:
    pipeline = _load_pipeline()
    print("[ INTELLIGENCE ] WebSum pipeline loaded from", WEBSUM_PATH)
except Exception as e:
    print(f"[ INTELLIGENCE ] WARNING: Could not load WebSum pipeline: {e}")
    pipeline = None


# ---------------------------------------------------------------------------
# SCHEMA EXTENSION — add signals table to the existing WebSum SQLite DB
# ---------------------------------------------------------------------------
SIGNALS_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT    NOT NULL,
    title       TEXT,
    summary     TEXT    NOT NULL,
    score       REAL    NOT NULL DEFAULT 0.0,
    triggered   INTEGER NOT NULL DEFAULT 0,   -- 1 if Oracle was fired
    detected_at TEXT    NOT NULL,
    fired_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_signals_score ON signals(score DESC);
CREATE INDEX IF NOT EXISTS idx_signals_triggered ON signals(triggered, score);
"""

def extend_db(db_path: Path) -> sqlite3.Connection:
    """Open the WebSum DB and add the signals table if missing."""
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SIGNALS_SCHEMA)
    con.commit()
    return con


# ---------------------------------------------------------------------------
# LLM SUMMARISER — replaces heuristic TF-IDF with gpt-4o-mini
# ---------------------------------------------------------------------------
def llm_summarise(text: str, url: str = "", max_chars: int = 6000) -> str:
    """
    Summarise page text using gpt-4o-mini.
    Falls back to WebSum's heuristic summariser if the API call fails.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage

    snippet = text[:max_chars].strip()
    if not snippet:
        return "(empty page)"

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    sys_msg = SystemMessage(content=(
        "You are a concise intelligence analyst. "
        "Read the following web page text and extract 5-7 key insights as a numbered list. "
        "Each insight must be one sentence. Focus on facts, data, and developments. "
        "Do not include navigation text, ads, or boilerplate. "
        "Return ONLY the numbered list, nothing else."
    ))
    hum_msg = HumanMessage(content=f"URL: {url}\n\nPAGE TEXT:\n{snippet}")

    try:
        response = llm.invoke([sys_msg, hum_msg])
        return response.content.strip()
    except Exception as e:
        print(f"[ INTELLIGENCE ] LLM summarise failed ({e}), falling back to heuristic")
        if pipeline:
            return pipeline.summarize(text)
        return snippet[:500]


# ---------------------------------------------------------------------------
# RELEVANCE SCORER — how much does this summary match your interests?
# ---------------------------------------------------------------------------
DEFAULT_PROFILE = {
    # Each entry is a list of aliases — ANY match counts as one topic hit.
    # This handles "large language models" vs "llm", "generative ai" vs "ai", etc.
    "topics": [
        ["ai", "artificial intelligence", "generative ai"],
        ["machine learning", "deep learning", "ml model"],
        ["llm", "large language model", "language model"],
        ["gpt", "chatgpt", "openai"],
        ["anthropic", "claude"],
        ["google", "gemini", "deepmind", "bard"],
        ["meta", "llama", "mistral", "open source model"],
        ["transformer", "neural network", "neural"],
        ["fine-tuning", "fine tuning", "finetuning", "rag", "retrieval"],
        ["agentic", "agent", "autonomous"],
        ["regulation", "act", "policy", "compliance", "law"],
        ["model", "chatbot", "assistant"],
        ["safety", "alignment", "guardrail"],
        ["benchmark", "performance", "accuracy", "capability"],
        ["compute", "gpu", "inference", "training"],
        ["python", "software", "developer", "code", "api"],
        ["automation", "robotics", "robot"],
        ["security", "vulnerability", "breach", "hack"],
        ["investment", "funding", "startup", "billion"],
        ["layoff", "hiring", "employees", "workforce"],
    ],
    "boost_keywords": [
        "breakthrough", "released", "launched", "announced",
        "outperforms", "surpasses", "open source", "record",
        "new model", "new ai", "just released", "today",
    ],
    "threshold": 0.15,        # store signals with 3+ topic hits
    "oracle_threshold": 0.40, # fire Oracle with 8+ topic hits (solid AI story)
}

def score_relevance(summary: str, profile: dict = None) -> float:
    """
    Returns 0.0-1.0 relevance score.
    Each topic entry is a list of aliases — any alias match counts as one hit.
    This handles "large language models" vs "llm", "generative ai" vs "ai" etc.
    """
    if profile is None:
        profile = DEFAULT_PROFILE

    text_lower = summary.lower()
    topic_hits = 0
    boost_hits = 0.0

    for topic_group in profile["topics"]:
        # topic_group is a list of aliases — count hit if ANY alias matches
        if isinstance(topic_group, list):
            if any(alias.lower() in text_lower for alias in topic_group):
                topic_hits += 1
        else:
            # fallback: plain string (backwards compat)
            if topic_group.lower() in text_lower:
                topic_hits += 1

    for kw in profile["boost_keywords"]:
        if kw.lower() in text_lower:
            boost_hits += 1.0

    topic_score = topic_hits / max(1, len(profile["topics"]))
    boost_bonus = min(0.25, boost_hits / max(1, len(profile["boost_keywords"])) * 0.25)

    return round(min(1.0, topic_score + boost_bonus), 3)


# ---------------------------------------------------------------------------
# FEED WATCHER — polls URLs on a schedule, scores them, stores signals
# ---------------------------------------------------------------------------

# Default feed list — edit this or pass your own list
DEFAULT_FEEDS = [
    "https://techcrunch.com",
    "https://www.theverge.com/ai-artificial-intelligence",
    "https://news.ycombinator.com",
    "https://arxiv.org/list/cs.AI/recent",
    "https://www.anthropic.com/news",
    "https://huggingface.co/blog",
    "https://spectrum.ieee.org/artificial-intelligence",
    "https://aibusiness.com",
    "https://www.wired.com/tag/artificial-intelligence",
    # openai.com/news blocks scrapers (403) — skipped
    # venturebeat.com rate-limits (429) — skipped
]


def watch_once(
    feeds: list,
    db_path: Path = WEBSUM_DB,
    profile: dict = None,
    oracle_callback=None,
    timeout_s: int = 20,
) -> list:
    """
    Fetch + summarise every feed URL, score each one, store high-signal
    results to the signals table.

    Returns list of signal dicts that crossed the oracle_threshold.
    """
    if pipeline is None:
        print("[ INTELLIGENCE ] WebSum pipeline not available — skipping watch cycle")
        return []

    if profile is None:
        profile = DEFAULT_PROFILE

    con = extend_db(db_path)
    triggered_signals = []
    now = datetime.now(timezone.utc).isoformat()

    for url in feeds:
        try:
            print(f"[ INTELLIGENCE ] Fetching: {url}")
            final_url, html = pipeline.fetch_url(url, timeout_s=timeout_s)
            title   = pipeline.extract_title(html)
            text    = pipeline.extract_text(html)
            summary = llm_summarise(text, url=final_url)
            score   = score_relevance(summary, profile)

            print(f"[ INTELLIGENCE ] Score: {score:.3f} | {title[:60]}")

            # Only store if above minimum threshold
            if score >= profile.get("threshold", 0.35):
                con.execute(
                    """
                    INSERT INTO signals(url, title, summary, score, triggered, detected_at)
                    VALUES(?, ?, ?, ?, 0, ?)
                    """,
                    (final_url, title, summary, score, now),
                )
                con.commit()

                # Fire Oracle if above oracle threshold
                oracle_thresh = profile.get("oracle_threshold", 0.65)
                if score >= oracle_thresh:
                    signal = {
                        "url":     final_url,
                        "title":   title,
                        "summary": summary,
                        "score":   score,
                    }
                    triggered_signals.append(signal)

                    if oracle_callback:
                        oracle_callback(signal)

                    # Mark as triggered in DB
                    con.execute(
                        "UPDATE signals SET triggered=1, fired_at=? WHERE url=? AND detected_at=?",
                        (now, final_url, now),
                    )
                    con.commit()

        except Exception as e:
            print(f"[ INTELLIGENCE ] Error fetching {url}: {e}")

    con.close()
    return triggered_signals


# ---------------------------------------------------------------------------
# ORACLE TRIGGER — constructs a task and fires the Nexus pipeline
# ---------------------------------------------------------------------------
def build_oracle_task(signal: dict) -> str:
    """Convert a high-signal detection into a research directive for the Oracle."""
    return (
        f"A high-relevance signal was detected. "
        f"Research and analyse the following development: '{signal['title']}'. "
        f"Source: {signal['url']}. "
        f"Initial summary: {signal['summary'][:300]}. "
        f"Provide a sovereign analysis of the implications, key facts, and recommended actions."
    )


def fire_oracle(signal: dict, max_iterations: int = 2, min_confidence: float = 0.6):
    """
    Fire the Nexus sovereign pipeline with the signal as the task.
    Runs in a background thread so the watcher loop is not blocked.
    """
    try:
        # Import here to avoid circular dependency at module level
        sys.path.insert(0, str(Path(__file__).parent))
        from core.orchestrator import create_nexus_graph

        task = build_oracle_task(signal)
        print(f"[ ORACLE TRIGGER ] Firing pipeline for: {signal['title'][:60]}")

        app = create_nexus_graph()
        config = {"configurable": {"thread_id": f"intel_{int(time.time())}"}}

        initial_state = {
            "task":              task,
            "plan":              [],
            "research_notes":    [],
            "uncertainty_flags": [],
            "visual_context":    None,
            "user_profile":      {},
            "global_workspace":  None,
            "cognitive_mode":    "EXPLAIN",
            "urgency_level":     0.7,
            "iterations":        0,
            "max_iterations":    max_iterations,
            "min_confidence":    min_confidence,
            "confidence_score":  0.0,
            "proposed_edit":     None,
            "approval_granted":  False,
            "judge_verdict":     "",
        }

        async def _run():
            async for event in app.astream(initial_state, config=config):
                for node_name in event:
                    print(f"[ ORACLE TRIGGER ] {node_name.upper()} complete")

        asyncio.run(_run())
        print(f"[ ORACLE TRIGGER ] Pipeline complete for: {signal['title'][:60]}")

    except Exception as e:
        print(f"[ ORACLE TRIGGER ] Pipeline error: {e}")


def fire_oracle_async(signal: dict):
    """Fire the Oracle in a background thread — non-blocking."""
    thread = threading.Thread(
        target=fire_oracle,
        args=(signal,),
        daemon=True,
        name=f"oracle-trigger-{int(time.time())}"
    )
    thread.start()


# ---------------------------------------------------------------------------
# CONTINUOUS WATCHER — runs on a schedule
# ---------------------------------------------------------------------------
def run_watcher(
    feeds: list = None,
    interval_minutes: int = 30,
    db_path: Path = WEBSUM_DB,
    profile: dict = None,
    auto_trigger: bool = True,
):
    """
    Main watcher loop. Polls all feeds every `interval_minutes`.
    Call this from a background thread or run standalone.
    """
    if feeds is None:
        feeds = DEFAULT_FEEDS
    if profile is None:
        profile = DEFAULT_PROFILE

    callback = fire_oracle_async if auto_trigger else None
    interval_s = interval_minutes * 60

    print(f"[ INTELLIGENCE ] Watcher started — {len(feeds)} feeds, every {interval_minutes} min")
    print(f"[ INTELLIGENCE ] Oracle threshold: {profile.get('oracle_threshold', 0.65)}")
    print(f"[ INTELLIGENCE ] Auto-trigger: {auto_trigger}")

    while True:
        print(f"\n[ INTELLIGENCE ] === Watch cycle: {datetime.now().strftime('%H:%M:%S')} ===")
        triggered = watch_once(
            feeds=feeds,
            db_path=db_path,
            profile=profile,
            oracle_callback=callback,
        )
        if triggered:
            print(f"[ INTELLIGENCE ] {len(triggered)} signal(s) triggered the Oracle")
        else:
            print("[ INTELLIGENCE ] No Oracle-level signals this cycle")

        print(f"[ INTELLIGENCE ] Sleeping {interval_minutes} min until next cycle...")
        time.sleep(interval_s)


# ---------------------------------------------------------------------------
# DASHBOARD INTEGRATION — call this to get recent signals for the UI
# ---------------------------------------------------------------------------
def get_recent_signals(db_path: Path = WEBSUM_DB, limit: int = 10) -> list:
    """Returns the most recent high-score signals for display in the dashboard."""
    try:
        con = extend_db(db_path)
        rows = con.execute(
            """
            SELECT url, title, summary, score, triggered, detected_at
            FROM signals
            ORDER BY score DESC, detected_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        con.close()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"[ INTELLIGENCE ] get_recent_signals error: {e}")
        return []


def get_signal_stats(db_path: Path = WEBSUM_DB) -> dict:
    """Returns summary stats for the dashboard sidebar."""
    try:
        con = extend_db(db_path)
        total     = con.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        triggered = con.execute("SELECT COUNT(*) FROM signals WHERE triggered=1").fetchone()[0]
        avg_score = con.execute("SELECT AVG(score) FROM signals").fetchone()[0] or 0.0
        con.close()
        return {"total": total, "triggered": triggered, "avg_score": round(avg_score, 3)}
    except Exception:
        return {"total": 0, "triggered": 0, "avg_score": 0.0}


# ---------------------------------------------------------------------------
# CLI — run standalone
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Nexus Intelligence Layer — Phase 2")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # watch — continuous watcher
    p_watch = sub.add_parser("watch", help="Start the continuous feed watcher")
    p_watch.add_argument("--interval", type=int, default=30, help="Minutes between cycles")
    p_watch.add_argument("--no-trigger", action="store_true", help="Disable Oracle auto-trigger")

    # once — single scan
    p_once = sub.add_parser("once", help="Run a single watch cycle and exit")
    p_once.add_argument("--no-trigger", action="store_true")

    # status — show recent signals
    p_status = sub.add_parser("status", help="Show recent signals from the DB")
    p_status.add_argument("--limit", type=int, default=10)

    # score — score a single URL
    p_score = sub.add_parser("score", help="Fetch, summarise, and score a single URL")
    p_score.add_argument("url")

    args = parser.parse_args()

    if args.cmd == "watch":
        run_watcher(interval_minutes=args.interval, auto_trigger=not args.no_trigger)

    elif args.cmd == "once":
        triggered = watch_once(
            feeds=DEFAULT_FEEDS,
            oracle_callback=fire_oracle_async if not args.no_trigger else None,
        )
        print(f"\nCycle complete. {len(triggered)} Oracle trigger(s).")

    elif args.cmd == "status":
        stats   = get_signal_stats()
        signals = get_recent_signals(limit=args.limit)
        print(f"\n=== SIGNAL STATS ===")
        print(f"Total signals:   {stats['total']}")
        print(f"Oracle triggers: {stats['triggered']}")
        print(f"Avg score:       {stats['avg_score']}")
        print(f"\n=== RECENT SIGNALS (top {args.limit}) ===")
        for s in signals:
            fired = "FIRED" if s["triggered"] else "     "
            print(f"[{fired}] {s['score']:.3f} | {s['title'][:55]}")

    elif args.cmd == "score":
        if pipeline is None:
            print("ERROR: WebSum pipeline not available")
            sys.exit(1)
        print(f"Fetching {args.url}...")
        _, html  = pipeline.fetch_url(args.url)
        title    = pipeline.extract_title(html)
        text     = pipeline.extract_text(html)
        summary  = llm_summarise(text, url=args.url)
        score    = score_relevance(summary)
        print(f"\nTitle:   {title}")
        print(f"Score:   {score}")
        print(f"\nSummary:\n{summary}")
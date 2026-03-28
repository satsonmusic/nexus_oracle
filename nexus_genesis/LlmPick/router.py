import argparse
import json
import random
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple

class TransientError(RuntimeError):
    """Raised when a simulated model provider is 'down' or 'rate-limited'."""
    pass

@dataclass
class ModelSpec:
    name: str
    provider: str
    family: str
    version: str
    quality: int      # 1=low, 2=med, 3=high
    latency_ms: int   # Simulated expected p50
    cost_cents: float # Simulated cost per 1k tokens
    failure_rate: float # Simulated uptime/reliability

def log(event: str, **fields) -> None:
    """Structured JSON logging for enterprise observability."""
    print(json.dumps({"ts": time.time(), "event": event, **fields}, ensure_ascii=False))

def _q_min(quality: str) -> int:
    return {"low": 1, "med": 2, "high": 3}.get(quality, 2)

def choose_candidates(
    models: List[ModelSpec],
    quality: str,
    latency_ms: int,
    max_cost_cents: float,
    deny: Optional[List[str]] = None,
    allow: Optional[List[str]] = None,
) -> List[ModelSpec]:
    deny = [d.strip().lower() for d in (deny or []) if d.strip()]
    allow = [a.strip().lower() for a in (allow or []) if a.strip()]

    def matches_any(m: ModelSpec, patterns: List[str]) -> bool:
        hay = " | ".join([m.name, m.provider, m.family, m.version]).lower()
        return any(p in hay for p in patterns)

    # 1. Filter by allow/deny lists
    cands = models
    if allow:
        cands = [m for m in cands if matches_any(m, allow)]
    if deny:
        cands = [m for m in cands if not matches_any(m, deny)]

    # 2. Enforce hard constraints (Quality must be met)
    qmin = _q_min(quality)
    eligible = [
        m for m in cands 
        if m.quality >= qmin and m.cost_cents <= max_cost_cents and m.latency_ms <= latency_ms
    ]

    # 3. Graceful Degradation: If no models match cost/latency, prioritize Quality
    if not eligible:
        eligible = [m for m in cands if m.quality >= qmin]

    # 4. Sort Strategy: Cheapest -> Fastest -> Highest Quality
    eligible.sort(key=lambda m: (m.cost_cents, m.latency_ms, -m.quality))
    return eligible

def call_model_simulated(model: ModelSpec, prompt: str) -> str:
    """Simulates a real-world API call with latency and occasional failures."""
    time.sleep(model.latency_ms / 1000.0)
    if random.random() < model.failure_rate:
        raise TransientError(f"503 Service Unavailable: {model.name}")
    return f"[{model.name}] SUMMARY: {prompt[:50]}..."

def call_with_fallback(models: List[ModelSpec], prompt: str) -> Tuple[str, Dict]:
    """Tries models in order until one succeeds or the list is exhausted."""
    attempt_history = []
    for m in models:
        for attempt in range(1, 3): # 2 attempts per model before falling back
            try:
                result = call_model_simulated(m, prompt)
                return result, {
                    "final_model": m.name,
                    "provider": m.provider,
                    "attempts": attempt_history + [{"model": m.name, "status": "OK"}]
                }
            except TransientError as e:
                attempt_history.append({"model": m.name, "status": "FAIL", "error": str(e)})
                continue
    
    raise RuntimeError(f"Critical System Failure: All candidates failed. History: {attempt_history}")

def main():
    p = argparse.ArgumentParser(description="LlmPick: Intelligent Model Routing Gateway")
    p.add_argument("prompt", help="The text to process")
    p.add_argument("--quality", default="med", choices=["low", "med", "high"])
    p.add_argument("--latency", type=int, default=1200, help="Max latency budget in ms")
    p.add_argument("--cost", type=float, default=1.0, help="Max cost budget in cents")
    args = p.parse_args()

    # 2026 Model Catalog (Simulated)
    catalog = [
        ModelSpec("Claude 4.6 Sonnet", "Anthropic", "Claude", "4.6", 3, 800, 0.8, 0.05),
        ModelSpec("GPT-5.4 Turbo", "OpenAI", "GPT", "5.4", 3, 900, 0.7, 0.04),
        ModelSpec("Gemini 3.1 Flash", "Google", "Gemini", "3.1", 2, 400, 0.2, 0.08),
        ModelSpec("DeepSeek-R1", "DeepSeek", "R1", "V3", 3, 1100, 0.5, 0.10),
        ModelSpec("Llama 4 (400B)", "Meta", "Llama", "4", 3, 1400, 0.6, 0.12),
    ]

    candidates = choose_candidates(catalog, args.quality, args.latency, args.cost)
    
    log("routing_started", count=len(candidates), target_quality=args.quality)

    try:
        res, meta = call_with_fallback(candidates, args.prompt)
        log("routing_success", **meta)
        print(f"\nRESULT:\n{res}")
    except Exception as e:
        log("routing_failed", error=str(e))

if __name__ == "__main__":
    main()
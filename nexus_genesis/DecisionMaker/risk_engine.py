import csv
import argparse
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple

DATE_FMT = "%Y-%m-%d"

def _lab_root() -> Path:
    """Uses the folder where the script is located, making it portable."""
    return Path(__file__).parent.resolve()

def _resolve_io_path(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    return (_lab_root() / path).resolve()

@dataclass
class Milestone:
    program: str
    workstream: str
    owner: str
    name: str
    due_date: Optional[date]
    status: str
    last_update: Optional[date]
    slip_count: int

@dataclass
class Decision:
    program: str
    workstream: str
    decider: str
    title: str
    status: str
    deadline: Optional[date]
    last_update: Optional[date]
    context: str

@dataclass
class Update:
    program: str
    workstream: str
    owner: str
    text: str
    update_date: Optional[date]

@dataclass
class Escalation:
    type: str
    program: str
    workstream: str
    owner: str
    title: str
    severity: int
    confidence: int
    urgency: int
    signals: List[str]
    recommendation: str
    decision_needed_by: Optional[date]

# --- LOADERS ---
def parse_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s: return None
    try:
        return datetime.strptime(s, DATE_FMT).date()
    except ValueError:
        return None

def load_csv_dicts(path: Path) -> List[Dict[str, str]]:
    if not path.exists(): return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def load_milestones(path: Path) -> List[Milestone]:
    return [Milestone(
        program=r.get("program", "").strip(),
        workstream=r.get("workstream", "").strip(),
        owner=r.get("owner", "").strip(),
        name=r.get("name", "").strip(),
        due_date=parse_date(r.get("due_date", "")),
        status=r.get("status", "").strip(),
        last_update=parse_date(r.get("last_update", "")),
        slip_count=int(r.get("slip_count", "0") or "0")
    ) for r in load_csv_dicts(path)]

def load_decisions(path: Path) -> List[Decision]:
    return [Decision(
        program=r.get("program", "").strip(),
        workstream=r.get("workstream", "").strip(),
        decider=r.get("decider", "").strip(),
        title=r.get("title", "").strip(),
        status=r.get("status", "").strip(),
        deadline=parse_date(r.get("deadline", "")),
        last_update=parse_date(r.get("last_update", "")),
        context=r.get("context", "").strip()
    ) for r in load_csv_dicts(path)]

def load_updates(path: Path) -> List[Update]:
    return [Update(
        program=r.get("program", "").strip(),
        workstream=r.get("workstream", "").strip(),
        owner=r.get("owner", "").strip(),
        text=r.get("text", "").strip(),
        update_date=parse_date(r.get("update_date", ""))
    ) for r in load_csv_dicts(path)]

# --- SCORING LOGIC ---
def clamp(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))

def keyword_signal(text: str) -> Tuple[int, List[str]]:
    if not text: return 0, []
    low = text.lower()
    keywords = {"blocked": 20, "waiting on": 10, "risk": 10, "slip": 15, "delayed": 15, "escalate": 25}
    score = 0
    signals = []
    for k, w in keywords.items():
        if k in low:
            score += w
            signals.append(f"Keyword detected: '{k}'")
    return score, signals

def score_milestone(m: Milestone, today: date, stale_days: int) -> Optional[Escalation]:
    severity, urgency, signals = 0, 0, []
    if m.status.lower() in ["red", "r"]: 
        severity += 40
        signals.append("Status is RED")
    
    if m.due_date:
        if m.due_date < today:
            severity += 35
            urgency += 50
            signals.append(f"Overdue (Target: {m.due_date})")
        elif today <= m.due_date <= (today + timedelta(days=14)):
            urgency += 30
            signals.append("Due within 14-day window")

    if m.slip_count >= 2:
        severity += 20
        signals.append(f"Frequent slippage (Count: {m.slip_count})")

    if severity < 50: return None

    return Escalation(
        type="milestone", program=m.program, workstream=m.workstream,
        owner=m.owner, title=m.name, severity=clamp(severity, 0, 100),
        confidence=80, urgency=clamp(urgency, 0, 100), signals=signals,
        recommendation="Conduct immediate scope-vs-resource audit. Propose one recovery path.",
        decision_needed_by=m.due_date
    )

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="escalations")
    args, _ = p.parse_known_args()

    today = date.today()
    out_dir = _resolve_io_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    milestones = load_milestones(_resolve_io_path("milestones.csv"))
    decisions = load_decisions(_resolve_io_path("decisions.csv"))
    
    escalations = []
    for m in milestones:
        e = score_milestone(m, today, 7)
        if e: escalations.append(e)

    for e in escalations:
        fname = f"{e.program}_{e.workstream}_{e.type}.md".replace(" ", "_")
        content = f"# Escalation: {e.title}\n- Severity: {e.severity}\n- Signals: {', '.join(e.signals)}\n- Recommendation: {e.recommendation}"
        (out_dir / fname).write_text(content)
        print(f"Generated: {fname}")

if __name__ == "__main__":
    main()
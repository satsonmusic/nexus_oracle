import csv
import argparse
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Dict, Optional

DATE_FMT = "%Y-%m-%d"  # Standard format: 2026-03-22

def _lab_root() -> Path:
    """Uses the directory where the script is located, making it portable."""
    return Path(__file__).parent.resolve()

def _resolve_io_path(p: str) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    return (_lab_root() / path).resolve()

@dataclass
class Update:
    program: str
    workstream: str
    owner: str
    status: str  # Green/Yellow/Red
    milestone: str
    due_date: Optional[date]
    last_update: Optional[date]
    blockers: str
    notes: str

def parse_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, DATE_FMT).date()
    except ValueError:
        return None

def load_updates(csv_path: Path) -> List[Update]:
    rows: List[Update] = []
    if not csv_path.exists():
        raise FileNotFoundError(f"Input file not found: {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"program", "workstream", "owner", "status", "milestone", 
                    "due_date", "last_update", "blockers", "notes"}
        
        missing = required - set((reader.fieldnames or []))
        if missing:
            raise ValueError(f"updates.csv missing columns: {sorted(missing)}")

        for r in reader:
            rows.append(
                Update(
                    program=(r.get("program") or "").strip(),
                    workstream=(r.get("workstream") or "").strip(),
                    owner=(r.get("owner") or "").strip(),
                    status=(r.get("status") or "").strip(),
                    milestone=(r.get("milestone") or "").strip(),
                    due_date=parse_date(r.get("due_date") or ""),
                    last_update=parse_date(r.get("last_update") or ""),
                    blockers=(r.get("blockers") or "").strip(),
                    notes=(r.get("notes") or "").strip(),
                )
            )
    return rows

def status_rank(status: str) -> int:
    s = (status or "").strip().lower()
    if s in {"green", "g"}: return 0
    if s in {"yellow", "amber", "y"}: return 1
    if s in {"red", "r"}: return 2
    return 1  # default to yellow

def compute_program_rollup(rows: List[Update]) -> str:
    if not rows: return "Unknown"
    max_rank = max(status_rank(u.status) for u in rows)
    return ["Green", "Yellow", "Red"][max_rank]

def render_status_md(updates: List[Update], today: date, stale_days: int, due_soon_days: int) -> str:
    programs: Dict[str, List[Update]] = {}
    for u in updates:
        programs.setdefault(u.program or "(No program)", []).append(u)

    lines = [f"# Program Control Tower — Status ({today.isoformat()})", ""]
    
    lines.append("## Executive Summary")
    for prog, rows in sorted(programs.items()):
        lines.append(f"- {prog}: **{compute_program_rollup(rows)}**")
    lines.append("")

    lines.append("## Needs Attention")
    attention = []
    for u in updates:
        if status_rank(u.status) == 2:
            attention.append(f"- **RED**: {u.program} / {u.workstream} (Owner: {u.owner})")
        elif u.blockers and u.blockers.lower() != "none":
            attention.append(f"- **Blocker**: {u.program} / {u.workstream} — {u.blockers}")
        elif u.due_date and u.due_date < today:
            attention.append(f"- **Overdue**: {u.program} / {u.workstream} (Due {u.due_date})")
        elif u.last_update and (today - u.last_update).days >= stale_days:
            attention.append(f"- **Stale**: {u.program} / {u.workstream} — No update since {u.last_update}")

    lines.extend(attention if attention else ["- No critical issues detected."])
    lines.append("")

    lines.append("## Program Detail")
    for prog, rows in sorted(programs.items()):
        lines.append(f"### {prog}")
        for u in sorted(rows, key=lambda x: (-status_rank(x.status), x.due_date or date.max)):
            lines.append(f"- [{u.status.upper()}] {u.workstream} — {u.milestone}")
            lines.append(f"  - Owner: {u.owner} | Due: {u.due_date or 'TBD'}")
            if u.blockers: lines.append(f"  - Blockers: {u.blockers}")
    
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="updates.csv")
    p.add_argument("--out", default="status.md")
    args = p.parse_args()

    csv_path = _resolve_io_path(args.csv)
    out_path = _resolve_io_path(args.out)

    try:
        updates = load_updates(csv_path)
        md = render_status_md(updates, date.today(), 7, 14)
        out_path.write_text(md, encoding="utf-8")
        print(f"--- COMMANDER SUCCESS: Generated {out_path} ---")
    except Exception as e:
        print(f"--- COMMANDER ERROR: {e} ---")

if __name__ == "__main__":
    main()
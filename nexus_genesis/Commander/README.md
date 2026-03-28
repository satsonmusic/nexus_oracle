# 🕹️ Commander - Program Control Tower

> **Execution Visibility at Scale.** A lightweight, zero-dependency engine for tracking cross-functional programs and automating executive status reporting.

Commander is a "Control Tower" designed to solve the primary bottleneck in high-growth organizations: the visibility gap. Instead of manual slide decks and fragmented Slack updates, Commander normalizes program data into a single, deterministic source of truth, automating the generation of RAID logs (Risks, Issues, Assumptions, Dependencies) and executive rollups.

## 🚀 Key Features

* **Deterministic Status Rollup:** Implements enterprise business logic to programmatically calculate Program Health (Green/Yellow/Red) based on multi-level workstream status.
* **Automated Needs Attention Flagging:** Scans milestones to instantly identify overdue items, upcoming deadlines (14-day window), and stale updates (7-day window).
* **Zero-Dependency Architecture:** Built entirely on the Python 3.12 Standard Library, ensuring 100% portability across restricted corporate environments without requiring `pip` installs.
* **Executive-Ready Artifacts:** Automatically transforms raw CSV workstream data into professionally formatted Markdown status reports, ready for distribution via Slack, GitHub, or internal documentation sites.

## 🛠️ Tech Stack

* **Language:** Python 3.12 (Standard Library)
* **Data Handling:** `csv`, `dataclasses`, `datetime`
* **Output:** Markdown (optimized for GitHub/Notion/Slack)

## ⚙️ How to Run Locally

### 1. Clone the Repository
```bash
git clone [https://github.com/satsonmusic/Commander.git](https://github.com/satsonmusic/Commander.git)
cd Commander
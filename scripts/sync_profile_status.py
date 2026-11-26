#!/usr/bin/env python3
"""Synchronizes the dynamic roadmap status section in TheRollerBlader/README.md."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any, Dict, Optional

START_MARKER = "<!-- AUTOMATION_STATUS:START -->"
END_MARKER = "<!-- AUTOMATION_STATUS:END -->"

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCHEDULE_PATH = ROOT_DIR / "automation_schedule.json"
DEFAULT_README_PATH = ROOT_DIR / "README.md"


def get_quarter_for_date(target_date: datetime.date) -> str:
    month = target_date.month
    if month in (11, 12, 1):
        return "Q1"
    if month in (2, 3, 4):
        return "Q2"
    if month in (5, 6, 7):
        return "Q3"
    return "Q4"


def render_status_section(
    schedule: Dict[str, Any],
    target_date: Optional[datetime.date] = None,
) -> str:
    today = target_date or datetime.date.today()
    weekday = today.strftime("%A")
    quarter_key = get_quarter_for_date(today)
    quarter = schedule.get("quarters", {}).get(quarter_key, {})
    archetype = schedule.get("weekday_archetypes", {}).get(weekday, {})

    primary = ", ".join(f"`{r}`" for r in quarter.get("primary", [])) or "None"
    secondary = ", ".join(f"`{r}`" for r in quarter.get("secondary", [])) or "None"
    repo_count = len(schedule.get("repositories", {}))

    lines = [
        START_MARKER,
        "### Autonomous Engineering Roadmap Status",
        "",
        "| Metric | Active Configuration |",
        "| :--- | :--- |",
        f"| **Active Quarter** | `{quarter_key}` — {quarter.get('theme', 'Ecosystem Engineering')} |",
        f"| **Primary Focus** | {primary} |",
        f"| **Secondary Maintenance** | {secondary} |",
        f"| **Daily Cadence ({weekday})** | **{archetype.get('name', 'Engineering')}** — {archetype.get('deliverables', '')} |",
        f"| **Tracked Repositories** | {repo_count} repositories |",
        f"| **Last Synced** | `{today.isoformat()}` |",
        END_MARKER,
    ]
    return "\n".join(lines)


def update_readme_status(
    readme_path: Path = DEFAULT_README_PATH,
    schedule_path: Path = DEFAULT_SCHEDULE_PATH,
    target_date: Optional[datetime.date] = None,
) -> str:
    schedule = json.loads(schedule_path.read_text(encoding="utf-8"))
    readme_text = readme_path.read_text(encoding="utf-8")
    block = render_status_section(schedule, target_date=target_date)

    if START_MARKER in readme_text and END_MARKER in readme_text:
        before, rest = readme_text.split(START_MARKER, 1)
        _, after = rest.split(END_MARKER, 1)
        updated = f"{before.rstrip()}\n\n{block}\n{after.lstrip()}"
    else:
        updated = f"{readme_text.rstrip()}\n\n{block}\n"

    readme_path.write_text(updated, encoding="utf-8")
    return updated


if __name__ == "__main__":
    update_readme_status()
    print("✓ Updated README.md autonomous roadmap status block.")

#!/usr/bin/env python3
"""
Autonomous Daily Engineering Worker.

Executes micro-engineering commits across target repositories according to
the 3-Year Master Roadmap and Weekly 7-Day Micro-Commit Cadence defined in:
/Users/krish/Documents/github_automation_schedule_and_audit.md
"""

import os
import sys
import json
import datetime
import subprocess
from typing import Dict, Any, Optional

SCHEDULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "automation_schedule.json")


def load_schedule() -> Dict[str, Any]:
    if not os.path.exists(SCHEDULE_PATH):
        raise FileNotFoundError(f"Missing schedule configuration at {SCHEDULE_PATH}")
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_current_quarter(date: datetime.date) -> str:
    month = date.month
    # Master schedule starts Year 1 Q1 in November (Month 11)
    if month in (11, 12, 1):
        return "Q1"
    elif month in (2, 3, 4):
        return "Q2"
    elif month in (5, 6, 7):
        return "Q3"
    else:
        return "Q4"


def determine_todays_target(schedule: Dict[str, Any], target_repo_override: Optional[str] = None) -> Dict[str, Any]:
    today = datetime.date.today()
    weekday = today.strftime("%A")
    day_archetype = schedule.get("weekday_archetypes", {}).get(
        weekday,
        {
            "type": "testing",
            "name": "Testing & Verification",
            "deliverables": "Vitest/Pytest unit suites, mock data fixtures, boundary condition assertions",
        },
    )

    quarter_key = get_current_quarter(today)
    quarter_info = schedule.get("quarters", {}).get(quarter_key, {})
    primary_repos = quarter_info.get("primary", ["SignBridge", "frc-vision-scout"])
    secondary_repos = quarter_info.get("secondary", ["rocky", "flood-alert", "TheRollerBlader"])

    # Rotate target repository based on day of month to ensure balanced progress
    all_active = primary_repos * 2 + secondary_repos
    repo_name = target_repo_override or all_active[today.day % len(all_active)]
    repo_meta = schedule.get("repositories", {}).get(repo_name, {})

    return {
        "date": today.isoformat(),
        "weekday": weekday,
        "quarter": quarter_key,
        "archetype": day_archetype,
        "repo_name": repo_name,
        "repo_path": repo_meta.get("path"),
        "test_cmd": repo_meta.get("test_cmd", ""),
    }


def run_command(cmd: str, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=True)


def execute_daily_run(target_repo_override: Optional[str] = None, dry_run: bool = False):
    schedule = load_schedule()
    target = determine_todays_target(schedule, target_repo_override)

    print("=" * 60)
    print(f"Autonomous Daily Engineering Worker — {target['date']} ({target['weekday']})")
    print(f"Quarter:   {target['quarter']}")
    print(f"Archetype: {target['archetype']['name']}")
    print(f"Repo:      {target['repo_name']} ({target['repo_path']})")
    print(f"Focus:     {target['archetype']['deliverables']}")
    print("=" * 60)

    repo_path = target["repo_path"]
    if not repo_path or not os.path.exists(repo_path):
        print(f"Error: Target repository directory does not exist: {repo_path}")
        sys.exit(1)

    # 1. Run baseline tests
    if target["test_cmd"]:
        print(f"Running baseline verification ({target['test_cmd']})...")
        res = run_command(target["test_cmd"], repo_path)
        if res.returncode == 0:
            print("✓ Baseline verification tests passed.")
        else:
            print(f"! Warning: Baseline test returned non-zero code {res.returncode}:\n{res.stdout}\n{res.stderr}")

    if dry_run:
        print("Dry run requested. Completed audit successfully without modifications.")
        return

    # 2. Check git status
    status = run_command("git status --porcelain", repo_path).stdout.strip()
    if status:
        print(f"Detected existing staged/unstaged changes in {target['repo_name']}:\n{status}")
        # Run test suite to verify changes
        if target["test_cmd"]:
            verify_res = run_command(target["test_cmd"], repo_path)
            if verify_res.returncode != 0:
                print(f"Verification failed after changes:\n{verify_res.stderr}")
                sys.exit(1)

        # Stage and commit
        commit_type = target["archetype"]["type"].split("_")[0]
        scope = target["repo_name"].lower().replace("-", "")
        commit_msg = f"{commit_type}({scope}): automated daily engineering for {target['archetype']['name']}"

        print(f"Committing changes with message: '{commit_msg}'...")
        run_command("git add -A", repo_path)
        commit_res = run_command(f'git commit -m "{commit_msg}"', repo_path)
        print(commit_res.stdout)

        print(f"Pushing to origin main...")
        push_res = run_command("git push origin main", repo_path)
        if push_res.returncode == 0:
            print("✓ Successfully pushed verified commit.")
        else:
            print(f"Push failed: {push_res.stderr}")
    else:
        print(f"Repository {target['repo_name']} working tree is clean. Ready for agent turn additions.")


if __name__ == "__main__":
    override = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None
    is_dry = "--dry-run" in sys.argv
    execute_daily_run(target_repo_override=override, dry_run=is_dry)

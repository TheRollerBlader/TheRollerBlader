"""
Unit and integration tests for TheRollerBlader autonomous daily engineering engine.
"""

import os
import sys
import datetime
import pytest

# Add parent directory and scripts directory to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from agent_daily_worker import (
    load_schedule,
    get_current_quarter,
    determine_todays_target,
    get_active_repositories,
    get_rotating_repositories,
    load_environment,
    generate_fallback_deliverable,
    push_with_retry,
    SCHEDULE_PATH,
)


def test_schedule_file_exists_and_parses():
    assert os.path.exists(SCHEDULE_PATH), f"Missing {SCHEDULE_PATH}"
    schedule = load_schedule()
    assert "version" in schedule
    assert "weekday_archetypes" in schedule
    assert "repositories" in schedule
    assert "quarters" in schedule


def test_weekday_archetypes_complete():
    schedule = load_schedule()
    archetypes = schedule["weekday_archetypes"]
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day in weekdays:
        assert day in archetypes
        assert "type" in archetypes[day]
        assert "name" in archetypes[day]
        assert "deliverables" in archetypes[day]


def test_quarter_computation():
    assert get_current_quarter(datetime.date(2026, 11, 4)) == "Q1"
    assert get_current_quarter(datetime.date(2026, 12, 25)) == "Q1"
    assert get_current_quarter(datetime.date(2027, 1, 15)) == "Q1"
    assert get_current_quarter(datetime.date(2027, 3, 1)) == "Q2"
    assert get_current_quarter(datetime.date(2027, 6, 1)) == "Q3"
    assert get_current_quarter(datetime.date(2027, 9, 1)) == "Q4"


def test_target_determination():
    schedule = load_schedule()
    target = determine_todays_target(schedule)
    assert "date" in target
    assert "weekday" in target
    assert "quarter" in target
    assert "archetype" in target
    assert "repo_name" in target
    assert target["repo_name"] in schedule["repositories"]


def test_target_override():
    schedule = load_schedule()
    target = determine_todays_target(schedule, target_repo_override="SignBridge")
    assert target["repo_name"] == "SignBridge"
    assert target["repo_path"] == schedule["repositories"]["SignBridge"]["path"]


def test_get_active_repositories():
    schedule = load_schedule()
    q1_active = get_active_repositories(schedule, quarter_key="Q1")
    assert "SignBridge" in q1_active
    assert "frc-vision-scout" in q1_active
    assert len(q1_active) >= 4


def test_get_rotating_repositories():
    schedule = load_schedule()
    rotating = get_rotating_repositories(schedule, custom_date=datetime.date(2026, 11, 12))
    assert len(rotating) >= 3
    assert len(rotating) == len(set(rotating)), "Rotating repos must be deduplicated"
    for r in rotating:
        assert r in schedule["repositories"]


def test_environment_loader():
    load_environment()
    # If ~/.env exists, verify it loaded
    if os.path.exists("/Users/krish/.env"):
        assert "GEMINI_API_KEY" in os.environ


def test_all_mapped_repositories_exist_on_disk():
    schedule = load_schedule()
    for name, meta in schedule["repositories"].items():
        path = meta.get("path")
        assert path and os.path.isdir(path), f"Repository '{name}' path does not exist on disk: {path}"


def test_quarters_reference_valid_repositories():
    schedule = load_schedule()
    repos = set(schedule["repositories"].keys())
    for q_id, q_data in schedule["quarters"].items():
        for r in q_data.get("primary", []):
            assert r in repos, f"Quarter {q_id} primary repo '{r}' not in repositories list"
        for r in q_data.get("secondary", []):
            assert r in repos, f"Quarter {q_id} secondary repo '{r}' not in repositories list"


def test_fallback_deliverable_generator_multi_archetype():
    schedule = load_schedule()
    
    # Test all 7 weekdays to guarantee high-leverage deliverables across all archetypes
    test_dates = [
        ("Monday", datetime.date(2026, 11, 2), "SignBridge"),
        ("Tuesday", datetime.date(2026, 11, 3), "frc-vision-scout"),
        ("Wednesday", datetime.date(2026, 11, 4), "rocky"),
        ("Thursday", datetime.date(2026, 11, 5), "flood-alert"),
        ("Friday", datetime.date(2026, 11, 6), "frc-vision-scout"),
        ("Saturday", datetime.date(2026, 11, 7), "SignBridge"),
        ("Sunday", datetime.date(2026, 11, 8), "TheRollerBlader"),
    ]

    for expected_day, date_val, repo in test_dates:
        target = determine_todays_target(schedule, target_repo_override=repo, custom_date=date_val)
        assert target["weekday"] == expected_day
        deliverable = generate_fallback_deliverable(target)
        assert deliverable is not None, f"Failed to generate deliverable for {expected_day}"
        assert "file_path" in deliverable
        assert "content" in deliverable
        assert len(deliverable["content"]) > 150, f"Deliverable too short for {expected_day} ({len(deliverable['content'])} chars)"
        assert "commit_message" in deliverable
        assert "description" in deliverable


def test_friday_testing_archetype_produces_no_dummy_strings():
    schedule = load_schedule()
    # Test Python repo
    target_py = determine_todays_target(schedule, target_repo_override="frc-vision-scout", custom_date=datetime.date(2026, 11, 13))
    deliv_py = generate_fallback_deliverable(target_py)
    assert "assert os.path.exists(\"README.md\")" not in deliv_py["content"], "Must not produce dummy README checks"
    assert "TestDailyInvariantVerification" in deliv_py["content"]

    # Test TS repo without vitest (e.g. global-earthquake-live-map)
    target_ts = determine_todays_target(schedule, target_repo_override="global-earthquake-live-map", custom_date=datetime.date(2026, 11, 13))
    deliv_ts = generate_fallback_deliverable(target_ts)
    assert "from 'vitest'" not in deliv_ts["content"], "Must not import uninstalled vitest in build-only TS repo"
    assert "verifyNumericalBounds" in deliv_ts["content"]


def test_safety_guard_skips_dirty_repositories(monkeypatch):
    from agent_daily_worker import execute_single_repo_run
    import subprocess

    target = {
        "date": "2026-11-14",
        "weekday": "Saturday",
        "quarter": "Q1",
        "archetype": {"name": "Type Safety", "type": "types_and_linting", "deliverables": "contracts"},
        "repo_name": "mock-repo",
        "repo_path": "/tmp",
        "test_cmd": "",
    }

    # Simulate dirty working tree
    def mock_run_command(cmd, cwd):
        if "git status --porcelain" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=" M dirty_file.py\n", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("agent_daily_worker.run_command", mock_run_command)
    # Must return cleanly without modifying or committing anything
    execute_single_repo_run(target, dry_run=False, auto_generate=True)



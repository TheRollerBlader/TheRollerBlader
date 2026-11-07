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
    # Test Saturday (types_and_linting)
    target_sat = determine_todays_target(
        schedule,
        target_repo_override="SignBridge",
        custom_date=datetime.date(2026, 11, 7),
    )
    fallback_sat = generate_fallback_deliverable(target_sat)
    assert fallback_sat is not None
    assert "file_path" in fallback_sat
    assert "content" in fallback_sat
    assert "isDomainEntityContract" in fallback_sat["content"] or "DomainEntityContract" in fallback_sat["content"]

    # Test Friday (testing)
    target_fri = determine_todays_target(
        schedule,
        target_repo_override="frc-vision-scout",
        custom_date=datetime.date(2026, 11, 6),
    )
    fallback_fri = generate_fallback_deliverable(target_fri)
    assert fallback_fri is not None
    assert "test" in fallback_fri["file_path"]

    # Test Tuesday (logic)
    target_tue = determine_todays_target(
        schedule,
        target_repo_override="frc-vision-scout",
        custom_date=datetime.date(2026, 11, 3),
    )
    fallback_tue = generate_fallback_deliverable(target_tue)
    assert fallback_tue is not None
    assert "compute_running_statistics" in fallback_tue["content"]

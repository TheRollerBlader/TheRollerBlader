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
    load_environment,
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


def test_environment_loader():
    load_environment()
    # If ~/.env exists, verify it loaded
    if os.path.exists("/Users/krish/.env"):
        assert "GEMINI_API_KEY" in os.environ

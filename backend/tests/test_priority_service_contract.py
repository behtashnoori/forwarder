"""Characterization tests for automatic initial priority assignment."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from backend.services import priority_service


def test_priority_service_missing_pickup_date_returns_normal_contract():
    """Missing pickup/loading date keeps the current normal fallback."""
    now = datetime(2026, 5, 29, 10, 0, 0)

    assert priority_service.determine_initial_priority({}, now=now) == "normal"
    assert priority_service.determine_initial_priority({"pickup_date": None}, now=now) == "normal"
    assert priority_service.determine_initial_priority({"pickup_date": ""}, now=now) == "normal"


def test_priority_service_urgent_pickup_date_contract():
    """Past, today, and within-24-hour pickup dates are urgent."""
    now = datetime(2026, 5, 29, 10, 0, 0)

    assert priority_service.determine_priority_from_pickup_date(now - timedelta(hours=1), now=now) == "urgent"
    assert priority_service.determine_priority_from_pickup_date(date(2026, 5, 29), now=now) == "urgent"
    assert priority_service.determine_priority_from_pickup_date(now + timedelta(hours=23), now=now) == "urgent"


def test_priority_service_high_pickup_date_contract():
    """Pickup dates beyond 24 hours and within 72 hours are high."""
    now = datetime(2026, 5, 29, 10, 0, 0)

    assert priority_service.determine_priority_from_pickup_date(now + timedelta(hours=25), now=now) == "high"
    assert priority_service.determine_priority_from_pickup_date(now + timedelta(hours=72), now=now) == "high"


def test_priority_service_normal_future_pickup_date_contract():
    """Pickup dates beyond 72 hours remain normal."""
    now = datetime(2026, 5, 29, 10, 0, 0)

    assert priority_service.determine_priority_from_pickup_date(now + timedelta(hours=73), now=now) == "normal"


def test_priority_service_date_parsing_contract():
    """Priority service accepts current ISO date strings and safely ignores invalid dates."""
    now = datetime(2026, 5, 29, 10, 0, 0)

    assert priority_service.determine_initial_priority({"pickup_date": "2026-05-30"}, now=now) == "urgent"
    assert priority_service.determine_initial_priority({"loading_date": "2026-05-31T12:00:00"}, now=now) == "high"
    assert priority_service.determine_initial_priority({"requested_pickup_date": "2026-06-05"}, now=now) == "normal"
    assert priority_service.determine_initial_priority({"pickup_date": "bad-date"}, now=now) == "normal"


def test_priority_normalization_contract():
    """Priority normalization keeps observed values and falls back safely."""
    for priority in ["low", "normal", "high", "urgent"]:
        assert priority_service.normalize_priority(priority) == priority

    assert priority_service.normalize_priority("medium") == "normal"
    assert priority_service.normalize_priority(None) == "normal"

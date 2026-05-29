"""Service helpers for shipment request priority assignment."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Mapping


ALLOWED_PRIORITIES = {"low", "normal", "high", "urgent"}
DEFAULT_PRIORITY = "normal"
URGENT_WINDOW = timedelta(hours=24)
HIGH_WINDOW = timedelta(hours=72)


def normalize_priority(value: Any) -> str:
    """Return a safe priority value using the current observed priority set."""
    if isinstance(value, str) and value in ALLOWED_PRIORITIES:
        return value
    return DEFAULT_PRIORITY


def determine_initial_priority(payload_or_dates: Mapping[str, Any] | Any, now: datetime | None = None) -> str:
    """Determine initial request priority from available pickup/loading date data."""
    pickup_date = payload_or_dates
    if isinstance(payload_or_dates, Mapping):
        pickup_date = (
            payload_or_dates.get("pickup_date")
            or payload_or_dates.get("loading_date")
            or payload_or_dates.get("requested_pickup_date")
        )
    return determine_priority_from_pickup_date(pickup_date, now=now)


def determine_priority_from_pickup_date(pickup_date: Any, now: datetime | None = None) -> str:
    """Map pickup/loading date urgency to the current priority values."""
    pickup_datetime = parse_pickup_datetime(pickup_date)
    if pickup_datetime is None:
        return DEFAULT_PRIORITY

    current_time = now or datetime.utcnow()
    remaining = pickup_datetime - current_time

    if remaining <= URGENT_WINDOW:
        return "urgent"
    if remaining <= HIGH_WINDOW:
        return "high"
    return DEFAULT_PRIORITY


def parse_pickup_datetime(value: Any) -> datetime | None:
    """Parse supported pickup/loading date values without raising for invalid input."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return datetime.fromisoformat(stripped)
        except ValueError:
            return None
    return None

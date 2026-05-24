"""Service helpers for user-management assignment statistics endpoint."""
from __future__ import annotations

from typing import Any


def normalize_assignment_statistics(raw_stats: dict[str, Any]) -> dict[str, Any]:
    """Keep the current assignment engine statistics payload unchanged."""
    return raw_stats


def build_assignment_statistics_response_payload(raw_stats: dict[str, Any]) -> dict[str, Any]:
    """Build the current assignment statistics response payload."""
    return normalize_assignment_statistics(raw_stats)


def get_assignment_statistics_payload() -> dict[str, Any]:
    """Fetch assignment statistics from the current assignment engine."""
    from backend.assignment_engine import assignment_engine

    raw_stats = assignment_engine.get_assignment_statistics()
    return build_assignment_statistics_response_payload(raw_stats)

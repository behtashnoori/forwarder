"""Strict parser for successful Document Catalog CLI APPLY certification output."""

from __future__ import annotations

import json
from typing import Any


REQUIRED_APPLY_FIELDS = frozenset(
    {
        "run_id",
        "status",
        "catalog_name",
        "catalog_version",
        "schema_version",
        "checksum",
        "environment",
        "database_fingerprint",
        "planned_count",
        "created_count",
        "updated_count",
        "unchanged_count",
        "conflict_count",
        "definitions",
    }
)


def parse_successful_apply_output(raw: str) -> dict[str, Any]:
    """Parse the authoritative flat CLI output and fail closed on contract drift."""
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("catalog APPLY output must be a JSON object")
    missing = sorted(REQUIRED_APPLY_FIELDS - payload.keys())
    if missing:
        raise ValueError(f"catalog APPLY output is missing fields: {missing}")
    if "run" in payload:
        raise ValueError("catalog APPLY output must use flat run_id/status fields")
    if not isinstance(payload["run_id"], str) or not payload["run_id"]:
        raise ValueError("catalog APPLY output run_id must be non-empty")
    if payload["status"] != "succeeded":
        raise ValueError("catalog APPLY did not succeed")
    return payload

"""Read-only verification helpers for ADR-039 V1 certification."""

from __future__ import annotations

from typing import Any

from backend.external_reference_models import ExternalReferenceType
from backend.external_reference_type_package import (
    ExternalReferenceTypePackage,
    _expected_row,
)


def verify_package_database_equivalence(
    package: ExternalReferenceTypePackage,
) -> dict[str, Any]:
    """Compare the normalized package projection with all persisted type rows."""
    rows = {
        row.code: row
        for row in ExternalReferenceType.query.order_by(ExternalReferenceType.code).all()
    }
    expected_codes = {item["code"] for item in package.definitions}
    mismatches: dict[str, list[str]] = {}
    revisions: dict[str, int | None] = {}
    for item in package.definitions:
        row = rows.get(item["code"])
        if row is None:
            mismatches[item["code"]] = ["missing"]
            revisions[item["code"]] = None
            continue
        expected = _expected_row(item)
        mismatches[item["code"]] = [
            key for key, value in expected.items() if getattr(row, key) != value
        ]
        revisions[item["code"]] = row.revision
    unexpected_codes = sorted(set(rows) - expected_codes)
    return {
        "equivalent": not unexpected_codes
        and all(not fields for fields in mismatches.values()),
        "type_count": len(rows),
        "unexpected_codes": unexpected_codes,
        "mismatches": mismatches,
        "revisions": revisions,
    }

#!/usr/bin/env python3
"""Fail-closed validator for the MT-1 human adjudication review CSV."""

from __future__ import annotations
import argparse
import csv
import json
import re
from datetime import datetime
from collections import Counter
from pathlib import Path

ALLOWED_DECISIONS = {
    "ASSIGN_TO_ORGANIZATION",
    "KEEP_QUARANTINED",
    "RETIRE_INACTIVE_LEGACY_ROW",
    "REDESIGN_REQUIRED",
    "NEEDS_MORE_EVIDENCE",
}
ALLOWED_STATUSES = {"PENDING", "IN_REVIEW", "APPROVED", "REJECTED", "SUPERSEDED"}
ALLOWED_DISCLOSURE = "ASSIGN_TO_ORGANIZATION|KEEP_QUARANTINED|RETIRE_INACTIVE_LEGACY_ROW|REDESIGN_REQUIRED|NEEDS_MORE_EVIDENCE"
REQUIRED = {
    "entity_type",
    "entity_id",
    "classification",
    "quarantine_status",
    "mapping_status",
    "organization_candidate_count",
    "human_decision",
    "allowed_human_decisions",
    "target_organization_id",
    "evidence_reference",
    "active_inactive_disposition",
    "decision_reason",
    "reviewer_1",
    "reviewer_2",
    "reviewed_at",
    "decision_status",
    "decision_version",
    "predecessor_decision_id",
    "decision_id",
}
PII = {
    "name",
    "customer_name",
    "company_name",
    "email",
    "phone",
    "address",
    "notes",
    "free_text",
    "document_content",
    "username",
    "department",
}
IMMUTABLE = (
    "classification",
    "quarantine_status",
    "mapping_status",
    "organization_candidate_count",
)
DECISION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


def _rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        return fields, list(reader)


def validate(original, review):
    _, source = _rows(original)
    fields, rows = _rows(review)
    errors = []
    if fields != REQUIRED:
        errors.append(
            f"required columns mismatch missing={sorted(REQUIRED - fields)} extra={sorted(fields - REQUIRED)}"
        )
    pii = sorted(
        {
            c
            for c in fields
            if c.lower() in PII
            or any(
                t in c.lower()
                for t in ("email", "phone", "address", "customer_name", "company_name")
            )
        }
    )
    if pii:
        errors.append(f"PII columns prohibited: {pii}")
    source_keys = {(r["entity_type"], r["entity_id"]) for r in source}
    source_by_key = {(r["entity_type"], r["entity_id"]): r for r in source}
    review_keys = []
    active = Counter()
    known = {r["entity_type"] for r in source}
    for i, r in enumerate(rows, 2):
        key = (r.get("entity_type", ""), r.get("entity_id", ""))
        review_keys.append(key)
        if key[0] not in known:
            errors.append(f"row {i}: unknown entity type")
        try:
            if int(key[1]) < 1:
                raise ValueError
        except ValueError:
            errors.append(f"row {i}: malformed entity_id")
        source_row = source_by_key.get(key)
        if source_row and any(
            r.get(field, "") != source_row.get(field, "") for field in IMMUTABLE
        ):
            errors.append(
                f"row {i}: census classification/quarantine state is immutable"
            )
        if r.get("allowed_human_decisions", "") != ALLOWED_DISCLOSURE:
            errors.append(f"row {i}: allowed decision disclosure is invalid")
        decision = r.get("human_decision", "")
        status = r.get("decision_status", "")
        if decision and decision not in ALLOWED_DECISIONS:
            errors.append(f"row {i}: unknown human_decision")
        if status not in ALLOWED_STATUSES:
            errors.append(f"row {i}: unknown decision_status")
        target = r.get("target_organization_id", "").strip()
        if target:
            try:
                if int(target) < 1:
                    raise ValueError
            except ValueError:
                errors.append(f"row {i}: malformed target_organization_id")
        if target and decision != "ASSIGN_TO_ORGANIZATION":
            errors.append(f"row {i}: target requires ASSIGN_TO_ORGANIZATION")
        if decision == "ASSIGN_TO_ORGANIZATION" and not target:
            errors.append(f"row {i}: assignment requires target")
        if status == "APPROVED":
            if not decision:
                errors.append(f"row {i}: approved row requires decision")
            if not r.get("evidence_reference", "").strip():
                errors.append(f"row {i}: approved row requires evidence_reference")
            if (
                not r.get("reviewer_1", "").strip()
                or not r.get("reviewer_2", "").strip()
                or r.get("reviewer_1") == r.get("reviewer_2")
            ):
                errors.append(f"row {i}: approved row requires two distinct reviewers")
            if (
                not r.get("reviewed_at", "").strip()
                or not r.get("decision_id", "").strip()
            ):
                errors.append(
                    f"row {i}: approved row requires reviewed_at and decision_id"
                )
            if r.get("decision_id") and not DECISION_ID.fullmatch(r["decision_id"]):
                errors.append(f"row {i}: malformed decision_id")
            try:
                datetime.fromisoformat(r.get("reviewed_at", "").replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"row {i}: malformed reviewed_at")
            try:
                version = int(r.get("decision_version", ""))
                if version < 1:
                    raise ValueError
            except ValueError:
                errors.append(
                    f"row {i}: approved row requires positive decision_version"
                )
            else:
                predecessor = r.get("predecessor_decision_id", "").strip()
                if version > 1 and not DECISION_ID.fullmatch(predecessor):
                    errors.append(
                        f"row {i}: successor requires valid predecessor_decision_id"
                    )
                if version == 1 and predecessor:
                    errors.append(f"row {i}: first decision cannot name a predecessor")
        if status == "SUPERSEDED":
            errors.append(
                f"row {i}: superseded history cannot replace the current review row"
            )
        if status in {"PENDING", "IN_REVIEW", "APPROVED"}:
            active[key] += 1
    if set(review_keys) != source_keys or len(review_keys) != len(source):
        errors.append("review rows must exactly match original package")
    if any(n > 1 for n in active.values()):
        errors.append("duplicate active decision for stable entity")
    if errors:
        raise ValueError("\n".join(errors))
    return {"valid": True, "rows": len(rows), "MT1_OWNERSHIP_RESOLUTION_READY": False}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True)
    p.add_argument("--review", required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(validate(a.original, a.review), sort_keys=True))
        return 0
    except (ValueError, KeyError) as e:
        print(str(e))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

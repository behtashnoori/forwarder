#!/usr/bin/env python3
"""Validate a fail-closed cohort plan/review and optional row expansion."""

from __future__ import annotations
import argparse
import csv
import json
from datetime import datetime
from collections import Counter
from pathlib import Path

ACTIVE = {"PENDING", "IN_REVIEW", "APPROVED"}
DECISIONS = {
    "ASSIGN_TO_ORGANIZATION",
    "KEEP_QUARANTINED",
    "RETIRE_INACTIVE_LEGACY_ROW",
    "REDESIGN_REQUIRED",
    "NEEDS_MORE_EVIDENCE",
}


def load_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def validate(original, plan_path, review_path, expansion_path=None):
    original_rows = load_csv(original)
    source = {(r["entity_type"], int(r["entity_id"])) for r in original_rows}
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    review = load_csv(review_path)
    errors = []
    membership = Counter()
    cohorts = {}
    for c in plan.get("cohorts", []):
        cid = c.get("cohort_id")
        members = {
            (m.get("entity_type"), m.get("entity_id")) for m in c.get("members", [])
        }
        if not cid or cid in cohorts:
            errors.append("duplicate or missing cohort_id")
        cohorts[cid] = c
        if not members or not members <= source:
            errors.append(f"{cid}: missing/injected member")
        if (
            c.get("cohort_type") != "SINGLE_MEMBER_FAIL_CLOSED"
            or len(c.get("members", [])) != 1
            or c.get("structural_root") is not None
            or c.get("member_decisions_may_inherit_disposition") is not False
            or c.get("target_organization_assignment_allowed") is not False
        ):
            errors.append(
                f"{cid}: v1 plan permits only non-inheriting single-member cohorts"
            )
        for key in members:
            membership[key] += 1
        if (
            c.get("target_organization_assignment_allowed")
            and c.get("cohort_type") != "INDIVIDUALLY_VALIDATED_ASSIGNMENT"
        ):
            errors.append(f"{cid}: cohort assignment lacks member validation")
        if len(members) > 1 and not c.get("structural_root"):
            errors.append(f"{cid}: multi-member cohort lacks exact root")
    if set(membership) != source or any(n != 1 for n in membership.values()):
        errors.append("every original row must belong to exactly one cohort")
    seen_review = set()
    reviews = {}
    approved_decision_ids = []
    for r in review:
        cid = r.get("cohort_id", "")
        seen_review.add(cid)
        if cid in reviews:
            errors.append(f"{cid}: duplicate review row")
        reviews[cid] = r
        c = cohorts.get(cid)
        status = r.get("decision_status", "")
        decision = r.get("human_decision", "")
        if not c:
            errors.append(f"{cid}: review references unknown cohort")
            continue
        if (
            r.get("cohort_type") != c.get("cohort_type")
            or r.get("structural_class") != c.get("structural_class")
            or r.get("structural_root", "") != ""
        ):
            errors.append(f"{cid}: review structural metadata differs from plan")
        if int(r.get("member_count", "0")) != len(c["members"]):
            errors.append(f"{cid}: partial member count")
        if decision and decision not in DECISIONS:
            errors.append(f"{cid}: invalid decision")
        if decision and decision not in set(c.get("permitted_decision_classes", [])):
            errors.append(f"{cid}: decision is not permitted for this cohort")
        if decision == "ASSIGN_TO_ORGANIZATION" and not c.get(
            "target_organization_assignment_allowed"
        ):
            errors.append(f"{cid}: Organization assignment prohibited")
        if r.get("target_organization_id") and decision != "ASSIGN_TO_ORGANIZATION":
            errors.append(f"{cid}: target injected after decision")
        if status == "SUPERSEDED":
            errors.append(f"{cid}: stale cohort cannot be active review")
        if status == "APPROVED" and (
            not decision
            or not r.get("evidence_reference")
            or not r.get("reviewer_1")
            or not r.get("reviewer_2")
            or r.get("reviewer_1") == r.get("reviewer_2")
            or not r.get("decision_id")
        ):
            errors.append(f"{cid}: approval requires evidence, ID, and two reviewers")
        if status == "APPROVED":
            approved_decision_ids.append(r.get("decision_id", ""))
            try:
                reviewed = datetime.fromisoformat(
                    r.get("reviewed_at", "").replace("Z", "+00:00")
                )
                if reviewed.tzinfo is None:
                    raise ValueError
            except ValueError:
                errors.append(f"{cid}: approval requires timezone-aware reviewed_at")
            if r.get("decision_version") != "1" or r.get("predecessor_decision_id", ""):
                errors.append(
                    f"{cid}: v1 approval requires version 1 and no predecessor"
                )
    if seen_review != set(cohorts):
        errors.append("partial cohort review")
    if len(set(approved_decision_ids)) != len(approved_decision_ids):
        errors.append("approved cohort decision IDs must be unique")
    if expansion_path:
        expanded = load_csv(expansion_path)
        expanded_keys = {
            (r.get("entity_type"), int(r.get("entity_id", "0"))) for r in expanded
        }
        if expanded_keys != source or len(expanded) != len(source):
            errors.append("partial or injected expansion")
        if any(
            not r.get("decision_id") or r.get("quarantine_status") != "QUARANTINED"
            for r in expanded
        ):
            errors.append("expansion must retain quarantine and row decision IDs")
        row_decision_ids = [r.get("decision_id", "") for r in expanded]
        if len(set(row_decision_ids)) != len(row_decision_ids):
            errors.append("expansion row decision IDs must be unique")
        if any(r.get("decision_status") != "APPROVED" for r in review):
            errors.append("expansion requires every cohort to be currently APPROVED")
        expanded_by_key = {
            (r.get("entity_type"), int(r.get("entity_id", "0"))): r for r in expanded
        }
        for cid, c in cohorts.items():
            cohort_review = reviews.get(cid, {})
            for member in c.get("members", []):
                key = (member.get("entity_type"), member.get("entity_id"))
                row = expanded_by_key.get(key, {})
                if (
                    row.get("cohort_id") != cid
                    or row.get("human_decision") != cohort_review.get("human_decision")
                    or row.get("target_organization_id", "")
                    != cohort_review.get("target_organization_id", "")
                    or row.get("cohort_decision_id") != cohort_review.get("decision_id")
                    or not row.get("decision_id")
                ):
                    errors.append(
                        f"{cid}: expansion is not bound to approved cohort decision"
                    )
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "valid": True,
        "rows": len(source),
        "cohorts": len(cohorts),
        "safe_multi_member_cohorts": 0,
        "readiness": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--review", required=True)
    p.add_argument("--expansion")
    a = p.parse_args(argv)
    try:
        print(
            json.dumps(
                validate(a.original, a.plan, a.review, a.expansion), sort_keys=True
            )
        )
        return 0
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print(e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

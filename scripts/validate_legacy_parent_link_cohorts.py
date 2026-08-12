#!/usr/bin/env python3
"""Validate and optionally generate the MT-1 parent-link cohort v2 package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

EXPECTED = {
    "csv": "57265f19fd0e8695a0e60c310f68f14d730d7898d2bc4ab55a6351ec2212bce6",
    "json": "7b400ff3f8499b59b289faba390537aabcc7893f06acb005654c549405cf5df3",
    "summary": "50f9613c9f7f913bc7591a55d4babee3c721ff510584e758a68cc222692b6fef",
}
PRIMARY = {
    "CaseDocumentRequirement": "shipment_request_id",
    "DocumentAuditEvent": "shipment_request_id",
    "ExpertConsoleLog": "shipment_request_id",
    "ExpertConsoleNotification": "shipment_request_id",
    "ExpertQuote": "shipment_request_id",
    "ReferralAssignmentLog": "request_id",
    "ShipmentRequestLog": "shipment_request_id",
    "ShipmentTracking": "shipment_request_id",
    "ShipmentTransportUnit": "tracking_id",
    "ShipmentTransportUnitUpdate": "unit_id",
}
ROOT_TYPES = {
    "Customer",
    "CustomerGamification",
    "ShipmentRequest",
    "ReferralAutoAssignState",
}
CONDITIONAL = {"DocumentAuditEvent", "ExpertConsoleNotification"}
DISPOSITIONS = ["KEEP_QUARANTINED", "NEEDS_MORE_EVIDENCE", "RETIRE_INACTIVE_LEGACY_ROW"]


def rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package(package_dir, original):
    p = Path(package_dir)
    paths = {
        "csv": p / "legacy-parent-links.csv",
        "json": p / "legacy-parent-links.json",
        "summary": p / "legacy-parent-links-summary.json",
    }
    errors = [
        f"{k} hash mismatch" for k, v in paths.items() if digest(v) != EXPECTED[k]
    ]
    links = rows(paths["csv"])
    original_rows = rows(original)
    source = {(r["entity_type"], int(r["entity_id"])) for r in original_rows}
    children = {(r["child_entity_type"], int(r["child_entity_id"])) for r in links}
    allowed_fields = {
        "child_entity_type",
        "child_entity_id",
        "child_table",
        "parent_relation",
        "parent_entity_type",
        "parent_entity_id",
        "parent_table",
        "parent_column",
        "relation_status",
        "evidence_source",
    }
    if len(links) != 289:
        errors.append("parent-link record count is not 289")
    if children != source or len(source) != 135:
        errors.append("parent-link child coverage differs from original 135")
    if set(links[0]) != allowed_fields:
        errors.append("unexpected or missing parent-link fields")
    if any(
        r["classification"] != "UNRESOLVED"
        or r["quarantine_status"] != "QUARANTINED"
        or r["mapping_status"] != "NONE"
        or r["organization_candidate_count"] != "0"
        for r in original_rows
    ):
        errors.append("original rows are not uniformly fail-closed")
    for r in links:
        try:
            if int(r["child_entity_id"]) <= 0:
                raise ValueError
            if r["parent_entity_id"] and int(r["parent_entity_id"]) <= 0:
                raise ValueError
        except ValueError:
            errors.append("malformed entity ID")
        if r["child_entity_type"] not in {x[0] for x in source}:
            errors.append("unknown child entity type")
        if r["relation_status"] not in {
            "PARENT_PRESENT",
            "PARENT_NULL",
            "ROOT_OR_SINGLETON",
        }:
            errors.append("unsupported relation status")
    summary = json.loads(paths["summary"].read_text(encoding="utf-8-sig"))
    if (
        summary.get("pii_included") is not False
        or summary.get("ownership_assignment") != "NONE"
        or summary.get("organization_inference") != "NONE"
        or summary.get("quarantine_change") != "NONE"
    ):
        errors.append("package safety flags are not fail-closed")
    if (
        summary.get("extraction_database_access") != "READ_ONLY"
        or summary.get("completion_database_access") != "NONE"
    ):
        errors.append("package read-only provenance is invalid")
    if errors:
        raise ValueError("\n".join(sorted(set(errors))))
    by_child = defaultdict(list)
    for r in links:
        by_child[(r["child_entity_type"], int(r["child_entity_id"]))].append(r)
    return source, links, by_child


def analyze(package_dir, original):
    source, links, by_child = package(package_dir, original)
    memo = {}

    def trace(key, trail=()):
        if key in memo:
            return memo[key]
        if key in trail:
            return {"complete": False, "cycle": True, "root": None, "path": []}
        typ, _ = key
        if typ in ROOT_TYPES:
            out = {"complete": True, "cycle": False, "root": key, "path": [key]}
        else:
            rel = PRIMARY.get(typ)
            raw_hits = [r for r in by_child[key] if r["parent_relation"] == rel]
            hits = list(
                {
                    (
                        r["parent_entity_type"],
                        r["parent_entity_id"],
                        r["relation_status"],
                    ): r
                    for r in raw_hits
                }.values()
            )
            if len(hits) != 1 or hits[0]["relation_status"] != "PARENT_PRESENT":
                out = {"complete": False, "cycle": False, "root": None, "path": [key]}
            else:
                parent = (
                    hits[0]["parent_entity_type"],
                    int(hits[0]["parent_entity_id"]),
                )
                if parent not in source:
                    out = {
                        "complete": False,
                        "cycle": False,
                        "root": None,
                        "path": [key],
                    }
                else:
                    up = trace(parent, trail + (key,))
                    out = {**up, "path": [key] + up["path"]}
        memo[key] = out
        return out

    for key in source:
        trace(key)
    return source, links, by_child, memo


def expected_plan(package_dir, original):
    source, links, by_child, graph = analyze(package_dir, original)
    groups = defaultdict(list)
    broken = []
    for key in sorted(source):
        g = graph[key]
        (groups[g["root"]] if g["complete"] else broken).append(key)
    cohorts = []
    for root, members in sorted(groups.items()):
        cid = f"root:{root[0]}:{root[1]}"
        cohorts.append(_cohort(cid, root, members, graph))
    for key in broken:
        cohorts.append(_cohort(f"individual:{key[0]}:{key[1]}", None, [key], graph))
    counts = Counter()
    for key, g in graph.items():
        if key[0] == "ReferralAutoAssignState":
            counts["platform_singleton"] += 1
        elif key[0] in ROOT_TYPES:
            counts["root"] += 1
        elif not g["complete"]:
            counts["unproven"] += 1
        elif key[0] in CONDITIONAL:
            counts["conditional"] += 1
        else:
            counts["derived"] += 1
    return {
        "plan_version": 2,
        "cohort_version": 2,
        "source_rows": 135,
        "parent_link_hashes": EXPECTED,
        "projection": {
            **counts,
            "connected_root_components": len(groups),
            "safe_multi_member_cohorts": sum(len(c["members"]) > 1 for c in cohorts),
            "single_member_cohorts": sum(len(c["members"]) == 1 for c in cohorts),
            "minimum_human_decision_events": len(cohorts),
        },
        "MT1_OWNERSHIP_RESOLUTION_READY": False,
        "AUTO_BACKFILL_ALLOWED": False,
        "QUARANTINE_MUST_REMAIN": True,
        "cohorts": cohorts,
    }


def _cohort(cid, root, members, graph):
    allowed = (
        ["KEEP_QUARANTINED", "NEEDS_MORE_EVIDENCE", "REDESIGN_REQUIRED"]
        if members == [("ReferralAutoAssignState", 1)]
        else DISPOSITIONS
    )
    return {
        "cohort_id": cid,
        "cohort_version": 2,
        "predecessor_cohort_id": None,
        "predecessor_cohort_version": None,
        "structural_root_entity_type": root[0] if root else None,
        "structural_root_entity_id": root[1] if root else None,
        "members": [
            {
                "entity_type": k[0],
                "entity_id": k[1],
                "path_proof": [
                    {"entity_type": p[0], "entity_id": p[1]} for p in graph[k]["path"]
                ],
                "path_completeness": "COMPLETE" if graph[k]["complete"] else "BROKEN",
            }
            for k in members
        ],
        "member_count": len(members),
        "allowed_disposition_decisions": allowed,
        "organization_assignment_allowed": False,
        "expansion_rule": "Expand one current two-person approved disposition to exactly all enumerated members with unique row decision IDs; retain quarantine.",
        "approval_requirements": {"distinct_reviewers": 2, "evidence_required": True},
        "evidence_source_hash": EXPECTED["csv"],
        "parent_link_package_hashes": EXPECTED,
    }


def validate(original, package_dir, plan_path, review_path, expansion_path=None):
    expected = expected_plan(package_dir, original)
    actual = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("v2 plan differs from mechanically reconstructed hashed graph")
    review = rows(review_path)
    cohorts = {c["cohort_id"]: c for c in actual["cohorts"]}
    if len(review) != len(cohorts) or {r["cohort_id"] for r in review} != set(cohorts):
        raise ValueError("partial, duplicate, or injected cohort review")
    approved = {}
    decision_ids = []
    for r in review:
        c = cohorts[r["cohort_id"]]
        if int(r["member_count"]) != c["member_count"] or r["structural_root"] != (
            f"{c['structural_root_entity_type']}:{c['structural_root_entity_id']}"
            if c["structural_root_entity_type"]
            else ""
        ):
            raise ValueError("review metadata or membership drift")
        if r["target_organization_id"]:
            raise ValueError("Organization target propagation is prohibited")
        if r["decision_status"] not in {"PENDING", "APPROVED"}:
            raise ValueError("unknown or stale review status")
        if r["decision_status"] == "APPROVED":
            reviewer_1 = r["reviewer_1"].strip().casefold()
            reviewer_2 = r["reviewer_2"].strip().casefold()
            if (
                r["human_decision"] not in c["allowed_disposition_decisions"]
                or not r["evidence_reference"]
                or not reviewer_1
                or reviewer_1 == reviewer_2
                or not reviewer_2
                or not r["decision_id"]
                or not r["reviewed_at"]
                or r["decision_version"] != "1"
                or r["predecessor_decision_id"]
            ):
                raise ValueError("approval is incomplete, stale, or invalid")
            try:
                reviewed_at = datetime.fromisoformat(
                    r["reviewed_at"].replace("Z", "+00:00")
                )
                if reviewed_at.tzinfo is None:
                    raise ValueError
            except ValueError as exc:
                raise ValueError("approval timestamp is invalid") from exc
            decision_ids.append(r["decision_id"])
            approved[r["cohort_id"]] = r
        elif any(
            r[k]
            for k in (
                "human_decision",
                "evidence_reference",
                "reviewer_1",
                "reviewer_2",
                "reviewed_at",
                "decision_version",
                "predecessor_decision_id",
                "decision_id",
            )
        ):
            raise ValueError("non-approved review contains decision data")
    if len(decision_ids) != len(set(decision_ids)):
        raise ValueError("duplicate active cohort decision")
    if expansion_path:
        exp = rows(expansion_path)
        source = {(r["entity_type"], int(r["entity_id"])) for r in rows(original)}
        keys = [(r["entity_type"], int(r["entity_id"])) for r in exp]
        if (
            len(keys) != len(source)
            or set(keys) != source
            or len(set(keys)) != len(keys)
        ):
            raise ValueError("partial or injected expansion")
        if len(approved) != len(cohorts):
            raise ValueError("expansion requires current approval of every cohort")
        row_ids = []
        member_to_cohort = {
            (m["entity_type"], m["entity_id"]): c["cohort_id"]
            for c in cohorts.values()
            for m in c["members"]
        }
        for r, key in zip(exp, keys):
            a = approved[member_to_cohort[key]]
            if (
                r["cohort_id"] != member_to_cohort[key]
                or r["human_decision"] != a["human_decision"]
                or r["cohort_decision_id"] != a["decision_id"]
                or r["target_organization_id"]
                or r["quarantine_status"] != "QUARANTINED"
                or not r["decision_id"]
            ):
                raise ValueError("expansion is not exactly bound or clears quarantine")
            row_ids.append(r["decision_id"])
        if len(row_ids) != len(set(row_ids)):
            raise ValueError("duplicate active row decision")
    return {
        "valid": True,
        "rows": 135,
        "cohorts": len(cohorts),
        **actual["projection"],
        "readiness": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--original", required=True)
    p.add_argument("--package-dir", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--review", required=True)
    p.add_argument("--expansion")
    a = p.parse_args(argv)
    try:
        print(
            json.dumps(
                validate(a.original, a.package_dir, a.plan, a.review, a.expansion),
                sort_keys=True,
            )
        )
        return 0
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
        print(e)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

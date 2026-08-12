import csv
import json
from pathlib import Path
import pytest
from scripts.validate_legacy_adjudication_cohorts import validate

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/architecture/legacy-adjudication"
ORIGINAL = BASE / "legacy-human-adjudication-review.csv"
PLAN = BASE / "legacy-adjudication-cohort-plan.json"
REVIEW = BASE / "legacy-adjudication-cohort-review.csv"


def test_pristine_single_member_plan_passes():
    result = validate(ORIGINAL, PLAN, REVIEW)
    assert result == {
        "valid": True,
        "rows": 135,
        "cohorts": 135,
        "safe_multi_member_cohorts": 0,
        "readiness": False,
    }


def _plan(tmp_path, mutate):
    value = json.loads(PLAN.read_text())
    mutate(value)
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(value))
    return p


def _review(tmp_path, mutate):
    with REVIEW.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0])
    mutate(rows)
    p = tmp_path / "review.csv"
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return p


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["cohorts"][0]["members"].append(
            {"entity_type": "Customer", "entity_id": 999999}
        ),
        lambda p: p["cohorts"][1]["members"].append(p["cohorts"][0]["members"][0]),
        lambda p: p["cohorts"][0].update(
            {
                "members": p["cohorts"][0]["members"] + p["cohorts"][1]["members"],
                "structural_root": None,
            }
        ),
        lambda p: p["cohorts"][0].update(
            {"target_organization_assignment_allowed": True}
        ),
    ],
)
def test_plan_bypasses_rejected(tmp_path, mutation):
    with pytest.raises(ValueError):
        validate(ORIGINAL, _plan(tmp_path, mutation), REVIEW)


@pytest.mark.parametrize(
    "changes",
    [
        {
            "decision_status": "APPROVED",
            "human_decision": "KEEP_QUARANTINED",
            "reviewer_1": "one",
            "reviewer_2": "one",
            "evidence_reference": "evidence:1",
            "decision_id": "decision-1",
        },
        {"decision_status": "SUPERSEDED"},
        {"human_decision": "ASSIGN_TO_ORGANIZATION", "target_organization_id": "1"},
        {"member_count": "0"},
    ],
)
def test_review_bypasses_rejected(tmp_path, changes):
    with pytest.raises(ValueError):
        validate(
            ORIGINAL, PLAN, _review(tmp_path, lambda rows: rows[0].update(changes))
        )


def test_partial_review_rejected(tmp_path):
    with pytest.raises(ValueError, match="partial cohort review"):
        validate(ORIGINAL, PLAN, _review(tmp_path, lambda rows: rows.pop()))


def test_invented_mixed_root_cohort_rejected(tmp_path):
    def mutation(plan):
        plan["cohorts"][0]["members"].extend(plan["cohorts"][1]["members"])
        plan["cohorts"][0]["structural_root"] = {
            "entity_type": "ShipmentRequest",
            "entity_id": 999,
        }
        plan["cohorts"].pop(1)

    with pytest.raises(ValueError, match="single-member"):
        validate(ORIGINAL, _plan(tmp_path, mutation), REVIEW)


def test_pending_reviews_cannot_authorize_injected_expansion(tmp_path):
    with ORIGINAL.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    fields = [
        "cohort_id",
        "entity_type",
        "entity_id",
        "human_decision",
        "target_organization_id",
        "cohort_decision_id",
        "decision_id",
        "quarantine_status",
    ]
    expansion = tmp_path / "expansion.csv"
    with expansion.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "cohort_id": f"single:{row['entity_type']}:{row['entity_id']}",
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "human_decision": "ASSIGN_TO_ORGANIZATION",
                    "target_organization_id": "999999",
                    "cohort_decision_id": "injected-cohort",
                    "decision_id": f"injected-row-{row['entity_type']}-{row['entity_id']}",
                    "quarantine_status": "QUARANTINED",
                }
            )
    with pytest.raises(ValueError, match="currently APPROVED"):
        validate(ORIGINAL, PLAN, REVIEW, expansion)


def test_cohort_specific_decision_enum_is_enforced(tmp_path):
    def mutate(rows):
        customer = next(r for r in rows if r["cohort_id"] == "single:Customer:1")
        customer["human_decision"] = "REDESIGN_REQUIRED"

    with pytest.raises(ValueError, match="not permitted"):
        validate(ORIGINAL, PLAN, _review(tmp_path, mutate))


def test_duplicate_expansion_decision_ids_rejected(tmp_path):
    with ORIGINAL.open(encoding="utf-8", newline="") as f:
        source_rows = list(csv.DictReader(f))

    def approve(rows):
        for row in rows:
            row.update(
                {
                    "human_decision": "KEEP_QUARANTINED",
                    "evidence_reference": "evidence:reviewed",
                    "reviewer_1": "reviewer-one",
                    "reviewer_2": "reviewer-two",
                    "decision_status": "APPROVED",
                    "decision_version": "1",
                    "decision_id": f"cohort-decision-{row['cohort_id']}",
                }
            )

    approved = _review(tmp_path, approve)
    with approved.open(encoding="utf-8", newline="") as f:
        reviews = {r["cohort_id"]: r for r in csv.DictReader(f)}
    fields = [
        "cohort_id",
        "entity_type",
        "entity_id",
        "human_decision",
        "target_organization_id",
        "cohort_decision_id",
        "decision_id",
        "quarantine_status",
    ]
    expansion = tmp_path / "duplicate-expansion.csv"
    with expansion.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for source in source_rows:
            cid = f"single:{source['entity_type']}:{source['entity_id']}"
            writer.writerow(
                {
                    "cohort_id": cid,
                    "entity_type": source["entity_type"],
                    "entity_id": source["entity_id"],
                    "human_decision": "KEEP_QUARANTINED",
                    "target_organization_id": "",
                    "cohort_decision_id": reviews[cid]["decision_id"],
                    "decision_id": "DUPLICATE-FOR-ALL-ROWS",
                    "quarantine_status": "QUARANTINED",
                }
            )
    with pytest.raises(ValueError, match="must be unique"):
        validate(ORIGINAL, PLAN, approved, expansion)


def test_forged_unversioned_duplicate_cohort_approvals_rejected(tmp_path):
    def forge(rows):
        for row in rows:
            row.update(
                {
                    "cohort_type": "FORGED",
                    "structural_class": "ROOT_DECISION",
                    "structural_root": "invented-root",
                    "human_decision": "KEEP_QUARANTINED",
                    "evidence_reference": "evidence:reviewed",
                    "reviewer_1": "reviewer-one",
                    "reviewer_2": "reviewer-two",
                    "reviewed_at": "",
                    "decision_status": "APPROVED",
                    "decision_version": "",
                    "predecessor_decision_id": "nonexistent-stale-predecessor",
                    "decision_id": "SAME-COHORT-DECISION-ID",
                }
            )

    with pytest.raises(
        ValueError,
        match="structural metadata|timezone-aware|version 1|must be unique",
    ):
        validate(ORIGINAL, PLAN, _review(tmp_path, forge))

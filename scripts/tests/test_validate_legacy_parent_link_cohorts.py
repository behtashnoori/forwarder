import csv
import json
from pathlib import Path

import pytest

from scripts.validate_legacy_parent_link_cohorts import validate

ROOT = Path(__file__).parents[2]
ORIGINAL = (
    ROOT / "docs/architecture/legacy-adjudication/legacy-human-adjudication-review.csv"
)
PLAN = (
    ROOT
    / "docs/architecture/legacy-adjudication/legacy-adjudication-cohort-plan-v2.json"
)
REVIEW = (
    ROOT
    / "docs/architecture/legacy-adjudication/legacy-adjudication-cohort-review-v2.csv"
)
PACKAGE = Path(r"D:\1-webapp\legacy-parent-links")


def test_pristine_v2_is_fail_closed():
    out = validate(ORIGINAL, PACKAGE, PLAN, REVIEW)
    assert out["valid"] and out["rows"] == 135 and out["cohorts"] == 22
    assert out["minimum_human_decision_events"] == 22 and not out["readiness"]


@pytest.mark.parametrize(
    "mutation", ["remove", "inject", "root", "path", "org", "hash"]
)
def test_plan_forgery_is_rejected(tmp_path, mutation):
    plan = json.loads(PLAN.read_text())
    if mutation == "remove":
        plan["cohorts"][0]["members"].pop()
    elif mutation == "inject":
        plan["cohorts"][0]["members"].append(
            {
                "entity_type": "Customer",
                "entity_id": 999,
                "path_proof": [],
                "path_completeness": "COMPLETE",
            }
        )
    elif mutation == "root":
        plan["cohorts"][0]["structural_root_entity_id"] = 999
    elif mutation == "path":
        plan["cohorts"][0]["members"][0]["path_proof"] = []
    elif mutation == "org":
        plan["cohorts"][0]["organization_assignment_allowed"] = True
    else:
        plan["parent_link_hashes"]["csv"] = "0" * 64
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan))
    with pytest.raises(ValueError):
        validate(ORIGINAL, PACKAGE, p, REVIEW)


@pytest.mark.parametrize("reviewer_2", ["same", " same ", "SAME"])
def test_one_person_approval_is_rejected(tmp_path, reviewer_2):
    rs = list(csv.DictReader(REVIEW.open(newline="")))
    r = rs[0]
    r.update(
        human_decision="KEEP_QUARANTINED",
        evidence_reference="E",
        reviewer_1="same",
        reviewer_2=reviewer_2,
        reviewed_at="2026-08-12T00:00:00Z",
        decision_status="APPROVED",
        decision_version="1",
        decision_id="D1",
    )
    p = tmp_path / "review.csv"
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rs[0])
        w.writeheader()
        w.writerows(rs)
    with pytest.raises(ValueError):
        validate(ORIGINAL, PACKAGE, PLAN, p)

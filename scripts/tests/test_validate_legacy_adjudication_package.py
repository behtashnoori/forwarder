import csv
from pathlib import Path
import pytest
from scripts.validate_legacy_adjudication_package import validate

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = Path(
    r"D:\1-webapp\legacy-human-adjudication\legacy-human-adjudication-package.csv"
)
REVIEW = (
    ROOT / "docs/architecture/legacy-adjudication/legacy-human-adjudication-review.csv"
)


def _mutate(tmp_path, **changes):
    with REVIEW.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0])
    rows[0].update(changes)
    out = tmp_path / "review.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return out


def test_pristine_review_package_passes():
    assert validate(ORIGINAL, REVIEW)["rows"] == 135


@pytest.mark.parametrize(
    "changes",
    [
        {"target_organization_id": "1"},
        {"human_decision": "ASSIGN_TO_ORGANIZATION"},
        {"human_decision": "UNKNOWN"},
        {"classification": "DETERMINISTIC"},
        {"quarantine_status": "CLEAR"},
        {"allowed_human_decisions": "ASSIGN_TO_ORGANIZATION"},
        {"decision_status": "SUPERSEDED"},
        {
            "human_decision": "KEEP_QUARANTINED",
            "decision_status": "APPROVED",
            "reviewer_1": "one",
            "reviewer_2": "one",
            "evidence_reference": "evidence:1",
            "reviewed_at": "2026-08-12T00:00:00Z",
            "decision_version": "1",
            "decision_id": "decision-1",
        },
        {
            "human_decision": "KEEP_QUARANTINED",
            "decision_status": "APPROVED",
            "reviewer_1": "one",
            "reviewer_2": "two",
            "reviewed_at": "2026-08-12T00:00:00Z",
            "decision_version": "1",
            "decision_id": "decision-1",
        },
    ],
)
def test_fail_closed_rules(tmp_path, changes):
    with pytest.raises(ValueError):
        validate(ORIGINAL, _mutate(tmp_path, **changes))


def test_missing_or_new_row_rejected(tmp_path):
    with REVIEW.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0])
    rows.pop()
    rows.append({**rows[0], "entity_id": "999999"})
    out = tmp_path / "review.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with pytest.raises(ValueError, match="exactly match"):
        validate(ORIGINAL, out)

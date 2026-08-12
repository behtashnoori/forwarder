# MT-1 parent-link cohort review v2

This derivative is structural and fail-closed. It contains no human decision or
Organization target. Reviewers may approve only the enumerated disposition
classes. Two distinct reviewers, evidence, a current version-1 decision ID and
timestamp are mandatory. The validator reconstructs every member path from the
three hash-pinned parent-link files; editing the plan cannot manufacture proof.

An approved cohort expands to every listed stable pair with a unique row
decision ID. Expansion never supplies an Organization ID and never clears
quarantine. `DocumentAuditEvent:1` remains an individual broken-lineage review.
`ReferralAutoAssignState:1` remains a platform/singleton redesign case.
`Customer:1` is an orphan root and may only be kept quarantined, retired by a
human, or marked as needing more evidence.

Run `python scripts/validate_legacy_parent_link_cohorts.py` with `--original`,
`--package-dir`, `--plan`, and `--review`. A nonzero result blocks review.

`MT1_OWNERSHIP_RESOLUTION_READY=false`

`AUTO_BACKFILL_ALLOWED=NO`

`QUARANTINE_MUST_REMAIN=YES`

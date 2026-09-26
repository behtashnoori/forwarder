# P3-14 controlled integration receipt

Local date: 2026-09-27, Asia/Tehran. LPAF v2.7, governance level B.

| Identity | SHA |
| --- | --- |
| Clean canonical entry / P3-01..13 base | `835d46f7008bbc374168d1f5eba415b444574f7f` |
| P3-14 qualified Product | `c9347815746c25d3e943e1a00bc2d3cab87958ee` |
| P3-14 retained Evidence | `fbca04db284417df2b9bcb8cfd0914fee9b185c6` |
| Fast-forward integration target | `fbca04db284417df2b9bcb8cfd0914fee9b185c6` |

The canonical `integration/golden-controlled` worktree was clean at the entry
SHA. A fresh `github` fetch showed local/remote ahead/behind `0/0`. The
canonical branch then advanced only by `git merge --ff-only` to the retained
P3-14 Evidence SHA. Push to `github/integration/golden-controlled` succeeded;
a subsequent fetch confirmed local/remote `0/0` at the integration target.

The accepted qualification is in
`docs/operational/evidence/phase3-p3-14-final-runtime-ux-20260926/`. Its owned
PostgreSQL and Chrome processes stopped, the temporary runtime was removed,
and `production_accessed=false` / `production_mutated=false` are machine
recorded. No migration, release, deployment, Production access or Production
mutation occurred.

This receipt is documentation-only. After this receipt is pushed and verified
at `0/0`, its canonical SHA is the sole authorized P3-15 entry base. P3-15 must
use a new isolated worktree and may qualify or harden already-authorized
behavior only; it may not add a Product capability.

```text
PHASE3_P3_14=PASS
PHASE3_P3_14_INTEGRATED=PASS
P3_14_PRODUCT_HEAD=c9347815746c25d3e943e1a00bc2d3cab87958ee
P3_14_EVIDENCE_HEAD=fbca04db284417df2b9bcb8cfd0914fee9b185c6
P3_14_CANONICAL_INTEGRATION=PASS
CANONICAL_PUSH=PASS
LOCAL_REMOTE_ALIGNMENT=PASS
AHEAD_BEHIND=0/0
P3_14_MIGRATION_REQUIRED=NO
PHASE3_P3_15=NOT_STARTED
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
```

# Phase 3 human-walkthrough Customer Request hardening

Date: 2026-09-27. Governance: frozen canonical LPAF v2.7, Level B.

This pack binds the bounded post-final-candidate hardening requested after the
Product Owner's real Human Product Walkthrough. It is automated evidence for a
new Phase 3 candidate; it is not Human Walkthrough approval, a release,
deployment, or Production record.

## Candidate identity

- New Product SHA: `fe73dbf3c2789d9b88052be9098c28c8e2b2add7`.
- Historical pre-hardening Product SHA:
  `b1a8f4fafb89e4e8e9b2f35ffcb79bc98c7ec86a`.
- Branch: `codex/human-walkthrough-customer-request-hardening`.
- Migration required: **NO**.
- Alembic head: exactly one, `20261012_phase3_cargo_eta`.
- The evidence commit is recorded by the controlled integration receipt after
  this directory is committed.

## Bounded Product changes

- `HW-DEFECT-001`: authenticated Customer Request create/detail projections
  expose only the current Request assignee's safe display name, or a truthful
  pending-assignment state. The value is read after commit. Public Tracking and
  anonymous create responses do not receive this projection.
- `HW-DEFECT-002`: Customer Request detail is Request-centric and restores the
  submitted route, transport-selection policy/method, Cargo items or legacy
  Cargo facts, quantity/UOM, dates, instructions, and current safe assignee.
  Quote and Quote history remain below Request facts and keep their semantics.
- `HW-UX-005`: authenticated `ثبت درخواست جدید` opens a shared domestic /
  international chooser directly; the existing forms and public entry remain.
- `HW-UX-006`: an authenticated Customer sees `پنل مشتری`; an anonymous visitor
  continues to see `ورود مشتری`.
- Customer navigation priority is requests, shipments, Customer documents,
  profile, and password.
- `HW-UX-007`: copy now explains who selects the transport method; the actual
  method selector still appears only for Customer selection.
- `HW-UX-008`: selector layout uses local containment/min-width behavior and was
  verified at desktop and 390 px RTL without global overflow hiding.

No table, migration, dependency, role, domain capability, AI, agent, GPS,
geography expansion, signup-host relaxation, release, deployment, or Production
action was added.

## Accepted qualification

| Gate | Result |
| --- | --- |
| Focused backend hardening/security | PASS — 71 tests |
| Focused frontend hardening | PASS — 29 tests |
| Full backend regression | PASS — 1,564 passed, 121 classified skips, 0 failed, 902.09 s |
| Full frontend regression | PASS — 459 passed in 97 files, 0 failed, 208.39 s |
| Focused OpenAPI contracts | PASS — 16 passed, 0 failed |
| PostgreSQL 18 base-to-head migration chain | PASS |
| Phase 3 PostgreSQL 18 qualification | PASS |
| Public Tracking PostgreSQL regression | PASS |
| Chrome P3-01..P3-15, MT3 and IPJ-01..04 | PASS |
| TypeScript | PASS |
| ESLint | PASS — 0 errors, 14 retained warnings |
| Non-release production-mode frontend build | PASS — 2,583 modules; existing Browserslist/chunk advisories retained |
| Structure / backend determinism / architecture governance | PASS |
| Credential policy / current-tree secret scan | PASS — 0 findings |
| Git diff check | PASS |
| Owned runtime/database cleanup | PASS |

`automated-final/result.json` is the consolidated PostgreSQL 18 and real Chrome
run. `full-backend/result.json`, the qualification summary, and the checked-in
gate logs bind the complete regression results. The screenshots contain only a
fresh synthetic Customer and synthetic Request.

## Honest state boundary

- The six authorized findings are fixed and automated-qualified.
- The original walkthrough observations remain historical facts and are not
  rewritten by this pack.
- The Product Owner has not completed the Human Product Walkthrough:
  `HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS`.
- Broader public-site ideas remain `NOT_IMPLEMENTED`.
- Global Product validation remains `EVIDENCE_PENDING`.
- `RELEASE_READY=NO`.
- Production was not accessed or mutated.

```text
LPAF_BASELINE=2.7
POST_WALKTHROUGH_HARDENING=PASS
NEW_PHASE3_FINAL_PRODUCT_HEAD=fe73dbf3c2789d9b88052be9098c28c8e2b2add7
SLICE_JOURNEYS=PASS
INTEGRATED_PRODUCT_JOURNEYS=PASS
AUTOMATED_PRODUCT_JOURNEYS=PASS
MIGRATION_REQUIRED=NO
ALEMBIC_HEAD=20261012_phase3_cargo_eta
ALEMBIC_HEAD_COUNT=1
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
RELEASE_READY=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
```

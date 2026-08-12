# MT-1 canonical ownership slice 2 — local evidence

Date: 2026-08-12. Initial commit: `3ce265ef391ccc1fa82455896bf04c2b02fb59f7`.

The canonical owner remains `operational_organization.id`, stored in the legacy
business graph as `operational_organization_id`. No legacy row was backfilled and
no Organization was fabricated for the 135-row synthetic cohort.

## Implemented contract

- Activity and Task store an explicit owner/scope. Every present Customer,
  Opportunity, and ShipmentRequest parent must resolve to that owner. Actors,
  creators, assignees, and experts never establish ownership.
- ShipmentTransportUnit and ShipmentTransportUnitUpdate store an explicit owner
  and are protected by composite same-Organization foreign keys to their parent.
- CRM customer/opportunity/activity reads and expert-console shipment list/detail/
  tracking reads are fenced by the actor's single active Organization membership.
  NULL-owned and quarantined rows are not tenant-readable.
- `POST /api/expert/requests/<id>/accept-intake` is authenticated, role-gated,
  membership-derived, atomic, audited, and idempotent for same-Organization replay.
  It cannot re-tenantize a request or infer ownership from assignment.
- Tenant roots cannot be re-owned or reverted to INTAKE through ORM update paths.

## Local validation

- Focused slice, CRM, expert-console, transport, ownership, quarantine, and census
  selection: 88 passed, 5 PostgreSQL-marked skips before fixture repair; repaired
  fixture groups: 28 passed; focused adversarial slice: 15 passed.
- Full backend: 672 passed, 79 skipped, 1 expected xfail, 17 failed, 20 setup
  errors. The remaining failures are bounded certification-fixture debt: 12 legacy
  tests hard-code a former Alembic sole head, and case-document/tracking-location
  fixtures create tenant resources without Organization membership/ownership.
  Those surfaces fail closed; no cross-tenant success was observed.
- Isolated loopback PostgreSQL 18: clean full upgrade reached
  `20260824_mt1_graph`; all six sampled composite constraints exist; downgrade to
  `20260823_mt1_ownership_expand` and re-upgrade passed. This is local, not server,
  certification.
- Python compilation, JSON parse, Alembic sole-head, and `git diff --check` passed.
  Ruff passed with only repository-pre-existing F401/E712 categories excluded.
- Bounded secret/PII scan covered 99 tracked backend/architecture files changed
  since v1.9.1 plus both new slice files. No credential, token, DB-password URL, or
  private-key candidate was found. PII candidates were `example.test` addresses
  and reserved synthetic phone fixtures only.

## Verdict

`MT-1 CANONICAL OWNERSHIP SLICE-2 SECURITY REVIEW — BLOCK`

The implemented slice is fail-closed and its focused adversarial review passes,
but the repository-wide local certification gate remains blocked until the
bounded legacy case-document/tracking-location fixtures and stale sole-head
assertions are made Organization-aware and the full backend suite is green.
Production, server database, deploy, and push were not used.

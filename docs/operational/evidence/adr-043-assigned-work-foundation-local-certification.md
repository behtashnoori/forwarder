# ADR-043 assigned-work foundation — local certification

- Date: 2026-08-30
- Scope: local implementation foundation only; no production access, deployment, or push.
- Governing decisions: ADR-042, ADR-043, ADR-037.

## Implemented

- A fail-closed `authorize_work_action(actor, resource, action)` service resolves active identity, exactly one active tenant membership, canonical authority, resource tenant, request or direct-shipment root, current responsibility, intrinsic action class, and explicit Organization Admin capability.
- `PLATFORM_ADMIN` without tenant membership is denied tenant work. `role=admin` is not used to derive Platform authority.
- Direct OperationalShipment now has an additive `primary_responsible_expert_id` migration/model field. Creation validates an in-tenant responsible Expert and defaults only to the authenticated creation actor when no responsible Expert is supplied; this is creation-time root assignment, not creator-history authorization.
- Existing Direct Shipments with no responsibility remain denied to Basic Expert by the evaluator.

## Local certification

- `pytest backend/tests/test_assigned_work_authorization.py backend/tests/test_tenant_architecture_contract.py backend/tests/test_referral_tenant_fencing.py -q`: 20 passed, 1 expected xfail.
- Operational/CRM/admin/selector regression set: 35 passed.
- Python compilation and whitespace diff check passed.
- Local PostgreSQL 18 isolated database `forwarder_auth_test`: fresh Alembic upgrade to `20260907_direct_shipment_responsibility` passed; the `primary_responsible_expert_id` column was present; empty-state downgrade to `20260906_global_logistics_point_materialization` and re-upgrade to head passed. No production connection was used.

## Deferred to later controlled implementation phases

Endpoint-wide evaluator integration, SQL collection-scope predicates, all certified child-resource enforcement, Organization Admin category migration, observational shadow telemetry, direct-shipment reassignment endpoint/audit stream, PostgreSQL migration upgrade/downgrade evidence, and browser E2E remain required before `IMPLEMENTATION_READY` can be YES. No permissive dual-evaluator composition has been added.

## Local data-quality certification — 2026-08-30

Read-only checks ran against the isolated local test database only. No
production environment file, production connection, data mutation, backfill,
or credential was used or recorded.

| Check | Count | Result |
| --- | ---: | --- |
| Tenant-owned request missing organization | 0 | PASS |
| Accepted-quote shipment missing request parent | 0 | PASS |
| Direct shipment missing primary responsibility | 0 | PASS |
| Accepted-quote shipment/request tenant mismatch | 0 | PASS |
| Active membership ambiguous or missing for a listed user | 0 | PASS |
| WorkItem missing shipment parent | 0 | PASS |
| Operational exception missing shipment parent | 0 | PASS |

`DATA_QUALITY_CHECKS_CERTIFIED = YES` for this isolated, currently empty
local test target. This does not certify production data or authorize a
backfill, deployment, or production rollout.

## Reassignment / concurrency completion — 2026-08-30

`REASSIGNMENT_CONCURRENCY_CERTIFIED = YES` for local backend/API evaluation.

- The evaluator now treats a passed ORM object as an identity hint only. It
  refreshes the active user, membership, root, and child parent from persisted
  state for every decision. A prior request object, browser list, session, or
  known child ID cannot retain an allow after commit.
- Deterministic authorization tests prove A allow before reassignment; A deny
  and B allow after commit; inherited shipment-child revocation; current-root
  collection filtering; denial despite historical knowledge/capability; and
  denial for a forged cross-tenant assignee/root.
- API certification exercises the protected Organization Admin reassignment
  route then the old/new Expert request detail, tracking detail, and list
  routes. The former assignee receives non-disclosing denials/empty scope and
  the new assignee receives allow responses immediately.
- Shadow telemetry is observational only (`emit_shadow_decision`); its result
  is never composed with the canonical decision. The tracking API shadow test
  confirms mismatches do not alter enforcement.
- ADR-037 CRM regression and ADR-043 reporting fail-closed regression passed;
  CRM/list/write surfaces remain bounded by their accepted contracts and
  reporting/export remains denied pending its companion decision.
- Active legacy compatibility inventory: legacy role labels, selector/history
  compatibility, and date serialization remain explicitly bounded. No active
  `legacy_allow OR canonical_allow` path was found in the assigned-work
  enforcement surface.
- Adversarial assurance passed for cross-tenant assignment/tenant context,
  legacy-admin authority, stale state, and forged root cases.

### Evidence commands

| Evidence set | Result |
| --- | --- |
| Reassignment API + service regression (`test_assigned_work_authorization`, `test_expert_assignment_referral_contract`) | 24 passed |
| Shadow, ADR-037 CRM, reporting fail-closed, adversarial tenant, legacy-permission regression | 44 passed |
| Definitive local r3 full-regression aggregate (`pytest backend/tests -q`) | **835 passed, 92 skipped, 1 xfailed** |

The r3 aggregate initially exposed three deterministic-test isolation defects:
three tests defaulted to a persistent local PostgreSQL target and collided with
prior rows. They now own an in-memory test database; their focused rerun and
the r3 aggregate passed. This changed only test isolation, not authorization.

`SHADOW_EVIDENCE_COMPLETE = YES`

`ADR_037_CRM_REGRESSION = PASS`

`LEGACY_COMPATIBILITY_INVENTORY = COMPLETE`

`ADVERSARIAL_SECURITY_ASSURANCE = PASS`
`LOCAL_EXIT_GATE = PASS`

No push, deployment, production connection, migration execution, or unrelated
workspace cleanup occurred.

## Immutable release-candidate binding — 2026-08-30

`CODE_CERTIFIED_HEAD = adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e`

`TESTED_HEAD = adcc5da2c6f6d696dbad15b9b2cd7900bd96bc9e`

`TESTED_HEAD_MATCHES_CODE_CERTIFIED_HEAD = YES`

The exact commit was certified from a clean detached temporary Git worktree;
the user's primary worktree remained dirty only with separately classified
unrelated work and uncommitted evidence. The isolated worktree contained no
uncommitted release implementation change.

| Certification field | Value |
| --- | --- |
| Branch containing code candidate | `codex/pr-4a-dms-gate-repair` |
| Full regression command | `python -m pytest backend/tests -q` |
| Exit code | 0 |
| Aggregate | 835 passed, 0 failed, 92 skipped, 1 xfailed, 0 xpassed |
| Duration | 299.37 seconds |
| Durable log | `C:\Users\pc\AppData\Local\Temp\forwarder-adr043-cert-adcc5da\adr043-immutable-full-regression.log` |
| Alembic head | `20260907_direct_shipment_responsibility` |

The exact-SHA aggregate covers the preserved API E2E, reassignment/concurrency,
shadow telemetry, CRM/ADR-037, logistics-selector, cross-tenant, role-admin
authority, collection non-disclosure, and direct-shipment CRM negative suites.

`API_E2E_CERTIFIED = YES`

`REASSIGNMENT_CONCURRENCY_CERTIFIED = YES`

`SHADOW_EVIDENCE_COMPLETE = YES`

`CRM_REGRESSION_PASS = YES`

`LOGISTICS_SELECTOR_REGRESSION_PASS = YES`

`CROSS_TENANT_NEGATIVES = YES`

`ROLE_ADMIN_AUTHORITY_EXPERT_NEGATIVE = YES`

`COLLECTION_LEAKAGE_NEGATIVES = YES`

`DIRECT_SHIPMENT_CRM_NEGATIVE = YES`

`CERTIFIED_RELEASE_DIFF_UNCOMMITTED = NONE`

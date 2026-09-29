# Governed Platform Maintenance Admin Bootstrap — Qualification Evidence

## Identity and verdict

- Authoritative LPAF baseline: `2.7`
- Entry canonical/evidence SHA:
  `87471aedcf144c0ab635de74f77f1a02aa68b2da`
- Product SHA: `cf05be76815f963e91d7d829112a53d94cf5ac73`
- Canonical branch: `integration/golden-controlled`
- Schema/head: `20261012_phase3_cargo_eta` / one head
- Capability qualification: `PASS`
- Walkthrough provisioning: `PASS`
- Cargo Continuity Repair PLAN: `PASS`
- Cargo Continuity Repair APPLY: `NOT_EXECUTED`
- Human Product Walkthrough: `IN_PROGRESS`
- Release Ready: `NO`

## Baseline authority chain

`DECLARED_CONTEXT_BASELINE=2.7` and
`REPOSITORY_CANDIDATE_BASELINE=2.6` were reconciled to
`AUTHORITATIVE_LPAF_BASELINE=2.7`.

Normative precedence is established by:

1. `current/LPAF-v2.7-Architecture-Framework-FA.md` §1, which declares v2.7
   the single active baseline and defines the internal authority order;
2. the LPAF root `README.md`, which activates v2.7 and classifies v2.6 as
   superseded/historical/non-normative;
3. `LPAF-v2.7-BASELINE-ACCEPTANCE.md`, recording Product Owner selection,
   freeze date 2026-09-24, and predecessor disposition;
4. `LPAF-v2.7-SHA256SUMS.txt`, for which all 53 entries matched with zero
   missing or mismatched artifacts;
5. tracked canonical Forwarder `AGENTS.md` at entry SHA `87471ae`, which applies
   the same v2.7 normative set to the Product repository.

The v2.6 acceptance and protocol files are authentic historical artifacts but
are expressly superseded by the activated successor. The contradiction is
therefore resolved rather than silently selected.

## Product Authority and design

- Product Authority Record:
  `docs/product/phase3/PLATFORM-ADMIN-BOOTSTRAP-MISSION-AUTHORITY.md`.
- Architecture/security/transaction decision:
  `docs/operational/adr/ADR-073-governed-platform-maintenance-admin-provisioning.md`.
- Capability: CLI-only `provision-platform-maintenance-admin`.
- Trust model: explicitly confirmed offline Product command, bounded named
  operator, bounded Product approval reference, and password supplied outside
  the command line. It does not require a pre-existing Platform Admin.
- Persistence: existing `ExpertUser`, `OperationalMembership`,
  `OperationalAudit`, and `OperationalIdempotency`; no migration.
- Concurrency: target organization row lock on PostgreSQL; equivalent concurrent
  calls serialize to one `CHANGED` and one `UNCHANGED`.
- Existing username handling: fail closed; no promotion or repurposing.
- Audit actions: `actor_created`, `authority_assigned`, and
  `membership_assigned`, all in the same transaction and action time.
- UI/API/startup/bulk provisioning: none.

## Exact qualification results

- Focused provisioning plus existing composition: `18 passed`.
- Wider administration, tenant authorization, user-management, and Cargo repair
  regression: `75 passed`.
- Owned disposable PostgreSQL 18 concurrency: `1 passed`; server version
  `180000`, migrated head `20261012_phase3_cargo_eta`, outcomes exactly one
  `CHANGED` and one `UNCHANGED`, with one user, one membership, three audit
  rows, and one idempotency row.
- Full backend regression: `1622 passed, 124 skipped`; skips were explicit
  external/owned-environment gates. The new PostgreSQL test was run separately
  and passed.
- Architecture governance: `PASS`.
- Python compile: `PASS`.
- Git diff check: `PASS`.
- Alembic heads: one, `20261012_phase3_cargo_eta`.
- Frontend change: `NONE`; no UI was required or added.

PDA-07 reconciliation: the new explicit creation behavior is `AUTHORIZED`;
existing-user refusal, authority semantics, tenant isolation, no operational
ownership, and all named walkthrough business facts are `PRESERVED`; no
`VIOLATION` or `UNKNOWN` remains in the implemented scope.

## Controlled integration and runtime

Product SHA `cf05be76815f963e91d7d829112a53d94cf5ac73` was fast-forwarded
to `integration/golden-controlled`, pushed to `github`, fetched, and verified
at ahead/behind `0/0` before runtime mutation.

The preserved runtime was restarted from the integrated Product SHA against the
same PostgreSQL 18 data directory and database `forwarder_human_walkthrough`.
No database reset or recreation occurred. Backend health/readiness and frontend
returned `200/200/200`. A fresh pre-provision backup was written to
`D:\1-webapp\forwarder-human-walkthrough-runtime\pre-platform-admin-bootstrap-20260929.dump`
with SHA-256
`98A5996E690134A6AFEB324E91581561A325C1043815DFC3180A7EB6478B74D1`.

The governed command used:

- username: `walkthrough_platform_admin`;
- full name: `Walkthrough Platform Maintenance Admin`;
- authority: `PLATFORM_ADMIN`;
- organization: `da81186a-d226-49a5-ae73-95ad60f2ab40`;
- operator: `local-human-walkthrough-bootstrap`;
- approval reference: `PLATFORM-ADMIN-BOOTSTRAP/2026-09-29`.

First execution returned `CHANGED`; the equivalent retry returned `UNCHANGED`.
Read-only proof shows exactly one persisted/active Platform Admin, exactly one
active membership in the target tenant carrying only `organization.admin`,
three audit facts at `2026-09-29 10:36:07.197396+03:30`, and one idempotency
mapping. `walkthrough_admin` remains active `ORGANIZATION_ADMIN` with one
membership in the same tenant. The target Shipment owner remains
`walkthrough_expert`.

## Cargo Continuity Repair PLAN

PLAN was executed with the mission's exact Shipment, Cargo, Request tracking,
Request Cargo, RoutePlan revision, terminal RouteLeg, database, and new
maintenance actor identities. Final result:

```text
ELIGIBILITY=YES
CONFLICTS=0
PLAN_FINGERPRINT=df299f46c1d98528514ef6b5942dfbc9d3d7befb550b06749292e509cb090ff8
REASON=KNOWN_REQUEST_TO_SHIPMENT_CREATION_CONTINUITY_DEFECT
STATE=MISSING_CONTINUITY
```

Every eligibility check passed:

1. `MAINTENANCE_AUTHORITY`;
2. `EXPECTED_SOURCE_REQUEST_MATCH`;
3. `COMMERCIAL_LINEAGE_EXACT`;
4. `EXPECTED_CARGO_BINDING_MATCH`;
5. `SOURCE_REQUESTED_QUANTITY_PRESENT`;
6. `SOURCE_CARGO_FACTS_EXACT`;
7. `KNOWN_DEFECT_SIGNATURE_PROVEN`;
8. `ROUTE_PLAN_CREATION_REVISION_PROVEN`;
9. `UNIQUE_ROUTE_DESTINATION`;
10. `CONTINUITY_FACTS_MISSING`;
11. `EXISTING_EXECUTION_PRESERVED`;
12. `NO_DOWNSTREAM_CONFLICT`.

The first display attempt computed the plan but the Windows console could not
encode a Persian location value; the command caught that output exception and
rolled back. It was rerun with UTF-8 console encoding and returned the complete
PASS result above. This was an output-transport issue, not a domain eligibility
failure, and both invocations were read-only.

## Preservation evidence

Before provisioning, after provisioning, and after PLAN, counts and canonical
row hashes were identical for Request, Request log, Request Cargo, both Quotes,
Customer/contact/role/link history, Shipment, Shipment Cargo, RoutePlan,
RouteLeg, RouteStageExecution, ExecutionUnit, RouteCargoDestination,
allocation, delivery, and owner-transfer tables.

The target record remains:

- planned quantity `100.000000`;
- actual quantity `NULL`;
- requested quantity `NULL`;
- source Request lineage `NULL`;
- source Request Cargo lineage `NULL`;
- RoutePlan `1`, revision `1`, terminal RouteLeg `1`;
- one RouteStageExecution and one ExecutionUnit;
- zero RouteCargoDestination, allocation, delivery, owner transfer, and Cargo
  repair audit rows.

Only the explicitly authorized actor, exact membership, three governance audit
rows, and one idempotency mapping were added. No raw SQL mutation, Cargo repair
APPLY, Production access/mutation, deployment, or release occurred.

## Qualification-state separation

```text
ENGINEERING_COMPLETE=PASS
PRODUCT_COMPLETE=NOT_CLAIMED
RELEASE_READY=NO
RELEASE_COMPLETE=NO
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
APPLY_EXECUTED=NO
```

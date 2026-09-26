# P3-13 — exceptional owner transfer with current authorization

LPAF v2.7 / rigor C. This is the retained P3-11..13 mission, governed by its
explicit Product authority and accepted ADR-069. Architecture acceptance:
`6259830f2a5fe94798bf4183d2643bf624529c26`. Entry canonical was clean, freshly
fetched and 0/0 at `c2e6140d52eda620ecaef6e255bcd591f58da2cb`.

- Product SHA: `c0914906af6675c016d5b77d51ecc8a0c05c0b72`.
- Product tree: `c30513984d4d723fbfa565297c3973e47b10f439`.
- Evidence SHA: the evidence-only descendant containing this report, identified
  exactly in the separate controlled integration receipt.
- Sole migration: `20261011_phase3_owner_transfer`, parent
  `20261010_phase3_closure`. No P3-11 draft migration/runtime is imported.

## Product behavior

Only a currently active same-tenant Organization Admin can issue TRANSFER_OWNER.
Application authentication binds the real actor and organization; the request
cannot supply actor, tenant or time. The named command requires the current
owner, Shipment version, eligible target, nonblank reason and idempotency key.
The target must satisfy the existing active same-organization Expert membership
policy. Ordinary Expert and Platform identity do not gain this capability.

One immutable receipt records old/new owners and retained labels, actor, reason,
server time, prior/next version, sequence and previous receipt. Initial owner time
is reported unknown when there is no historical fact. A valid exact replay
returns its original receipt even after a later transfer; altered replay fails.

The current owner remains the Shipment source of truth. Former-owner access
derived only from ownership ends; any separately valid Project/read or explicit
capability remains governed independently. New owner receives the existing normal
owner rights. Document authority follows the current owner without changing file
bytes, exact versions, recorded authors or audience. The transferring Admin does
not receive document-management authority. Customer DN10/Cargo entitlement is
unchanged, and Customer projection contains no transfer reason or internal history.

Request/Quote assignment, existing WorkItem/Action responsibility and pinned SLA
responsibility are unchanged, including subsequent SLA evaluation. The count of
open work assigned to the former owner is informational. Transfer invokes no
reassignment or general reconciliation. Closed Shipments may receive this
separately approved administrative transfer; their state/ClosureDecision remain
fixed, and the P3-12 prohibition on new physical operations remains enforced.

## Authentication and database boundary

Application authentication/authorization is responsible for human identity
binding. PostgreSQL revalidates supplied actor eligibility, tenant, target,
owner/version, immutable chain, idempotency and transaction atomicity. A caller
holding the trusted application database credential and a structurally valid
Admin identity is not independently authenticated as that human by PostgreSQL.
No new DB identity-binding mechanism is claimed or introduced.

The one SECURITY DEFINER routine has a dedicated isolated NOLOGIN owner,
`pg_catalog,pg_temp` fixed search_path, fully qualified static SQL, no dynamic
SQL and no PUBLIC EXECUTE. The normal restricted LOGIN cannot SET ROLE to the
owner, disable triggers, fabricate or alter history, or perform an ordinary
owner update. The existing owner guard remains SECURITY INVOKER and requires
the narrow routine's same-transaction receipt. No session bypass flag exists.
Runtime readiness refuses elevated/schema-owning credentials even under TESTING.

Organization, Shipment, actor/target and membership fences serialize transfer
and live revocation. Competing same-predecessor transfers have one winner;
same-command replay creates no extra history. Receipt, owner/version, audit and
outbox succeed atomically or all roll back. Ownership-dependent existing mutation
paths lock/reload the parent before current authorization. Tests include former
owner document, milestone and checkpoint commands waiting behind a transfer.

Empty downgrade restores the original fixed-owner guard and preserves prior-head
rows. Once transfer history exists, downgrade refuses before destructive DDL.
Cluster roles may remain empty/unprivileged for other synthetic databases.
There is no historical owner restoration, migration branch or production action.

## Current browser authorization

Shipment detail/list, Workspace and both Tower views refresh on browser resume
and discard responses from obsolete authorization generations. On resume, a
changed Shipment version retires descendant forms, including same-name owner
transfers. Unchanged focus and file chooser returns preserve valid forms; normal
command reloads preserve the active closure section. Lists retain the last
explicitly applied filters. These changes do not alter Tower ranking or SLA.

The transfer UI provides current owner/history, eligible target search, mandatory
reason and explicit review. An uncertain network result retains the original
idempotency key. No internal owner ID is added to existing general DTOs.

## Exact-source qualification

| Gate | Verified final outcome |
| --- | --- |
| Complete backend | 1535 passed, 120 environment-dependent skips, zero failures/errors; all 1655 collected cases in 225 modules accounted for once |
| Complete frontend | 441 passed in 92 files |
| PostgreSQL 18 | 14 passed: current structural/concurrency proofs, P3-01..12 affected regressions, Public Tracking |
| Real Chrome | 15 passed across the transfer journey and affected prior slices/Customer/Public paths |
| Static | All nine passed: app/node types, lint, build, architecture, structure, backend determinism, diff and sole Alembic head |
| Visual | Three fresh desktop/mobile/Customer captures inspected; actual loaded Customer content, no internal transfer projection |

[Machine-readable qualification and exact-byte manifest](phase3-p3-13-owner-transfer-20260926/qualification.json)
retain 129 selected evidence files with SHA256 and byte counts.
The final Product stayed fixed during every mandatory run. Both backend partitions
completed; their 732 and 923 JUnit cases equal the full collection. PostgreSQL
and browser owned processes stopped and their runtime directory was removed.
Backend process IDs 20200/25472 and their listeners were verified absent.

Automatic approval review rejected deletion of the first P3-13 stopped backend
fixture directory (`.../forwarder-owned-backend-f4631875e2a64b8cb8853e4e9d3ede43`)
with `blocked by policy`, like the earlier P3-12 cleanup. No retry or alternative
deletion was attempted. The final stopped backend fixture directory
`C:/Users/pc/AppData/Local/Temp/forwarder-owned-backend-303d68e1a597428dacaaf0f7fd5d1d7c`
is retained under that known restriction; no fresh rejection for that final path
is claimed. Mission §74 permits accurately disclosed stopped-fixture retention.
Exact paths, process checks and the prior rejection are retained in cleanup.json.


The mission's required cases map to retained executable evidence:

| Mission cases | Proof location |
| --- | --- |
| A valid transfer; E/F independent old/third-party work; M Request independence | `test_transfer_receipt_current_authority_and_independent_work_and_request`, repeated SLA background test, real Chrome transfer |
| B/C old denial/new normal owner; D exact document authority | HTTP/current-scope and document-bytes tests; genuine PostgreSQL waiting mutation tests; Chrome old download denial and new-owner upload |
| G invalid live target/actor; H ordinary ORM/API mutation | Parametrized current authority/eligibility tests, HTTP actor-field rejection and ORM prohibition |
| I raw DB invariant and history integrity | Actual restricted LOGIN PostgreSQL test: raw owner/history denial, PUBLIC and SET ROLE denial, unsafe DDL/trigger privilege denial |
| J competing transfer; K replay | Genuine simultaneous database sessions, predecessor/version conflict, single retained receipt, later-chain replay and injected atomic rollback |
| L stale browser/cache | Current list/Workspace/Tower tests, generation/focus frontend cases and actual old-tab Chrome refresh |
| N Customer privacy; O regressions | Exact-byte Customer document tests, recursive OpenAPI allowlists, Customer Chrome, complete backend/frontend plus 14 PG and 15 Chrome cases |

The exact test sources are retained in the Product commit:
[unit/current authority](../../../backend/tests/test_phase3_owner_transfer.py),
[PostgreSQL](../../../backend/tests/test_phase3_owner_transfer_postgresql.py),
[Chrome](../../../e2e/phase3-owner-transfer.spec.ts).

The final package binds each gate to the clean Product SHA/tree above.
Complete backend coverage uses two disjoint module partitions and a hashed
manifest/JUnit census; environment-dependent opt-ins are reported as skips,
with the relevant PostgreSQL boundaries separately executed on owned PG18.
Browser evidence is slice-specific plus affected regressions, not global
Integrated Product Journey qualification or a Human Product Walkthrough.

## Retained preliminary evidence and environment correction

The working note and prior-attempt manifest record preliminary failures: initial
fixture helper naming, owned migration startup
create_all conflict, four expanded unit fixture/schema assertions, frontend
retry interaction/current-owner wording, and an unchanged NewOperation wait
failure under concurrent load. Corrected focused runs passed without weakening
Product authority or assertions. Dirty-source PostgreSQL/browser passes are
retained for diagnosis and never substituted for final Product qualification.

The first clean Product `212d01fa19979e520f8ba9d4a5b4cefd9248cb9e` completed all
1655 backend cases with 1534 passes, 120 skips and one legacy OpenAPI text-range
assertion failure; frontend, PostgreSQL, Chrome and static gates passed. It was
not integrated. Moving only the owner-transfer schema block ahead of the
ProjectConfiguration block preserved parsed YAML equality, all runtime files,
tests and assertions. The correction produced c091490; every mandatory gate was
rerun against that clean final source. `contract-order-proof.json` and the previous
logs preserve this distinction. Warnings remain visible; no blanket claim that
every warning predates this slice is made.

An early metadata smoke omitted an explicit testing URI and selected the
preconfigured local `forwarder_auth_test` database. create_all failed before seed
or Product commands; its DDL transaction rolled back. No follow-up access,
cleanup or migration to that database occurred. The entry environment note
records this incident. Subsequent smoke/qualification explicitly sets both
DATABASE_URL and TEST_DATABASE_URL and verifies owned synthetic targets.
No Production endpoint, data or credential was requested or used.

## Product/reference reconciliation and stopping boundary

The working note's PDA-07 table maps every observable change to AUTHORIZED or
PRESERVED authority. OpenAPI's three private routes and recursive allowlists,
tenant inventory, ADR/index, architecture baseline and current Phase 3 status
are reconciled. Historical proposal/evidence remains historical.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J03/J04/J06/J08/J09;
FWD-IPJ-01/IPJ-03/IPJ-04. REFERENCE_RECONCILIATION=PASS;
REFERENCE_IMPACT=NONE. DN02 owner-transfer portion and DN09 are resolved for P3-13.
P3-11 remains independently blocked on Product stop-range placement; its retained
draft is not qualified or integrated. P3-12 remains integrated at c2e6140.

GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN; HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN;
RELEASE_READY=NO; P3_14_STARTED=NO; P3_15_STARTED=NO;
PRODUCTION_ACCESSED=NO; PRODUCTION_MUTATED=NO;
DEPLOYMENT_PERFORMED=NO; RELEASE_CREATED=NO.

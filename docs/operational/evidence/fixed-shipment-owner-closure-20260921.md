# ADR-047 Fixed Operational Shipment Owner — Closure Evidence

Date: 2026-09-21

Starting canonical: `2cadaefef8e5d44163ac92a45dce5ac2cb769269`

Candidate branch: `codex/adr047-fixed-shipment-owner-closure`

Design commit: `7a953713920fabcb69e9e67f2edaeb156eb008c2`

Implementation commit: `462d82d9f7d064331abe47ad64891be0a8dc2604`

## A. LPAF Governance Gate

The active governing baseline is LPAF v2.2 and its mandatory Agent Entry
Protocol. The reviewed v2.3 Product Integration and `REFERENCE_IMPACT`
controls were applied as the Forwarder strong default. LPAF v2.4 was not
adopted and no generic LPAF framework file was changed.

This was treated as a Level B product/runtime change with elevated
authorization, immutable ownership, migration, PostgreSQL, concurrency, normal
browser navigation, negative authorization, recovery, and release evidence.
The implementation-authorizing design was committed before runtime code. The
mission did not authorize deployment, Production access, Product Acceptance
Retry, modularization, history rewrite, force push, or a temporary-branch push.

The capability owner is Operations/Product. `OperationalShipment` is the
System of Record for one fixed responsible Transport Expert. Quote issuance,
Request assignment, Documents, and Control Tower remain separate bounded
capabilities whose downstream authorization consumes that Shipment-owned fact.

## B. P1 Demo Blocker

The failed Final Product Acceptance evidence at commit
`10e13612b57e9b0c3a31d2fa6f8de8359eb5be6f` identified one causal P1 blocker:
accepted-Quote Shipments did not persist the ADR-047 owner, while general
Shipment authorization and Control Tower scope followed mutable Request
assignment. This also prevented the Shipment-owned Documents journey from
being accepted.

That finding was not bypassed or reclassified. This slice closes it by making
the persisted Shipment owner mandatory, immutable, and authoritative across
both creation paths and all affected downstream authorization.

## C. Existing Drift

Before this implementation:

- Direct Shipment creation populated the nullable
  `primary_responsible_expert_id` with incomplete validation.
- Accepted-Quote Shipment creation left that field null.
- General Shipment Expert authorization and collection scope could derive from
  `ShipmentRequest.assigned_to`.
- Control Tower Expert scope and owner projection could derive from the current
  Request assignee.
- Shipment Documents correctly required a persisted parent owner and therefore
  failed closed for null-owner accepted-Quote Shipments.

The relevant Architecture Drift Report row now records
`IMPLEMENTED — QUALIFIED`; historical pre-closure evidence remains preserved.
No unrelated drift row was closed or reclassified.

## D. Authoritative ADR-047 Contract

Every Operational Shipment owns exactly one responsible Transport Expert. The
relationship is established atomically when the Shipment is created, remains
tenant-consistent, and cannot be changed. Request assignment remains a
commercial workflow and is not Shipment authority.

The owning active Expert is authorized within the existing action/state
contract. A same-organization peer Expert, foreign actor, inactive/revoked
actor, or actor possessing only a child/Request/Project identifier does not gain
ownership. Existing tenant-scoped Admin/Manager oversight remains separately
governed and never substitutes an owner or grants document mutation.

## E. Accepted-Quote Owner Derivation

`create_from_accepted_quote` resolves and locks the exact accepted official
Quote identified by the Shipment lineage. It validates the Quote, Request,
Customer, and Organization relationship, then uses only
`ExpertQuote.created_by_expert_id` as the owner source. That issuer must be an
active canonical `EXPERT` with exactly one active membership in the same
Organization.

The owner is persisted in the same Shipment creation transaction. The
Customer cannot select it. The current or later Request assignee is not an
owner candidate. Quote revision after Shipment creation cannot change it.

Replay authorization is evaluated before idempotency-hash comparison, so an
unauthorized caller cannot use replay/conflict differences as an ownership or
payload oracle.

## F. Direct Shipment Compatibility

Direct Shipment creation retains its existing explicit/default owner input but
now validates that value through the same active, canonical, exactly-one-active-
membership, same-Organization Transport Expert contract. Admin, Manager,
Platform Admin, Customer, foreign, inactive, ambiguous-membership, and invalid
identities cannot be persisted as the responsible Expert.

The responsible Expert participates in the idempotency payload. A replay with
different ownership intent cannot silently return a Shipment created for a
different owner.

## G. Shipment Authorization

The persisted `OperationalShipment.primary_responsible_expert_id` is now the
only Expert ownership root for Shipment list, detail, and governed mutations.
Authorization remains tenant-first, active-identity and capability aware, and
non-disclosing. The accepted-Quote Request is lineage only.

An application-layer update guard rejects owner mutation. Revision
`20260926_fixed_shipment_responsible_expert` also installs a PostgreSQL/SQLite
write-once database trigger and makes the owner column non-null. There is no
owner mutation route, state, command, audit event, or UI control.

The existing separately accepted Project-derived read remains a read contract;
it does not create ownership, document-management authority, tracking mutation
authority, or a different owner projection.

## H. Request Assignment Separation

Request assignment and reassignment continue to govern Request-commercial work.
They do not mutate an already-created Shipment and do not transfer Shipment
detail access, Shipment commands, Control Tower population, or Shipment
Document management to the new Request assignee.

Actual overlapping PostgreSQL transactions proved that accepted-Quote Shipment
creation racing Request reassignment still records the exact Quote issuer. The
original owner retains the governed Shipment after reassignment; the new
Request assignee does not acquire it.

## I. Control Tower

Control Tower remains a read model and changes no business fact. Expert
candidates are now scoped by tenant, active Shipment lifecycle, and persisted
Shipment owner before search, attention evaluation, aggregate counts, ordering,
or windowing. Responsible-Expert presentation also comes from the Shipment.

ADR-051 scalability semantics remain unchanged: server-side authorization and
windowing, complete global KPIs, deterministic traversal, bounded hydration,
signed cursor, query-time consistency, and fail-closed invariant handling are
preserved. PostgreSQL qualification at 500 active Shipments reconfirmed this
contract.

## J. Documents

Shipment Document upload, append, targeted replace, and known-failed retry
continue to derive management authority from the parent Shipment. The active
persisted owner can manage; the reassigned Request Expert cannot. Admin/Manager
oversight remains read-only and does not become management authority.

No file/version/history/readiness model, storage behavior, retry meaning,
Customer visibility, or generalized document permission changed. The change
supplies the fixed parent authority already required by PDR-020 and ADR-050.

## K. Historical / Null Owner Inventory

Historical rows are classified from persisted Shipment source and lineage. A
null accepted-Quote owner is eligible for deterministic repair only when its
exact `accepted_quote_id` resolves one accepted Quote with matching Request,
Organization, valid issuer identity, canonical Expert role, and exactly one
active same-Organization membership.

Null Direct/other owners, missing or malformed accepted lineage, foreign or
invalid issuer lineage, ambiguous membership, and persisted owner/issuer
contradiction are not repairable by inference. The current Request assignee,
creator identity, Admin/Manager identity, and current Project relation are never
used as fallback owner evidence.

## L. Schema / Migration Decision

```text
FIXED_SHIPMENT_OWNER_SCHEMA_DECISION=ADDITIVE_MIGRATION_REQUIRED
```

The existing nullable column could not enforce the approved invariant. The
single additive migration `20260926_fixed_shipment_responsible_expert` descends
linearly from `20260925_quote_communication`. It performs reconciliation inside
the migration transaction, changes the column to `NOT NULL`, and adds the
write-once owner trigger.

Downgrade removes the trigger and relaxes nullability but retains all owner
evidence, including deterministic repaired values. Re-upgrade is safe. The
final graph has one head:
`20260926_fixed_shipment_responsible_expert`.

## M. Deterministic Reconciliation

The migration tests proved the complete designed matrix:

- H1: uniquely valid null accepted-Quote owner is repaired from the exact
  accepted Quote issuer;
- H2: missing/ambiguous/invalid lineage aborts without guessed repair;
- H3: valid Direct owner remains unchanged;
- H4: correct accepted-Quote owner remains unchanged; and
- H5: a persisted owner that contradicts the accepted Quote issuer aborts
  without rewrite.

No partial repair or constraint change survives a rejected migration
transaction.

## N. Ambiguous History Fail-Closed

The migration deliberately fails closed if any row cannot be reconciled from
authoritative persisted evidence. Error output uses safe row identifiers and
does not select an owner. Such a row requires explicit operator/data-owner
adjudication in a separately governed deployment plan.

This qualification did not inspect or claim anything about Production data and
did not execute the migration against Production.

## O. PostgreSQL Evidence

Qualification used an owned, loopback-only disposable PostgreSQL 18.0 cluster,
not a developer or Production database.

- Fixed-owner PostgreSQL creation, authorization, concurrency, immutability,
  and lineage cohort: **4 passed** in 18.34 seconds.
- Migration H1-H5, downgrade, preservation, and re-upgrade cohort:
  **2 passed**.
- Control Tower scalability cohort at 500 active Shipments: **1 passed** in
  240.29 seconds.
- Schema inspection: current/head both
  `20260926_fixed_shipment_responsible_expert`; owner column nullable = `NO`;
  trigger = `trg_operational_shipment_fixed_owner`; no pending revision.

The Control Tower run covered 0/1/99/100/101/250/500 populations, complete
static traversal, deterministic ordering, authorized owner/foreign/platform
scope, search, full-population KPIs, bounded page hydration, non-growing query
count, less than 100 queries per page, page calls below 30 seconds, and aggregate
plan execution below 1000 ms on the qualification workstation.

## P. Concurrency

Real PostgreSQL overlapping transactions, rather than sequential mocks, proved:

- Shipment creation racing Request reassignment still records the accepted
  Quote issuer;
- Request reassignment racing Shipment authorization does not transfer access;
- the next Control Tower query retains the Shipment only for the fixed owner;
- Shipment Document management remains with that same fixed owner; and
- attempted owner mutation is rejected by the database guard.

Existing accepted-Quote uniqueness and idempotency protections continue to
prevent duplicate Shipment creation.

## Q. Browser Journeys

Playwright used the real frontend, backend, and owned disposable PostgreSQL 18
database. Result: **1 passed in 1.5 minutes**.

The normal navigation journey proved E1 issues Q1; the Customer accepts it; the
Shipment is created with E1 as fixed owner; an actual open operational exception
places it in Control Tower; E1 uploads a Shipment document; the Request is then
reassigned to E2 through the existing API; E1 still discovers and opens the
Shipment, Documents, and Control Tower card; E2 receives non-disclosing denial
for detail and document mutation and does not see the Shipment in Control Tower;
and same-Organization Admin retains detail/Control Tower oversight while
Documents management remains read-only.

The journey included leave/return, desktop Persian RTL, and a 390x844 mobile
RTL viewport. The final run had no page error, console error, failed request, or
unexpected 4xx. Database audit reported:

```json
{"fixed_owner":"fixed_owner_e2e_e1","postgresql":"18","request_assignee":"fixed_owner_e2e_e2","result":"PASS","shipment_documents":1}
```

```text
FIXED_SHIPMENT_OWNER_BROWSER_QUALIFICATION=PASS
FIXED_SHIPMENT_OWNER_E2E_CLEANUP=PASS
```

## R. Negative Authorization

Focused and full tests cover the same-Organization peer Expert, reassigned
Request Expert, foreign tenant, Platform Admin without tenant-work authority,
inactive/revoked owner, wrong role, missing/ambiguous membership, forged
owner/tenant/parent/child lineage, known identifiers, null/malformed historical
lineage, replay-oracle ordering, Admin/Manager document mutation, and owner
mutation.

Denials remain non-disclosing. Counts, search results, Control Tower KPIs,
cursor metadata, lists, detail, child resources, and document operations do not
leak unauthorized Shipment presence.

## S. Full Regression

- Final full backend after all product changes: **1333 passed, 106 skipped** in
  514.19 seconds.
- Final focused replay/owner follow-up: **27 passed** in 9.39 seconds.
- Earlier complete fixed-owner focused cohort: **204 passed**.
- Final full frontend: **72 files, 357 tests passed** in 150.82 seconds.
- TypeScript `--noEmit`: **PASS**.
- ESLint: **PASS**, zero errors and 13 pre-existing warnings.
- Production frontend build: **PASS** with only the known Browserslist/chunk
  advisories.
- Current release/source/package/architecture bounded cohort: **46 passed**.
- Architecture governance checks: **PASS**.
- Current-tree secret scan: **0 findings**.
- Backend determinism, structure, and compile checks: **PASS**.
- `git diff --check`: **PASS**; only configured LF/CRLF advisories appeared.
- Alembic graph: exactly one head,
  `20260926_fixed_shipment_responsible_expert`.

A preliminary over-broad package selection also collected four frozen
historical D2/Personal Analytics builders whose intentional old Alembic-head
pins predate this candidate. That exploratory result was **47 passed, 4
failed** and is not a current release assertion. The corrected current-tree
release/source/package/architecture cohort passed **46/46**.

## T. Architecture Drift Closure

Only the responsible-Expert row of
`docs/architecture/ARCHITECTURE-DRIFT-REPORT.md` was changed from `OPEN` to
`IMPLEMENTED — QUALIFIED`, with the implementation commit and this evidence
file cited. The footer now identifies fixed responsible-Expert ownership,
alongside MT-3, as an explicit implementation/qualification closure. All other
open/deferred rows and historical decision evidence remain unchanged.

## U. Reference Re-check

Immediately before this PASS verdict, the following were re-read against the
final implementation, migration, tests, PostgreSQL state, concurrency behavior,
and browser journey:

- active LPAF v2.2 index, mandatory Agent Entry Protocol, and Architecture
  Framework;
- reviewed v2.3 Product Integration and `REFERENCE_IMPACT` controls;
- ADR-047, ADR-050, PDR-019, and PDR-020;
- FDD-001, FDM-001, and the Canonical Business Object Catalog owner/SOR,
  Quote, Shipment, Documents, and Control Tower contracts;
- Forwarder Architecture Baseline and Architecture Drift Report;
- ADR-051, the Control Tower scalability design, and its build evidence;
- Documents design, build evidence, and reference reconciliation;
- Simple Quote Communication design and build evidence; and
- the failed Final Product Acceptance closure evidence at
  `10e13612b57e9b0c3a31d2fa6f8de8359eb5be6f`.

No unresolved runtime/reference contradiction remains in this slice. Product
truth did not change; the required reference update is the bounded drift-status
closure recorded above.

```text
REFERENCE_IMPACT_FINAL=UPDATE_REQUIRED
REFERENCE_ALIGNMENT=PASS
```

## V. Demo Blocker Closure

The formerly missing chain now holds end to end:

```text
exact accepted official Quote
-> issuing active same-tenant Expert
-> persisted immutable Shipment owner
-> Shipment authorization
-> Shipment Documents management
-> Control Tower scope and owner projection
```

Request reassignment was exercised after Shipment creation and did not alter
any downstream ownership or access. The prior P1 blocker is therefore closed
by implementation evidence rather than by waiver or scope reduction.

## W. Remaining Risks

- Production history was not inspected. A deployment-time migration may fail
  safely on ambiguous or contradictory historical rows and require explicit
  data-owner adjudication before retry.
- An inactive/revoked fixed owner is denied. Operational continuity remains
  same-Organization Admin/Manager oversight; no automatic replacement or
  reassignment workflow exists.
- PostgreSQL performance measurements are bounded workstation evidence through
  500 active Shipments, not an infinite-scale or Production SLA claim.
- The known frontend chunk-size/Browserslist advisories remain unrelated and
  non-blocking.
- Product Acceptance Retry, deployment, Production validation, and modular
  architecture work remain separate goals.

## X. Verdict

```text
FIXED_SHIPMENT_OWNER_STATUS=CLOSED
ADR047_IMPLEMENTATION_STATUS=COMPLETE
P1_FIXED_OWNER_DEMO_BLOCKER=CLOSED
ONE_TRANSPORT_EXPERT_PER_OPERATIONAL_SHIPMENT=YES
SHIPMENT_RESPONSIBLE_EXPERT_IS_FIXED=YES
SHIPMENT_EXPERT_REASSIGNMENT_WORKFLOW=NO
NEW_ACCEPTED_QUOTE_SHIPMENT_FIXED_OWNER=YES
NEW_DIRECT_SHIPMENT_FIXED_OWNER=YES
REQUEST_REASSIGNMENT_TRANSFERS_SHIPMENT_OWNERSHIP=NO
REQUEST_REASSIGNMENT_TRANSFERS_SHIPMENT_ACCESS=NO
REQUEST_REASSIGNMENT_CHANGES_CONTROL_TOWER_OWNER_SCOPE=NO
REQUEST_REASSIGNMENT_TRANSFERS_SHIPMENT_DOCUMENT_MANAGEMENT=NO
ACCEPTED_QUOTE_OWNER_SOURCE=ACCEPTED_QUOTE_ISSUER
HISTORICAL_OWNER_GUESSING_ALLOWED=NO
ADMIN_MANAGER_SHIPMENT_OWNER_SUBSTITUTION=NO
CONTROL_TOWER_SCALABILITY_CHANGED=NO
DOCUMENTS_PRODUCT_CONTRACT_CHANGED=NO
QUOTE_COMMUNICATION_BEHAVIOR_CHANGED=NO
CARGO_OPTIONALITY_CHANGED=NO
COMBINED_TRANSPORT_BEHAVIOR_CHANGED=NO
DUAL_CALENDAR_BEHAVIOR_CHANGED=NO
MT3_PUBLIC_TRACKING_BEHAVIOR_CHANGED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
DEPLOYMENT_PERFORMED=NO
FIXED_SHIPMENT_OWNER_SCHEMA_DECISION=ADDITIVE_MIGRATION_REQUIRED
REFERENCE_IMPACT_FINAL=UPDATE_REQUIRED
```

PASS — ADR-047 FIXED SHIPMENT OWNER CLOSURE COMPLETE

# Golden Contract Freeze — Phase A — 2026-09-19

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Starting branch | `codex/golden-production-20260921` |
| Phase A branch | `codex/golden-contract-freeze-phase-a` |
| Starting HEAD | `2b95c35acc12e1ba28c390a125eb51f46af7dd4b` |
| Starting cleanliness | clean |
| Golden application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` |
| Engineering base | `b48e51c8d0eda00bcc7582b68da85528b14547d2` |
| Golden certification evidence | `0a6f1d368d0c266657188960e0507ff6d9039f59` |
| Database head | `20260921_shipment_evidence_ownership` |

All four required commits were present as commit objects. The Phase A branch was created directly from the required starting HEAD. The donor repositories were not modified.

## B. Contract Inventory

The machine-readable ledger is `docs/operational/evidence/golden-contract-freeze-phase-a-20260919.json`.

| Contract | Coverage | Frozen Golden behavior |
| --- | --- | --- |
| Application shell, routing, deep links, catch-all | STRENGTHENED | Exact 26-route inventory, route ordering, malformed-auth redirect, tenant requirement for operational routes |
| Navigation and role/capability visibility | STRENGTHENED | Exact operational links for read/create/OIP/dashboard permissions; tenant customer link only for Organization Admin |
| Authentication/session continuity | EXISTING | Missing/malformed/expired authentication denial, canonical redirects, session revocation and no token disclosure |
| Tenant, role and assigned-work authorization | EXISTING | Platform/Organization/Expert boundaries, same-tenant scope, unrelated/reassigned/revoked/inactive denial |
| Customer request workflow | EXISTING | Current create, opaque identity, request/detail/summary, transport, optional cargo, quote, tracking and evidence projections |
| Expert workflow | STRENGTHENED | Current list/detail shapes, assignment/referral, SLA, unread, mutation and immediate reassignment revocation |
| Admin workflow | EXISTING | Admin read/report/assignment/user-management behavior and organization-context checks |
| Shipment Detail | STRENGTHENED | Exact top-level shipment graph and source disclosure fields plus existing route/history/cargo/economics/document UI behavior |
| Request list/counter consistency | NEW CHARACTERIZATION | Same assignee/status scope through creation, pagination, transition and reassignment |
| Geography/reference data | EXISTING + INTENTIONAL FUTURE CHANGE | Current governed two-country/four-location snapshot, Iran destinations, ports/airports and stable identities; breadth changes in Phase B |
| Logistics/private points | EXISTING | Active same-tenant selection, wrong-tenant/inactive denial, bounded projection and immutable snapshot |
| Quote/economics/currency | STRENGTHENED + INTENTIONAL FUTURE CHANGE | Accepted/declined only; request remains `quoted`; response audit/unread/replay/conflict and economics authority; EUR bounded change later |
| Tracking/timeline/history | EXISTING + INTENTIONAL FUTURE CHANGE | Canonical units/events, occurred/recorded time, safe visibility, ordering and legacy add-unit fail-closed |
| Documents/evidence | STRENGTHENED + INTENTIONAL FUTURE CHANGE | Private ownership/version/audit plus current single-selection replacement UI; batch/retry policy deferred |
| Dates/time/localization | EXISTING + INTENTIONAL FUTURE CHANGE | Assignment event is distinct from request creation; current UTC/local-date/Persian behavior; calendar policy deferred |
| Numeric presentation | EXISTING + INTENTIONAL FUTURE CHANGE | Current quantity decimals/grouping/zero behavior and excluded identifier consumers; shared formatter comes later |
| Database/migrations | EXISTING | Immutable 97-revision, one-base/one-head graph and explicit non-auto-migrating runtime |
| Windows launcher/release | EXISTING | Canonical cmd/PYTHONPATH/cwd/release-Python/approved-launcher/Waitress chain and refusal rules |

## C. Tests Added or Strengthened

Only test code was changed:

- `src/tests/App.routing.test.tsx`: exact complete route inventory and catch-all-last contract.
- `src/tests/components/OperationsNav.test.tsx`: exact permission-driven navigation inventory for Organization Admin and Expert, including customer-link exclusion.
- `src/tests/components/CaseDocumentsTab.test.tsx`: current one-file selection and `replace=true` behavior when an active file exists, including a requirement whose backend cap is greater than one.
- `backend/tests/test_expert_assignment_referral_contract.py`: transaction-level count/list scope through a new assigned request, status transition, pagination and reassignment.
- `backend/tests/test_customer_quote_response.py`: accepted and declined responses both leave the Golden request status as `quoted`.
- `backend/tests/test_operational_vertical_slice.py`: exact Shipment Detail top-level payload and source field-disclosure inventory.

No product code, migration, fixture framework, snapshot framework, or donor runtime file was added.

## D. Current Golden Behavior vs Future Remediation

Golden invariants frozen here include the shell and all current routes; authentication and tenant/assignment fences; request and shipment identities; current list/detail/status behavior; Shipment Detail payload and operational provenance; accepted/declined quote behavior; canonical tracking units/events; private evidence ownership; governed reference identities and private points; existing timestamp/localization behavior; current numeric semantics; the database head; and the certified launcher topology.

The following are `GOLDEN_CURRENT_BEHAVIOR + FUTURE_CONTROLLED_REMEDIATION_REQUIRED`:

- Geography breadth is currently two countries and four international locations. Phase B may reconcile the approved FWD-02 catalog without a migration.
- Request intake remains scalar and currently permits optional cargo in existing paths. Multimodal and mandatory-cargo rules require product decisions.
- Count/list semantics are now frozen; Phase B may introduce a canonical shared query for additional cards.
- Quotes currently accept only `accepted` or `declined`; either response leaves the request `quoted`. EUR is a bounded Phase B change, while negotiating/reject transitions remain decision-dependent.
- The canonical tracking model remains authoritative and the retired legacy add-unit write fails closed. Later UX/provenance work must not revive it.
- The document backend supports multiple immutable rows, while the current case UI selects only `files[0]` and treats any active requirement file as replacement. Append/version/batch/partial-failure/lost-response rules remain deferred.
- Current calendar/timezone/localization behavior is preserved. A per-surface Jalali/Gregorian policy remains undecided.
- Numeric formatting is currently distributed. A shared formatter may be introduced later, but identifiers, phone numbers, tracking codes, vehicle references and UUIDs must remain excluded.

## E. Authorization Contract

- Unauthenticated requests are rejected by protected backend and frontend boundaries.
- Platform Admin does not implicitly receive organization-scoped operational access.
- Organization Admin operates only inside the current organization context.
- Expert private reads are governed by current assignment/responsibility and active membership, not historical capability or remembered IDs.
- Reassignment immediately revokes the former Expert's request, tracking and derived shipment access.
- Cross-tenant, unrelated, inactive and revoked actors do not gain access through guessed numeric, UUID or child-resource identifiers.
- Customer/public projections omit private audit, raw notes, internal document storage and unrelated tenant data.

## F. Frontend Shell Contract

The Golden shell exposes exactly 26 routes, including public information, customer request/tracking, Expert list/detail, CRM, Admin/customer maintenance, operational list/new/detail/work queue/current Golden control-tower, dashboards/builder, intelligence, execution units, verification and the final `*` not-found route. Operational routes retain authentication plus organization-context guarding. CRM retains its explicit role allowlist. Admin routes retain AdminRoute. Expert/CRM/Admin operational screens retain the Persian-only wrapper where present.

The operational navigation is capability driven. `operational_shipment.read` exposes shipment list and the existing Golden control-tower link; `oip.read` exposes work queue; `personal_dashboard.read` exposes dashboards; create permissions expose new operation; only tenant customer-maintenance authority exposes customers. Future Control Tower work may append/reconcile within these seams but cannot replace `App.tsx`, `OperationsNav.tsx`, or Golden Shipment Detail.

## G. Operational Contract

Shipment Detail retains exact identity, source, customer, current-route provenance, route plan/legs, milestone evidence, open work, recent events and audit-summary fields. Its related focused suites continue to protect route authoring, occurrence time, replan/correction/verification, execution units, cargo allocations, conditions, economics, external references, evidence/documents, logistics points and unified history.

Quotes remain accepted/declined with same-response replay, conflicting-response refusal, expiration checks, opaque customer capability and audit/unread facts. Tracking retains canonical execution units, safe customer projection and occurred/recorded semantics. Evidence retains tenant/assignment authorization, private storage, validation, audit and immutable version history. Private logistics points remain active-same-tenant-only with safe snapshots.

## H. Database Contract

```text
DATABASE_HEAD = 20260921_shipment_evidence_ownership
MIGRATION_FILES_CHANGED = NO
PRODUCT_MIGRATION_ADDED = NO
```

The repository migration graph remains 97 immutable revisions with one base and one head. `git diff` against the Phase A parent for `backend/migrations` was empty. A disposable local SQLite database stamped at the Golden head returned `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=no` for both `current` and `check`. The focused runtime/version-table gate passed 30 tests.

The historical from-base chain is not SQLite-portable and no local PostgreSQL service was available; Phase A therefore relies on the already certified graph/package equivalence plus the unchanged PostgreSQL-gated suites, which remain environment-skipped rather than represented as newly executed PASS.

## I. Deployment Contract

No release engineering file changed. The local launcher model passed:

```text
TASK_TRANSFORMATION_PRESERVES_LAUNCHER=PASS
EXECUTE_ROLLBACK_LISTENER_COMMAND_GATES=PASS
LAUNCHER_CHAIN_MODEL=PASS
DIRECT_WAITRESS_TASK_ASSUMPTIONS=0
```

The canonical chain remains Scheduled Task -> system `cmd.exe /d /c` -> explicit release `PYTHONPATH` and cwd -> release-local Python -> approved external `phase1b_production_cutover_runtime.py serve` -> explicit external env/repo/host/port/log -> release-local Waitress child.

The 39 release-builder/tooling tests passed. The separate real-process rerun could not start because this source-only worktree does not contain `release-candidates/Forwarder-Operational-Workspace-Production-CERTIFIED/artifact/runtime/python.exe`; it failed at its fixture precondition before launching any process. The prior Golden certification executed and passed that exact real-runtime test against the preserved package. Because no product, release script, dependency input or launcher file changed in Phase A, this is classified as an environment/fixture absence, not a product regression. No Production fallback was attempted.

## J. Full Qualification Results

| Gate | Result |
| --- | --- |
| Focused frontend characterization | PASS — 3 files, 12 tests |
| Focused backend characterization | PASS — 11 tests |
| Backend full suite | PASS — 1,047 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failures |
| Frontend full suite | PASS — 57 files, 283 tests |
| TypeScript | PASS — `npx tsc --noEmit` |
| Frontend production build | PASS — 2,536 modules; Golden asset names/sizes reproduced; no tracked `dist` delta |
| ESLint | PASS — 0 errors, 13 historical warnings |
| Migration/runtime focused suite | PASS — 30 tests |
| Migration graph/files | PASS — one expected head; no migration diff from Phase A parent |
| Disposable DB current/check | PASS — expected head, `pending=no` |
| Release-builder/tooling | PASS — 39 tests |
| Launcher contract model | PASS — all four required markers |
| Real packaged-runtime launcher rerun | ENVIRONMENT NOT AVAILABLE — certified runtime fixture absent from this source-only worktree; prior unchanged-input certification remains authoritative |

## K. Scope Integrity

```text
FWD_RUNTIME_IMPORTED=NO
CONTROL_TOWER_IMPORTED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

No deploy, push, merge, cherry-pick, RC build, Production endpoint, Production environment file, Production database, Production process, Scheduled Task, IIS site, credential or secret was accessed or changed.

## L. Remaining Risks

- PostgreSQL-only tests remain skipped without an owned disposable PostgreSQL service. This is the same known environmental limitation recorded by Golden certification and becomes mandatory before any schema-bearing phase or final RC.
- The real packaged-runtime launcher process test requires the allowlisted Windows runtime ZIP/package, which is not present in this source-only worktree. Launcher/release inputs are unchanged and the certified prior evidence plus current model tests remain valid; final RC qualification must restore the owned runtime fixture and rerun the real process gate.
- Product decisions for multimodal requests, mandatory cargo, quote negotiating/reject transitions, per-surface calendar policy, document append/retry semantics and notification recipient/channel policy remain intentionally unresolved. None blocks the first bounded Phase B geography slice.

## M. Verdict

PASS — GOLDEN REGRESSION CONTRACTS FROZEN

## N. Next Goal

Execute only the first approved Phase B slice: governed geography reconciliation.

- Baseline: this Phase A commit on `codex/golden-contract-freeze-phase-a`; require a clean worktree and the exact Phase A parent identity before starting.
- Goal: replace the intentionally small Golden international geography snapshot through a controlled, idempotent reconciliation of the approved FWD-02 catalog while preserving Golden identity, authorization, inactive-record and round-trip contracts.
- Donor evidence: runtime/catalog commit `4b06ed039d72c15f10d2f114fed07fc2fdef457b`; qualification-only commit `1714118340943f1dbbf99e4b25edc9ef41f817e6`. Use as reviewed semantic/test donors only; do not merge or cherry-pick.
- Allowed scope: a new governed catalog/builder if required; narrowly reconciled Golden location routes/services and location selectors/forms; focused tests and evidence. Preserve private logistics-point ownership and safe projections.
- Schema: no Alembic migration. Data reconciliation must be explicit, idempotent and non-destructive, with dataset identity/hash/count evidence; do not reactivate inactive identities or reuse IDs.
- Required behavior: Italy and Norway coverage, broad Iran coverage, pagination/search, stable identity, inactive-record preservation, create/review/reopen round trip, bounded large-catalog performance, and honest Persian-source fallback labeling.
- Gates: relevant Phase A geography/private-point/auth contracts before and after; focused backend/frontend geography tests; disposable reconciliation rehearsal; full backend/frontend suites; typecheck/build/lint; single database head; no unexplained test-count reduction.
- Stop conditions: catalog provenance/hash is ambiguous; reconciliation would delete/rekey/reactivate referenced rows; Persian fallback would be presented as a verified translation; tenant/private-point disclosure broadens; agreed performance budget is exceeded; any migration or unrelated product decision becomes necessary.
- Forbidden: FWD cumulative page/service replacement, Control Tower work, notification work, transport/cargo/quote/tracking/document changes, schema changes, Production access, secrets, deploy, push or beginning a second Phase B slice.

Do not execute this next goal as part of Phase A.

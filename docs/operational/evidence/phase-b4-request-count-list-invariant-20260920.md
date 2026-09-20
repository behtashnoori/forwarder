# Phase B — Slice 4 — Canonical Request Count/List Invariant — 2026-09-20

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/phase-b3-existing-transport-summary` |
| Slice branch | `codex/phase-b4-request-count-list-invariant` |
| Starting HEAD / B3 commit | `d1dd6b60abc27846d563816c34b9aa4de190161a` |
| Required parent / B2 commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| Starting cleanliness | clean |
| Golden application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` |
| Engineering base | `b48e51c8d0eda00bcc7582b68da85528b14547d2` |
| Phase A commit | `953a67ff5820864c08bc8727f34f49ed66237527` |
| B1 geography commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| B2 numeric commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| B3 transport commit | `d1dd6b60abc27846d563816c34b9aa4de190161a` |
| Database head | `20260921_shipment_evidence_ownership` |

The required Phase A Markdown/JSON evidence, B1/B2/B3 evidence, and controlled integration plan were present and read before implementation. The repository had one base and one head. A disposable SQLite database stamped at that head returned `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=no`. No prerequisite differed.

Read-only donor inspection was limited to the request count/list portions of `D:\1-webapp\15-forwarder` commit `d10f6e003a684626cdb382ba25d6f5bd329150f2`. Reused semantics were a shared pre-pagination scope, database-side counts, `total_visible`, and search-aligned frontend refresh. Transport intent, schema, migrations, cumulative pages, status changes, and all other donor behavior were rejected.

## B. Existing Count/List Inventory

| Path | Classification | Result |
| --- | --- | --- |
| `assigned_request_scope` | `CANONICAL_POPULATION` | Existing current identity, active membership, active organization, tenant, authority/capability, and current assignment predicate. Preserved as the authorization root. |
| `canonical_request_population` in `expert_request_list_service` | `CANONICAL_POPULATION` | New composition point for authorization plus assigned-to, status, priority, and search predicates before ordering, count, or pagination. |
| `GET /api/expert/requests` | `DERIVED_LIST` | Uses the canonical population, deterministic ordering, database pagination, and the paginator's full population total. |
| `GET /api/expert/dashboard/kpis` | `DERIVED_COUNT` | Previously a separate legacy query; now one conditional SQL aggregate over the same canonical population with status intentionally removed before per-status counts. |
| `ExpertConsole.tsx` request cards and tab badges | `DERIVED_LIST` / `DERIVED_COUNT` | Consumes server list rows, pagination semantics, canonical KPI counts, and `total_visible`; refresh and search re-query both views. |
| `admin_shipment_request_service` list | `DIFFERENT_BUSINESS_METRIC` | Admin panel population and response contract; not an Expert counter source and unchanged. |
| `admin_dashboard_service` summaries | `DIFFERENT_BUSINESS_METRIC` | Organization reporting metrics with different statuses/time windows; unchanged. |
| `expert_workload_service` | `DIFFERENT_BUSINESS_METRIC` | Assignment workload for routing/user management, not the Expert console status tabs; unchanged. |
| unread notification count | `DIFFERENT_BUSINESS_METRIC` | Counts notification records, not requests; unchanged. |
| unassigned intake/admin queues | `OUT_OF_SCOPE` | Deliberately not part of current assigned Expert visibility. |
| former KPI route-local query | `LEGACY` | Removed. It filtered only `assigned_to` for non-admins and was unscoped for admins. |

`closed_today` remains explicitly classified as a different time-bounded metric: it is labeled “closed today,” shares the authorized base, and adds the preserved Golden terminal-status/creation-date predicate. It is not redefined as the full closed-tab population.

## C. Root Cause

Before this slice, list rows and `pagination.total` called `assigned_request_scope`, which requires an active persisted identity, exactly one active membership in an active organization, tenant-owned requests, the existing authority/capability rule, and current assignment for an Expert.

The KPI endpoint did not use that predicate. Its concrete logic was:

- non-admin: `ShipmentRequest.assigned_to == current_user["id"]` only;
- admin: no tenant, organization, membership, ownership-scope, or capability predicate at all;
- status counts: separate route-local `.count()` queries.

Consequently a revoked/inactive membership could receive aggregate counts even when its list was empty, and an Organization Admin KPI query could count requests outside the current tenant while the list remained tenant-fenced. The common active-Expert case happened to agree, which is why the Phase A mutation characterization passed, but the implementation was not authorization-equivalent.

The frontend also refreshed only the list from the visible refresh button and did not send its search predicate to the KPI endpoint. It could therefore display a refreshed/filtered list beside a stale or differently filtered counter.

## D. Canonical Population Contract

For one authenticated actor and filter set, the population is exactly:

1. persisted active user identity;
2. exactly one active operational membership in an active organization;
3. request `ownership_scope == "TENANT"`;
4. request `operational_organization_id` equals the membership organization;
5. ordinary Expert: `assigned_to` equals the current actor ID;
6. Organization Admin: existing `request.read` capability, with tenant scope retained;
7. Platform Admin or any invalid/inactive/revoked identity: empty population;
8. optional existing filters: assigned-to, status (single or comma-separated), priority, and search over phone/customer/cargo description.

List ordering and pagination are applied only after those predicates. KPI status counters start from the same authorized/filter population with only the caller's status filter omitted, then add the exact preserved status predicate for each counter. No historical assignment participates.

## E. Implementation

| Runtime file | Bounded change |
| --- | --- |
| `backend/services/expert_request_list_service.py` | Adds the canonical population builder, separates predicates from ordering, derives all KPI counts in one SQL aggregate, adds ID tie-breaking for stable pages, and eager-loads the displayed assignee. |
| `backend/routes/expert_console.py` | Replaces the legacy route-local KPI queries with the shared service population. |
| `src/lib/api.ts` | Adds `total_visible` to the KPI contract and permits the existing search filter on KPI reads. |
| `src/pages/ExpertConsole.tsx` | Uses server `total_visible`, sends search to both reads, and refreshes list and counts together. |

Focused coverage was added to `backend/tests/test_expert_assignment_referral_contract.py` and `src/tests/pages/ExpertConsole.count-list.test.tsx`. No status mutation, assignment mutation, schema, migration, notification, geography, numeric, transport, date, quote, or Control Tower runtime was changed.

## F. Create Invariant

The focused transaction test begins with one eligible new request, inserts five additional eligible current-assignment rows, one same-tenant row assigned elsewhere, and one foreign-tenant row. The Expert list total and KPI `new`/`total_visible` increase from one to six; the unrelated and foreign rows affect neither view.

Public intake semantics remain unchanged: unowned intake is not fabricated into the assigned Expert population. Once an existing Golden flow creates a tenant-owned, currently assigned, eligible new row, the next list/count read observes it without another lifecycle transition or cache invalidation.

## G. Transition Invariant

The existing status endpoint changes one eligible row from `new` to `in_progress`. The next reads prove the new-list total and new counter both decrease from six to five, while the in-progress list and counter both increase from zero to one. No status name, transition, or taxonomy changed.

## H. Reassignment Invariant

The existing Admin assignment endpoint remains authoritative and retains its Golden behavior of changing the request to `assigned`. After reassignment:

- the old Expert loses one `total_visible` row and direct detail access returns 403;
- the new Expert gains one `total_visible` row and one assigned-list row;
- the new Expert's `new` count does not increase, because Golden reassignment makes the request `assigned`, not `new`.

This preserves rather than reinterprets assignment semantics.

## I. Pagination Invariant

The test creates equal-timestamp rows and proves page 1 and page 2 are stable and disjoint. Ordering remains the existing selected column/direction, with request ID added only as the deterministic tie-breaker. With six matching new requests:

- `per_page=2`, pages 1 and 2: `pagination.total=6`;
- `per_page=3`: `pagination.total=6`;
- page 99: zero returned rows and `pagination.total=6`.

Pagination changes returned rows only. The population count remains database-side and pre-pagination.

## J. Refresh / Frontend Consistency

The backend test repeats identical list and KPI reads and receives identical state. The frontend test proves initial load, the visible refresh button, and a changed search all request list and KPI data together. Status mutations continue to refetch KPIs while the existing active-tab change refetches the corresponding list. Visibility restoration already refetched both and remains unchanged.

The UI no longer derives total visibility by summing a partial set of status cards; it renders backend `total_visible`. It also does not compute a status total from the current page length.

## K. Authorization / Aggregate Privacy

The focused test proves:

- a foreign-tenant row assigned to the same numeric Expert does not appear and does not change any counter;
- a same-tenant row assigned to another Expert is excluded for the first Expert;
- an Organization Admin with the existing `request.read` capability sees only its tenant in both list and count;
- reassignment immediately removes the old Expert's list/count/detail authority;
- revoking the Expert membership yields an empty list and zeroed aggregates, disclosing no inaccessible count.

Count is therefore governed by the same fail-closed SQL predicate as rows, not by frontend filters or a broader dashboard query.

## L. Performance

KPI computation is one database conditional-aggregate query over the canonical SQL population: one total plus status/SLA expressions. It does not load request rows into Python and replaces six separate `.count()` round trips. The list remains database-paginated; the displayed assignee is eager-loaded to avoid the prior per-row assignee lookup introduced during payload construction. Source/query inspection confirms authorization and filters are applied before aggregate/pagination, and focused first/middle/beyond-page tests exercise the strategy. No hard SLA exists, so no invented timing threshold is claimed.

## M. Regression Status

```text
GCF-A-001 = PASS
GCF-A-002 = PASS
GCF-A-003 = PASS
GCF-A-004 = PASS
GCF-A-006 = PASS
GCF-A-011 = PASS
GCF-A-012 = PASS

PHASE_B1_GEOGRAPHY = PASS
PHASE_B2_NUMERIC = PASS
PHASE_B3_TRANSPORT_SUMMARY = PASS
```

The focused Phase A/B1/B2/B3 regression selection passed 90 backend tests and 98 frontend tests. Full suite counts increased by exactly one backend and one frontend test from B3; there was no unexplained reduction.

## N. Tests

| Gate | Exact result |
| --- | --- |
| Expert assignment/request focused suite | PASS — 22 passed |
| New Expert Console frontend test | PASS — 1 passed |
| Focused Phase A + B1/B2/B3 backend regression | PASS — 90 passed |
| Focused Phase A + B1/B2/B3 frontend regression | PASS — 13 files, 98 tests |
| Full backend suite | PASS — 1,053 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failed |
| Full frontend suite | PASS — 62 files, 299 tests |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,538 modules; isolated output removed after verification; no tracked `dist` delta |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Migration/runtime focused suite | PASS — 32 passed |
| Alembic graph/current/check | PASS — one base, one expected head, disposable current equals head, `pending=no` |
| Diff integrity | PASS — `git diff --check`; only Git line-ending notices, no whitespace errors |

The 93 PostgreSQL/environment-dependent skips and one expected xfail are unchanged and are not represented as executed PASS. No Production fallback was attempted.

## O. Database Contract

```text
DATABASE_HEAD =
20260921_shipment_evidence_ownership

MIGRATION_ADDED =
NO

MIGRATION_MODIFIED =
NO

PENDING_MIGRATION =
NO
```

There is no diff under `backend/migrations` from the slice parent.

## P. Scope Integrity

```text
REQUEST_STATUS_TAXONOMY_CHANGED=NO
ASSIGNMENT_SEMANTICS_CHANGED=NO
TRANSPORT_BEHAVIOR_CHANGED=NO
GEOGRAPHY_REGRESSED=NO
NUMERIC_PRESENTATION_REGRESSED=NO
DATE_TIME_BEHAVIOR_CHANGED=NO
NOTIFICATION_WORK_IMPORTED=NO
CONTROL_TOWER_IMPORTED=NO
OTHER_FWD_FEATURE_IMPORTED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

No deploy, push, merge, cherry-pick, RC build, Production endpoint, Production environment, Production database, process, task, credential, or secret was accessed or changed. `D:\1-webapp\15-forwarder` was used read-only.

## Q. Remaining Risks

- Count and list are separate HTTP reads, so a legitimate concurrent mutation committed between them can briefly produce different snapshots. Both reads use the same predicates and the next paired refresh converges; cross-endpoint transaction snapshots were not introduced because that would expand the architecture beyond this slice.
- Offset pagination is deterministic for a fixed population, but concurrent inserts before the current page can shift later offsets. Cursor pagination was not introduced because the Golden contract is offset/page-based.
- `closed_today` retains the existing creation-date interpretation. It is a separately labeled metric, not the full closed-list count; changing its business time definition requires a separate approved decision.

## R. Verdict

PASS — CANONICAL REQUEST COUNT/LIST INVARIANT COMPLETE

## S. Next Goal

Execute exactly one next approved Phase B slice: **EUR quote support**.

Start from this clean B4 commit. Add only EUR support to the existing Golden quote create/read/respond and presentation paths while preserving the accepted/declined-only response model, the current `quoted` request-state effect, tenant/assignment authorization, shared numeric presentation, existing transport/geography behavior, and the database lineage. Use only bounded FWD-05 EUR semantics/tests, add no unrelated quote lifecycle states, notification work, documents, tracking, Control Tower, or another Phase B slice. This goal is derived from the controlled integration plan and is not executed here.

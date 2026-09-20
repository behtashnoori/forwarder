# Phase B — Slice 6 — Retired Tracking-Action Removal — 2026-09-20

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/phase-b5-eur-quote-support` |
| Slice branch | `codex/phase-b6-retired-tracking-action-removal` |
| Starting HEAD / B5 commit | `49e2ceecee6b6ddbead7ae735fe15ecb63ed4869` |
| Required parent / B4 commit | `02acad646e2349296653bf0cf0bc5fe38519fb98` |
| Starting cleanliness | clean |
| Golden application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` |
| Phase A commit | `953a67ff5820864c08bc8727f34f49ed66237527` |
| B1 geography commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| B2 numeric commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| B3 transport commit | `d1dd6b60abc27846d563816c34b9aa4de190161a` |
| B4 count/list commit | `02acad646e2349296653bf0cf0bc5fe38519fb98` |
| B5 EUR commit | `49e2ceecee6b6ddbead7ae735fe15ecb63ed4869` |
| Database head | `20260921_shipment_evidence_ownership` |

The required Phase A Markdown/JSON evidence, B1/B2/B3/B4/B5 evidence, and controlled integration plan were present and read before implementation. The exact required branch, HEAD, parent, clean state, one-base/one-head 97-revision graph, and disposable `pending=no` result matched. The slice branch was created directly from the required B5 commit. The database proof used a disposable SQLite file with environment-file loading disabled; neither the user-local development database nor Production was used.

## B. Tracking Action Inventory

| Classification | Current path | Decision |
| --- | --- | --- |
| `CANONICAL` | `/operations/projects/:projectId/units`, `ExecutionUnits.tsx`, and `/api/v2/projects/:project_id/execution-units` | Project-scoped creation/read/update remains the primary execution-unit workflow. |
| `CANONICAL` | `POST /api/v2/projects/:project_id/execution-units/:unit_id/events` | Canonical event creation remains unchanged, including permission, tenant, version, visibility, idempotency, and occurred/recorded semantics. |
| `CANONICAL` | Operational Shipment Detail `ShipmentCargoItems.tsx` and `/canonical-transport-units` | Shipment-scoped UI continues to create a real `ExecutionUnit` through the existing canonical service and continues to display canonical units and allocations. |
| `RETIRED` | Expert Request Detail card labelled `افزودن بخش قابل رهگیری` / `Add transport unit` | Removed. It called the legacy request-tracking add-unit endpoint, which cannot supply canonical execution identity or project lineage and already fails closed. |
| `READ_ONLY` | Expert Request Detail unit cards; Customer/Public Tracking; Project Tracking; unified shipment history | Preserved. Current units, events, timeline, route/location snapshots, and customer-safe fields remain visible under existing rules. |
| `INTERNAL` | Legacy metadata/update compatibility calls for an already mapped historical unit | Preserved. They write only through one exact same-tenant canonical mapping and otherwise fail closed; this slice does not redesign compatibility. |
| `ADMIN_ONLY` | Tracking location reference maintenance | Unchanged and outside this UI-removal slice. |
| `OUT_OF_SCOPE` | Legacy cargo transport-unit endpoint and historical compatibility storage | No current UI creates through this endpoint; backend historical behavior remains untouched. |

Repository-wide reachability inspection covered buttons, forms, empty states, menus, responsive branches, routes, and API helpers. The retired add-unit form had one current UI exposure: the shared responsive `TrackingManagementCard` in Expert Request Detail. No separate desktop/mobile component, overflow menu, keyboard command, deep-link component, or alternate role branch exposed it.

## C. FWD-06 Donor Analysis

Read-only donor inspection used implementation commit `71414b6af5a750f2f39682407f2315b540a86322`, integrity/qualification commit `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`, and closure commit `c85ebec1b1d49599b6ebfe0811367f310932b7ac` in `D:\1-webapp\forwarder-dev`.

Relevant inspected donor files/scenarios were:

- `src/pages/RequestDetail.tsx`
- `src/pages/PublicTracking.tsx`
- `src/lib/api.ts`
- `backend/routes/expert_console.py`
- `backend/services/multi_unit_tracking_service.py`
- `backend/tests/test_fwd06_m1_time.py`
- `backend/tests/test_fwd06_m1_postgresql.py`
- `scripts/uat/fwd06_browser_runner.mjs`
- `docs/operational/evidence/fwd-06-tracking-timeline/FINAL-DELIVERY-2026-09-16.md`

Reused only as scenario evidence were the distinction between internal mutation and customer-safe projection, authorization before tracking writes, stable timeline ordering, input/action reachability checks, and the need to preserve visible status/location history. Golden's canonical execution-unit/event model remained authoritative.

Explicitly rejected were the donor migration, five-field manual-time provenance, receipts/idempotency additions to the legacy path, manual-time UI, cumulative Request Detail/Public Tracking replacements, notification behavior, rollback machinery, and broader tracking redesign. No merge or cherry-pick occurred, no donor file was copied wholesale, and neither donor repository was changed.

## D. Retired Action

The retired action was the Expert Request Detail tracking card titled `افزودن بخش قابل رهگیری` / `Add transport unit`. When tracking was enabled it displayed free-text unit code, type, display name, and vehicle-reference controls and called `POST /api/expert/requests/:requestId/tracking/units` through `addTrackingUnit`.

That request lacks the canonical `ExecutionUnit` identity and project lineage. Golden therefore deliberately raises `LegacyWriteMappingError` and returns HTTP 409 with `code=LEGACY_WRITE_MAPPING` and `state=NEEDS_DECISION`; it does not create a legacy row.

This slice removed the entire card/form, its component state/import, and its now-unreachable frontend API helper. It did not replace the card with another business action. The zero-unit empty state now explicitly directs creation/management to the existing project execution-unit workflow instead of telling the Expert to add a legacy tracking subject locally.

## E. Canonical Tracking Path

Authorized users retain both existing canonical creation surfaces:

- Project Execution Units: `ایجاد بخش اجرایی`, unit list/detail, `ثبت به‌روزرسانی بخش`, canonical timeline, carrier, and cargo allocation.
- Operational Shipment Detail: `افزودن وسیله حمل` through `/canonical-transport-units`, canonical unit display, and cargo allocation.

Focused tests invoke both canonical create commands and the canonical event command. Existing backend execution-unit and tracking suites preserve permission, tenant, assignment, version, idempotency, ordering, and event projection behavior. No canonical runtime file changed.

## F. Customer Tracking

Customer/Public Tracking runtime and API projections did not change. The existing public tests prove customer-visible timeline/read behavior, opaque tracking identity, and absence of internal fields/actions. The full backend/frontend suites preserve event ordering, visible-only projection, safe locations, and read-only Customer behavior.

## G. Expert Tracking

Expert Request Detail still loads and renders existing units, allows supported metadata/event operations only where the legacy record has an exact canonical mapping, and displays status/location/history. The canonical Project Execution Units and Shipment Detail actions remain available. Focused UI tests prove mapped unit reads and update controls survive while the retired create form and unit-code input do not render.

Authorization was not broadened. Existing assigned-work and execution-unit suites prove unrelated, cross-tenant, revoked, and unauthorized actors do not gain actions or writes.

## H. Backend Fail-Closed Contract

No backend runtime change was needed. `POST /api/expert/requests/:requestId/tracking/units` remains present for historical compatibility and remains intentionally fail-closed with HTTP 409. `test_legacy_add_unit_fails_closed_without_creating_a_legacy_row` passed. This report does not claim that the backend route was removed.

## I. Responsive / Alternate Reachability

Expert Request Detail uses one `TrackingManagementCard` DOM path for desktop and responsive layouts; the retired card was removed from that shared branch rather than hidden by CSS or breakpoint. The focused test renders the enabled and zero-unit conditional branches, proves no add-unit button or unit-code input exists, and verifies the empty state points to the canonical workflow. Source inventory found no menu, modal, mobile duplicate, route, or other component calling the removed helper.

## J. Product Changes

| Runtime file | Bounded change |
| --- | --- |
| `src/pages/RequestDetail.tsx` | Removes the retired add-unit card, handler reachability, and local form state while preserving reads, mapped edits, and mapped event updates. |
| `src/lib/api.ts` | Removes the frontend-only `addTrackingUnit` helper; backend compatibility remains unchanged. |
| `src/i18n.tsx` | Rewords the empty state in Persian and adds its English equivalent to direct users to the canonical project execution-unit workflow. |

Focused coverage changed or added:

- `src/tests/pages/RequestDetail.tracking-actions.test.tsx`
- `src/tests/pages/ExecutionUnitPages.test.tsx`
- `src/tests/components/CargoFoundation.test.tsx`

No backend runtime, model, migration, route, tracking projection, date/time, geography, numeric, transport, request count/list, quote, notification, document, or Control Tower file changed.

## K. Regression Status

```text
GCF-A-001 = PASS
GCF-A-002 = PASS
GCF-A-005 = PASS
GCF-A-007 = PASS
GCF-A-009 = PASS
GCF-A-011 = PASS

PHASE_B1_GEOGRAPHY = PASS
PHASE_B2_NUMERIC = PASS
PHASE_B3_TRANSPORT_SUMMARY = PASS
PHASE_B4_REQUEST_COUNT_LIST = PASS
PHASE_B5_EUR = PASS
```

The named Phase A/B1–B5/tracking regression selection passed 104 backend tests and 51 frontend tests. No prior runtime contract changed.

## L. Tests

| Gate | Exact result |
| --- | --- |
| Pre-change tracking/auth/execution backend baseline | PASS — 52 passed |
| Pre-change tracking/execution frontend baseline | PASS — 4 files, 16 tests |
| Final focused tracking/auth/execution backend | PASS — 52 passed |
| Final focused retired/canonical tracking frontend | PASS — 5 files, 20 tests |
| Focused Phase A + B1/B2/B3/B4/B5 backend regression | PASS — 104 passed |
| Focused Phase A + B1/B2/B3/B4/B5 frontend regression | PASS — 15 files, 51 tests |
| Full backend suite | PASS — 1,059 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failed |
| Full frontend inventory | PASS — 65 files, 305 tests, executed as 64 files/298 tests plus the 7 timezone tests in process-start timezone batches |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,539 modules transformed; isolated output outside the repository; no tracked `dist` delta |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Migration/runtime focused suite | PASS — 33 passed |
| Alembic graph/current/check | PASS — 97 revisions; one base; one expected head; disposable current equals head; two read-only status checks report `pending=no` |
| Migration delta | PASS — zero files changed under `backend/migrations` |
| Diff integrity | PASS — `git diff --check`; only Git line-ending notices |

B5 recorded 1,059 backend passes and 301 frontend tests. This slice changes no backend tests and adds four frontend tests, producing 1,059 backend passes and 305 frontend passes with no unexplained reduction.

On this Windows/Node runtime, `process.env.TZ` changes made after process start are not applied to JavaScript `Date`. Consequently the pre-existing `localDateTime.test.ts` cannot exercise Tehran and UTC cases in one process: a Tehran-started full run passed 304/305 and failed only its UTC assertion; a UTC-started full run passed 302/305 and failed only its three Tehran assertions. The authoritative frontend qualification ran the other 298 tests once, then ran six Tehran/invalid cases in an `Asia/Tehran` process and the UTC case in a `UTC` process; all 305 tests passed. No date/time source or test was changed, and the relevant Phase A date/time contract is therefore preserved rather than waived.

## M. Database Contract

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

The final disposable database was stamped at the repository head and read twice through the migration runtime: `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=no`. The graph remains 97 revisions with base `20240917_initial_schema`. The UAT CLI wrapper correctly rejects SQLite, so the final SQLite proof called the same read-only `revision_status` runtime directly with an explicit disposable URL; it did not fall back to any local or Production database.

## N. Scope Integrity

```text
RETIRED_TRACKING_ACTION_REACHABLE=NO
CANONICAL_TRACKING_PATH_CHANGED=NO
TRACKING_MODEL_CHANGED=NO
TRACKING_TIME_SEMANTICS_CHANGED=NO
CUSTOMER_TRACKING_DISCLOSURE_CHANGED=NO
NOTIFICATION_WORK_IMPORTED=NO
DOCUMENT_WORK_IMPORTED=NO
CONTROL_TOWER_IMPORTED=NO
OTHER_FWD_FEATURE_IMPORTED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

No deploy, push, merge, cherry-pick, RC build, Production endpoint, Production configuration, Production database, process, task, credential, or secret was accessed or changed. No second Phase B slice was started.

## O. Remaining Risks

- Stale external clients can still call the historical add-unit endpoint, but it remains deliberately fail-closed with the stable 409 mapping response and creates no row.
- Metadata and status-update compatibility controls remain visible for historical units only because Golden can delegate them to one exact canonical execution mapping. Unmapped, cross-tenant, or cross-root writes continue to fail closed. A future compatibility-retirement decision may remove those controls separately.
- The pre-existing Windows/Node process-timezone limitation requires the date/time test file to run in two process-start timezone batches on this host. It does not affect runtime code changed by this slice.

## P. Verdict

PASS — RETIRED TRACKING ACTION REMOVED

## Q. Next Goal

Execute exactly one separate approved slice: **Phase B — Slice 7 — Private-Point Selector Reachability**.

Start from the clean B6 commit. Make active same-tenant private logistics points reachable through the existing applicable selector flow while preserving inactive/wrong-tenant/unauthorized denial, immutable understandable location snapshots, Customer/public safe projection, governed global geography, and all Phase A/B1–B6 contracts. Add no migration, do not broaden disclosure or authority, do not redesign tracking/location models, and do not begin notifications, documents, Control Tower, or another phase. This next goal is derived from the controlled integration plan and was not executed here.

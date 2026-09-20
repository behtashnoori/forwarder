# Phase B7 — Private-Point Selector Reachability Evidence

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/phase-b6-retired-tracking-action-removal` |
| Slice branch | `codex/phase-b7-private-point-selector-reachability` |
| Starting HEAD / B6 commit | `b623f7fa7135caac69798def574556140f78191f` |
| Required parent / B5 commit | `49e2ceecee6b6ddbead7ae735fe15ecb63ed4869` |
| Starting worktree | clean |
| Phase A commit | `953a67ff5820864c08bc8727f34f49ed66237527` |
| B1 geography commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| B2 numeric commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| B3 transport commit | `d1dd6b60abc27846d563816c34b9aa4de190161a` |
| B4 count/list commit | `02acad646e2349296653bf0cf0bc5fe38519fb98` |
| B5 EUR commit | `49e2ceecee6b6ddbead7ae735fe15ecb63ed4869` |
| B6 tracking-action-removal commit | `b623f7fa7135caac69798def574556140f78191f` |
| Database head | `20260921_shipment_evidence_ownership` |

The required Phase A Markdown/JSON evidence, B1 through B6 evidence, and the controlled integration plan were present and read before implementation. The exact starting HEAD, parent, clean state, one-base/one-head 97-revision graph, and disposable `pending=no` result matched. The slice branch was created directly from B6. `D:\1-webapp\15-forwarder` and `D:\1-webapp\forwarder-dev` remained read-only references and were not changed.

## B. Existing Private-Point Architecture

`LogisticsPoint` is the existing tenant-owned point model. Its `organization_id` binds it to one operational organization; its opaque `public_id` is the governed selector/write identity; and `is_active`, the active point type, and the caller's active organization determine current selectability. Private warehouses, yards, loading points, depots, terminals, and similar facilities are ordinary rows in this model. This slice adds no model and changes no ownership.

The pre-existing `GET /api/internal/logistics-points/tracking-selector` seam already returned a bounded safe projection of active points from the authenticated actor's organization. It already rejected client-supplied `organization_id`, filtered inactive points and point types, and supported safe name/code search. Existing operational creation and route-authoring flows already consumed tenant logistics points. The reachability gap was the canonical execution-unit event form, while Request Detail had a private-only compatibility selector that was not reconciled with the global tracking-location reference choices.

Canonical event writes already accept `location.logistics_point_public_id`. The service resolves the point inside the execution unit's organization, requires an active point/type, and creates immutable `OperationalEventLocationEvidence` with the governed source identity and event-time display snapshots. The mapped legacy compatibility service delegates to that same canonical event evidence only when one exact same-tenant canonical mapping exists.

## C. Selector Inventory

| Selector / surface | Classification | B7 decision |
| --- | --- | --- |
| Public/request-intake worldwide `LocationForm` | `GLOBAL_ONLY`, `CUSTOMER_SAFE` | Unchanged. Tenant-private points are not added. |
| New Operation origin/destination facility selector | `PRIVATE_POINT_ALLOWED`, `INTERNAL_OPERATIONAL` | Existing private reachability preserved. |
| Route Authoring leg origin/destination selector | `PRIVATE_POINT_ALLOWED`, `INTERNAL_OPERATIONAL` | Existing private reachability preserved. |
| Route Authoring checkpoint geography selector | `GLOBAL_ONLY`, `INTERNAL_OPERATIONAL` | Unchanged; private facilities are intentionally not injected into checkpoint geography. |
| Canonical Execution Units event-location selector | `PRIVATE_POINT_ALLOWED`, `INTERNAL_OPERATIONAL` | Changed: the shared combined selector is now reachable before `POST .../events`. |
| Request Detail mapped compatibility event-location selector | `PRIVATE_POINT_ALLOWED`, `INTERNAL_OPERATIONAL` | Changed: reconciled onto the same combined selector. |
| Project logistics-network/configuration association UI | `OUT_OF_SCOPE` management/configuration | Unchanged; this is not an event-location picker. |
| Admin global/private logistics CRUD | `OUT_OF_SCOPE` | Unchanged. |
| Customer/Public Tracking | `CUSTOMER_SAFE` read-only | Unchanged; no private selector is mounted. |
| Historical shipment cargo-unit compatibility creation | `OUT_OF_SCOPE` / retired | Unchanged; B6 fail-closed behavior remains. |

## D. Product Behavior

The two changed selectors are:

1. the canonical project Execution Units “register update” location selector; and
2. the Request Detail update selector for an already mapped compatibility unit.

Both now use one `OperationalEventLocationSelector`. A user can search the existing bounded tenant selector and the existing global tracking-location reference catalog in one control. The UI groups organization points separately from global references and labels an ordinary tenant row as `نقطه خصوصی سازمان`; a materialized governed global adoption is labelled `نقطه مرجع شبکه سازمان`; a global tracking reference is labelled `مکان مرجع`. Manual location text remains available.

Selecting a private point produces a typed private selection and submits its exact opaque `public_id`: nested as `location.logistics_point_public_id` on the canonical event command, or as `logistics_point_public_id` on the mapped compatibility command. No tenant identifier, audit metadata, internal notes, or ownership field is exposed in the selector. Canonical timeline rendering now shows the persisted event-time location snapshot after save/read.

## E. Authorization

The selector continues to derive organization identity exclusively through the authenticated user's one active membership in one active organization. A frontend tenant override remains forbidden. The safe selector projection is available only to an actor holding one of the already-established logistics/operational command authorities that needs this point identity, including `execution_unit.update`; it does not grant write authority. Each write service independently revalidates tenant and active-point scope.

Focused evidence proves:

- an actor with `execution_unit.update` sees and searches the active point in the actor's own organization;
- a different organization's point is absent from the result;
- `?organization_id=...` is rejected with 403;
- a guessed cross-tenant `logistics_point_public_id` is rejected with 404 by the canonical write;
- an inactive point is absent and remains `is_active=False` in the database;
- deactivating the membership removes disclosure;
- deactivating the user identity removes disclosure with 401; and
- deactivating the organization removes disclosure with 403.

## F. Global vs Private Separation

Private points remain `LogisticsPoint` rows owned by one organization. They are not inserted into, remapped to, or returned by the B1 worldwide geography catalog. The shared UI makes two distinct calls and keeps two distinct typed values: tenant point `public_id` versus global tracking reference integer ID. `selector_kind` classifies an organization-owned materialized reference separately from an organization-private row without turning either into a global record.

The B1 governed geography suite passed, including the 249-country contract, Italy, Norway, Iran, bounded search/pagination, and stable global identities. Global materialization tests also passed. No B1 catalog or geography runtime file changed.

## G. Round Trip

Backend proof executes the complete canonical path:

```text
select active same-tenant LogisticsPoint.public_id
-> POST canonical execution event with location.logistics_point_public_id
-> persist OperationalEventLocationEvidence.source_identity
-> GET internal timeline
-> same opaque source_identity and event-time display snapshot
```

The frontend canonical test selects `private-point-1`, proves the exact nested identifier payload, reloads the timeline, and proves `مکان: انبار خصوصی` is rendered. The Request Detail test proves the same private identity is sent in the mapped compatibility payload. Display text is never substituted for the governed identifier.

## H. Historical Snapshot

No snapshot model or write rule changed. The canonical service still copies the point's event-time Persian/English name, type, country, and city fields into immutable event evidence. The focused test creates a customer-visible event at a private point, renames and deactivates the source point, then proves the internal and public historical timelines still show the original display snapshot and the internal read retains the original governed source identity. Deactivation therefore means “not selectable now,” not “erase historical evidence.”

## I. Customer/Public Safety

No Customer/Public selector was changed or added. Public tracking continues to use the existing allowlisted event projection. The focused test proves the public timeline can retain the already-approved safe display snapshot while omitting `organization_id`, the private immutable code, private ownership, audit fields, internal notes, and the opaque private source identity. Private selector responses remain authenticated/internal only.

## J. Product Changes

Exact runtime files:

- `backend/services/logistics_network_service.py` — aligns the existing bounded selector with the exact existing operational authorities that consume it, keeps server-derived tenant/active filters, adds `has_more`, and adds safe private-versus-materialized-reference classification.
- `src/components/OperationalEventLocationSelector.tsx` — one shared internal selector combining the two already-distinct sources, with search, grouped labels, typed identity, retained selection, and manual fallback.
- `src/lib/api.ts` — types `selector_kind`, bounded `has_more`, and the existing canonical timeline location projection.
- `src/pages/ExecutionUnits.tsx` — exposes the selector on the canonical event command, sends the exact governed identity, and renders the returned snapshot in event history.
- `src/pages/RequestDetail.tsx` — replaces the private-only compatibility picker with the shared selector and preserves the existing mapped canonical write contract.

Focused test files added/updated:

- `backend/tests/test_phase_b7_private_point_selector_reachability.py`
- `src/tests/components/OperationalEventLocationSelector.test.tsx`
- `src/tests/pages/ExecutionUnitPages.test.tsx`
- `src/tests/pages/RequestDetail.tracking-actions.test.tsx`

## K. Regression Status

```text
GCF-A-001 = PASS
GCF-A-002 = PASS
GCF-A-003 = PASS
GCF-A-005 = PASS
GCF-A-007 = PASS
GCF-A-009 = PASS
GCF-A-011 = PASS

PHASE_B1_GEOGRAPHY = PASS
PHASE_B2_NUMERIC = PASS
PHASE_B3_TRANSPORT_SUMMARY = PASS
PHASE_B4_REQUEST_COUNT_LIST = PASS
PHASE_B5_EUR = PASS
PHASE_B6_TRACKING_ACTION = PASS
```

B6's retired add-unit action remains absent, while canonical execution-unit creation/update/timeline behavior remains reachable. No numeric, summary, request-count/list, quote/EUR, date/time, or tracking-time contract changed.

## L. Tests

| Qualification | Result |
| --- | --- |
| B7 backend proof | PASS — 2 passed |
| Backend location/tracking/regression set | PASS — 154 passed across the 15 explicitly listed B7, logistics network/materialization, route orchestration, execution unit, multi-unit tracking, projection/public timeline, tracking location, B1 geography, membership, operational vertical, customer response, and B5 files |
| Full backend suite | PASS — 1,061 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failed; 522.88 seconds |
| Frontend focused selector/pages | PASS — 3 files, 11 tests |
| Full frontend inventory | PASS — 66 files, 308 unique tests: 65 non-timezone files/301 tests in seven non-overlapping batches plus 1 timezone file/7 tests; the timezone file passed in both Tehran-started and UTC-started processes |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,540 modules transformed; isolated output outside the repository; no tracked `dist` delta |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Migration/runtime focused tests | PASS — 38 executions (32 migration safety/portability/version tests plus 6 browser migration-contract tests) |
| Alembic graph/current/check | PASS — 97 revisions; one base; one expected head; disposable current equals head; two independent status reads report `pending=no` |
| Migration delta | PASS — zero files changed under `backend/migrations` |

The full backend run completed before the final test-only strengthening of inactive identity/organization assertions; the current focused 154-test run subsequently executed that strengthened test and passed. No backend runtime code changed between those runs. The frontend inventory, typecheck, build, and lint all ran after the final timeline-read rendering change.

The 93 backend skips are environment-dependent suites, principally owned PostgreSQL/socket gates; they are not reported as passes. The one xfail is the existing expected failure. The direct single-process frontend collector exhibited the already-recorded Windows/Vitest stall, so the authoritative run covered the complete inventory in non-overlapping batches. There is no unexplained count reduction: B6 recorded 65 files/305 tests; B7 adds one file and three tests, producing 66 files/308 tests.

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

The graph remains 97 revisions with base `20240917_initial_schema` and sole head `20260921_shipment_evidence_ownership`. A new isolated SQLite status database was stamped to the repository head, then read twice through `revision_status`; both reads returned `current=20260921_shipment_evidence_ownership` and `pending=no`. No environment file, local development database, Production database, or fallback target was used.

A separate attempt to replay the entire historical chain on SQLite stopped at the pre-existing PostgreSQL-oriented `20240920_add_transport_method_to_shipment_request` `ALTER COLUMN ... DROP DEFAULT`. That attempt is not claimed as a passing upgrade proof. B7 adds or edits no migration; the authoritative no-migration evidence is the unchanged migration tree, passing migration safety/portability suites, static one-head graph, and the same disposable head-status method used by B6. PostgreSQL-only upgrade gates remain correctly classified as unavailable environmental skips rather than silently falling back.

## N. Scope Integrity

```text
ACTIVE_SAME_TENANT_PRIVATE_POINTS_REACHABLE=YES
WRONG_TENANT_PRIVATE_POINTS_REACHABLE=NO
INACTIVE_PRIVATE_POINTS_SELECTABLE=NO
PRIVATE_POINTS_ADDED_TO_GLOBAL_CATALOG=NO
CUSTOMER_PRIVATE_DISCLOSURE_BROADENED=NO
PRIVATE_POINT_OWNERSHIP_CHANGED=NO
TRACKING_MODEL_CHANGED=NO
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

No deploy, push, merge, cherry-pick, RC build, Production endpoint, Production configuration, Production database, process, task, credential, or secret was accessed or changed. No second slice was started.

## O. Remaining Risks

- The private selector deliberately returns only the first bounded page (`limit=20` by the frontend, with `has_more` available). The current UI relies on refining the search rather than exposing pagination controls, so a very broad query in an organization with more than 20 matching points requires a more specific term.
- The combined selector fetches tenant points and global tracking references together. If either source fails, the healthy selectable source is not shown for that request, although manual location entry remains available and no stale/cross-tenant option is exposed.
- Request Detail remains a compatibility surface for already mapped historical units only. An unmapped or ambiguous unit continues to fail closed under B6; B7 does not make that legacy write path canonical.

## P. Verdict

PASS — PRIVATE-POINT SELECTOR REACHABILITY COMPLETE

## Q. Next Goal

Exactly one next approved implementation slice is derived from Phase C of the controlled integration plan:

**Phase C — inactive channel-neutral notification foundation, first schema/model slice only:** add the fresh additive Golden-based intent/action/attempt ownership schema and models, inactive by default, with one head and rollback/sentinel proof. Do not activate a business-event consumer, infer recipients, choose a default channel, call a provider, use credentials, alter Expert inbox meaning, or expose notification data to Control Tower.

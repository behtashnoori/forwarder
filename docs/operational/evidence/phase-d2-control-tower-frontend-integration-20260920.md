# Phase D2 — Control Tower Frontend Integration Evidence

Date: 2026-09-20
Scope: existing Golden Control Tower route connected to the D1 governed read backend

## A. Starting State

- Canonical baseline: `integration/golden-controlled` at `f3e0338f40a32c35108588a1cdae9c9220557939`.
- D1 product commit: `d0f2c57602d5d00320bb550935f9b9930d71f172`; ancestry check passed.
- D1 synchronization evidence commit / D2 parent: `f3e0338f40a32c35108588a1cdae9c9220557939`.
- Upstream: `github/integration/golden-controlled`; starting ahead/behind was `0/0` and the starting worktree was clean.
- D2 branch: `codex/phase-d2-control-tower-frontend`, created from the exact required parent. The canonical branch was not moved and no D2 branch was pushed.
- Alembic graph: exactly one head, `20260923_notification_lifecycle`. A disposable SQLite database reported `current=head=20260923_notification_lifecycle` and `alembic check` reported no new upgrade operations.
- Required D1 and contract-freeze evidence existed before implementation.

## B. Existing Golden Page

The existing route remained `/operations/control-tower`, implemented by `src/pages/OperationsControlTower.tsx`, behind the existing `ProtectedRoute` and `OperationalRoute` guards and linked from the existing Operations navigation.

Before D2, its no-props route rendered the generic Semantic Analytics dashboard runtime. That runtime requested the operational context, semantic registry, and up to four parallel analytics queries across eight widgets: active shipments, open exceptions, open work, document readiness, lifecycle distribution, route-leg status, route modes, and delay trend. Its global filters were time, customer identity, and project identity; it refreshed every 120 seconds, supported analytics drilldowns, clone-to-personal-dashboard, loading/partial/error widget states, and a one-column-to-four-column responsive grid.

| Existing section | D2 classification | Disposition |
| --- | --- | --- |
| Golden shell, route, guards, Operations navigation | KEEP | Unchanged. |
| No-props `/operations/control-tower` runtime | ADAPT_TO_D1 | Now renders the dedicated D1 operational view. |
| Time/customer/project analytics filters and aggregate widgets on the operational route | REMOVE_AS_OBSOLETE | Replaced by D1-supported attention filters and shipment cards; no fallback remains. |
| Personal-dashboard and Builder semantic runtime | KEEP | Preserved when an explicit dashboard definition is supplied. |
| Analytics clone/drilldown behavior | DEFER outside the operational route | Still available in the personal-dashboard subsystem, not used as Control Tower truth. |
| App shell, navigation, Shipment Detail, dashboard manifests | OUT_OF_SCOPE | Unchanged. |

## C. Frontend Adapter

`src/control-tower/api.ts` is the feature-local boundary. It calls only `GET /api/control-tower/shipments`, builds only D1-supported `page_size`, `attention`, and `cursor` parameters, passes the cursor through as an opaque string, and maps the response into feature-local types. It normalizes presentation absence to `null`, copies ordered actual route modes, and preserves the request-transport object, operational status, occurred/recorded timestamps, safe progress, attention, work summary, and supplied Shipment Detail destination without inventing business facts.

The existing shared `request` transport is reused for authentication refresh and `ApiError`; no shared API type or unrelated response contract changed.

## D. Product Presentation

The existing page now gives an operations user a concise Persian card per governed shipment: shipment reference and operational status, current responsible Expert, current safe location, request transport facts, ordered actual route modes and route label, latest tracking event, primary/additional attention reasons, open-reason count, and the existing Shipment Detail action. The page provides refresh, D1 attention filters, continuation, and explicit loading/empty/authorization/unavailable/general-error states.

The personal-dashboard semantic runtime remains available only to explicit dashboard-definition consumers; it is not a fallback for the operational Control Tower route.

## E. Source-of-Truth Integrity

- Request transport and actual route transport are separate labelled panels. A Sea request and `road → rail → road` route remain visibly distinct.
- `operationalStatus` is rendered as the shipment state. No request state is substituted or merged; D1 does not expose a request state on this projection.
- `latestEventOccurredAt` and `latestEventRecordedAt` are rendered as separately labelled instants.
- Missing owner, location, request transport, route, mode, event, or timestamp remains `null` in the adapter and is presented as not recorded; no business default is synthesized.
- Existing Golden business/transport labels, numeric formatting, and date-time presentation policy are reused.

## F. Filters / Pagination

The only attention filters are `urgent`, `follow_up`, and `review`, plus the unfiltered view. Every filter change issues a fresh backend request; there is no client-only population filtering. Continuation sends the returned cursor unchanged, retains existing cards while a normal continuation request is pending, appends only new keys, and never invents page numbers.

## G. Safe Ceiling / 503

`503 EVALUATION_UNAVAILABLE` enters a dedicated unavailable state, clears any previously loaded or partial cards, and explains that no list is displayed because complete evaluation is unavailable. It does not retry through Semantic Analytics and does not raise the D1 ceiling.

`SEMANTIC_ANALYTICS_FALLBACK_ON_D1_FAILURE=NO`

## H. Shipment Detail Integration

Every action uses the exact `destination` supplied by D1. The existing `/operations/shipments/:id` route and `OperationalShipmentDetail.tsx` were not modified, copied, or reimplemented.

## I. Authorization

Existing route and organization guards remain unchanged. The feature reuses the shared authenticated request behavior. A remaining 401 is shown as an invalid-session state, 403 as a permission state, and neither is represented as empty data. Backend scope remains authoritative; the frontend adds no role grant or source-capability inference. Actor/session changes remount the bounded view and late responses from an old session are discarded.

## J. Responsive / Accessibility

The view uses the existing responsive card/stacking conventions: one-column mobile content, two-column fact sections at larger breakpoints, wrapping identifiers and controls, and a full-width mobile detail action. Buttons and links retain semantic elements, filters expose `aria-pressed`, loading/empty/error states have status/alert semantics, and attention labels include text rather than relying only on color.

## K. Product Changes

Runtime files:

- `src/control-tower/api.ts` — feature-local D1 types, adapter, request, and safe error classification.
- `src/control-tower/ControlTowerOperationalView.tsx` — operational Persian D1 page presentation and states.
- `src/pages/OperationsControlTower.tsx` — bounded dispatch: the existing no-props route uses D1; explicit personal-dashboard definitions retain the existing Semantic Analytics runtime.

Tests:

- `src/tests/control-tower/api.test.ts`
- `src/tests/control-tower/ControlTowerOperationalView.test.tsx`
- `src/tests/control-tower/OperationsControlTower.integration.test.tsx`
- `src/tests/dashboard/control-tower.test.tsx` (explicitly exercises the retained semantic personal-dashboard runtime)

No shared shell, navigation, Shipment Detail, backend, migration, notification, donor, or compiled artifact is part of the product delta.

## L. Backend Integrity

No backend runtime or test file changed in D2. The exact four-file D1 focused cohort passed unchanged.

`CONTROL_TOWER_BACKEND_SEMANTICS_CHANGED=NO`

## M. Notification Isolation

The adapter types and runtime UI contain no NotificationAction, NotificationAttempt, recipient, channel, provider, or delivery field. No notification source is requested and no activation path changed.

```text
NOTIFICATION_UI_ADDED=NO
NOTIFICATION_DATA_CONSUMED=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
```

## N. Database Contract

```text
DATABASE_HEAD =
20260923_notification_lifecycle

MIGRATION_ADDED =
NO

MIGRATION_MODIFIED =
NO

PENDING_MIGRATION =
NO
```

## O. Regression Status

- Phase A shell/route/auth/disclosure contracts: preserved; route and navigation inventories pass.
- B1 geography and B7 private points: no geography query or ownership metadata was added; only the D1 safe location string is shown.
- B2 numeric: existing `formatBusinessNumber` is reused for counts.
- B3 transport: request transport and ordered actual modes are separately rendered and tested.
- B4 count/list: no client aggregate or alternate population was introduced.
- B5 EUR/economics: no quote, currency, or economics file or field changed.
- B6 tracking action removal: this view is read-only and adds no tracking write.
- C1/C2: notification foundation/lifecycle remains inactive and unconsumed.
- D1: endpoint contract, authorization, boundedness, attention semantics, and 100-shipment fail-closed behavior are unchanged.

## P. Tests

| Gate | Exact result |
| --- | --- |
| D2 focused frontend + route/navigation/retained dashboard runtime | PASS — 6 files, 26 tests |
| Explicit App route, Operations navigation, and Shipment Detail preservation | PASS — 3 files, 40 tests |
| Full frontend inventory | PASS — 69 files, 322 tests |
| TypeScript (`npx tsc --noEmit`) | PASS |
| Production build | PASS — Vite 6.4.3, 2,543 modules transformed |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| D1 focused backend | PASS — 186 passed |
| Full backend, explicit `TEST_DATABASE_URL=sqlite:///:memory:` | PASS — 1,258 passed, 97 skipped, 1 expected xfail, 0 failed in 914.89 seconds |
| Source/package/architecture cohort, explicit isolated DB | PASS — 87 passed, 1 expected xfail, 27 warnings |
| Alembic heads/current/check on disposable DB | PASS — one head, current=head, no pending operations |
| Worktree whitespace | PASS |

One preliminary release test selection was intentionally stopped because it included unrelated historical artifact suites. A subsequent bounded source/package cohort initially inherited the host PostgreSQL test URL and reproduced the already-documented three tenant-architecture fixture setup errors. The authoritative rerun explicitly used in-memory SQLite and passed (87 plus one expected xfail). No failing product assertion was suppressed or called PASS.

## Q. Scope Integrity

```text
CONTROL_TOWER_FRONTEND_INTEGRATED=YES
EXISTING_GOLDEN_CONTROL_TOWER_ROUTE_REUSED=YES
APP_SHELL_REPLACED=NO
OPERATIONS_NAV_REPLACED=NO
SHIPMENT_DETAIL_REPLACED=NO
SEMANTIC_ANALYTICS_FALLBACK_ON_D1_FAILURE=NO
CONTROL_TOWER_BACKEND_SEMANTICS_CHANGED=NO
NOTIFICATION_UI_ADDED=NO
NOTIFICATION_DATA_CONSUMED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

## R. Remaining Risks

1. D1's deliberate 100-shipment complete-population ceiling remains. For an authorized active population above that ceiling, the page correctly becomes unavailable rather than displaying a partial list. Scaling that backend contract is not part of D2.
2. D2 has automated responsive/accessibility coverage and a production build, but it does not claim a separately captured browser screenshot/UAT artifact.
3. The qualified packaged real-process launcher remains unavailable in this workspace, as recorded in D1; no stale artifact was substituted.

## S. Verdict

PASS — CONTROL TOWER FRONTEND INTEGRATION COMPLETE

## T. Next Goal

Execute exactly the approved Phase F shared-seam reconciliation: verify and, only if required by the frozen contract, minimally reconcile the existing shared operational backend so the current responsible Expert can open the existing Shipment Detail destination while former, unrelated, revoked, and cross-tenant Experts remain denied, preserving the default detail payload and economics boundaries. Do not begin qualification, decision-dependent feedback work, notification activation, deployment, or Production access in that slice.

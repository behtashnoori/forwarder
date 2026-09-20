# Phase D1 — Isolated Control Tower Backend Evidence

Date: 2026-09-20
Scope: backend-only Golden-controlled Control Tower read capability

## A. Starting State

- Canonical baseline: `integration/golden-controlled` at `b52741d8ff4b58071000c5416213d8d0b872e77b`.
- C2 product commit: `2bbc369effb70ca428b1dfb23b987bd16b8634bf`; ancestry check passed.
- Sync evidence commit / required starting HEAD: `b52741d8ff4b58071000c5416213d8d0b872e77b`.
- Upstream: `github/integration/golden-controlled`; fetch completed and ahead/behind was `0/0` before branching.
- D1 branch: `codex/phase-d1-control-tower-backend`, created from the exact required HEAD. The canonical integration branch was not moved.
- Database head: exactly one Alembic head, `20260923_notification_lifecycle`.
- Starting worktree: clean.
- Donor reference: read-only `D:\1-webapp\15-forwarder` at `d6297fdf50b27f7d69a5bf2086d11ef2eed882ed` (`S7-RC-d6297fd-ct1-frozen`). It was not used as the baseline and was not modified by D1.

## B. Existing Golden Control Tower Seam

Classification: **OTHER — current frontend Control Tower backed by generic Semantic Analytics, with no dedicated Control Tower backend route**.

Before D1, Golden already had the `/operations/control-tower` page/navigation seam. That page consumed the generic Semantic Analytics API and did not have a feature-local Control Tower backend endpoint. There was therefore no existing dedicated endpoint to replace or duplicate. D1 adds a separate, isolated backend read seam at `GET /api/control-tower/shipments`; it does not wire the existing page to that endpoint and does not modify the application shell, navigation, API client, page, or Shipment Detail.

## C. Donor Analysis

| Donor backend component | Classification | D1 disposition |
| --- | --- | --- |
| `backend/routes/control_tower.py` | RECONCILED | Kept the bounded read-route concept; adapted authentication, errors, explicit serialization, and cache policy to current Golden. |
| `backend/services/control_tower_scope.py` | REIMPLEMENTED | Rebuilt against current persisted actor, membership, capability, assignment, tenant, and responsibility rules; removed donor assumptions that could broaden scope. |
| `backend/services/control_tower_sources.py` | RECONCILED | Retained bounded attention-source semantics while batching current Golden reads and revalidating authority before disclosure. |
| `backend/services/control_tower_read_model.py` | REIMPLEMENTED | Rebuilt the public projection around current Golden request-transport and canonical tracking projections, deterministic HMAC cursors, and explicit allowlists. |
| `backend/services/control_tower_oip.py` | RECONCILED | Preserved verified, read-only enrichment only where current Golden policy/source linkage proves it. |
| `backend/services/control_tower_translation.py` | RECONCILED | Preserved safe Persian operational vocabulary and unknown-value handling without competing product translations. |

Rejected donor assumptions include an unbounded population, per-row authority/context queries, capability-free administrative access, and a narrower attention-only projection that omitted the current Golden transport/tracking distinctions.

## D. Control Tower Authorization

The route is authenticated and fail-closed. Every read resolves the current persisted actor rather than trusting request-supplied persona or tenant fields.

- An active Expert or Organization Admin must have one active membership in one active operational organization and the current `operational_shipment.read` capability.
- Platform Admin is denied this tenant operational summary even if accidental grants exist.
- Organization Admin receives only the authorized, active (`planned` or `in_progress`) population of the current tenant.
- Expert scope is narrower: accepted-quote shipments require current request assignment to that Expert; direct shipments require that Expert to be the current primary responsible Expert.
- Existing `assigned_shipment_scope` remains an additional Golden authorization boundary.
- Foreign-tenant, terminal, unrelated, inactive, revoked, malformed-lineage, and guessed-identity rows never enter the presentation population.
- Responsibility, actor, membership, and capability are revalidated during evaluation and again before disclosure. A changed or invalid scope fails the whole read; it is never represented as an empty or partial success.
- The response contains no aggregate total, so inaccessible work cannot affect a disclosed count.

## E. Control Tower Sources

The read model uses only existing Golden-controlled facts and services:

- `OperationalShipment` for public shipment identity, lifecycle state, source type, and current responsibility lineage.
- `ShipmentRequest` for tenant-owned request identity, assignment, and request transport intention through `project_existing_request_transport`.
- Active `RoutePlan` and ordered non-cancelled `RouteLeg` rows for the actual route/mode chain and governed location snapshots.
- `project_operational_shipments` for canonical execution-unit/event tracking, safe current location, event occurrence time, and event recorded time.
- Existing operational delays, exceptions, work items, checkpoints, milestones, and their governed reason catalogs for attention.
- Existing document-readiness/MDPM decisions for bounded readiness blockers; no document body or storage detail is read into the public projection.
- Existing OIP policy thresholds only as verified enrichment of an already-authoritative source fact.

Quotes/economics, private notes, notification tables, provider state, document bodies, raw paths, and unrelated audit metadata are not Control Tower sources.

## F. Read Model

`GET /api/control-tower/shipments` returns an authenticated, private/no-store page with:

- evaluation state/time and an opaque continuation cursor;
- shipment public reference;
- source type and request public identity when an accepted-quote request exists;
- current shipment operational state, kept distinct from request state;
- request transport intention, kept distinct from ordered actual route-leg modes;
- safe route and Persian transport labels only when the active route chain is continuous and known;
- current responsible Expert display name;
- canonical current location/progress, unit count, latest event type, and distinct occurred/recorded timestamps;
- one primary attention reason, bounded additional reasons, and a small work summary;
- an existing Shipment Detail destination URL, without changing Shipment Detail itself.

Missing facts remain absent/`null`; no fallback business fact is invented. Only `urgent`, `follow_up`, and `review` are valid attention filters. Responses use an explicit field allowlist and `Cache-Control: private, no-store`.

## G. OIP

OIP is read-only and bounded. It may enrich an existing, linked delay/work/readiness reason only when current policy/version, source linkage, threshold, timing, and scope checks all succeed. It creates no workflow state, score, write, action, outbox event, or replacement source of truth. Unsupported or stale OIP facts are ignored; authority/source failures make the read unavailable rather than partially successful.

## H. Shared Seam Changes

Only one shared backend file changed: `backend/routes/__init__.py`. It imports and registers `control_tower_bp` additively. Existing route registrations and ordering remain intact. `backend/routes/operations.py`, `backend/services/operational_service.py`, and all other shared product services were unchanged.

## I. Shipment Detail / Economics Preservation

No Shipment Detail, quote, currency, economics model, serializer, or route was modified. Control Tower exposes no quote/economic fields. The relevant operational-detail, quote/economics, assigned-work, and authorization regressions passed within the 175-test focused regression cohort, and the isolated full backend suite passed.

SHIPMENT_DETAIL_BEHAVIOR_CHANGED=NO
ECONOMICS_BEHAVIOR_CHANGED=NO

## J. Tracking / Geography / Private Point Preservation

Tracking is projected through the existing canonical tracking service; the retired legacy add-unit path was not reintroduced. The projection preserves latest event occurrence and recording as separate timestamps. Route display uses the active plan's governed location snapshots and only forms a route when the ordered chain is continuous. No geography catalog is returned, and no global/private point fallback or conflation was added. Tracking, route, geography, and tenant-safe private-point regression tests passed.

## K. Notification Isolation

The endpoint imports no notification model and reads no notification table. Tests seed/count `NotificationAction` and `NotificationAttempt` around a Control Tower read and prove that both remain zero. No outbox consumer or notification lifecycle behavior was introduced.

NOTIFICATION_DATA_EXPOSED_TO_CONTROL_TOWER=NO
NOTIFICATION_ACTION_CREATED_BY_CONTROL_TOWER=NO
OUTBOX_NOTIFICATION_CONSUMER_ADDED=NO

## L. Frontend Isolation

No frontend file has a D1 diff. The existing page remains on its pre-D1 Semantic Analytics seam; D1 does not make the new backend visible in the UI.

CONTROL_TOWER_FRONTEND_INTEGRATED=NO
FRONTEND_RUNTIME_CHANGED=NO

## M. Database Contract

Alembic reports exactly one head. A disposable empty SQLite database was stamped to that head and verified with Alembic `current`, `heads`, and `check`; `check` exited successfully with no pending operation. No migration or model schema file changed.

DATABASE_HEAD = 20260923_notification_lifecycle
MIGRATION_ADDED = NO
MIGRATION_MODIFIED = NO
PENDING_MIGRATION = NO

## N. Performance / Boundedness

- The complete authorized active population is hard-limited to 100 shipments. A tenant population above that ceiling fails closed with `503 EVALUATION_UNAVAILABLE`; it is not silently truncated.
- `page_size` is constrained to 1–100 (default 25).
- Opaque HMAC-signed cursors bind actor/scope, filter, page size, and deterministic result ordering. Changed authority or ordering invalidates continuation.
- Candidate shipments, requests, responsible users, memberships, source rows, active plans/legs, request context, and tracking context use bounded batch reads.
- A query-growth test compares one and ten request-owned shipments and proves request/owner/route/tracking access does not become per-row N+1 work.
- Attention sources are fully evaluated and aggregated before filtering/pagination. No total count, full timeline, document body, geography catalog, notification history, or private provenance is returned.

## O. Tests

| Gate | Exact result |
| --- | --- |
| Focused Control Tower (`test_control_tower_api.py`, `test_control_tower_read_model.py`, `test_control_tower_scope.py`, `test_control_tower_sources.py`) | **186 passed** |
| Relevant backend regression (assigned work/membership, operational reads/detail/population, tracking, quote/economics, geography/private point, notification foundation/lifecycle, documents) | **175 passed, 1 skipped** |
| Full backend, explicitly isolated with `TEST_DATABASE_URL=sqlite:///:memory:` | **1258 passed, 97 skipped, 1 xfailed, 0 failed** in 770.60s |
| Full frontend inventory | **66 test files, 308 tests passed** |
| TypeScript (`npx tsc --noEmit`) | **PASS** |
| Production frontend build | **PASS**; Vite 6.4.3, 2540 modules transformed |
| ESLint | **PASS: 0 errors, 13 pre-existing warnings** |
| C2 source/package contract cohort | **72 passed**, 27 warnings in 8.25s |
| Alembic heads/current/check | **PASS**; one unchanged head, no pending migration |
| Packaged real-process launcher | **NOT RUN — qualified certified package artifact unavailable in this workspace** |

The first full-backend attempt inherited an external `TEST_DATABASE_URL` pointing at an incompatible local PostgreSQL schema and stopped with three fixture-setup errors while creating a notification foreign key. The exact affected architecture-contract tests passed independently on SQLite (`8 passed, 1 xfailed`), and the complete suite was then rerun in the explicit isolated environment with the result above. No product failure was suppressed. The real-process launcher is deliberately not claimed as PASS: `release-candidates/Forwarder-Operational-Workspace-Production-CERTIFIED` is absent, and no stale/superseded artifact was substituted.

## P. Regression Status

- Phase A contract/scope boundaries: preserved; baseline and full-suite gates pass.
- B1 geography: preserved through active governed route snapshots and geography/private-point regression coverage.
- B2 numeric presentation: no frontend/runtime or numeric formatter change; frontend inventory/type/build/lint pass.
- B3 transport: request transport and actual ordered route modes remain distinct and are directly tested.
- B4 count/list: no public aggregate total was added; canonical authorization/population/list regressions pass.
- B5 EUR/quotes: no quote/economics path changed; quote/economics regressions pass.
- B6 tracking-action removal: no write/action path was added; canonical projection tests pass.
- B7 private points/tracking: tenant-safe location and canonical tracking regressions pass.
- C1 notification foundation and C2 lifecycle hardening: no notification data or behavior is used; relevant regression and source/package contract gates pass.

No frontend, migration, notification, deployment, Production, or donor-repository delta is part of D1.

## Q. Scope Integrity

CONTROL_TOWER_BACKEND_CREATED=YES
CONTROL_TOWER_FRONTEND_INTEGRATED=NO
CONTROL_TOWER_SCHEMA_ADDED=NO
SHIPMENT_DETAIL_BEHAVIOR_CHANGED=NO
ECONOMICS_BEHAVIOR_CHANGED=NO
NOTIFICATION_DATA_EXPOSED_TO_CONTROL_TOWER=NO
NOTIFICATION_ACTIVATION_CHANGED=NO
FRONTEND_RUNTIME_CHANGED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO

## R. Remaining Risks

1. The deliberate 100-shipment complete-population ceiling makes the endpoint unavailable for a tenant whose authorized active population exceeds that bound. A future slice must choose a server-side search/windowing contract before relaxing it; partial summary disclosure is not acceptable.
2. The dedicated backend is intentionally not consumed by the current Control Tower page. The later UI integration must reconcile the existing Semantic Analytics page with this read model rather than leaving two competing product interpretations.
3. A packaged real-process launcher could not be qualified because the required certified package artifact is absent. Source/package contracts pass, but no runtime-artifact PASS is claimed.

## S. Verdict

PASS — ISOLATED CONTROL TOWER BACKEND COMPLETE

## T. Next Goal

Integrate the existing Golden Control Tower page with `GET /api/control-tower/shipments` through a feature-local frontend adapter, reconciling the current Semantic Analytics presentation while preserving the Golden application shell, navigation, Shipment Detail, authorization boundaries, and all backend source-of-truth distinctions.

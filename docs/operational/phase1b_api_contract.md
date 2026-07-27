# Phase 1B API contract

Route plans support list, create, detail, validate, activate, and replan beneath `/api/operational-shipments/{shipment_id}/route-plans`. Draft legs and checkpoints are created beneath a plan. Checkpoint commands are `arrive`, `complete-processing`, and `depart`. Timeline returns `planned`, `projected`, `actual`, `delays`, `dependencies`, and `open_exceptions`.

Timeline also returns `effective`, `route_plan_id`, `route_plan_revision`, `reconciliation_version`, and `reconciled_at`. Every effective arrival/departure names its source (`actual`, `projected`, or `planned`). `POST /api/operational-shipments/{shipment_id}/timeline/reconcile` accepts `expected_route_plan_version` and requires `Idempotency-Key`; it is organization-scoped, permission-checked, active-plan-only, optimistic, idempotent, and transactional.

Errors use the existing `{error:{code,message,fields}}` envelope. Tenant-scoped missing resources return 404 to prevent identifier leakage.

Cross-plan references use `CROSS_PLAN_REFERENCE_NOT_ALLOWED`; idempotency payload mismatches use `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`. Direct HTTP tests cover these stable responses, resource-scoped key independence, inactive membership, permission/tenant isolation, and absence of raw SQL, constraint names, or tracebacks.

Checkpoint report, verify, correction, and re-verification use `expected_version`; report, verify, and correction endpoints require `Idempotency-Key`. Verify returns `REPORTER_CANNOT_VERIFY_OWN_EVENT` when actor identity matches the current report/correction actor. Correction returns `CORRECTION_REASON_REQUIRED` without a reason. Stale lifecycle commands return `STALE_MILESTONE_VERSION`. Successful verification/correction records its event, aggregate summaries, audit, outbox, and idempotency result in one transaction.

`POST /api/operational-shipments/{shipment_id}/route-plans/{source_plan_id}/replan` requires `reason`, `expected_version`, and `Idempotency-Key`. It returns the active next revision. Stable replan errors are `ROUTE_PLAN_NOT_FOUND`, `REPLAN_REASON_REQUIRED`, `ROUTE_PLAN_NOT_ACTIVE`, `STALE_ROUTE_PLAN_VERSION`, `ROUTE_PLAN_REPLAN_CONFLICT`, `INVALID_ROUTE_GRAPH`, and `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`. Database exception text, constraint names, and tracebacks are not exposed.

## Route exceptions

`POST /api/operational-shipments/{shipment_id}/route-exceptions/reconcile` accepts `expected_route_plan_version` and optional server-testable `calculation_time`; public calls require `Idempotency-Key`. It returns opened, resolved, reopened, unchanged, work-item, revision, timestamp, and replay counts. `GET /api/operational-shipments/{shipment_id}/route-exceptions` lists tenant-scoped history. `POST /api/route-exceptions/{exception_id}/resolve` requires `expected_version`, a non-empty reason, and `Idempotency-Key`; an exact replay returns the stored result without another transition, audit, or outbox event.

Stable errors are `ROUTE_PLAN_NOT_ACTIVE`, `ROUTE_EXCEPTION_NOT_FOUND`, `ROUTE_EXCEPTION_ALREADY_RESOLVED`, `EXCEPTION_RESOLUTION_REASON_REQUIRED`, `STALE_ROUTE_EXCEPTION_VERSION`, `STALE_ROUTE_PLAN_VERSION`, and `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`.

The exception list response also exposes stored transition metadata:
`resolved_at`, `resolution_source`, `resolution_reason`,
`last_reconciled_at`, and `occurrence_count`. These are additive projections of
existing fields and do not change the lifecycle contract.

Checkpoint report commands require `occurred_at`, `expected_version`, and
`Idempotency-Key`. Checkpoint verification requires `expected_version` and
`Idempotency-Key`. The operational shipment compatibility graph includes both
legacy leg-scoped milestones and active-plan checkpoint milestones so the
append-only Phase 1B event history is visible without changing legacy routes.

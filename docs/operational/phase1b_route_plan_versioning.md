# Route-plan versioning

Statuses are `draft`, `active`, `superseded`, and `cancelled`. A shipment has at most one active plan through the existing partial unique index. Revision numbers are unique per shipment. `expected_version` guards activation, replanning, and checkpoint commands.

Replan requires a reason, source-plan `expected_version`, and idempotency key. The shipment row and current active-plan row are locked, the next revision is allocated inside that lock, and the target is created as non-active `draft`. The complete leg/checkpoint/dependency/milestone graph is cloned and validated before the source becomes `superseded` and the target becomes `active` in the same transaction.

`created_from_plan_id`, source entity IDs, revision, reason, actor, creation time, and effective time retain provenance. Verified actual summaries are carried forward, but historical milestone events are not cloned or changed. Open work items owned by the superseded plan are retained as history and resolved with `PLAN_SUPERSEDED`; no target duplicates or general exception reconciliation are created by replan.

Same-key/same-payload retries replay one result. Same-key/different-payload requests return `IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`. A stale source version returns `STALE_ROUTE_PLAN_VERSION`; a source that is no longer current returns `ROUTE_PLAN_NOT_ACTIVE`. PostgreSQL concurrency tests prove one active target and one unique next revision.

Final validation on PostgreSQL 18.0 used separate Phase 1A and Phase 1B guard-compatible disposable databases after fresh upgrades to `20260730_multileg_route`. Concurrent replan, graph mapping, completed-segment immutability, future-segment editing, rollback, work-item supersession, and unique audit/outbox behavior passed. A populated downgrade was rejected before destructive DDL, and cleanup left no disposable database resources.

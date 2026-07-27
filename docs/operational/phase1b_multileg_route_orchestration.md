# Phase 1B multi-leg route orchestration

Phase 1B extends the Phase 1A aggregate without replacing its API. An operational shipment can retain multiple route-plan revisions; each plan owns ordered legs, checkpoints, and dependency edges. Active plan structure is immutable: structural changes start as a draft revision and become effective only after validation and activation.

Planned, projected, and actual timestamps are stored separately. Actual history is never overwritten by timeline projection.

Graph ownership is enforced in PostgreSQL with composite foreign keys rather than service checks alone. Route exceptions reference a shipment in the declared organization, a plan in that shipment, and—when present—a checkpoint in that plan. Organization access is also filtered in every service command/query through the shipment membership scope.

Resource-scoped idempotent commands use the tuple `(organization_id, operation, resource_type, command_resource_id, idempotency_key)`. PostgreSQL serializes only this exact tuple with a transaction-scoped advisory lock. Canonical JSON hashing is key-order-insensitive, and the idempotency result, domain change, audit, and outbox entries commit or roll back together.

Checkpoint actual timestamps are derived summaries of verified milestone events. Correction appends provenance instead of rewriting history, clears the affected current actual, and makes the milestone reported until an independent verifier appends a new verification event. PostgreSQL keeps the event ledger append-only; no lifecycle-specific schema change was required.

Replan uses the shipment row as its serialization boundary, so unrelated shipments are not globally serialized. It clones legs first, then checkpoints, dependency edges with remapped target IDs, and milestones with explicit source provenance. The target remains non-active until graph validation succeeds. Source supersession, target activation, old-plan work-item resolution, idempotency result, audit, and `route_plan.replanned` outbox creation share one commit.

Controlled failure tests cover target creation, every clone stage, source supersession, activation, audit, outbox, and pre-commit. Every injected failure leaves the source active and removes the target graph and all partial transaction records.

## Delay propagation and projected timeline

The active plan alone is reconciled. Kahn topological ordering uses `(sequence_number, checkpoint_id)` as the deterministic tie-break, so query and insertion order do not affect results. A cycle fails with `INVALID_ROUTE_GRAPH_CYCLE` before mutation. Each successor waits for its latest predecessor release; planned checkpoint intervals provide non-negative dwell and edge travel durations. Actual verified arrival/departure takes precedence, projected values remain derived, and planned values are never rewritten.

Checkpoint projections synchronize checkpoint milestones and the owning route leg. Verified milestone actuals remain authoritative and the milestone-event ledger is never changed. A successful changed calculation increments the route-plan version and atomically emits one `route_plan.timeline_reconciled` audit/outbox pair; a no-op or idempotent replay emits neither. Exception/work-item creation and resolution are deliberately not part of timeline reconciliation.

`POST /api/operational-shipments/{shipment_id}/timeline/reconcile` requires route-plan replan permission, `expected_route_plan_version`, and `Idempotency-Key`. `GET .../timeline` returns separate planned/projected/actual/effective arrays, effective-value sources, delay seconds, plan revision, reconciliation version, and reconciliation time.

Timeline synchronization required schema additions in the existing uncommitted Phase 1B migration: route-plan reconciliation time and route-leg projected departure/arrival. The backfill does not infer actuals or overwrite planned values.

## Route exceptions and work-item reconciliation

Exception reconciliation reads only the active revision and the already-calculated effective timeline. Overdue checkpoints, dependency-blocked successors, and the existing 24-hour replan threshold map to one historical `OperationalWorkItem` per plan/checkpoint/type scope. PostgreSQL partial uniqueness prevents two open actionable rows for the same scope.

Automatic reconciliation opens, resolves, or reopens that row and records audit/outbox events in the same transaction. Manual resolution requires a reason, expected exception version, permission, and a resource-scoped idempotency key. It does not suppress a persisting condition: the next reconciliation deliberately reopens the historical row, increments occurrence/version, and preserves a single actionable item.

Successful replan resolves source-plan open items with `PLAN_SUPERSEDED`, retains their history, and does not clone them into the target. The target is evaluated only from its own state. PostgreSQL 18 concurrent reconciliation produced one opener and one unchanged result with no duplicate exception, audit, or outbox.

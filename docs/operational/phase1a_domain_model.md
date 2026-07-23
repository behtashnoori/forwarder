# Phase 1A domain model

`OperationalOrganization` is the tenant boundary; active explicit membership is mandatory and ambiguous/missing membership fails closed. `OperationalShipment` uniquely references an accepted Quote and its Request. `RoutePlan` supports revisions with one active plan; `RouteLeg` enforces sequence, distinct endpoints, UTC timeline, and version. `CanonicalLocation` deduplicates source identities.

Each leg has unique departure/arrival `Milestone` rows. Reported, verified, and corrected `MilestoneEvent` rows are ordered and append-only; PostgreSQL rejects UPDATE/DELETE and validates correction scope. Corrections require a reason and superseded event. Optimistic versions reject stale commands. One partial-unique open `OVERDUE_MILESTONE` work item exists per milestone/type. Verification resolves it. Every command writes `OperationalAudit` and `OperationalOutbox` in the same transaction.

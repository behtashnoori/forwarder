# ADR-055 — Operational monitoring run fencing and clock-aware freshness

- Status: ACCEPTED for the Product-approved Phase 2.5 reliability mission
- Date: 2026-09-24
- Owners / authority: Product Owner (mission); OIP/Operations architecture under LPAF v2.7
- Extends: ADR-031, ADR-032, ADR-054

## Context

Phase 2 already evaluates organization SLA, Exception and Action facts through the tenant-scoped OIP reconciliation CLI. Stable Situation identity and database uniqueness prevent duplicate semantic Attention. Two reliability gaps remain: elapsed time can cross an already-governed threshold without changing a database row, and the committed `REBUILDING` marker cannot distinguish a live run from a process that disappeared before completion. Control Tower also lacks the canonical evaluation-health contract.

## Decision

1. Keep `backend.operational_cli evaluate-sla` and `oip_service.reconcile` as the single browser-independent execution boundary. No worker, queue, daemon, service or deployment topology is added.
2. Hold one PostgreSQL session advisory lock for the complete organization evaluation. Live overlap is rejected. Connection/process loss releases the lock, allowing the next invocation to record and recover an abandoned run.
3. Preserve the OIP states `FRESH`, `STALE`, `REBUILDING`, and `DEGRADED`. A successful source evaluation is `FRESH` only when its final authoritative fingerprint matches the evaluated fingerprint. Source movement during the run produces `STALE`, not a false success.
4. Persist the earliest future boundary, derived only from already-approved UTC deadlines and configured OIP thresholds, that can change Attention without a row mutation. Reaching it makes the effective health `STALE` until reconciliation succeeds. No cadence, business calendar, pause rule or Product SLA is inferred.
5. Use an ordered tenant-scoped identity/version fingerprint instead of count/max aggregates. Existing source versions remain the mutation contract.
6. Extend projection-health history with sanitized count/duration details. Expose last attempt, last success, failure, next required evaluation and the latest terminal run summary without customer content.
7. Workspace, Control Tower, OIP status and operator CLI consume the same effective health calculation. Control Tower remains a read-only consumer; stale or degraded Attention cannot be presented as proof of healthy operations.
8. A projection-only rebuild may finish structurally while authoritative source evaluation is still behind. `REBUILDING -> STALE` is therefore allowed for that honest result; only a source-consistent operation reports `FRESH`.

## Consequences

- One minimal additive migration after `20260928_operational_workspace_phase2` adds clock-boundary and run-detail fields to the existing OIP health tables.
- Retry remains external and bounded: a failed command exits non-zero, and the next scheduled/manual invocation may recover safely.
- Catch-up records source occurrence/deadline separately from the actual evaluation/detection time.
- Existing Product meaning, authorization, tenant scope, fixed Shipment ownership and OIP advisory-only authority are unchanged.

## Rejected

- browser-triggered evaluation;
- Celery, Redis, Kafka, a Windows Service, a new container or another independently deployed runtime;
- a hard-coded Product cadence or business-calendar interpretation;
- treating a projection rebuild, an unchanged row count, or command exit success alone as proof that Attention is current;
- an unlimited automatic retry loop or a second Attention store.

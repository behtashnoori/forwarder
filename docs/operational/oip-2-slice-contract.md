# OIP-2 Situation + Attention Queue slice contract

- Candidate: `CAND-FWD-OIP-2-001`
- Implementation branch: `codex/oip-2-situation-attention`
- Projection: `oip-attention-v1`
- Implementation status: implemented with explicit threshold and validation limitations

## Source admission matrix

| Source | Admission | Adapter / constraint |
|---|---|---|
| Milestone / MilestoneEvent | OIP_SAFE | Tenant carried by milestone; correction and supersession respected |
| RoutePlan | OIP_SAFE | Active plan only |
| OperationalCheckpoint / RouteDependency | OIP_SAFE_WITH_ADAPTER | Checkpoint lacks opaque ID; adapter identity is active-plan + checkpoint identity |
| OperationalWorkItem | OIP_SAFE | Compatibility projection; it is not Situation truth |
| OperationalDelay / OperationalException | OIP_SAFE | Active means `resolved_at` absent; opaque source IDs |
| ExecutionUnit / OperationalEvent | OIP_SAFE_WITH_ADAPTER | Tenant resolved through Project; policy inactive without freshness authority |
| MDPM readiness / requirement / audit | OIP_SAFE | Consume readiness result; never recalculate it |
| OperationalAudit | OIP_SAFE | Audit evidence only, not business truth |
| Legacy Task / Activity / Document / Notification | NOT_YET_OIP_SAFE | No canonical operational tenant envelope |

## Signal catalog and thresholds

| Policy | Version | Identity | Activation |
|---|---|---|---|
| SIG-OIP-001 NEXT_MILESTONE_OVERDUE | 1.0.0 | org + shipment + milestone + policy major | Inactive: overdue tolerance/effective-time precedence not authorized |
| SIG-OIP-002 CHECKPOINT_OVERDUE | 1.0.0 | org + active plan + checkpoint/due dimension + policy major | Existing route reconciliation evidence |
| SIG-OIP-003 ROUTE_DEPENDENCY_BLOCKED | 1.0.0 | org + active plan + dependency edge + policy major | Explicit graph edge only |
| SIG-OIP-004-LOCAL-24H REPLAN_REQUIRED | 1.0.0-local | org + active plan + checkpoint + policy | Existing local route policy only |
| SIG-OIP-005 DOCUMENT_READINESS_BLOCKED | 1.0.0 | org + shipment + milestone/target + readiness policy | Authoritative MDPM decision |
| SIG-OIP-006 ACTIVE_DELAY_OR_EXCEPTION | 1.0.0 | org + source type + source opaque ID + policy | No threshold; active source state |
| SIG-OIP-007 EXECUTION_UNIT_STALE | 1.0.0 | org + execution unit + policy major | Inactive: freshness duration not authorized |

No missing threshold defaults to zero. Invalid or absent authority disables the affected policy and appears through `/api/oip/policies` and reconciliation results.

## Situation, projection and API contracts

Situation has opaque identity, tenant, subject reference, approved type/status, severity/urgency/priority, timestamps, assignee, recurrence, policy/projection versions, watermark/freshness, disposition data, and optimistic version. Evidence links FactReference → Signal → Situation. Repeated active observations update one identity; clear resolves it; recurrence reopens it, increments occurrence count, and retains history.

Queue ordering is priority, urgency, severity, due time, then opaque public ID. Explanations expose the drivers. Snooze requires future expiry and reason; resolve/dismiss require reason. Every mutation requires `oip.manage`, expected version, actor, tenant-first lookup, and audit. Reconciliation requires `oip.reconcile`; reads require `oip.read`. Opaque Situation IDs are the only OIP route identifiers.

The attention workspace replaces the existing page presentation while retaining the `/operations/work-queue` route and `OperationalWorkItem` source behavior. It shows no KPIs or charts. DecisionContext is computed read-only and exposes source evidence, blockers, time pressure, missing information, permissions, versions, freshness, recommendation, and existing action target.

## Rebuild, outcomes and downgrade

Facts/signals/attention links are replayable; Situation and history are durable. Reconciliation is tenant-scoped, idempotent by deterministic identity/watermark, and marks projection state `REBUILDING` then `FRESH`. Stale/degraded states are explicit fields and UI labels. History preserves detected, acknowledged, intervention-started, resolved/dismissed, and reopened timestamps. It never asserts operational recovery. Downgrade fails closed when Situation/history evidence exists.


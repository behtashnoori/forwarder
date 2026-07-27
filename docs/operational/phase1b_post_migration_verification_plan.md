# Phase 1B post-migration verification plan

## Scope

This plan is for a later, separately approved migration gate. Nothing here was executed against a persistent database. Verification evidence must be sanitized and must not contain row data, customer/user/shipment identities, credentials, or raw connection strings.

## Database verification

| Control | Expected result |
|---|---|
| Alembic revision | Exactly `20260801_route_exception` |
| Pending revisions | Zero; one local head |
| Encoding/collation/timezone | Unchanged from pre-migration inventory |
| Tables/columns | All objects defined by the two approved revisions are present |
| Constraints/indexes | Expected same-scope FKs, unique/check constraints, partial open-exception uniqueness, and indexes are present and valid |
| Migration function/trigger | Expected validation function/trigger metadata matches the approved migration definition |
| Shipment duplication | Zero duplicate groups under the documented canonical key |
| RoutePlan graph | Zero partial plans, invalid active-plan cardinality, invalid versions, self-dependencies, or cross-plan edges |
| Checkpoint/milestone state | Zero invalid status/verification transitions or ownership combinations |
| Exception/work item | Zero orphan or cross-scope rows; reconciliation fields obey constraints |
| Cross-organization relationships | Zero violations |
| Audit/outbox/idempotency | Required structures present; scoped idempotency metadata valid |
| Database size/connections | Within the documented expected class and baseline tolerance |

All integrity checks must be bounded aggregate queries with statement timeout and no row output. Any non-zero violation count is a No-Go and rollback decision trigger.

## Minimal application smoke

After database checks pass and the approved application artifact starts:

1. health and readiness endpoints return the expected status;
2. login succeeds for designated synthetic/test principals;
3. shipment list and detail load without duplicates;
4. active RoutePlan, legs, checkpoints, milestones, and dependencies render correctly;
5. milestone reporting and verification follow permission/state rules;
6. authorized correction succeeds and Reporter correction remains denied as designed;
7. replan and exception/work-item surfaces behave consistently;
8. no unexpected 5xx, CORS error, stale backend target, duplicate-fetch loop, or unhandled client error occurs.

Any write-capable smoke action requires an explicitly approved synthetic record and cleanup/reconciliation plan. Otherwise use read-only surfaces and designated pre-existing test fixtures.

## Monitoring and rollback triggers

Observe at 0–15 minutes, one hour, and 24 hours:

- 5xx rate and database exceptions;
- lock waits, long-running queries, connection saturation, and resource pressure;
- migration-related exceptions, outbox backlog, and audit failures;
- RoutePlan graph/integrity errors and duplicate shipment display;
- permission-denial anomalies and unexpected correction/replan failures.

Before execution, owners must assign numeric/operational thresholds based on the environment baseline. Immediate rollback evaluation is required for any integrity violation, unknown schema state, persistent critical smoke failure, sustained database unavailability, cross-organization exposure, or evidence of data loss/corruption.

## Evidence and closure

The verifier records target fingerprint, application commit, migration revision, timestamps, aggregate results, smoke outcomes, monitoring snapshots, deviations, and Go/No-Go decision. Closure requires database owner, technical owner, and business/Go-No-Go authority acceptance. Raw logs must be redacted before attachment.

## Current isolation state

- Product source changed: NO
- Migration or seed executed: NO
- Persistent database changed: NO
- Production repository/service/port 5001 touched: NO
- Public PostgreSQL touched: NO
- Merge, deploy, commit, or push performed: NO

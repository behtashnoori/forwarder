# Release 1.9.0 final RC review

Date: 2026-08-04

Outcome: **BLOCKED**. Production was not accessed or changed.

## Passed evidence

- PostgreSQL 18.0 ran on `127.0.0.1:55418` from `C:\Program Files\PostgreSQL\18\bin` with a disposable data directory.
- The repository migration runner upgraded an empty database to the single `20260812_operational_execution` head with no pending revision.
- `operational_milestone.route_plan_id` is nullable at the Release 1.9 head.
- The Release 1.9 migration created zero DelayReason, ExceptionReason, or Milestone rows.
- An upgrade from `security_credential_remediation` preserved three representative RoutePlan-backed milestones and three shipments.
- `fk_operational_milestone_plan_shipment` rejected raw cross-shipment and cross-tenant RoutePlan updates.
- A downgrade with a NULL RoutePlan milestone failed closed with SQLSTATE 23502. After satisfying the documented precondition, downgrade restored `NOT NULL`; re-upgrade restored nullable and preserved all legacy rows.
- The repository Phase 1B authenticated fixture succeeded on PostgreSQL 18 after adding required organization ownership to its milestone events.

Historical migrations include their existing reference-data migration. The Release 1.9 revision itself did not add or mutate reference data.

## Blocking findings

1. On the authenticated shipment detail page, the Release 1.9 initialization panel rendered `0 expected milestones` and disabled confirmation while the same authenticated preview API returned one active, valid Project milestone definition with `confirmation_allowed: true`.
2. Operational list/detail/timeline/checkpoint UI visibly exposes numeric shipment, quote, request, plan, and checkpoint identifiers. This fails the requested no-numeric-ID browser security gate.
3. Because initialization could not be confirmed through the browser, downstream lifecycle, correction/verification, delay, exception, progress, and complete role-matrix browser flows are not approved.

No files are approved for staging and no corrective RC commit may be created until these findings are resolved and fresh evidence is collected.

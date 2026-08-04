# Release 1.9.0 Operational Execution Implementation Review

## Baseline and scope

Implementation started from `61ba2e6298f96bd230e19516ab222ddba3600661` on `feature/case-document-management-phase1a`; governance commit `ea17e1f` and Security Track commit `61ba2e6` were ancestors. The bounded non-Evidence PDR-018/ADR-029 slice is implemented. Evidence, dashboards/reporting, automation, Shipment-status derivation, Seed/catalog apply, and Production activity remain excluded.

## Aggregate, initialization, and lifecycle

The existing `operational_milestone` is reused and extended with opaque identity, organization/Shipment scope, immutable Project definition/type/point/target snapshots, sequence, lifecycle timestamps, and optimistic versioning. Preview is read-only; confirm is explicit, atomic, idempotent, version-checked, and creates only active valid Project definitions. No creation/view/backfill path initializes milestones. The explicit table supports PENDING, READY, IN_PROGRESS, COMPLETED, SKIPPED, CANCELLED, and BLOCKED. Block retains the prior active state; terminal states reopen only through the elevated correction permission and a reason.

## Events, Delay, Exception, and progress

MilestoneEvent remains append-only with occurred/effective and recorded instants, public identity, tenant, actor, channel, notes, correction lineage, and verification metadata. Verification is permission-separated and self-verification is refused. Delay and Exception remain separate records and never replace milestone or Shipment status. Their reason catalogs are organization-scoped, administrator-managed, immutable-code, versioned, and empty after migration.

Progress is calculated as `(COMPLETED + SKIPPED) / (total - CANCELLED) * 100`, returning zero for a zero denominator. It reports all lifecycle counts, the first non-terminal sequence as current, and active Delay/Exception counts.

## Permissions, APIs, and UI

The internal opaque-ID API uses `operational_execution.read/manage`, `operational_event.create/correct/verify`, `delay_reason.manage`, and `exception_reason.manage`; organization-first lookups return tenant-safe 404 responses. The Shipment UI provides preview/confirm, milestone controls, conditions, progress, and immutable timeline with responsive layouts and governed selectors. The administrator UI provides empty-state catalog creation and activation/deactivation.

## Migration, PostgreSQL, and performance

`20260812_operational_execution` descends from `security_credential_remediation` and is additive. It creates no Reference Data or Milestone rows, performs no Shipment backfill, and adds organization-leading composite foreign keys and timestamp/status/version constraints. PostgreSQL 18 matrix results are recorded in the final implementation report; no Production database was accessed. The execution screen performs bounded parallel reads; indexes lead with organization and Shipment. Progress is calculated without a summary table. No Production SLA claim is made.

## Compatibility, limitations, rollout, and rollback

Existing route plans, checkpoints, legacy milestones/timeline, Project configuration, cargo, documents, and security behavior remain supported. No Evidence, business calendar, SLA analytics, notification/escalation, dashboard, workflow engine, public/customer API, or automatic status/initialization exists. Rollout is internal and opt-in after RC validation. Rollback disables new UI/routes first; appended history must be retained before schema downgrade.

## Final decision

**RELEASE 1.9.0 IMPLEMENTATION APPROVED FOR COMMIT.** Repository, OpenAPI, frontend/backend, and disposable PostgreSQL 18 gates completed successfully. Status remains Implemented, Not Published, and Not Deployed.

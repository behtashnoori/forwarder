# Release 1.8.0 Final RC Review

- **Candidate:** 1.8.0 — Project Configuration Foundation
- **State:** Implementation Complete — Not Published — Not Deployed
- **Migration:** `20260811_project_configuration` after `20260810_logistics_network`
- **Production:** unchanged
- **Seed:** not executed

## Scope, authority, and exclusions

The exact scope is opaque `DocumentDefinition.public_id`; governed MilestoneType; organization-scoped ProjectService, ProjectDocumentRequirement, and ProjectMilestoneDefinition; elapsed target/warning durations; four authorized selectors; bounded CRUD/lifecycle/reorder APIs; and the Services, reused Network, Documents, and Milestones UI panels. PDR-017, ADR-027, the Slice Contract, Governance Closure, and Identity Amendment remain aligned.

No workflow, SLA engine, defaults, visibility engine, snapshots, automatic operational-object creation, enforcement, reporting, GIS, ETA, allocation, or AI was added. The MilestoneType catalog is prepared and checksummed but not applied. No publication, package, tag, push, deployment, Production access, or Production Seed is claimed.

## Identity, domain model, and migration

The migration adds `document_definition.public_id` through nullable-add, independent UUIDv4 backfill, uniqueness, and non-null enforcement. Numeric primary keys and existing internal foreign keys remain intact, preserving legacy numeric case-document compatibility. Every new configuration API accepts and returns opaque public IDs only.

The three Project-owned configuration models have optimistic versions, active lifecycle, audit data, duplicate prevention, and bounded ordering. ProjectService enforces one active primary. ProjectDocumentRequirement reuses DocumentDefinition and supports REQUIRED, OPTIONAL, and CONDITIONAL with a descriptive non-executable condition. ProjectMilestoneDefinition supports positive elapsed target/warning values, DAY/HOUR unit validation, unique active sequence, reorder, and an optional ProjectLogisticsPoint.

The same-Project database boundary is enforced by composite parent candidate key `uq_project_logistics_point_project_id_id` and composite child FK `fk_project_milestone_definition_project_point`. Disposable PostgreSQL probes accepted valid/null references and rejected same-tenant cross-Project and cross-tenant references.

## API, selectors, UI, permissions, and isolation

Runtime and OpenAPI cover create/update/response/list schemas for all three resources, lifecycle actions, milestone reorder, pagination metadata, validation/conflict responses, and four selectors. Lists use bounded pagination, filters, and allowlisted sorting. Automated parity checks require every documented method to exist at runtime and every 1.8.0 runtime method to be documented; schemas contain no generic resource placeholder or numeric identity field.

ServiceType, DocumentDefinition, MilestoneType, and ProjectLogisticsPoint selectors are dedicated internal reads, exclude inactive rows, expose public identity only, apply search/pagination bounds, and do not depend on admin-only legacy routes. The security matrix covers admin, authorized manager/expert, read-only expert, unauthorized authenticated, unauthenticated, and foreign tenant behavior. Foreign Projects are non-disclosing 404s.

The responsive Project Configuration UI covers service flags/order/labels/notes, document requirement levels/conditional description, milestone durations/unit/point/reorder/mixed lifecycle, optimistic conflicts, read-only and loading/error states. The existing 1.7.0 Network component is reused exactly once. Component evidence covers Persian RTL, supported English LTR, desktop/mobile width, horizontal-overflow protection, labels/accessibility names, and keyboard-focusable primary actions.

## PostgreSQL and performance evidence

The [PostgreSQL migration and performance evidence](release-1.8.0-project-configuration-performance-evidence.md) records PostgreSQL 18 fresh, previous-head upgrade, downgrade, re-upgrade, UUIDv4 backfill, constraint probes, and a representative two-tenant fixture. It records bounded SQL counts, payload bytes, local timings, and EXPLAIN/index observations. Milestone reads remained constant at 12 statements for five and ten rows after a focused eager-load correction; no material read N+1 or large-child sequential scan remained. Reorder writes are bounded and versioned. These are local development observations, not a Production SLA.

No persistence or query file changed after the final same-Project evidence run except documentation reconciliation. Therefore the evidence remains current for this worktree. The fixture created zero OperationalShipment, RoutePlan, operational Milestone, or OperationalEvent rows.

## Compatibility, limitations, and rollback

Existing Projects, ProjectLogisticsPoints, DocumentDefinition numeric identities/FKs, case-document APIs, shipments, routes, checkpoints, documents, and cargo behavior remain compatible. Elapsed durations are not an SLA; conditional descriptions are not executable; current configuration is not a historical snapshot; reporting and external visibility remain unauthorized.

Before dependent configuration exists, authorized downgrade removes the additive tables and opaque column while retaining legacy numeric data. After configuration data exists, application rollback should retain additive schema; destructive database downgrade requires explicit data preservation/export authority.

## Final RC recommendation

The final recommendation is **RELEASE 1.8.0 RC APPROVED FOR COMMIT**, conditional on the current-worktree full backend/frontend, TypeScript, ESLint, build, static, documentation/security, OpenAPI parity, one-head, and explicit staging checks all passing. This recommendation authorizes only the bounded implementation commit; it does not authorize publication or deployment.

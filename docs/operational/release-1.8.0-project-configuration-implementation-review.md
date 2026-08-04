# Release 1.8.0 Project Configuration Implementation Review

Status: **Implemented — Not Deployed**. Change type: MINOR. Deployment type:
backend-frontend-migration. Migration `20260811_project_configuration` follows
`20260810_logistics_network`. Production Seed was not executed.

## Scope and exclusions

The implementation adds opaque DocumentDefinition identity, MilestoneType,
ProjectService, ProjectDocumentRequirement, ProjectMilestoneDefinition, elapsed
target/warning durations, internal APIs, and a four-panel Project Configuration UI.
It reuses ProjectLogisticsPoint. It does not add SLA calendars, snapshots,
visibility rules, workflow, document enforcement, or operational-object creation.

## Identity and domain model

The migration adds nullable `document_definition.public_id`, backfills each existing
row with an independently generated UUIDv4, enforces uniqueness and NOT NULL, and
does not alter numeric PK/FK values or semantic fields. New ORM rows generate UUIDv4.
New configuration APIs resolve and project only public identity; legacy case-document
routes retain numeric contracts.

The three Project children preserve history through activate/deactivate. Unique
logical associations, one active primary service, one active milestone sequence,
positive durations, a shared duration unit, warning >= target, and same-Project
logistics-point linkage are enforced by application and database constraints.

## Catalog, API, UI, permissions, and isolation

The separate `milestone-types-1.0.0` catalog contains exactly 13 accepted codes and
a deterministic approved checksum. Plan is read-only; apply is explicit, idempotent,
audited, conflict-refusing, and Production guarded. It is never auto-applied.

Internal routes live under `/api/v2/projects/{project_public_id}/configuration`.
They support list/detail/create/update/activate/deactivate and milestone reorder with
optimistic 409 behavior. Project lookup is organization-first and cross-tenant access
is a non-disclosing 404. Permissions are `project_configuration.read/manage` and
`milestone_type.read/manage`; admin-only MilestoneType mutation follows existing role
controls. The RTL, responsive UI exposes Services, reused Network, Documents, and
Milestones panels with governed selectors and no free-text governed identity.

## Verification and compatibility

Focused tests cover opaque identity, catalog shape, permission boundaries,
cross-tenant behavior, duplicate conflicts, conditional-document and duration
validation, and the single Alembic head. Full gate and disposable PostgreSQL evidence
must be recorded below after execution; no Production environment is used.

Legacy numeric DocumentDefinition identity and CaseDocumentRequirement foreign keys
remain unchanged. Existing Projects, network points, shipments, route plans,
checkpoints, operational milestones, documents, and cargo receive no automatic rows
or mutations.

## Performance observations

Configuration lists are bounded by a single Project and use relationship loading
consistent with the existing foundation. Development observations only; no
Production SLA is asserted.

## Rollout, rollback, and limitations

Rollout requires normal RC validation followed by an explicitly authorized migration
and separately authorized catalog apply. No deployment is part of this work. Before
configuration data exists, downgrade removes the four tables and public identity;
after dependent configuration exists, destructive downgrade requires export/data
retention authority. Durations are elapsed values only, conditional requirements are
descriptive only, and configuration creates no operational milestones.

Final implementation decision: **BLOCKED — not approved for commit**. PostgreSQL,
backend regression, frontend regression, build, lint, TypeScript, compile, Ruff,
OpenAPI parse, and diff gates passed. Remaining defects are: configuration lists do
not yet implement the required bounded pagination/filter/sort contract; ServiceType
and DocumentDefinition selectors still depend on admin-only legacy endpoints rather
than dedicated authorized-manager selectors; focused UI tests and measured SQL/N+1/
payload evidence are incomplete; and all mandated governance registers have not yet
been reconciled to Implemented / Not Deployed. No files were staged or committed.

## PostgreSQL evidence follow-up — 2026-08-04

See [Release 1.8.0 PostgreSQL Migration and Performance Evidence](release-1.8.0-project-configuration-performance-evidence.md).
The supported fresh, previous-head, downgrade/re-upgrade, UUID backfill, bounded
query and constraint checks ran on disposable PostgreSQL 18. A narrow eager-load
defect was corrected. Final evidence is nevertheless **REJECTED — MIGRATION OR
DATA-INTEGRITY FAILURE** because PostgreSQL accepts a ProjectMilestoneDefinition
whose ProjectLogisticsPoint belongs to another Project and organization. The
service rejects it, but the database-level same-Project constraint is absent.
Release 1.8.0 remains blocked and is not approved for commit.

## Same-Project database boundary resolution — 2026-08-04

The preceding rejection is retained as defect history and is now resolved. The
bounded fix adds `uq_project_logistics_point_project_id_id` and
`fk_project_milestone_definition_project_point`, with ORM metadata matching the
migration and no redundant single-column point FK. Nullable point references and
existing numeric primary keys remain unchanged. Fresh, previous-head,
downgrade/re-upgrade, UUIDv4 backfill, raw negative probes, mapper checks, focused
tests and representative PostgreSQL performance evidence passed. No Seed,
Production access, operational side effect or release operation occurred.

Final evidence decision: **SAME-PROJECT DATABASE INTEGRITY FIX VERIFIED**. No
remaining defect is known within this authorized integrity-fix scope. Full
governance-register reconciliation remains a separate task, as directed.

## Final governance and RC reconciliation — 2026-08-04

The governance registers, acceptance traceability matrix, and final RC review are
now reconciled to **Implemented — Not Deployed**. The earlier blocked/rejected
statements above are retained as review history and are superseded by the focused
pagination/selectors/UI/performance corrections, same-Project database fix, and
current-worktree gates. Release 1.8.0 is implementation complete, not published,
and not deployed. The MilestoneType catalog is prepared but not applied; Production
is unchanged and Seed was not executed. Defaults and snapshots remain deferred;
automatic execution side effects, reporting, and a visibility engine remain absent.

Final RC decision: **RELEASE 1.8.0 RC APPROVED FOR COMMIT**, subject to the final
full-gate and explicit-stage audit recorded at commit time. Publication, deployment,
Seed apply, packaging, tagging, and pushing remain unauthorized.

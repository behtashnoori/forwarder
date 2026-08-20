# Architecture Review Checklist

Use this checklist for implementation review and PR approval. Mark non-applicable items with a reason.

## Boundaries and ownership

- [ ] Affected aggregate and canonical owner are named.
- [ ] Canonical models are used; each legacy model touch has explicit compatibility authority.
- [ ] No new hidden cross-domain write or shared mutable truth exists.
- [ ] Document, cargo, CRM, logistics, tracking, and projection ownership match the baseline.

## Tenant and authorization

- [ ] Organization scope comes from authenticated context, hostname binding, or authorized parent.
- [ ] Body/query organization identity cannot broaden access.
- [ ] Cross-tenant parent, assignment, catalog, document, cargo, and project references fail closed.
- [ ] Backend authorization is enforced independently of UI visibility.
- [ ] Platform-admin and organization-admin authorities remain distinct.
- [ ] Quarantined/ambiguous legacy data is excluded from normal runtime paths.

## Time and API contracts

- [ ] Each temporal value has an explicit semantic type.
- [ ] New Instants use aware UTC backend values and timezone-aware DB columns.
- [ ] APIs emit RFC 3339 Instants with `Z` or offset; proven UTC is never offset-less.
- [ ] Local Dates are not parsed through UTC midnight.
- [ ] Browser/business timezone conversion occurs exactly once.
- [ ] Public IDs, pagination, stable errors, and compatibility contracts are preserved.

## Schema and migration safety

- [ ] Migration is additive/expand-first and retains a sole Alembic head.
- [ ] Backfill is explicit, idempotent, bounded, observable, and reversible or fail-closed.
- [ ] No migration/seed runs at import or startup.
- [ ] Downgrade/application rollback and evidence retention are documented.
- [ ] N/N-1 compatibility and existing-row behavior are tested.

## Integrity and operations

- [ ] Retry-sensitive commands have idempotency identity and request-hash behavior.
- [ ] Concurrent mutations use expected version/locking and PostgreSQL evidence where required.
- [ ] Audit records actor, scope, action, reason, correlation, and safe metadata.
- [ ] Logs/errors do not expose secrets, forbidden tenant data, or sensitive payloads.
- [ ] Performance is bounded with indexes, pagination, query-count or load evidence as appropriate.
- [ ] Rollback and failure behavior are deterministic and fail closed.

## Domain-specific checks

- [ ] Reference/master data uses explicit domain tables and approved authority; catalog apply is explicit and audited.
- [ ] Document requirements are not treated as files; upload is not approval; exact artifact versions are preserved.
- [ ] Cargo catalog edits do not rewrite shipment snapshots; no unit allocation is inferred.
- [ ] New location work uses the accepted LogisticsPoint/CanonicalLocation boundary, not an accidental legacy selector dependency.
- [ ] Tracking events preserve occurred versus recorded time, source, visibility, and historical snapshots.
- [ ] CRM remains internal/role-gated unless an Accepted ADR authorizes integration or permission redesign.

## Validation

- [ ] Unit, contract, tenant-negative, migration, PostgreSQL/concurrency, and UI tests cover the changed risk.
- [ ] Python compile, TypeScript compile/build, lint, `git diff --check`, sole-head check, and changed-scope secret scan pass as applicable.
- [ ] Architecture-governance checks pass.
- [ ] Deviations are `NONE` or backed by an Accepted ADR.

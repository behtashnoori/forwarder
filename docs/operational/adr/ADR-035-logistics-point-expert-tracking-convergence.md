# ADR-035: LogisticsPoint Convergence for Expert Tracking Locations

- Status: ACCEPTED
- Date: 2026-08-20
- Owners: Product, Architecture, Operations, Data, Security
- Affected domain: Logistics Network, legacy expert tracking, public tracking

## Context

ADR-025 establishes organization-owned `LogisticsPoint` as the governed logistics-place master and `ProjectLogisticsPoint` as Project configuration. ADR-005 establishes `CanonicalLocation` as the route-facing identity/snapshot abstraction. The architecture baseline classifies `TrackingLocationReference`, `ShipmentTransportUnit`, and `ShipmentTransportUnitUpdate` as compatibility models.

The current expert selector reads the global, platform-managed `/api/tracking-locations` catalog and submits its sequential numeric `location_reference_id`. A legacy update stores that reference plus `location_name_snapshot`, `country_code_snapshot`, and free text. Consequently, an active `LogisticsPoint` created by an Organization Admin is not selectable by that organization's experts.

`LogisticsPoint` already has opaque `public_id`, explicit `organization_id`, active lifecycle, governed type, bilingual names, governed country/province/city, and organization-scoped query services. It has no aliases. `CanonicalLocation` currently permits only geographic/platform source types and has neither organization ownership nor a `logistics_point` source type. `ShipmentTransportUnitUpdate` has an explicit tenant ownership envelope inherited from its legacy unit, but no canonical location FK.

## Problem

Decide how new legacy expert-tracking writes may use the canonical organization location master while preserving old reference identity and immutable display history. This is a legacy-to-canonical authority change and cross-domain write, so the baseline requires an Accepted ADR before implementation.

This decision is bounded to the existing expert multi-unit tracking workflow and its internal/public projections. It does not redesign tracking around `ExecutionUnit`/`OperationalEvent`, generate routes, alter Project configuration, backfill history, geocode places, or merge location catalogs.

## Decision

If accepted:

1. `LogisticsPoint` remains the canonical organization-owned location master. `TrackingLocationReference` remains a read-only compatibility authority for rows already referencing it and for explicitly identified compatibility clients; it is not populated from `LogisticsPoint` and receives no new long-term master-data role.
2. New expert selector reads use an additive tenant-scoped endpoint returning active `LogisticsPoint` rows for the authenticated active membership's organization. The browser cannot supply or override organization ownership. Selector identities are opaque `LogisticsPoint.public_id` values; numeric database IDs are never exposed as authority.
3. The selector may filter by bounded search, country code, and LogisticsPointType immutable code. Search covers Persian name, English name, and immutable code only. Alias search is absent until aliases become an Accepted `LogisticsPoint` contract. Only active points and active types are selectable.
4. Add nullable `logistics_point_id` to `ShipmentTransportUnitUpdate`, retaining nullable `location_reference_id`, `location_text`, and existing snapshots. Add a composite database foreign key from `(logistics_point_id, operational_organization_id)` to `(logistics_point.id, logistics_point.organization_id)` so storage independently rejects cross-tenant associations. The existing unit/update tenant envelope remains authoritative.
5. Add snapshots sufficient for deterministic historical display: `location_name_snapshot`, `country_code_snapshot`, plus nullable `location_name_en_snapshot`, `location_type_code_snapshot`, and `location_city_name_snapshot`. Existing columns retain their meaning. No snapshot is refreshed after insert when master data is renamed, moved, or deactivated.
6. Exactly one new-write location authority is accepted: canonical `logistics_point_public_id`, manual `location_text`, or an explicitly retained legacy `location_reference_id` compatibility input. Ambiguous simultaneous authorities fail validation. Canonical selection has no implicit fallback to a same-named legacy row.
7. Internal serialization reports `location_source` as `logistics_point`, `manual`, `legacy_reference`, or `unavailable`. Display text resolves from stored canonical snapshots first, stored legacy snapshots second, manual/free-text snapshot third, then unavailable. Master rows are not consulted to replace stored historical text.
8. Public tracking returns only allowlisted snapshots and source classification needed for display. It exposes no numeric location IDs, organization IDs, internal codes, hidden master metadata, or inactive-state details.
9. The existing legacy tracking write remains append-only. `occurred_at` continues its proven legacy UTC-naive storage and explicit-offset serialization contract under ADR-016; this slice adds or reinterprets no temporal field.
10. The Logistics Network UI explains that organization locations are reusable standardized choices for planning and shipment updates. The expert UI labels the section `مکان لجستیکی`, explains its organization-managed source, retains `محل در فهرست نیست`, and does not imply routing or optimization.

Explicit exclusions: automatic routing, route optimization, maps, GPS, geocoding, automatic master creation from free text, Project route redesign, historical rewrite/backfill, deletion of legacy references, `CanonicalLocation` source-type expansion, canonical `ExecutionUnit` tracking redesign, Production access, deployment, and release publication.

## Alternatives

- Continue expanding `TrackingLocationReference`: rejected because it is global legacy compatibility data and would compete with the accepted organization master.
- Silently replace the existing endpoint/catalog: rejected because identity, tenancy, filters, consumers, and history differ.
- Store only a mutable `LogisticsPoint` FK: rejected because later master edits would rewrite historical display meaning.
- Extend `CanonicalLocation` with `logistics_point` in this slice: deferred because its current global source identity lacks tenant ownership and changing it affects route consumers beyond this bounded workflow.
- Store only copied text without identity: rejected because standardized identity and safe reporting would be lost.
- Backfill legacy references by name/country: rejected because matches are ambiguous and would invent tenant ownership.
- Move the workflow directly to `ExecutionUnit` and `OperationalEvent`: deferred to a separately governed tracking migration slice under ADR-018/019.

## Consequences

Organization-created places become immediately available to same-tenant experts without duplicating master data. Historical labels remain stable after rename/deactivation, manual reporting remains possible, and old legacy-reference rows remain readable. Costs are an additive FK/snapshot migration, dual compatibility serialization, stricter input contracts, and additional tenant-negative coverage. The legacy tracking aggregate remains temporarily active rather than becoming canonical.

## Compatibility

Existing `ShipmentTransportUnitUpdate` rows and `location_reference_id` values are unchanged. Existing public tracking text continues to derive from stored snapshots/free text. The old selector endpoint remains available to its existing admin/compatibility consumers during an explicit deprecation period; the expert UI switches only after the additive endpoint and write contract are deployed together. N/N-1 application compatibility requires all new columns to be nullable and old writers to remain valid.

Legacy-reference write acceptance is limited to explicitly identified compatibility clients and must not be the default expert UI path. Removing that input or the legacy endpoint requires consumer inventory, usage evidence, notice, rollback rehearsal, and a separately accepted contract decision.

## Migration impact

An additive nullable migration is required. It adds `logistics_point_id`, the additional snapshot columns, a tenant-consistent composite FK, and a bounded selector/write index. It performs no data backfill and does not alter or drop legacy columns, constraints, or rows. Upgrade, downgrade, and re-upgrade must be certified against the resolved sole Alembic head on disposable PostgreSQL. Downgrade removes only unused new constraints/indexes/columns and is prohibited if canonical-linked rows exist unless application rollback and retained-data handling have been explicitly reconciled.

## Security/tenant impact

The authoritative organization is derived from the authenticated user's active `OperationalMembership` and the already-authorized tenant-owned `ShipmentTransportUnit`; request body/query organization values are rejected or ignored and never broaden scope. Lookup requires active organization, active membership, required permission, active point, active point type, and exact organization match before serialization or mutation. Cross-tenant, inactive, malformed, and unknown public IDs fail closed with non-enumerating errors. The composite FK is defense in depth, not a substitute for service authorization. Logs and public responses omit tenant internals and numeric master IDs.

## Operational impact

The selector query is bounded, tenant-indexed, paginated or capped, and search terms/filter values are length-limited. Empty, loading, and failure states retain manual entry. Metrics distinguish canonical, manual, legacy, unavailable, inactive rejection, and cross-tenant rejection without recording sensitive location text. Rollout order is migration, compatible backend, tested frontend switch, then observation; it is not a Production/deployment authorization.

## Rollback

Disable the canonical selector and canonical write input, return the expert UI to manual/legacy compatibility behavior, and continue reading stored canonical snapshots for rows already created. Do not null FKs, rewrite snapshots, manufacture legacy references, or delete master rows. Preserve added data for reconciliation. Database downgrade is allowed only before canonical adoption or after an explicit retained-data export/reconciliation gate.

## Validation

- Same-tenant newly created active point appears; inactive and cross-tenant points do not.
- Persian/English search and country/type filters are tenant-scoped; unsupported alias behavior is not claimed.
- Same-tenant canonical write succeeds and snapshots remain unchanged after master rename/deactivation.
- Cross-tenant, inactive-point, inactive-membership, malformed-ID, and organization-override writes fail closed.
- Canonical, manual, legacy, and unavailable inputs are mutually exclusive and serialize deterministically.
- Historical legacy-reference and free-text rows remain unchanged and readable internally and publicly.
- Public canonical/legacy projections expose correct text and no numeric IDs or tenant metadata.
- Explicit UTC tracking timestamp serialization remains compliant with ADR-016.
- Migration upgrade/downgrade/re-upgrade passes on disposable PostgreSQL and leaves one Alembic head.
- Focused logistics/tracking/tenant/public tests, full backend/frontend suites, Python compile, Ruff changed scope, TypeScript, ESLint, Vite build, architecture governance, diff check, and secret scan pass before commit.

## Supersedes / superseded by

- Supersedes: none; complements ADR-005, ADR-016, ADR-018, ADR-019, ADR-025, ADR-026, ADR-028, and ADR-029.
- Superseded by: none

## Status history

- 2026-08-20: PROPOSED — required by the architecture gate before changing the expert selector from legacy tracking references to organization-owned LogisticsPoint authority. Proposal is not implementation authority.
- 2026-08-20: ACCEPTED — approved as implementation authority for the bounded LogisticsPoint convergence decision described in this ADR.

# ADR-056: Governed Reference Catalog and Organization Activation

- **Status:** ACCEPTED — bounded P3-01 architecture and implementation authority
- **Date:** 2026-09-25
- **Owners:** Product Owner for the authorized Product behavior; Platform Architecture and Data for catalog structure; Security for authority boundaries; Operational Organization for tenant activation state
- **Affected domain:** Platform reference data, organization configuration, Cargo selectors
- **Implementation state:** P3-01 candidate in progress; qualification, Product acceptance, Release Ready, deployment, and Production use are not established by this ADR
- **Mission authority:** [P3-01 Reference Catalog Mission Contract](../../product/phase3/P3-01-REFERENCE-CATALOG-MISSION-CONTRACT-FA.md)

## Context

P3-01 must let an Organization Admin decide which approved central definitions are available for new use in that organization, while a Transport Expert selects only organization-approved options. Deactivation must stop new selection without changing historical snapshots or making prior records unreadable.

The repository already contains explicit platform-scoped `CargoType`, `UnitOfMeasure`, and `ServiceType` models under ADR-021 and administrator-managed empty-catalog behavior under ADR-028. ADR-022 keeps `CargoCatalogItem` organization-owned and makes `ShipmentCargoItem` the historical transaction snapshot. ADR-036 keeps `DocumentDefinition` and the existing organization/project/case document-policy chain under their present owners. ADR-041 establishes the separate platform `GlobalLogisticsPoint` to tenant-owned adoption pattern and has progressed through local platform governance, organization adoption, explicit tenant-point materialization, and current `LogisticsPoint`-based operational consumption. Its history is preserved and is not re-authored here.

Three required reference families do not have equivalent explicit central models: packaging type, transport means type, and transport equipment/load-unit type. The legacy `TransportMethod` catalog has different identity/version and Request-compatibility semantics. Reinterpreting or replacing it in P3-01 would exceed the approved boundary.

The Product Contract describes future organization-specific definitions and platform review/promotion, but decision `DN08` remains open. The P3-01 mission therefore authorizes only central definitions and tenant-owned activation of those definitions. It does not authorize organization-specific definition creation or promotion.

## Product Authority Record

| Field | P3-01 value |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Controlled central definitions; Organization Admin active/inactive availability for new tenant use; Expert selection only from active organization-approved options; retained historical readability and snapshots after rename/update/deactivation; audit of activation changes. |
| `DELEGATED_TECHNICAL_CHOICES` | Additive explicit tables, names and DTOs, tenant-safe association keys, versioning/concurrency, compatibility adapters, migration/rollback method, and bounded tests, provided they preserve the authorized behavior. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | Existing Request/Cargo/Cargo Catalog/Documents/Global Logistics adoption/Combined Transport/Customer/Public Tracking/Workspace/Control Tower behavior; empty installation; no automatic seed; no implicit Platform Admin tenant authority; no historical snapshot rewrite. |
| `DECISIONS_NEEDED` | `DN08`: organization-specific definition creation, review, and promotion. Those commands, APIs, and UI remain absent. Any other new Product behavior requires separate authority. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner instruction `START PHASE 3 IMPLEMENTATION — P3-01 ONLY`; LPAF v2.7 governs execution; this ADR governs the bounded architecture. |
| `APPROVAL_REFERENCE` | P3-01 mission contract; Phase 3 Implementation Plan P3-01; Product Contract v1 sections 5, 7, and 20; approved Phase 3 UX V2.1. |

This ADR records architecture authority and does not independently grant Product approval beyond the mission.

## Decision

### 1. Explicit central reference families

Keep `CargoType` and `UnitOfMeasure` as the existing platform Systems of Record and add three platform-scoped explicit models:

- `PackagingType` / `packaging_type`;
- `TransportMeansType` / `transport_means_type`;
- `TransportEquipmentType` / `transport_equipment_type`.

These are separate domain tables, not EAV rows and not free text. Each has an opaque immutable `public_id`, an immutable normalized platform `immutable_code`, bilingual names, optional governed description, deterministic display order, active/inactive lifecycle, positive optimistic `version`, and creation/update timestamps consistent with the existing master-data contract. Central catalog mutation requires the existing platform master-data authority.

`TransportMeansType` describes the kind of conveyance used to move Cargo. `TransportEquipmentType` describes the equipment, container, or load unit used with an execution. They are not interchangeable and do not create fleet assets, vehicles, drivers, carriers, execution records, or allocations.

`TransportMethod` is preserved as a legacy Request/intake and Expert-specialization compatibility catalog. P3-01 neither migrates its rows nor changes its readers, identity, lifecycle, or meaning. A later bounded decision may provide a proven adapter; none is inferred here.

### 2. Tenant-owned activation, not tenant-owned definitions

Add one explicit activation model for each P3-01 governed family:

- `OrganizationCargoTypeActivation` / `organization_cargo_type_activation`;
- `OrganizationUnitOfMeasureActivation` / `organization_unit_of_measure_activation`;
- `OrganizationPackagingTypeActivation` / `organization_packaging_type_activation`;
- `OrganizationTransportMeansTypeActivation` / `organization_transport_means_type_activation`;
- `OrganizationTransportEquipmentTypeActivation` / `organization_transport_equipment_type_activation`.

Each activation is `TENANT_OWNED_DIRECT` by non-null `organization_id`, has its own opaque `public_id`, references exactly one central definition, uses a unique `(organization_id, reference_id)` pair, and records `status=ACTIVE|INACTIVE`, optimistic `version`, actor attribution, and timezone-aware timestamps. The tenant comes from the authenticated active membership and never from a body, query, or header override.

Activation means only “available to this organization for new selection.” It does not copy or fork central metadata, transfer ownership of the central row, create a tenant-specific definition, grant use outside the current actor's normal operational authority, or imply platform approval of tenant data.

An inactive activation may be reactivated. The association is not hard-deleted after use. A central definition must be active to become newly selectable or newly activated. Central deactivation or organization deactivation blocks new selection, while existing references and snapshots remain readable.

### 3. Existing ownership boundaries remain authoritative

- `CargoCatalogItem` remains organization-owned reusable Cargo master data. Its organization ownership, code, aliases, and lifecycle are unchanged.
- `ShipmentCargoItem` remains the operational Cargo snapshot under ADR-022. Ordinary catalog or activation changes never regenerate it.
- `DocumentDefinition` remains platform document vocabulary. `OrganizationDocumentRequirement` and project/case/operational document policy keep their current ownership and semantics under ADR-036 and ADR-030. No generic P3-01 activation row is added for documents.
- `GlobalLogisticsPoint` and `OrganizationGlobalLogisticsPointAdoption` remain the location-specific catalog/adoption pattern under ADR-041. P3-01 reuses that ownership principle but does not replace, duplicate, or remap it.
- `ServiceType`, `LogisticsPointType`, `MilestoneType`, HS references, and geography catalogs are not placed behind the new activation API by this slice.

### 4. Consumption boundary and historical meaning

Current P3-01 operational consumption changes only the authenticated Expert Cargo option projection for `CargoType` and `UnitOfMeasure`. The Expert sees a central row only when both the central row and the active tenant's activation are active. An organization with no activations sees a truthful empty option set; there is no implicit “all active” fallback.

The three new families are governed foundation for later authorized slices. P3-01 exposes their central administration and organization activation, but it does not add Packaging, Means, or Equipment fields to Request, Cargo, Route, Execution Unit, or any other operational aggregate.

The authenticated Expert projection `GET /api/internal/cargo-options` keeps its existing envelope and catalog-item behavior, while its `cargo_types` and `uoms` arrays become the intersection of active central definitions and active organization activations. The public `GET /api/request-cargo-options` intake projection is unchanged and outside P3-01; changing public Request validation or availability requires separate Product authority.

Historical payloads and records continue to display their stored snapshots or retained referenced labels. Rename, central deactivation, or organization deactivation affects future selection only. Existing data is never rewritten to the current catalog label, activation state, or version.

### 5. API and UX contract

The existing platform master-data routes extend their bounded `resource` enum with `packaging-types`, `transport-means-types`, and `transport-equipment-types`. They retain opaque identity, immutable code, bounded pagination/search, deterministic ordering, lifecycle transition, optimistic concurrency, and existing Platform Admin authorization.

Organization administration receives `GET /api/admin/organization-reference-catalog/{resource}` and `POST /api/admin/organization-reference-catalog/{resource}/{definition_public_id}/{action}` for the five activation-enabled resources. The list is paginated and reports the central `public_id`, code, names, description, display order and lifecycle; organization state and `selectable`; activation identity/`activation_version` and activation timestamps; and `origin=CENTRAL_SYSTEM`. A transition uses `activate` or `deactivate`. An absent row may be activated without a version; every transition of an existing activation requires its expected `version`, and deactivate requires an existing activation. Stale writes return `409`. Unavailable central rows and tenant denial use stable, non-enumerating responses.

The Admin UI presents each family separately, distinguishes platform lifecycle from organization availability, includes an honest empty state, and makes clear that organization deactivation affects new use in this organization only. It does not offer local-definition creation, promotion, seed/import, or free-text replacement.

The Expert Cargo selector reports only active organization-approved `CargoType` and `UnitOfMeasure` choices. Previously stored inactive choices may be displayed in historical/read-only context but cannot be selected for a new write.

### 6. Authorization and audit

Platform catalog commands require Platform Admin authority and do not imply organization membership. Organization list and transition commands require one active Organization Admin membership and derive exactly one `OperationalOrganization` server-side. Transport Experts may consume only the approved selector projection; they cannot mutate central definitions or activation state. Platform Admin without tenant membership cannot act as Organization Admin.

Positive, wrong-role, inactive-membership, foreign-ID, direct-route, body/query tenant-override, and cross-tenant cases fail closed. Pagination, search, and counts are scoped before evaluation so they do not leak another organization's activation state.

Central definition changes remain governed by the existing version/timestamp and platform-authority contract. Every organization activation creation or transition additionally appends an `OperationalAudit` record containing organization, actor, central reference identity/family, previous and resulting active state, activation version, and timestamp. Audit data is retained without sensitive request content and is not exposed as cross-tenant metadata.

### 7. Installation, migration, compatibility, and rollback

The migration is expand-only from the sole current Alembic head. It creates the three central tables and five activation tables with foreign keys, opaque-identity/code uniqueness, tenant/reference uniqueness, version checks, audit fields, and query indexes. It does not seed a reference row, copy an existing catalog, infer a tenant, translate names, import an external standard, or backfill activation rows.

Consequently, an upgraded organization initially has no P3-01 activation unless an authorized Organization Admin creates it. The compatibility adapter preserves unrelated workflows and legacy readers, but the newly governed Expert Cargo option path has no global-active fallback. This behavior is the specifically authorized organization-approval boundary, not a data migration shortcut.

Application rollback disables the new organization routes/UI and returns compatible code paths where explicitly safe, while retaining central and activation data for reconciliation. Database downgrade may drop the additive tables only when no retained P3-01 data or references exist. Once data exists, default rollback is application rollback with schema/data retained; destructive downgrade requires separate authority and an export/reconciliation plan. Historical snapshots are never deleted or rewritten by rollback.

## Reconciliation with prior decisions

| Decision | Reconciliation |
| --- | --- |
| ADR-021 | Extended with three explicit domain tables and the same stable-code/lifecycle/version governance; no EAV or free-text substitute. |
| ADR-022 | Preserved. `CargoCatalogItem` stays organization-owned and `ShipmentCargoItem` stays the immutable descriptive snapshot. Packaging/means/equipment consumption is not added here. |
| ADR-028 | Preserved. Empty catalogs and empty organization activation sets are valid; install, startup, health, and release do not execute seed/import. |
| ADR-036 | Reused, not generalized. Document vocabulary and policy keep their existing owners and are excluded from the new activation tables. |
| ADR-041 | Reused as the central-to-tenant ownership pattern. Its implemented local phases are acknowledged; location-specific adoption/materialization and selectors remain unchanged. |

No prior ADR is superseded. ADR-056 is the narrower authority for P3-01 reference families and organization activation.

## Validation required

Implementation qualification must bind evidence to the exact Product SHA, previous and resulting migration head, PostgreSQL 18 environment, browser version, configuration/policy, and synthetic actors/tenants. At minimum it covers:

- sole-head upgrade, downgrade/re-upgrade where safe, empty installation, and proof that no seed/backfill occurred;
- explicit-table identity/code uniqueness, immutable codes, optimistic conflicts, activation uniqueness, tenant foreign keys, and central-inactive transition denial;
- Platform Admin catalog access without implicit tenant operation; Organization Admin tenant derivation; Expert read-only consumption; inactive/revoked/wrong-role and foreign-tenant negatives;
- active central + active activation selection, deactivation blocking new choice, reactivation, empty state, and historical snapshot/read continuity;
- compatibility regression for `CargoCatalogItem`, Shipment Cargo snapshots, Document policy, Global Logistics adoption, legacy `TransportMethod`, and unrelated Request/Shipment flows;
- desktop/mobile/RTL Admin and Expert states, including loading, empty, denied, error, conflict, inactive, and reopen behavior;
- OpenAPI, tenant-ownership inventory, ADR/reference alignment, audit evidence, and diff/secret/migration safety gates.

Required journey preparation is `P3-01-ADMIN`, `P3-01-EXPERT`, `P3-01-INACTIVE-HISTORY`, `P3-01-MISSING`, and `P3-01-TENANT`. The affected Product references remain `FWD-J06`, `FWD-J08`, `FWD-J09`, `FWD-IPJ-03`, and the P3-01 boundary of `FWD-IPJ-04`. Slice evidence does not establish a full integrated-journey or Human Product Walkthrough PASS.

## Exclusions and stop conditions

Out of scope are organization-specific definition creation/promotion (`DN08`), seed/import or external-standard qualification, automatic activation/backfill, HS catalog completion, `TransportMethod` migration, Packaging/Means/Equipment operational fields, fleet assets, Carrier/Driver portals, Cargo allocation, route/execution redesign, document policy changes, Global Logistics changes, Customer projection, ETA, delivery, closure, owner transfer, AI, GPS, finance, deployment, and release.

Stop the affected work if it requires a local-definition or promotion workflow, an unqualified seed/import, free text instead of a governed base type, historical snapshot rewrite, implicit tenant selection, or behavior outside P3-01.

## Consequences

The platform gains explicit reusable identities for the missing P3-01 families and each organization gains an auditable availability boundary without copying central definitions. The cost is five association tables, explicit administration, empty-state handling, and stricter tenant-aware selection. Existing organizations do not receive inferred approvals. Future slices can consume Packaging, Means, and Equipment only through separate authorized domain changes that define their own snapshot and history contracts.

## Reference and Product status

```text
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=ALIGNED
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
SLICE_JOURNEYS=NOT_RUN
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN
AUTOMATED_PRODUCT_JOURNEYS=NOT_RUN
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
RELEASE_READY=NO
```

LPAF v2.7 already governs this shape; no generic framework change is required. The ADR, both indexes, architecture baseline, ownership inventory, OpenAPI, and bounded P3-01 status/evidence-preparation record now agree with the current implementation candidate. Alignment must be rechecked at candidate freeze and does not establish Product or journey acceptance.

## Supersession

- **Supersedes:** none
- **Complements:** ADR-021, ADR-022, ADR-028, ADR-036, ADR-041
- **Superseded by:** none

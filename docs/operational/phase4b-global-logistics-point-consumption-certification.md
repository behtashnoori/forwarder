# Phase 4B operational consumption certification

Local implementation baseline: `32d1907af9f02e013484a23910c92c7dacc6c814`.

## Traced operational paths

- Expert UI calls `GET /api/internal/logistics-points/tracking-selector`, which requires `logistics_point.read`, derives the organization from the authenticated membership, and selects active tenant `LogisticsPoint` rows with active point types.
- Tracking UI submits `logistics_point_public_id`. `multi_unit_tracking_service.add_update` resolves the same-tenant active `LogisticsPoint`, stores `ShipmentTransportUnitUpdate.logistics_point_id`, and snapshots tenant name, English name, country, type and city. The independent `location_reference_id` compatibility path and conflicting-authority rejection remain intact.
- Project UI calls the ordinary tenant LogisticsPoint list and submits `logistics_point_public_id` to `POST /api/v2/projects/{project}/logistics-points`. The service scopes both project and point to the authenticated organization and persists `ProjectLogisticsPoint.logistics_point_id`.
- LogisticsPoint list/detail projections may display the allowlisted `global_source` marker already established by Phase 4A. Operational selectors and writes do not read global/adoption lifecycle.

## Certified behavior

Materialized and organization-only points use one operational contract. Cross-tenant opaque IDs fail closed. Global deprecation and adoption deactivation leave the active tenant point selectable. Tenant point deactivation removes it from active selectors and new writes while historical project references and tracking snapshots remain readable. An inactive point type removes either category from ordinary active selectors and prevents new project selection.

Experts receive no catalog, adoption, governance or materialization authority. Platform Admin catalog authority does not create tenant membership. Organization Admin adoption/materialization authority and operational project/tracking permissions remain separate backend checks.

No new operational endpoint, migration, direct global/adoption FK, origin/destination change, legacy mapping, seed, Production operation, deployment or push is part of this certification.

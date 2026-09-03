# S2 — Logistics Network UX Contract

## Scope and data ownership

| Concept | Scope / SOR | User-facing purpose |
| --- | --- | --- |
| `GlobalLogisticsPoint` | Platform/shared governed reference data | Reusable verified facility identity and provenance |
| `OrganizationGlobalLogisticsPointAdoption` | Organization-private governance/audit record | Internal tenant selection, lifecycle, uniqueness and provenance control |
| `LogisticsPoint` | Organization/tenant master data | The single operational point selected by Project and Tracking |

A private point and a reference-derived point are both `LogisticsPoint` objects. A private point has no global/adoption links. A reference-derived point retains `global_logistics_point_id` and `global_adoption_id`; these resolve to the reference identity, lifecycle and organization audit history.

General Geography remains independent. A global logistics point neither creates nor becomes Country or InternationalCity data.

## Normal Organization Admin workflow

The Organization Logistics Network is the primary entry point and offers two business actions:

1. **Add from Reference Network**: select an ACTIVE, VERIFIED global point and choose **Add to Organization Network**.
2. **Create Private Point**: create an organization-only `LogisticsPoint` through the existing tenant point form.

The reference action is one authorized, transactional application command:

`reference selection → ensure ACTIVE tenant adoption → materialize/reuse LogisticsPoint → return LogisticsPoint`

It is idempotent for an already materialized adoption. If an existing adoption is inactive, the command fails closed rather than silently reactivating it. Existing adopted-but-unmaterialized active records can be completed with the same action. The old adoption and materialization endpoints remain available for administrative detail and compatibility, but neither is a required normal user step.

## Lifecycle and authorization

Only an Organization Admin in the server-derived organization context can browse or add eligible references. Platform Admin and Expert identities are denied the tenant command; an adoption from another organization is not addressable. Platform Admin exclusively governs the global catalog.

Only ACTIVE and VERIFIED global points can be newly added. Deprecating a global source prevents new selection/materialization while preserving existing tenant `LogisticsPoint`, project associations, tracking references and provenance. Upstream deprecation does not automatically disable or delete the tenant object.

## Domain chain and capability value trace

`Platform governed facility → organization adoption/audit → organization LogisticsPoint → ProjectLogisticsPoint / tracking update → historical snapshot`

The platform catalog provides shared governed identity; adoption provides tenant selection and audit control; `LogisticsPoint` provides the operational identity consumed downstream. Adoption has no separate normal-user business decision and is intentionally abstracted behind Add from Reference.

## Permanent regression controls

| ID | Failure mode | Root-cause class | Control / test | Gate | Status |
| --- | --- | --- | --- | --- | --- |
| LN-R01 | Cross-tenant add/materialization | Tenant authorization | scoped adoption/materialization tests | M6 | Active |
| LN-R02 | Duplicate materialization | Idempotency / uniqueness | repeated unified add returns same point | M6 | Active |
| LN-R03 | Reference-derived point loses provenance | Data lineage | global/adoption link assertions | M6 | Active |
| LN-R04 | Deprecation destroys tenant history | Lifecycle coupling | deprecation retention tests | M6 | Active |
| LN-R05 | Private point requires reference | Domain boundary | direct `create_point` contract | M6 | Active |
| LN-R06 | Admin must adopt then materialize | UX abstraction | Organization Global Network UI test | M6 | Active |
| LN-R07 | Unauthorized actor can add a reference | Authorization | Expert/Platform negative tests | M6 | Active |
| LN-R08 | Project/Tracking rejects resulting point | Consumer compatibility | Phase 4B project/tracking contract test | M6 | Active |

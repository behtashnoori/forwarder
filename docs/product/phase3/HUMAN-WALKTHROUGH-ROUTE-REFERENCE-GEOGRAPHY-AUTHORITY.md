# Human Walkthrough — Route Reference canonical geography authority

Date: 2026-09-29. Baseline: LPAF v2.7, rigor C, capability tier Sol.
Canonical entry SHA: `c94dc423143e2532c991d9172e44b30d495a0181` on
`integration/golden-controlled`. Product parent SHA:
`f8f65e5b8dd83095e111b8b0448295adce075068`.

## Mission contract

Outcome: remove the Human Product Walkthrough blocker in the Organization Admin
Route Reference Time/Distance form by making Country and endpoint selection use
the governed geography/reference identities already owned by the Product. The
operator selects Country first and then one understandable, country-consistent
canonical location. Display labels remain descriptive snapshots and never become
an independent identity.

In scope: the Route Reference create selector, its create-command validation,
localized geography presentation, continuity of existing Route Reference rows,
focused regression controls, affected project references and qualification.

Out of scope: ETA ruleset changes; Shipment IA; broad geography/catalog redesign;
automatic Route Reference creation or pinning; historical Shipment, Request,
Quote, Allocation, Execution, report, progress, ETA or RoutePlan mutation;
heuristic identity merge; Production, deployment or release.

Actors and authority: the Product Owner supplied the bounded blocker-remediation
mission. Organization Admin remains the only Route Reference manager. Existing
Expert basis-selection authority and tenant/owner boundaries remain unchanged.

Definition of Done: the complete active canonical Country catalog is available
to this form in deterministic order; location selection is country-first and
localized; a create command proves the selected location belongs to the supplied
canonical Country; endpoint identity remains canonical and immutable; historical
labels/references remain readable; raw internal geography codes are absent from
the Persian selector; planned distance, basis pinning and ETA v2 regressions pass;
one Alembic head remains; PostgreSQL 18, backend, frontend, build, lint,
architecture and applicable Product journeys have explicit results.

Stop conditions: competing Country SORs, ambiguous geography ownership, a needed
destructive reconciliation, conflict with ADR-066/074 or a broad geography
redesign. Production access and automatic walkthrough-data creation are forbidden.

## Product Authority Record

| Field | Record |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Route Reference uses the canonical active Country catalog; requires explicit Country then canonical location; rejects mismatched Country/location and country-only endpoints; displays localized endpoint types; treats labels only as derived display snapshots; excludes Iranian `InternationalCity` records from new Route Reference selection while retaining historical reads. |
| `DELEGATED_TECHNICAL_CHOICES` | Reuse existing admin Country, governed geography, international-location and tenant Logistics Network APIs; presentation adapter/component shape; fail-closed create validation; tests, documentation and qualification mechanics. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | ETA_RULESET_V2 semantics; `planned_distance_km`; immutable `OrganizationRouteTimeVersion` and `RouteLegTimeBasis`; existing RouteLeg endpoint contract; all preserved walkthrough business rows and historical labels; other request/route selector behavior; authentication, roles, lifecycle and permissions. |
| `DECISIONS_NEEDED` | None if repository truth confirms one Country SOR and the existing canonical location resolver can enforce the contract without migration. Otherwise stop under the mission conditions. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing `FORWARDER — ROUTE REFERENCE CANONICAL GEOGRAPHY INTEGRATION HARDENING`. |
| `APPROVAL_REFERENCE` | Supplied mission §§2–21, especially Country source, location identity, legacy continuity, Route Reference model and walkthrough preservation. |

## Current-state evidence

Facts:

- `backend.models.Country` is the shared Country SOR. Its governed checked-in
  snapshot declares ISO 3166-1 alpha-2 authority and exactly 249 countries.
- `/api/admin/locations/countries` reads that SOR. `/api/countries` is a separate
  public-form projection intentionally filtered to countries with an active
  `InternationalCity`; it is not a complete Route Reference catalog.
- `OrganizationRouteTime` already owns `origin_location_id` and
  `destination_location_id` to `canonical_location`, plus optional same-tenant
  `LogisticsPoint` IDs. Snapshots preserve labels; natural-key identity uses IDs.
- `OrganizationRouteTimeVersion` and `RouteLegTimeBasis` are append-only and
  protected by application and database immutability controls.
- `RouteLocationPicker` currently mixes Province, Iran destination,
  `InternationalCity` and tenant LogisticsPoint projections. The Iran projection
  embeds raw source-type values such as `international_city` in Persian labels.
- `RouteLeg` uses the same canonical endpoint resolver and stable endpoint
  snapshots. No Route Reference schema change is necessary.

Assumptions to verify: the canonical Product database has the approved 249-country
snapshot applied; affected selectors have no unpublished second Country catalog;
historical Iranian `InternationalCity` references may exist and therefore must be
readable even though they are not valid for new Route Reference creation.

The first controlled qualification established 12 existing canonical Countries,
237 missing catalog Countries and 51 active unbound legacy `InternationalCity`
rows. Full catalog Apply correctly refused those legacy identity conflicts. The
Product Owner subsequently authorized only `COUNTRY_ONLY` Apply: insert the 237
missing exact ISO identities, preserve all 51 legacy rows without mapping or
mutation, and exclude those unbound rows from new Route Reference selection.

Unknown until the authorized Apply is qualified: the exact final Product/evidence
SHA and post-Apply audit IDs. They must be captured without creating or rewriting
the Product Owner's Route Reference.

## Target process, ownership and chain

`Country` is Platform/Shared Reference data owned by Reference Data. Province,
City, IranPort, CustomsOffice and InternationalCity are governed geography master
sources. `CanonicalLocation` is their stable operational identity projection.
Tenant LogisticsPoint is Organization/Tenant Master data and may refine an endpoint
without replacing its canonical geography. OrganizationRouteTime and versions are
Organization/Tenant configuration; RouteLegTimeBasis is immutable transactional
planning evidence.

The target chain is:

Product purpose -> Organization Admin -> active canonical Country -> eligible
country-consistent governed location -> canonical resolver -> immutable route key
and display snapshot -> version -> explicit Expert pin -> ETA v2 consumer ->
tests and walkthrough evidence.

For Iran, new Route Reference selection uses domestic Province/City/Port/Customs
sources and active same-tenant LogisticsPoints. `InternationalCity` remains the
international-request/legacy locality domain for Iran and is not silently merged,
deleted or remapped. Existing route references using it remain readable from their
stored canonical identity and snapshot. Outside Iran, only active
`InternationalCity` rows with a valid, country-matching UN/LOCODE binding are
eligible for a new Route Reference. Unbound legacy rows remain readable by
historical consumers and stored snapshots, but the selector and create command
both reject them. Eligible city/port/airport types remain localized for display.

## Journey and reference impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`.

Affected slice journeys: `FWD-J06`, `FWD-J08`, `FWD-J09`.
Affected integrated journeys: `FWD-IPJ-03`, `FWD-IPJ-04`.
The preserved Human Product Walkthrough remains `IN_PROGRESS`; the agent prepares
and qualifies the corrected step but cannot grant the human PASS.

LPAF v2.7 reference impact: `NONE`; the frozen framework is applied unchanged.
Project reference impact: `UPDATE_REQUIRED` for ADR-066, OpenAPI, this authority
record, the consolidated finding `HW_ADMIN_ROUTE_REFERENCE_001`, and exact-candidate
qualification evidence. ADR-074 semantics remain unchanged.

## PDA-07 reconciliation target

Authorized: transactional and audited `COUNTRY_ONLY` insertion of the 237 missing
ISO Countries from the approved checksum; complete canonical Country source;
country-first location selection; localized type labels; explicit create-time
Country/location validation; and new-selection exclusion of every unbound legacy
`InternationalCity` plus the prior Iran-specific compatibility exclusion.

Preserved: authentication/role meaning, tenant scope, route/version/basis
immutability, existing records and snapshots, `planned_distance_km`, ETA v2,
Shipment/Request/Quote/Cargo/Allocation/Execution/report/progress history.

Violation/Unknown: any historical rewrite, inferred label merge, automatic Route
Reference creation/pinning, raw enum in the final primary Persian selector, or an
unreconciled Product-visible difference blocks qualification.

## Human Walkthrough finding

`HW_ADMIN_ROUTE_REFERENCE_001 — CANONICAL REFERENCE INTEGRATION GAP`

| Subfinding | Disposition target |
| --- | --- |
| `COUNTRY_SELECTOR_NOT_CANONICAL` | Replace the incomplete public-request projection on this surface with the active canonical Admin Country projection. |
| `FREE_TEXT_ROUTE_ENDPOINT_IDENTITY_RISK` | Accept only structured Country/location references for new keys; labels remain derived snapshots. |
| `VALID_LOCATION_SELECTOR_MIXES_REFERENCE_DOMAINS` | Use a dedicated country-first Route Reference adapter with explicit localized types and exclude Iranian legacy `InternationalCity` from new selection. |
| `RAW_GEOGRAPHY_ENUM_LEAK` | Localize display types without changing persisted source-type semantics. |
| `LEGACY_LOCATION_RECORDS_NOT_RECONCILED` | Preserve existing identities and snapshots read-only; do not merge by text, delete or rewrite history. |

## Product Owner COUNTRY_ONLY authorization addendum

| Field | Record |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Add the missing 237 exact ISO Countries from the approved FWD-02 checksum so the Country catalog reaches 249; preserve the 12 existing Countries; exclude all 51 unbound legacy locations from new Route Reference selection; preserve historical reads. |
| `DELEGATED_TECHNICAL_CHOICES` | Explicit reconciler scope/CLI shape, transaction mechanics, audit receipt representation, selector query parameter, fail-closed service validation, tests and evidence capture. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | No legacy mapping, rename, delete, merge, historical-reference rewrite or fabricated CanonicalLocation; no Shipment/Request/Quote/CRM/DN10/Cargo/Allocation/RoutePlan/RouteLeg/Execution/ExecutionUnit/report/progress/ETA mutation; no walkthrough Route Reference creation; no Production, deployment or release. |
| `DECISIONS_NEEDED` | None for the bounded Country-only mission. Any location mapping remains a separate owner decision. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner. |
| `APPROVAL_REFERENCE` | `FORWARDER — COUNTRY-ONLY CANONICAL GEOGRAPHY APPLY`, supplied 2026-09-29. |

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`: re-qualify the Route Reference slice
and affected Route/ETA regressions on the new exact Product. The Human Product
Walkthrough remains `IN_PROGRESS`; the agent must not create the planned
اصفهان → بندرعباس reference or grant walkthrough PASS.

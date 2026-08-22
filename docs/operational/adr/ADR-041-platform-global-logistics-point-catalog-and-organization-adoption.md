# ADR-041: Platform Global Logistics Point Catalog and Organization Adoption

- Status: ACCEPTED
- Date: 2026-08-22
- Owners: Platform Architecture, Product, Security, Logistics Domain
- Affected domain: Logistics master data, geography, project configuration, tracking

## Context

Forwarder has four location concepts with different contracts. `TrackingLocationReference` is a platform-scoped legacy selector whose numeric identity and snapshots remain part of compatibility tracking. `LogisticsPointType` is platform-governed taxonomy. `LogisticsPoint` is organization-owned master data with non-null `organization_id`, opaque `public_id`, organization-local immutable code, tenant-filtered services and same-tenant foreign keys. `ProjectLogisticsPoint` selects an organization point for a project. `CanonicalLocation` is the route-facing geographic identity and snapshot bridge.

The additive convergence authorized by ADR-035 lets a new `ShipmentTransportUnitUpdate` reference an active tenant `LogisticsPoint` while retaining legacy `location_reference_id`, manual text and immutable snapshots. It does not merge catalogs or backfill history. ADR-040 keeps legacy tracking a bounded compatibility authority while canonical operational events become the target authority.

The platform cannot currently define a reusable global point that organizations adopt. Making `LogisticsPoint.organization_id` nullable would invalidate its tenant identity, uniqueness, query, audit, project and tracking-FK assumptions. Copying the 64 legacy tracking rows into every organization would create unrelated identities for the same apparent places and would confuse cities, hubs, facilities and border sides.

This ADR defines a target architecture. It authorizes only a bounded future implementation plan. It does not authorize a Production migration, seed, mapping, deployment or data rewrite.

## Problem

The system needs this governed chain:

```text
Platform GlobalLogisticsPoint
        -> organization adoption
        -> optional organization LogisticsPoint representation
        -> ProjectLogisticsPoint and expert tracking
```

The design must distinguish platform place identity, organization approval and organization facility identity; preserve existing histories; derive tenants server-side; support multilingual and external reference data; and remain additive and rollback-aware.

## Decision

Adopt **Model C: selection association first, optional LogisticsPoint materialization later**.

1. Add a platform-owned `GlobalLogisticsPoint` catalog classified by the existing `LogisticsPointType` catalog.
2. Add tenant-owned `OrganizationGlobalLogisticsPoint` adoption. Adoption means the organization approves a global point for use; it is not a copied facility and does not fork platform canonical metadata.
3. Permit current organization-owned `LogisticsPoint` to reference one adopted global point optionally. A materialized point exists only when the organization needs an internal code, local display override, notes or a distinct facility/operational representation.
4. Preserve direct organization-only `LogisticsPoint` creation. Global reference is never mandatory for private warehouses, factories, customer sites or other tenant-specific facilities.
5. Expert and project selectors consume a unified organization-approved projection: active adoptions plus active organization-only/materialized `LogisticsPoint` rows. They never expose arbitrary unadopted global rows as selectable operational authority.
6. Tracking writes continue through organization authority. They must not point directly to `GlobalLogisticsPoint`. Existing `LogisticsPoint` FK and snapshot behavior remain the materialized path; a future adoption-backed write may resolve through a tenant-owned adoption identity and store equivalent immutable snapshots only after a separate implementation contract proves tenant-safe FKs and compatibility.
7. Map legacy tracking references through a reviewed many-capable mapping table. Do not add a single FK to `TrackingLocationReference` and do not rewrite historical updates.
8. Continue using `CanonicalLocation` for route-facing identity/snapshots. Global points may later have an explicit canonical-location projection or link, but they do not replace geographic reference tables or canonical route history.

## Domain boundaries

| Concept | Identity and ownership | Purpose | Must not mean |
| --- | --- | --- | --- |
| `GlobalLogisticsPoint` | Platform-owned opaque identity | Canonical reusable real-world logistics place/facility | Tenant approval, project use or occurrence |
| `OrganizationGlobalLogisticsPoint` | Tenant-owned adoption identity | Organization approval, lifecycle and local policy for one global point | Copy or ownership of platform metadata |
| `LogisticsPoint` | Tenant-owned facility/representation identity | Organization code, local metadata and operational selection | Platform-global identity |
| `ProjectLogisticsPoint` | Tenant/project-owned association | Project role, order and participation | Route event or global identity |
| `TrackingLocationReference` | Platform legacy numeric identity | Historical/compatibility tracking selector | New global master catalog |
| `CanonicalLocation` | Platform route/geography bridge | Route identity and immutable snapshots | Organization adoption or facility master |

Platform identity, adoption identity and organization facility identity are never interchangeable. API projections may combine labels, but persisted references retain their owning identity.

## GlobalLogisticsPoint field contract

| Field | Classification | Operational reason |
| --- | --- | --- |
| `id` BIGINT | REQUIRED | Internal PK and FK target; never API authority |
| `public_id` UUID v4 | REQUIRED | Opaque API identity, globally unique and immutable |
| `immutable_code` varchar(64) | REQUIRED | Human-governed stable platform business identity, independent of names and external standards |
| `logistics_point_type_id` | REQUIRED | Governed classification using `LogisticsPointType` |
| `fa_name` | REQUIRED | Primary Persian display/search name |
| `en_name` | REQUIRED | International display/search and review name |
| `normalized_name` | DERIVED | Duplicate/search key; never identity |
| `country_id` | REQUIRED | Canonical country boundary and border-side separation |
| `province_id` | OPTIONAL | Governed subdivision when current Province coverage exists |
| `city_id` | OPTIONAL | Governed domestic city when current City coverage exists |
| `international_city_id` | OPTIONAL | Governed non-Iran locality where `InternationalCity` has reviewed coverage |
| `region_name` | OPTIONAL | Reviewed snapshot for geography not yet represented by governed subdivision rows; not a second authority |
| `city_name` | OPTIONAL | Reviewed locality snapshot when no governed city reference exists |
| `geography_key` | DERIVED | Stable normalized key from country, governed references, coordinates/facility discriminator |
| `short_address` | OPTIONAL | Human location clarification, not identity by itself |
| `latitude`, `longitude` | OPTIONAL | Routing/map validation; both-or-neither and bounded checks required |
| `timezone_name` | OPTIONAL | IANA zone for planning/display; inferred values must be reviewed, not guessed |
| `un_locode` | OPTIONAL | External reference metadata; normalized and uniqueness evaluated per facility function |
| `external_codes` JSON/object | OPTIONAL | Namespaced port/customs/terminal codes with source and scheme; no untyped code bag |
| `aliases` | OPTIONAL | Governed multilingual names/search aliases; normalized duplicates rejected |
| `alternate_transliterations` | OPTIONAL | Explicit transliteration search forms where aliases are insufficient for governance reporting |
| `supported_modes` | REQUIRED | Non-empty bounded set of `ROAD`, `RAIL`, `SEA`, `AIR`, `MULTIMODAL`; capability metadata, not a substitute for type |
| `corridor_tags` | OPTIONAL | Governed searchable significance such as `CHINA_IRAN_RAIL_V1`; tags are not route plans |
| `border_pair_key` | OPTIONAL | Groups reviewed opposite-side border facilities without merging their identities |
| `border_side` | OPTIONAL | `ENTRY`, `EXIT`, `BIDIRECTIONAL` or `NOT_APPLICABLE`; required policy for border crossings |
| `lifecycle_status` | REQUIRED | `DRAFT`, `ACTIVE`, `DEPRECATED`; no hard-delete business lifecycle |
| `verification_status` | REQUIRED | `UNVERIFIED`, `REVIEWED`, `VERIFIED`; only verified active points enter default adoption search |
| `source_records` | REQUIRED | Structured provenance entries: source organization/reference/version/retrieved date and reviewer; at least one for activation |
| `version` | REQUIRED | Positive optimistic-lock version |
| `created_at`, `updated_at` | REQUIRED | Timezone-aware audit instants |
| `created_by`, `updated_by` | REQUIRED | Platform actor FKs; global CRUD does not require organization membership |
| polygon, opening hours, capacity, tariffs, live congestion | FUTURE / OUT OF SCOPE | Separate operational/route-intelligence domains after concrete use cases |

`aliases`, `external_codes`, `supported_modes`, provenance and corridor tags should use normalized child tables when independent search, uniqueness, audit or lifecycle is required. JSON is acceptable only for an opaque display-only initial slice with a documented evolution path; implementation design must choose one representation before migration.

## Identity and uniqueness

`immutable_code` is a human-governed, stable, uppercase code allocated by Platform Admin or controlled import tooling. It may incorporate country/type mnemonic but is not generated from a mutable name and is not equal to UN/LOCODE. External codes can change, be reused or identify a locality rather than a facility.

Required constraints and duplicate controls:

- unique `public_id` and unique `immutable_code`;
- exact duplicate uniqueness over a reviewed `facility_identity_key`, derived from country, type/facility discriminator, governed geography, coordinate cell or external facility code as applicable;
- probable duplicate search over normalized names, aliases, external codes, country, nearby coordinates and compatible types;
- creation returns a non-enumerating conflict for exact duplicates and requires explicit reviewed override for probable duplicates;
- immutable code, country and facility identity changes require a controlled supersession workflow after use, not ordinary patch.

Examples:

- `Shanghai` is a locality and is not automatically a global logistics point.
- `Shanghai Port` may be a port-complex point if its operational boundary is reviewed.
- `Shanghai Waigaoqiao Terminal` is a separate facility point with its own discriminator/code.
- `Warehouse X, Shanghai` is normally an organization-only `LogisticsPoint`, not a platform global point.
- Khorgos China and Khorgos Kazakhstan are separate country-scoped points linked by one `border_pair_key`.
- Sarakhs Iran and Serakhs Turkmenistan are separate points linked as a border pair; transliteration similarity never merges them.

## Organization adoption semantics

`OrganizationGlobalLogisticsPoint` has its own opaque `public_id`, non-null `organization_id`, non-null `global_logistics_point_id`, organization-local status (`ACTIVE`, `INACTIVE`), optional local display label, optional internal selection code, optional notes, version and actor/timestamps. Unique `(organization_id, global_logistics_point_id)` prevents duplicate adoption. A composite unique `(id, organization_id)` supports same-tenant FKs.

Adoption follows these rules:

- tenant comes only from the authenticated active membership;
- only active, verified global points may be newly adopted;
- deactivating adoption prevents new selection but does not delete project/tracking history;
- platform canonical names continue to flow into default display; local display label is an explicit overlay, not a fork;
- organization notes and codes remain tenant-private;
- platform deprecation prevents new adoption and new project/tracking selection, but existing references remain readable with warnings and snapshots;
- deleting adoption is not exposed after use; the API action is deactivate. A never-used adoption may be removable only under an explicitly verified implementation rule.

Current `LogisticsPoint` receives an optional `global_logistics_point_id` or, preferably, `organization_global_logistics_point_id` referencing an active adoption in the same tenant. The adoption FK is recommended because it proves approval and tenant context. Organization-local immutable code remains required. A tenant point can be:

1. **adopted representation**: one organization representation of a global place;
2. **organization-specific facility**: no global reference, or an optional `parent_global_logistics_point_id` context link that does not assert identity equivalence.

Examples:

| Business statement | Representation |
| --- | --- |
| Uses Sarakhs Border Crossing exactly as governed | Active adoption; materialize `LogisticsPoint` only if current consumers require it |
| Warehouse A, Sarakhs | Organization-only `LogisticsPoint`; optional contextual parent to Sarakhs, never identity-equivalent |
| Customer Factory X, Shanghai | Organization-only `LogisticsPoint` of type `CUSTOMER_SITE` or `FACTORY` |
| Uses Shahid Rajaee Port | Adoption of global port; optional tenant representation |
| Own depot inside Shahid Rajaee complex | Separate tenant `LogisticsPoint`, optionally context-linked to the global port complex |

## Legacy compatibility and reconciliation

The 64 `TrackingLocationReference` rows, numeric IDs, APIs, updates and snapshots remain unchanged. Add a separate reviewed table, tentatively `tracking_location_global_point_mapping`, with opaque `public_id`, `tracking_location_reference_id`, `global_logistics_point_id`, `mapping_kind`, status, confidence/review notes, provenance, version and platform audit fields.

Allowed `mapping_kind` values are `EQUIVALENT`, `LEGACY_BROADER_THAN_GLOBAL`, `LEGACY_NARROWER_THAN_GLOBAL`, and `RELATED_ONLY`. The table supports 1:1, many:1, 1:many and unmapped outcomes. Only reviewed active `EQUIVALENT` mappings may support reconciliation; other mappings are explanatory. Mapping never changes legacy reads or rewrites `ShipmentTransportUnitUpdate`.

An explicit reconciliation package must contain source legacy key, proposed global code(s), cardinality, mapping kind, reviewer, evidence, geography/type decision and disposition. Plan/apply must be separate, idempotent and conflict-reporting. No mapping is created automatically from name equality.

## Global point type governance

Use the existing eleven `LogisticsPointType` values in V1. Do not add a type in this ADR.

| Candidate type | V1 decision |
| --- | --- |
| `DRY_PORT` | Use `ROAD_TERMINAL`, `RAIL_TERMINAL` or `OTHER_GOVERNED` plus supported modes until an operational distinction is proven |
| `MULTIMODAL_TERMINAL` | Use the facility's primary governed type plus `MULTIMODAL` and other supported modes |
| `LOGISTICS_HUB` | Use the actual facility type; a whole city/hub requires geography review and usually is not a point |
| `CONTAINER_DEPOT` | Use `WAREHOUSE`, `ROAD_TERMINAL` or `OTHER_GOVERNED` according to reviewed function |

If reporting, permissions or workflow rules later depend on one of these classifications, amend ADR-025/ADR-028 or accept a focused taxonomy ADR before adding the code.

## Geography

`Country` is the required country authority. `Province` and `City` remain governed domestic subdivisions. `InternationalCity` may be reused for a reviewed non-Iran locality but is not mandatory because its coverage is incomplete and its current city/port conflation must not become global facility identity. `IranPort` and `CustomsOffice` may provide reviewed mapping/provenance, but `GlobalLogisticsPoint` remains a distinct logistics-place identity rather than reusing their IDs.

Coordinates are optional because authoritative coordinates are not available for every row; if supplied, latitude and longitude are both required and source-reviewed. UN/LOCODE is reference metadata, not primary identity. Ports/customs spanning municipalities use the facility/complex identity with optional municipality associations; they are not forced into one city FK. Each border side is a separate country-owned point joined by `border_pair_key`.

The design must not create unmanaged country/city strings as a second geography universe. Snapshot strings are permitted only when governed coverage is absent, with provenance and a future reconciliation state.

## Authority

| Operation | Platform Admin | Organization Admin | Expert |
| --- | --- | --- | --- |
| Create GlobalLogisticsPoint | Yes, no membership required | No | No |
| Update global metadata | Yes | No | No |
| Activate/deprecate global point | Yes | No | No |
| Browse active global catalog | Yes | Yes | No by default |
| Browse draft/inactive global catalog | Yes | No | No |
| Adopt global point | No tenant action without explicit tenant context | Yes for derived tenant | No |
| Deactivate organization adoption | No tenant action without explicit tenant context | Yes | No |
| Create organization-only LogisticsPoint | No without organization membership | Yes with current permission | Only if explicitly granted current manage permission |
| Customize organization representation | No without tenant context | Yes | No by default |
| Use in project | No without tenant context | With project permission | With project permission |
| Use in tracking | No without tenant context | If tracking-authorized | Tracking-authorized Expert |

Platform endpoints use `PLATFORM_ADMIN` authority directly and never call tenant membership resolution for global CRUD. Organization endpoints derive exactly one active tenant server-side. Body, query and headers cannot select `organization_id`. Foreign global/adoption/tenant identities fail closed without existence disclosure.

## API principles

Routes follow current platform/admin/internal conventions:

```text
GET    /api/platform/global-logistics-points
POST   /api/platform/global-logistics-points
GET    /api/platform/global-logistics-points/{public_id}
PATCH  /api/platform/global-logistics-points/{public_id}
POST   /api/platform/global-logistics-points/{public_id}/activate
POST   /api/platform/global-logistics-points/{public_id}/deprecate

GET    /api/admin/global-logistics-points
POST   /api/admin/global-logistics-points/{public_id}/adopt
GET    /api/admin/global-logistics-point-adoptions
PATCH  /api/admin/global-logistics-point-adoptions/{adoption_public_id}
POST   /api/admin/global-logistics-point-adoptions/{adoption_public_id}/deactivate
```

`/api/platform` is chosen for platform authority without tenant context; `/api/admin` is chosen for tenant administrative mutation, consistent with current Logistics Network admin routes. Expert selectors remain under `/api/internal` and return only the organization-approved unified projection.

List APIs use `page` (minimum 1), `per_page` (1–100), deterministic immutable-code/public-ID ordering, and bounded `q` (maximum 160). Filters include country code, point-type immutable code, lifecycle/active status, verification status, supported mode and governed corridor tag. Platform may query all statuses; organization discovery defaults to active verified rows; experts cannot override adoption scope. Responses expose opaque public IDs, never numeric IDs or organization IDs.

Mutations require `version`; stale writes return `409 VERSION_CONFLICT`. Exact duplicates return `409 EXACT_DUPLICATE`; probable duplicates return a safe conflict requiring an explicit reviewed confirmation. Foreign or unavailable records return non-enumerating `404`; tenant override returns `403 TENANT_SCOPE_VIOLATION`. Search is capped, indexed and rate-limited as appropriate.

## UI principles

Platform Admin receives **Global Logistics Network** with list/search, country, type, mode, corridor, verification/lifecycle filters, create/edit, activate/deprecate, aliases, geography, external codes, provenance and probable-duplicate review.

Organization Admin's existing **Logistics Network** distinguishes:

- `GLOBAL · ADOPTED`;
- `GLOBAL · AVAILABLE`;
- `ORGANIZATION ONLY`;
- `ORGANIZATION FACILITY AT GLOBAL HUB`.

It supports browse, adopt, local label/code/notes, deactivate adoption and private-facility creation. It must explain that deactivation affects the organization only.

Expert selectors show only active adopted points and active organization-only/materialized points authorized for the active tenant. Global provenance and platform draft catalog are not exposed. Labels clearly distinguish a platform point from a private facility when both share a locality.

## Tracking integration

Preserve the current boundary:

```text
GlobalLogisticsPoint
  -> OrganizationGlobalLogisticsPoint adoption
  -> optional organization LogisticsPoint
  -> ShipmentTransportUnitUpdate + immutable snapshots
```

Direct `GlobalLogisticsPoint -> ShipmentTransportUnitUpdate` is rejected because it bypasses organization approval, weakens the same-tenant FK and creates a second tracking authority. The first implementation should materialize or resolve an organization `LogisticsPoint` so existing `logistics_point_id` and snapshots remain unchanged. No historical backfill is authorized.

## Project integration

Projects continue to reference `ProjectLogisticsPoint`, which references an organization `LogisticsPoint`; projects do not own platform rows directly. Adoption may create/materialize the tenant point lazily or explicitly before project selection.

- Global rename: new projections show the canonical name where no local label exists; persisted project labels and tracking snapshots remain unchanged.
- Global deprecation: block new adoption/materialization and new project selection; existing project references remain readable with warning.
- Adoption deactivation: block new project/tracking use; do not delete existing associations or history.
- Existing project reference: remains valid and auditable even if upstream point/adoption becomes inactive.

## Review inventory for the 64 legacy rows

Classification is a design review disposition, not an approved mapping or seed. `NEEDS_GEOGRAPHY_REVIEW` means the source names a city/hub or insufficiently bounded facility. `NEEDS_SPLIT` means the legacy label may represent multiple facilities. Likely type is provisional.

### China

| Legacy key / name | Disposition | Likely type | Review note |
| --- | --- | --- | --- |
| cn-shanghai / Shanghai | NEEDS_SPLIT | PORT | Port complex versus individual terminals |
| cn-ningbo-zhoushan / Ningbo-Zhoushan | GLOBAL_POINT_CANDIDATE | PORT | Verify complex boundary/codes |
| cn-shenzhen-yantian / Shenzhen/Yantian | NEEDS_SPLIT | PORT | City/port/terminal ambiguity |
| cn-guangzhou-nansha / Guangzhou/Nansha | NEEDS_SPLIT | PORT | Port complex versus terminal |
| cn-qingdao / Qingdao | NEEDS_GEOGRAPHY_REVIEW | PORT | City name does not prove facility |
| cn-tianjin-xingang / Tianjin/Xingang | NEEDS_SPLIT | PORT | Complex/terminal ambiguity |
| cn-lianyungang / Lianyungang | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Verify rail terminal versus port/city |
| cn-yiwu / Yiwu | NEEDS_GEOGRAPHY_REVIEW | OTHER_GOVERNED | City/trade hub needs bounded facility |
| cn-xian / Xi'an | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify actual terminal |
| cn-zhengzhou / Zhengzhou | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify actual terminal |
| cn-chengdu / Chengdu | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify actual terminal |
| cn-chongqing / Chongqing | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify actual terminal |
| cn-wuhan / Wuhan | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify actual terminal |
| cn-lanzhou / Lanzhou | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify actual terminal |
| cn-urumqi / Urumqi | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City/transit role is not a facility |
| cn-kashgar / Kashgar | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City/transit role is not a facility |
| cn-alashankou / Alashankou | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Verify China-side road/rail facilities |
| cn-khorgos / Khorgos | NEEDS_SPLIT | BORDER_CROSSING | China side and road/rail components |

### Kazakhstan and Kyrgyzstan

| Legacy key / name | Disposition | Likely type | Review note |
| --- | --- | --- | --- |
| kz-dostyk / Dostyk | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Verify Kazakhstan-side rail crossing |
| kz-altynkol / Altynkol | GLOBAL_POINT_CANDIDATE | RAIL_TERMINAL | Pair with China Khorgos, do not merge |
| kz-almaty / Almaty | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City needs facility identity |
| kz-shymkent / Shymkent | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City needs facility identity |
| kz-aktau / Aktau | NEEDS_GEOGRAPHY_REVIEW | PORT | Verify port complex identity |
| KG-OSH / Osh | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City/hub needs facility identity |

### Uzbekistan and Turkmenistan

| Legacy key / name | Disposition | Likely type | Review note |
| --- | --- | --- | --- |
| uz-tashkent / Tashkent | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify terminal/hub |
| uz-samarkand / Samarkand | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City checkpoint may remain legacy-only |
| uz-navoi / Navoi | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Verify logistics terminal |
| uz-bukhara / Bukhara | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City checkpoint may remain legacy-only |
| tm-alat / Alat | NEEDS_GEOGRAPHY_REVIEW | BORDER_CROSSING | Verify correct country/border-side geography |
| tm-farap / Farap | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Turkmenistan-side crossing |
| tm-turkmenabat / Turkmenabat | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City needs facility identity |
| tm-mary / Mary | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City checkpoint may remain legacy-only |
| tm-tejen / Tejen | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City checkpoint may remain legacy-only |
| tm-serakhs / Serakhs | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Pair with Iran Sarakhs, do not merge |
| tm-etrek / Etrek | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Verify operational crossing |
| tm-turkmenbashi / Turkmenbashi | NEEDS_GEOGRAPHY_REVIEW | PORT | Verify port complex identity |

### Pakistan and Afghanistan

| Legacy key / name | Disposition | Likely type | Review note |
| --- | --- | --- | --- |
| pk-sost / Sost | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Verify Pakistan-side facility |
| pk-islamabad / Islamabad | LEGACY_TRACKING_ONLY | ROAD_TERMINAL | City checkpoint; no facility evidence |
| pk-quetta / Quetta | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | Identify terminal if globally reusable |
| pk-taftan / Taftan | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Pair with Iran Mirjaveh review |
| pk-karachi / Karachi | NEEDS_SPLIT | PORT | Multiple port facilities |
| pk-port-qasim / Port Qasim | GLOBAL_POINT_CANDIDATE | PORT | Verify complex identity/codes |
| pk-gwadar / Gwadar | NEEDS_GEOGRAPHY_REVIEW | PORT | Verify port identity and corridor scope |
| pk-gabd / Gabd | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Pair with Iran Rimdan review |
| af-herat / Herat | NEEDS_GEOGRAPHY_REVIEW | ROAD_TERMINAL | City needs facility identity |
| af-islam-qala / Islam Qala | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Pair with Iran Dogharoun review |
| af-zaranj / Zaranj | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Verify Iran-side pair/corridor |

### Iran

| Legacy key / name | Disposition | Likely type | Review note |
| --- | --- | --- | --- |
| ir-sarakhs / Sarakhs | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Iran side; pair with TM Serakhs |
| ir-incheh-borun / Incheh Borun | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Verify road/rail components |
| ir-mirjaveh / Mirjaveh | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Pair with Taftan review |
| ir-dogharoun / Dogharoun | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Pair with Islam Qala review |
| ir-rimdan / Rimdan | GLOBAL_POINT_CANDIDATE | BORDER_CROSSING | Pair with Gabd review |
| ir-mashhad / Mashhad | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | City/destination is not a facility |
| ir-zahedan / Zahedan | NEEDS_GEOGRAPHY_REVIEW | RAIL_TERMINAL | Identify terminal/transshipment facility |
| ir-tehran / Tehran | NEEDS_SPLIT | OTHER_GOVERNED | City; Aprin/terminals must be distinct |
| ir-qom / Qom | LEGACY_TRACKING_ONLY | ROAD_TERMINAL | City checkpoint; no facility evidence |
| ir-isfahan / Isfahan | LEGACY_TRACKING_ONLY | ROAD_TERMINAL | City checkpoint; no facility evidence |
| ir-yazd / Yazd | LEGACY_TRACKING_ONLY | ROAD_TERMINAL | City checkpoint; no facility evidence |
| ir-kerman / Kerman | LEGACY_TRACKING_ONLY | ROAD_TERMINAL | City checkpoint; no facility evidence |
| ir-shahid-rajaee / Shahid Rajaee Port | GLOBAL_POINT_CANDIDATE | PORT | Verify port/terminal boundary |
| ir-chabahar / Chabahar Port | GLOBAL_POINT_CANDIDATE | PORT | Verify port complex/codes |
| ir-imam-khomeini / Imam Khomeini Port | GLOBAL_POINT_CANDIDATE | PORT | Verify port complex/codes |
| ir-amirabad / Amirabad Port | GLOBAL_POINT_CANDIDATE | PORT | Verify port complex/codes |
| ir-anzali-caspian / Anzali/Caspian Port | NEEDS_SPLIT | PORT | Two distinct ports must not share identity |

Irkeshtam, Andijan, Ashgabat and Aprin are new candidates, not members of the legacy 64. Each requires the same evidence and review package before V1 inclusion.

## China-Iran V1 catalog scope

V1 is a reviewed, multimodal spine rather than all 64 rows.

### Core V1

| Corridor role | Points | Why core |
| --- | --- | --- |
| China sea gateways | Ningbo-Zhoushan; reviewed Shanghai port complex; Yantian; Nansha; Qingdao; Tianjin/Xingang | Principal China export gateways and sea-route origin coverage |
| China rail consolidation | reviewed Yiwu, Xi'an, Zhengzhou, Chengdu, Chongqing terminals | Major westbound train consolidation choices; facility review required before activation |
| China western gateways | Urumqi terminal; Kashgar terminal; Alashankou China; Khorgos China | Connect rail/road consolidation to Central Asian borders |
| Kazakhstan spine | Dostyk; Altynkol; Almaty terminal; Shymkent terminal | Rail-border handoff and south/west transit spine |
| Kyrgyz option | Osh terminal; Irkeshtam crossing if approved | Southern road alternative; Irkeshtam remains evidence-gated |
| Uzbekistan spine | Tashkent terminal; Samarkand terminal; Bukhara terminal; Farap-side reviewed counterpart | Main east-west transit chain; each city must resolve to a facility |
| Turkmenistan spine | Farap; Turkmenabat terminal; Mary terminal; Ashgabat terminal if approved; Serakhs Turkmenistan | Main Uzbekistan-to-Iran road/rail corridor and border handoff |
| Iran eastern entry/delivery | Sarakhs Iran; Incheh Borun; Mashhad terminal; Aprin terminal if approved; Tehran destination facilities | Primary land/rail entry and inland consolidation; city labels alone are not activated |
| Iran sea gateways | Shahid Rajaee; Chabahar; Imam Khomeini | Principal south-coast import alternatives |

Every item marked “reviewed”, “terminal” or “if approved” remains draft until facility identity, geography, type, modes and provenance pass review. This table is scope authority, not seed authority.

### V1 optional

Lianyungang, Wuhan, Lanzhou, Aktau, Turkmenbashi, Navoi, Tejen, Etrek, Mirjaveh/Taftan, Dogharoun/Islam Qala, Rimdan/Gabd, Amirabad and separately reviewed Anzali and Caspian ports. They add alternate rail, Caspian, Pakistan/Afghanistan and border corridors but are not necessary for the first operational spine.

### Future

Pakistan sea-route expansion beyond reviewed Port Qasim/Karachi facilities; Gwadar; Sost; Zaranj; general city checkpoints; minor organization facilities; live route capacity, schedules, tariffs and congestion.

## Migration strategy

Future migrations are additive from the then-current sole head:

1. Create `global_logistics_point` and normalized supporting tables/constraints/indexes selected by implementation design.
2. Create `organization_global_logistics_point` with tenant composite uniqueness/FKs, version and audit fields.
3. Add nullable same-tenant adoption linkage to `logistics_point`; retain all current non-null organization invariants.
4. Add indexes for active verified catalog search, country/type/mode/corridor, adoption tenant/status and duplicate keys.
5. Add `tracking_location_global_point_mapping` only after the review-package contract and mapping cardinality tests exist.
6. Do not backfill or rewrite tracking updates, organization points, project points, requests or canonical locations.

Schema downgrade may remove unused new structures in reverse order. Downgrade must refuse if any adoption, materialized link, legacy mapping or other production reference exists unless a separately authorized retained-data/application-rollback procedure has reconciled it. Immutable histories and audit data are never silently deleted.

## Rollout

1. **Phase 0 — ADR only:** this decision; no schema or data change.
2. **Phase 1 — schema and platform read API:** empty catalog, permissions, tenant-negative tests, migration upgrade/downgrade/re-upgrade evidence; old application remains compatible.
3. **Phase 2 — Platform Admin governance:** CRUD, provenance, duplicate review and draft/verification lifecycle; no tenant or expert consumption.
4. **Phase 3 — organization adoption:** browse/adopt/deactivate and optional materialization behind feature policy; no change to existing selectors until parity evidence.
5. **Phase 4 — expert/project consumption:** unified organization-approved selector, shadow comparison, snapshots, inactive/deprecated behavior and rollback switch.
6. **Phase 5 — legacy reconciliation:** reviewed mapping package, reporting and compatibility observation only; no historical rewrite.

Each phase deploys independently. Application rollback disables later routes/features and returns selectors to the last certified organization `LogisticsPoint` behavior while retaining new rows. No rollout phase authorizes Production seed automatically.

## Production data safety and retention

- Existing 64 `TrackingLocationReference` rows and numeric IDs remain untouched.
- Existing `ShipmentTransportUnitUpdate` rows, FKs, text and snapshots remain untouched.
- Existing `LogisticsPoint` and `ProjectLogisticsPoint` rows remain untouched.
- Existing request origin/destination geography remains untouched.
- No automatic mapping, name-based deduplication, cross-tenant copy or organization bulk adoption is allowed.
- Deactivation/deprecation replaces hard deletion after use.
- Snapshots remain immutable historical evidence even when global or tenant metadata changes.
- Platform audit, adoption audit and mapping review evidence follow the repository retention policy and are not removed by application rollback.

## Security and tenancy

Global catalog reads expose allowlisted business metadata, not audit actor IDs, internal numeric IDs or private provenance notes. Organization overlays and adoption existence are tenant-private. Global CRUD requires Platform Admin but no organization membership. Organization mutation resolves exactly one active membership and required permission. Same-tenant composite FKs protect adoption/materialization and downstream associations. Search caps, normalized validation, safe errors, audit redaction and non-enumeration apply. Coordinates and addresses are reviewed for business sensitivity before platform-wide visibility.

## Rejected alternatives

- **Nullable `LogisticsPoint.organization_id`:** rejected because it breaks established tenant semantics and same-tenant constraints.
- **Only a nullable global FK on every LogisticsPoint (Model A):** rejected because it cannot represent adoption without materialization and confuses approval with facility identity.
- **Association only forever (Model B):** rejected because current project/tracking consumers require organization `LogisticsPoint` identity and tenants need facility metadata.
- **Copy all global rows into every tenant:** rejected because identities and updates diverge and catalog growth leaks across tenants.
- **Promote `TrackingLocationReference`:** rejected because it is legacy, numeric, classification-limited and historically coupled to compatibility tracking.
- **Direct global FK from tracking/project:** rejected because it bypasses organization approval and creates parallel operational authority.
- **Automatic 64-row mapping by name:** rejected because city/facility, port-complex and border-side ambiguity is material.

## Consequences

The platform gains reusable governed network identity without weakening tenant ownership. Organizations can approve shared places while retaining private facilities and codes. Expert/project/tracking behavior remains organization-controlled. Costs include a new aggregate, adoption lifecycle, unified selector projection, review tooling, more explicit facility/geography curation and careful deprecation behavior.

The model supports future route intelligence through modes, corridor tags, border pairs, coordinates and canonical-location integration without making the catalog itself a route plan or event source.

## Open questions

No owner decision blocks this ADR. The following implementation choices remain bounded design tasks:

1. normalized child tables versus constrained JSON for aliases, external codes, modes, corridor tags and provenance;
2. explicit materialization command versus automatic materialization on first project/tracking use;
3. whether a contextual parent-global link belongs on organization-only facilities in the first slice;
4. exact permission names and rate limits;
5. authoritative external datasets and reviewers for V1 facility identity, coordinates, UN/LOCODE and border pairs.

None may be answered by Production inference or automatic legacy import.

## Compatibility

The change is additive. N/N-1 application behavior continues using current `LogisticsPoint` and legacy tracking contracts until a later phase is explicitly enabled. No existing public route or response field is removed. Numeric legacy identities never become new API authority. New clients use opaque global/adoption IDs. Historical snapshots remain the display fallback.

## Operational impact

Initial implementation needs indexed bounded search, audit/outbox decisions, catalog/adoption metrics, duplicate and mapping conflict reporting, deprecation warnings, feature/cohort controls and support runbooks. Empty catalogs are valid. Catalog population is an explicit reviewed plan/apply operation separate from deployment.

## Rollback

Before consumption, disable new routes/UI and retain empty or draft data. After adoption, disable adoption mutation and unified selectors, then use the last certified organization `LogisticsPoint` path; retain adoption rows. After project/tracking use, never delete global, adoption, tenant links or snapshots. Deprecate rather than delete. Database downgrade refuses while referenced data exists without an approved retained-data procedure.

## Validation required for implementation

- sole-head additive migration upgrade/downgrade/re-upgrade on disposable PostgreSQL and SQLite compatibility;
- model constraints, opaque identity, immutable code, version conflict and exact/probable duplicate tests;
- Platform Admin without membership CRUD tests;
- Organization Admin tenant derivation, foreign-ID non-enumeration and cross-tenant FK tests;
- Expert cannot see unadopted points and can use only active organization-approved projections;
- deprecation/adoption-inactive historical-read and new-write denial tests;
- project/tracking snapshot and N/N-1 compatibility tests;
- 1:1, many:1, 1:many and unmapped reconciliation tests with no historical mutation;
- frontend desktop/mobile/RTL distinction of global/adopted/private identities;
- architecture governance, ADR index, diff, secret scan and migration safety gates.

## Authorized next implementation slice

The next controlled implementation may add only the empty `GlobalLogisticsPoint` schema/supporting normalized structures, Platform Admin permissions and read-only platform catalog API, plus tests and migration evidence. It must not seed points, create legacy mappings, add organization adoption, switch expert/project selectors, access Production, deploy or push. If supporting-table representation cannot be resolved within existing constraints, stop for architecture review rather than inventing an ungoverned JSON contract.

## Supersedes / superseded by

- Supersedes: none
- Complements: ADR-005, ADR-006, ADR-025, ADR-026, ADR-028, ADR-035 and ADR-040
- Superseded by: none

## Status history

- 2026-08-22: ACCEPTED — platform global catalog, tenant adoption, optional organization representation and compatibility-preserving rollout approved; implementation and Production changes remain separately controlled.
- 2026-08-22: PHASE 1 IMPLEMENTED LOCALLY — empty `GlobalLogisticsPoint` schema, normalized alias/mode/external-code/corridor/provenance support, and Platform-Admin-only read API implemented; no Production migration, seed, adoption, legacy mapping, selector change, deployment or push authorized.
- 2026-08-23: PHASE 2 IMPLEMENTED LOCALLY — Platform-Admin-only governed create/update, normalized metadata replacement, review/verify/activate/deprecate operations, deterministic activation and duplicate gates, optimistic concurrency, and Global Logistics Network management UI implemented and certified on disposable PostgreSQL; no new migration, Production access, seed, adoption, legacy mapping, selector change, deployment or push performed.
- 2026-08-23: PHASE 3 IMPLEMENTED LOCALLY — tenant-owned organization adoption persistence, Organization-Admin-only browse/adopt/configure/deactivate/reactivate API and Global Network UI implemented with server-derived tenant context, retained-history deprecation semantics, and disposable PostgreSQL certification; no LogisticsPoint materialization, Expert/Project/Tracking consumption, seed, Production access, deployment or push performed.

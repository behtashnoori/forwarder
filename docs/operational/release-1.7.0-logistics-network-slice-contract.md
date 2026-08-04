# Release 1.7.0 — Logistics Network Foundation Slice Contract

- **Status:** Accepted — bounded Release 1.7.0 implementation complete in source; not deployed
- **Accepted:** 2026-08-02
- **Approver roles:** Product, Architecture, Operations, Data, Security
- **Date:** 2026-08-02
- **Target release:** 1.7.0 — Logistics Network Foundation
- **Current Production baseline:** Application 1.6.1; database `20260809_cargo_catalog_items`
- **Primary capabilities:** CAP-013 Master Data, CAP-001 Project Management
- **Supporting capabilities:** CAP-010 Security & Identity, CAP-009 Administration, CAP-003 Execution Management consultation
- **Authority:** [PDR-015](PDR-015-forwarder-domain-development-roadmap.md), [PDR-016](PDR-016-logistics-network-foundation.md), [ADR-025](adr/ADR-025-logistics-network-aggregate-boundaries.md)
- **Implementation authorization:** **YES — bounded scope only**
- **Architecture baseline:** DA-1.0; [FDD-001](FDD-001-forwarder-data-dictionary.md) and [FDM-001](FDM-001-forwarder-domain-map.md)

## 1. Purpose and release impact

This contract defines the exact bounded implementation and acceptance boundary for `LogisticsPointType`, `LogisticsPoint`, and `ProjectLogisticsPoint`. Its accepted implementation is complete in source. This status does not assert Production migration, seed apply, packaging, tagging, or deployment.

| Release concern | Implemented release impact |
| --- | --- |
| SemVer | MINOR: 1.6.1 → 1.7.0 |
| Release name | Logistics Network Foundation |
| Database | Additive migration `20260810_logistics_network` after `20260809_cargo_catalog_items` |
| Backend | New bounded internal/admin models, services, permissions, and APIs |
| Frontend | Internal admin management plus Project configuration selection/ordering |
| Existing contracts | Additive; existing Projects, RoutePlans, Checkpoints, and APIs remain valid |
| Seed | No migration seed; proposed separate governed catalog/seed authorization |
| Production | No migration, catalog apply, packaging, tagging, or deployment performed |

## 2. In scope

### LogisticsPointType

Governed Reference Data with immutable code, required Persian and English names, optional definition, display order, active state, optimistic version, timestamps, and actor audit. The accepted initial codes are:

`FACTORY`, `WAREHOUSE`, `DISTRIBUTION_CENTER`, `CUSTOMS`, `PORT`, `BORDER_CROSSING`, `AIRPORT`, `RAIL_TERMINAL`, `ROAD_TERMINAL`, `CUSTOMER_SITE`, `OTHER_GOVERNED`.

`LOADING_SITE`, `UNLOADING_SITE`, and generic `TERMINAL` are prohibited. Loading/unloading are Project roles.

### LogisticsPoint

Reusable organization-scoped Master Data with opaque identity, immutable organization-local code, required LogisticsPointType and governed Country, Persian name, optional English name, optional governed Province and City, optional short address, active state, optimistic version, and actor/timestamp audit. `region_name` is deferred by ADR-026. It has no hard-delete behavior after use, and inactive historical references remain readable.

### ProjectLogisticsPoint

Project configuration associating one Project with one LogisticsPoint, with Project-specific sequence, one bounded role per row, optional display label and notes, active state, optimistic version, and actor/timestamp audit. It creates no RoutePlan, Checkpoint, event, or historical rewrite.

Accepted roles are `ORIGIN`, `INTERMEDIATE`, `DESTINATION`, `CUSTOMS_PROCESSING`, `TRANSFER`, `STORAGE`, `LOADING`, `UNLOADING`, and `OTHER_GOVERNED`.

## 3. Explicit exclusions

Maps, GIS, latitude/longitude, geofencing, timezone automation, operating hours, capacity, contacts, traffic/weather, ETA, route optimization, automatic RoutePlan generation, automatic Checkpoint creation, location telemetry, public point catalog, customer point search, dashboards, reporting UI, bulk import, advanced approval workflow, automatic legacy backfill, free-text address conversion, allocation, cargo-to-unit linkage, packaging, generic workflow engine, and generic EAV are outside 1.7.0.

The Slice also excludes fuzzy-search infrastructure, a generic terminal type, new customer-visible endpoints, Reference Data Seed execution without separate authority, and changes to ADR-023/ADR-024.

## 4. Proposed physical data contract

The exact choices in this section are Accepted for the bounded Release 1.7.0 implementation.

### 4.1 Table `logistics_point_type`

| Column | Contract |
| --- | --- |
| `id` | Internal BIGINT primary key; never serialized |
| `public_id` | Required unique UUIDv4 string, 36 characters |
| `immutable_code` | Required uppercase governed code, maximum 64; globally unique and immutable |
| `fa_name`, `en_name` | Required, trimmed, maximum 160 |
| `definition` | Optional text |
| `display_order` | Required integer, default 0 |
| `is_active` | Required boolean, default true |
| `version` | Required integer ≥ 1; SQLAlchemy version column plus explicit expected-version check |
| `created_at`, `updated_at` | Required timezone-aware instants |
| `created_by`, `updated_by` | Required RESTRICT FKs to `expert_user.id` |

Indexes support active/display-order and code/name administration. Codes remain readable after deactivation and cannot be reused or changed.

### 4.2 Table `logistics_point`

| Column | Contract |
| --- | --- |
| `id`, `public_id` | Internal BIGINT plus globally unique UUIDv4 public ID |
| `organization_id` | Required RESTRICT FK to `operational_organization.id` |
| `immutable_code` | Required uppercase organization-local code, maximum 64 |
| `logistics_point_type_id` | Required RESTRICT FK to `logistics_point_type.id` |
| `fa_name`, `en_name` | Persian required; English optional; maximum 160 |
| `normalized_name` | Required deterministic value from Persian name; maximum 200 |
| `country_id` | Required RESTRICT FK to existing `country.id` |
| `province_id` | Optional RESTRICT FK to existing `province.id` |
| `city_id` | Optional RESTRICT FK to existing `city.id` |
| `short_address` | Optional, maximum 500 |
| `is_active`, `version` | Required lifecycle and optimistic concurrency fields |
| audit fields | Required timezone-aware timestamps and RESTRICT actor FKs |

Constraints and indexes:

- unique `(organization_id, immutable_code)` and unique `public_id`;
- composite unique `(id, organization_id)` to support same-organization foreign-key enforcement;
- city requires province; the city must belong to the selected province and province to the selected country, enforced by service validation and database composite FKs where the existing geographic keys support them;
- no free-text administrative region field is exposed; `region_name` is deferred by ADR-026, and short address is descriptive text rather than a reporting dimension;
- organization-leading indexes for active/type, normalized name, country/province/city, and updated order;
- an exact duplicate key over organization, normalized name, type, country, and null-safe governed Province/City geography. The normalized `geography_key` implementation may remain internal and must not expose a new business concept; SQLite-compatible tests must prove equivalent behavior.

### 4.3 Table `project_logistics_point`

| Column | Contract |
| --- | --- |
| `id`, `public_id` | Internal BIGINT plus globally unique UUIDv4 public ID |
| `project_id`, `organization_id` | Required; composite FK to `project(id, organization_id)` |
| `logistics_point_id` | Required; composite FK with organization to `logistics_point(id, organization_id)` |
| `sequence_number` | Required integer ≥ 1 |
| `project_role` | Required bounded string enum |
| `display_label` | Optional trimmed Project-only presentation label, maximum 160 |
| `notes` | Optional internal text; never changes master identity |
| `is_active`, `version` | Required lifecycle and optimistic concurrency fields |
| audit fields | Required timezone-aware timestamps and RESTRICT actor FKs |

One row represents one role. Multiple rows may reference the same point in one Project only when roles differ. Unique `(project_id, logistics_point_id, project_role)` prevents duplicate role associations. A PostgreSQL partial unique index on `(project_id, sequence_number) WHERE is_active` makes sequence unique in active configuration; SQLite test/migration behavior must enforce an equivalent partial index. Deactivation preserves the row and frees its active sequence for reuse. Reactivating requires a non-conflicting sequence and an active point.

## 5. Identity, normalization, and duplicate prevention

### Deterministic name normalization v1

In this exact order:

1. reject non-string/empty input and trim outer whitespace;
2. Unicode NFC normalization;
3. map Arabic Yeh `ي`/Alef Maksura `ى` to Persian Yeh `ی`;
4. map Arabic Kaf `ك` to Persian Kaf `ک`;
5. normalize Arabic-Indic and Persian digits to ASCII `0–9`;
6. collapse all Unicode whitespace runs to one ASCII space and trim;
7. apply Unicode case folding for Latin text.

The algorithm is versioned application logic with direct unit vectors; the stored normalized value is derived, not client-authoritative. Punctuation/transliteration/fuzzy similarity is not normalized in v1.

### Duplicate boundary

The exact governed duplicate key is organization + normalized Persian name + LogisticsPointType + country + null-safe Province + City. Exact matches are rejected with a stable conflict response. Probable candidates—same organization/country/type with matching code fragment, alternate English/Persian name, or same normalized name in adjacent/less-specific geography—produce an admin-only warning and require explicit confirmation to create a distinct record. Probable warnings never disclose another organization and never silently merge. No fuzzy engine or cross-tenant candidate lookup is included.

## 6. Historical and delete behavior

- No DELETE endpoint exists.
- Type and point records use activate/deactivate actions with expected version.
- An inactive type cannot be chosen for a new point; existing points remain readable.
- An inactive LogisticsPoint cannot be newly associated or reactivated in Project configuration; existing associations and authorized history remain readable.
- “Remove from Project configuration” means deactivate the ProjectLogisticsPoint row, not delete it.
- Deactivation changes future selection only. It does not modify Project, RoutePlan, Checkpoint, Milestone, OperationalEvent, or free-text legacy data.
- Reactivation is explicit, audited, version-checked, and revalidates organization, point/type state, uniqueness, and sequence.

## 7. Security and permissions

Proposed explicit permissions:

| Permission | Allowed behavior | Intended principal |
| --- | --- | --- |
| `logistics_point_type.read` | Internal type list/detail including inactive where authorized | Admin; expert selector receives active allowlist only |
| `logistics_point_type.manage` | Create/update/activate/deactivate type | Admin only |
| `logistics_point.read` | Organization-scoped list/detail/select | Admin and authorized expert |
| `logistics_point.manage` | Organization-scoped create/update/activate/deactivate and duplicate override | Admin only |
| `project_logistics_point.read` | Read network for an authorized Project | Admin and authorized expert |
| `project_logistics_point.manage` | Associate/update/deactivate/reactivate/reorder for authorized Project | Authorized expert and admin |

Every service resolves exactly one active OperationalMembership and organization before querying resource existence. Project and LogisticsPoint composite organization constraints are rechecked in commands. Public UUIDs are the only API identities; internal numeric IDs, organization IDs, candidate counts from other tenants, and forbidden-existence distinctions are never serialized.

Unauthenticated access returns 401. Authenticated unauthorized, cross-tenant, and nonexistent object access use the repository-approved non-disclosing 404/403 policy consistently; the implementation security review must freeze one response mapping and negative-test identical response shape. UI role guards are convenience only. All writes capture actor and audit; duplicate override requires an explicit reason.

## 8. Proposed internal API contract

No endpoint is public or customer-facing. OpenAPI must describe UUID parameters, request/response allowlists, pagination, filters, stable errors, and versions before implementation completion.

### LogisticsPointType admin APIs

- `GET /api/admin/logistics-point-types`
- `POST /api/admin/logistics-point-types`
- `GET /api/admin/logistics-point-types/{public_id}`
- `PATCH /api/admin/logistics-point-types/{public_id}`
- `POST /api/admin/logistics-point-types/{public_id}/activate`
- `POST /api/admin/logistics-point-types/{public_id}/deactivate`

### LogisticsPoint APIs

- Admin management under `/api/admin/logistics-points` with list, create, detail, update, activate, and deactivate.
- Expert selection: `GET /api/internal/logistics-points` and detail by public ID, always active-only and organization-scoped.

### ProjectLogisticsPoint APIs

- `GET /api/projects/{project_public_id}/logistics-points`
- `POST /api/projects/{project_public_id}/logistics-points`
- `GET /api/projects/{project_public_id}/logistics-points/{association_public_id}`
- `PATCH /api/projects/{project_public_id}/logistics-points/{association_public_id}`
- `POST .../{association_public_id}/activate`
- `POST .../{association_public_id}/deactivate`
- `POST /api/projects/{project_public_id}/logistics-points/reorder`

### Common behavior

- page ≥ 1; default 20, maximum 100; deterministic public cursor or page metadata consistent with existing internal APIs;
- safe sort allowlist: code, Persian/English name, display order, sequence, and updated time only where applicable;
- code/name search bounded to 160 characters;
- point filters: type, country, Province/City, active state; admin may request inactive, expert selector cannot;
- expected `version` required for every mutation; stale update returns stable 409 without mutation;
- list/detail serialize public IDs and display values, never numeric IDs;
- create returns 201; validation 400/422 per frozen repository convention; exact duplicate/version conflict 409; authentication 401; non-disclosing forbidden/not-found per accepted Security mapping;
- reorder is one atomic command containing all active association public IDs and expected versions, validates a complete nonduplicated sequence, and either commits all changes/audit or none;
- no hard delete, generic event endpoint, RoutePlan/Checkpoint side effect, or public route.

## 9. User experience contract

### Admin

Admin navigation provides separate Logistics Point Types and Logistics Points views. Both support bounded search/filter/sort/pagination, create/edit, activation/deactivation, version-conflict refresh, and bilingual labels. Codes become read-only after creation. Point creation shows exact-duplicate rejection and probable-duplicate warning with explicit reviewed override. There is no hard delete, bulk import, map, or approval-workflow UI.

### Project configuration

The mobile-safe, bilingual flow is:

1. select active LogisticsPointType;
2. filter active authorized points;
3. select LogisticsPoint;
4. assign one bounded Project role;
5. set sequence;
6. optionally set Project display label and notes;
7. save with expected Project/association version.

The display label is presentation-only, cannot substitute for point selection, and does not alter master name, duplicate matching, search identity, or historical evidence. Experts cannot type a new point or bypass inactive/tenant filters. A missing point is handled operationally by an admin; formal request/approval workflow remains deferred. Reordering supports touch/mobile interaction plus accessible non-drag controls.

## 10. Migration contract

- Expected revision: `20260810_logistics_network`.
- Parent: `20260809_cargo_catalog_items`.
- One Alembic head before and after upgrade.
- Add only `logistics_point_type`, `logistics_point`, `project_logistics_point`, their indexes, FKs, check/unique constraints, and no unrelated changes.
- Insert zero LogisticsPointType or LogisticsPoint rows. An authorized administrator creates the first and later type records through Admin UI. A versioned/checksummed catalog is optional import tooling and is never a release or deployment prerequisite (ADR-028).
- Perform no legacy backfill or conversion and preserve Country, Province, City, CanonicalLocation, Project, OperationalShipment, RoutePlan, Checkpoint, Milestone, and OperationalEvent data unchanged.
- Fresh-chain upgrade, Production-like PostgreSQL upgrade, downgrade/re-upgrade, constraint parity, and single-head checks are required before release.
- Downgrade drops only the three new tables in dependency order after explicit authorization. Operational rollback retains additive tables by default.

The migration name and parent are planned identifiers, not created by this documentation task.

## 11. Acceptance criteria and test traceability

### Domain and data quality

- Type create/list/detail/update/activate/deactivate enforces immutable unique code, required bilingual names, accepted type boundary, version, and audit.
- Point create/list/detail/update/activate/deactivate enforces organization-local code, active required type, country, optional consistent geography, normalization, duplicate rules, version, audit, and no delete.
- Project association supports multiple rows for one point only with different roles, unique Project–point–role, active unique sequence, bounded roles, atomic reorder, and Project/point organization equality.
- Inactive types/points are excluded from new selection; authorized historical references remain readable.
- No legacy value, free-text address, Project network, RoutePlan, or Checkpoint is inferred or created.

### Security

- Negative tests prove organization-first isolation for list, detail, search, duplicate warning, create/update, association, activation, and reorder.
- Admin/expert permission separation is backend-enforced.
- IDOR tests with another tenant’s UUID disclose neither object nor candidate existence.
- Responses, errors, logs, and OpenAPI expose no internal numeric resource or organization IDs.
- Inactive/historical reads follow explicit allowlists and never broaden customer/public access.

### Compatibility and frontend

- Existing Projects remain valid with zero ProjectLogisticsPoint rows; existing RoutePlans/Checkpoints and APIs are unchanged.
- Existing backend/frontend regression gates pass when implementation is later authorized.
- Admin and Project UI cover validation, duplicate warnings, inactive state, version conflicts, ordering, keyboard access, Persian/English consistency, and responsive layouts at 360, 390, 412, 768, and desktop widths.
- There is no uncontrolled point free text, bulk import, map, public search, reporting UI, or automatic operational side effect.

### Migration

- Full fresh chain reaches `20260810_logistics_network` with one head.
- Upgrade from `20260809_cargo_catalog_items`, downgrade, and re-upgrade preserve prior schema/data and prove new constraints/indexes.
- Upgrade inserts zero rows unless a later separately approved seed step is executed outside the migration.
- PostgreSQL behavior is proven for partial/expression uniqueness and composite tenant FKs; SQLite parity tests do not weaken Production invariants.

## 12. Development performance boundary

This is verification capacity, not a Production SLA:

- fixture/profile of 10,000 LogisticsPoints distributed across multiple organizations;
- organization-scoped paginated list and bounded code/name search;
- active/type/country/Province/City filters and safe sort;
- Projects tested at 50 active configured points, with a separate 100-point stress observation but no Product limit inferred;
- atomic reorder at the 50-point verification size;
- query-count/N+1 assertions for list, selector, Project network, and reorder reads;
- PostgreSQL `EXPLAIN`/index-use review for organization-leading list, exact duplicate, name/code search, geography, and active sequence queries.

Record timings and plans as development evidence only. No latency, throughput, or Production SLO is invented here.

## 13. Rollout and rollback contract

### Rollout after explicit implementation approval

1. Accept Section 15 decisions and implementation authority.
2. Implement migration, backend, OpenAPI, tests, and frontend under feature-controlled internal routes.
3. Validate one head, fresh/upgrade/downgrade paths, security negatives, compatibility, and performance evidence.
4. Back up the target database and explicitly apply the additive migration outside startup.
5. Deploy immutable backend/frontend Release 1.7.0 and verify health/auth/admin/Project smoke gates.
6. Populate initial types only through the separately approved seed catalog, or through explicitly approved admin entry if that decision changes.
7. Existing Projects remain unchanged; no backfill runs.

### Rollback

- switch application to immutable Release 1.6.1 and disable 1.7.0 routes/UI;
- retain additive tables and their data by default for reconciliation;
- do not auto-downgrade or delete configured points;
- database downgrade requires separate authorization, confirmed absence/export/backup of ProjectLogisticsPoint data, and restore readiness;
- a destructive downgrade must preserve/export LogisticsPointType, LogisticsPoint, ProjectLogisticsPoint, actor, version, and history evidence first.

## 14. OpenAPI and documentation completion gates

Before implementation acceptance, update OpenAPI with all bounded operations and schemas; release notes with actual delivered scope/exclusions; migration/database documentation; admin and Project user guidance; permission matrix; deployment/backup/migration/rollback runbook; release manifest identity; and roadmap matrix implementation state. Documentation cannot claim operational capability until corresponding tests and immutable release evidence exist.

## 15. Required decisions for governance approval

All ten decisions are Accepted by Product, Architecture, Operations, Data, and Security for the bounded scope. No personal signature is inferred.

| ID | Decision | Recommended bounded option | Required approvers | Fail-safe if unresolved | Status |
| --- | --- | --- | --- | --- | --- |
| R17-D01 | Multiple roles for one point in a Project | Multiple ProjectLogisticsPoint rows allowed only for distinct roles; unique Project + point + role | Product, Architecture, Operations, Data | Permit only one association and block duplicates | Accepted |
| R17-D02 | Sequence uniqueness | Positive sequence unique among active ProjectLogisticsPoint rows within one Project; reorder atomic | Product, Operations, Architecture, Data | Reject conflicting sequence and make no partial reorder | Accepted |
| R17-D03 | Country representation | Required FK to existing `country`; expose country code/name projection, not numeric ID | Product, Data, Architecture | Reject point creation without active governed country | Accepted |
| R17-D04 | Province/City integration | Optional existing FKs; City requires consistent Province/Country; do not redesign geography | Data, Architecture, Product, Operations | Accept country-only point; do not infer geography | Accepted |
| R17-D05 | Initial LogisticsPointType population | Separate governed, versioned/checksummed Reference Data catalog and explicit seed action; no migration rows | Product, Data, Operations, Architecture, Security consultation | Deploy empty catalog; Production apply separately authorized | Accepted |
| R17-D06 | Duplicate warning vs rejection | Hard reject exact composite duplicate; probable warning without fuzzy/trigram infrastructure; never merge | Product, Data, Operations, Security, Architecture | Reject exact/ambiguous creation pending steward review | Accepted |
| R17-D07 | Deactivation/removal | Deactivate only; removal from Project means inactive association; history readable; no delete endpoint | Product, Operations, Data, Architecture, Security | Preserve record and deny destructive action | Accepted |
| R17-D08 | Admin/expert permissions | Admin manages types/points; authorized expert reads/selects points and manages authorized Project associations | Product, Security, Operations, Architecture | Deny by default; admin-only management | Accepted |
| R17-D09 | Project display label | Optional presentation-only label; not searchable master identity and never overwrites master/history | Product, Operations, Data | Omit label and display master name | Accepted |
| R17-D10 | Release 1.7.0 implementation authority | Authorize only this contract after D01–D09 closure and readiness review | Product, Architecture, Operations, Data, Security | Scope expansion remains prohibited | Accepted |

## 16. Authorization verdict

R17-D01 through R17-D10 are Accepted. Release 1.7.0 implementation is authorized only for the exact data, API, UI, security, migration, catalog-preparation, OpenAPI, test, version, and documentation boundaries in this contract. Production Seed apply, Production migration, packaging, tagging, deployment, and every exclusion remain unauthorized.

# Release Notes

## 1.8.0 — Project Configuration Foundation

Status: **Implemented — Not Deployed**. This minor release adds opaque
`DocumentDefinition.public_id`, governed milestone types, and organization-scoped
Project service, document-requirement, milestone-definition configuration. It reuses
the existing Project Logistics Network and creates no operational objects. Database
revision: `20260811_project_configuration` (previous: `20260810_logistics_network`).
Production Seed was not executed.

## 1.7.0 — Logistics Network Foundation

| Item | Value |
| --- | --- |
| VERSION | `1.7.0` |
| PREVIOUS VERSION | `1.6.1` |
| CHANGE | Backward-compatible MINOR |
| DATABASE | Additive `20260810_logistics_network` |
| REFERENCE DATA | Separate checksummed catalog; no automatic or Production apply |
| DEPLOYMENT | Backend, frontend, and additive migration package |
| PRODUCTION | Not migrated, seeded, or deployed by release publication |

Adds governed LogisticsPointType reference data, organization-scoped LogisticsPoint master data, and ProjectLogisticsPoint configuration with bounded roles and atomic ordering. Internal/admin APIs and responsive staff UI support create, edit, select, reorder, activate, and deactivate without hard deletion. Exact duplicates are rejected, probable duplicates require explicit confirmation, all organization/project writes are actor-audited, and numeric database identifiers are not serialized.

Maps/GIS, coordinates, route or checkpoint generation, ETA/traffic/weather, customer/public discovery, dashboards/reporting, allocation, cargo-unit linkage, partial delivery, packaging, bulk import, generic workflow/approval/EAV, and AI behavior remain excluded.

Final acceptance passed 546 backend tests with 20 skips, 96 frontend tests,
TypeScript, ESLint, Ruff for the Logistics Network Python slice, production
build, OpenAPI/runtime parity, disposable PostgreSQL fresh/parent/round-trip
migrations, tenant isolation, and authenticated desktop/mobile UAT. The UI
bundle embeds version 1.7.0 through `VITE_APP_VERSION`; no visible version label
is rendered. The checksummed LogisticsPointType catalog is included as prepared
reference data, but Production Seed is not automatic and was not executed.

Application rollback targets `release-v1.6.1-20260802` and normally retains the
additive 1.7.0 tables. Database downgrade to `20260809_cargo_catalog_items`
requires separate authorization and preservation assessment after any use.

## 1.6.1 — Frontend Cache Policy Hardening

| Item | Value |
| --- | --- |
| VERSION | `1.6.1` |
| PREVIOUS VERSION | `1.6.0` |
| CHANGE | Backward-compatible PATCH |
| DATABASE | Unchanged: `20260809_cargo_catalog_items` |
| DEPLOYMENT | Frontend-only configuration/package hardening |
| BACKEND RESTART | Not required by application behavior |
| DATABASE MIGRATION | None |

Adds a tracked IIS configuration source with explicit response policies: application-shell HTML is not stored, content-hashed `/assets/` files are immutable for one year, and unhashed root manifests/icons revalidate. API proxy and SPA fallback ordering are unchanged. No Service Worker or PWA behavior is introduced.

## 1.6.0 — Cargo Catalog and Shipment Cargo Foundation

| Item | Value |
| --- | --- |
| VERSION | `1.6.0` |
| CHANGE | Backward-compatible MINOR |
| DATABASE | `20260809_cargo_catalog_items` |
| SEED | None; Release 1.5.0 catalog unchanged |
| PRODUCTION | Not deployed by this task |

Adds organization-owned CargoCatalogItem and CargoItemAlias administration, deterministic alias normalization, and OperationalShipment-owned ShipmentCargoItem snapshots with positive exact-UOM quantities. Legacy request cargo remains unmodified. Allocation, customer search/projection, dashboards, and reports are excluded.

## 1.5.0 — Reference Data Initial Catalog

| Field | Value |
| --- | --- |
| VERSION | `1.5.0` |
| CHANGE TYPE | MINOR |
| RELEASE NAME | Reference Data Initial Catalog |
| BASE RELEASE | `1.4.0` — Governed Master Data Foundation |
| DATABASE REVISION | `20260808_reference_seed` |

- Accepts PDR-014 D01-D10 and the reviewed initial catalog: 15 CargoTypes, 12 ServiceTypes, and 9 Units of Measure.
- Adds bounded persistent `ReferenceDataSeedRun` evidence under clarified ADR-021.
- Adds explicit, checksum-controlled, fail-closed `plan` and `apply --confirm` commands; no startup or migration seed execution.
- Preserves manual values, inactive values, legacy cargo fields, and current TransportMethod behavior; no automatic backfill or synchronization.
- Excludes `CARGO_GENERAL_GOODS`, `SERVICE_PROJECT_LOGISTICS`, packaging/handling/container concepts, cargo attributes, CargoCatalogItem, ShipmentCargoItem, allocations, service relationships, search, reports, and dashboards.
- Production Seed execution, release packaging, deployment, staging, committing, pushing, and tagging are not performed by this implementation task.

## 1.4.0 — Governed Master Data Foundation

### Feature: Governed Master Data Foundation

| Field | Value |
| --- | --- |
| VERSION | `1.4.0` |
| RELEASE NAME | `Governed Master Data Foundation` |
| CHANGE TYPE | `MINOR` |
| CAPABILITIES | `CAP-013` (primary), `CAP-009`, `CAP-010` |
| SLICE | `SLICE-B1` only |
| DATABASE REVISION | `20260807_master_data` |
| DEPLOYMENT TYPE | Additive database migration, backend restart, frontend immutable release |

- Adds explicit canonical CargoType, ServiceType, and UnitOfMeasure tables with immutable normalized codes, bilingual labels, activation lifecycle, timestamps, and optimistic versions.
- Adds admin-only bounded APIs and a reusable responsive administration surface with filtering, sorting, pagination, and no hard-delete action.
- Performs no seed insertion, classification, backfill, Cargo Catalog, ShipmentCargoItem, allocation, aliases, customer search, dashboard, or reporting work.
- Preserves legacy fields and behavior. Application rollback disables the new backend/frontend surface while retaining additive master-data tables; database downgrade is permitted only after confirming B1 records need not be retained.
- Production release preparation requires a backup, explicit migration to `20260807_master_data`, backend restart, immutable frontend build, smoke tests, and a new release manifest. No release package is built by this slice review.

### Patch: Central Route Scroll Restoration

| Field | Value |
| --- | --- |
| VERSION | `1.3.1` |
| RELEASE NAME | `Central Route Scroll Restoration` |
| CHANGE TYPE | `PATCH` |
| DEPLOYMENT TYPE | Frontend-only immutable release |
| DATABASE REVISION | `20260806_execution_units` (unchanged) |
| BACKEND | Operationally unchanged; restart not required |

- Added one centralized route-level scroll policy under `BrowserRouter`; no per-page patches were introduced.
- Reset PUSH and REPLACE navigation to a different pathname with automatic (non-smooth) behavior while preserving browser-native POP restoration, same-path query position, explicit `preserveScroll`, and modal state.
- Positioned valid hash targets below the sticky header with bounded asynchronous retries that stop after user interaction.
- Added optional accessible destination-heading focus and regression coverage at 360, 390, and 412 pixel viewport widths.
- Added no backend, API, database, migration, dependency, or environment change.
- If deployed over 1.3.0, rollback to immutable release `release-v1.3.0-20260801`. If Production still runs 1.2.0, the operational rollback target remains `release-v1.2.0-20260801` and deploying 1.3.1 introduces both the 1.3.0 Command Center and this patch.

### Feature: Forwarder Command Center

| Field | Value |
| --- | --- |
| VERSION | `1.3.0` |
| RELEASE NAME | `Forwarder Command Center` |
| CHANGE TYPE | `MINOR / Customer-facing UX Enhancement` |
| CAPABILITIES | `CAP-007` (primary), `CAP-010`, `CAP-001` |
| PRODUCT DECISION | `PDR-012` |
| DEPLOYMENT TYPE | Frontend-only immutable release; IIS pointer switch during deployment |

- Replaced the long-form root landing page with an operational portal focused on request registration and request/Project tracking; staff login remains available once, behind the compact header menu.
- Preserved the domestic/international request forms and public request and Project tracking routes.
- Moved concise About and Contact information to dedicated routes and removed promotional sections from root rendering.
- Added bilingual accessible validation, Enter submission, responsive layout, and purpose-aligned metadata.
- No backend, API, authentication, database, migration, dependency, or environment change.
- Rollback: switch the IIS pointer to immutable release `1.2.0`; no data rollback is needed.

### Feature: Multi-unit Operational Project Tracking

Release metadata:

| Field | Value |
| --- | --- |
| VERSION | `1.2.0` |
| RELEASE NAME | `Multi-unit Operational Project Tracking` |
| CHANGE TYPE | `MINOR / Feature` |
| PRIMARY CAPABILITY | `CAP-001 Project Management`, `CAP-003 Execution Management`, `CAP-004 Timeline Platform`, `CAP-007 Customer Portal`, `CAP-008 Expert Workspace` |
| RFC / EPIC / SLICE | `RFC-001` / `EPIC-001` / Release 1.2.0 vertical slice |
| DATABASE REVISION | `20260806_execution_units` |
| DEPLOYMENT TYPE | Additive database migration, backend restart, and frontend rebuild |

Changes:

- Added canonical Project-scoped `ExecutionUnit` state and append-only `OperationalEvent` history under accepted ADR-018/019 and PDR-005/006/010.
- Added opaque expert v2 and customer project-tracking APIs with pagination, filtering, search, idempotency, optimistic versions, and strict customer projections.
- Added separate delayed, stale, attention-required, and incomplete-document alert projections; document completeness remains unavailable in this release.
- Added scalable expert and customer unit lists with lazy timelines and 25-item pages.
- Added configurable threshold policy environment values `EXECUTION_UNIT_STALE_HOURS` (default `24`) and `EXECUTION_UNIT_THRESHOLD_POLICY_VERSION` (default `stale-v1`).
- Preserved legacy `ShipmentTransportUnit` models and APIs unchanged for the compatibility period.

Compatibility and rollout:

- Existing ShipmentRequest, OperationalShipment, legacy unit APIs, and public request-tracking responses remain unchanged.
- Existing Project and legacy unit rows receive no guessed or destructive backfill. New Project tracking codes are generated by the application; migrated existing Projects remain internal until explicitly assigned an approved opaque code.
- Upgrade explicitly to `20260806_execution_units`; migrations are never run at application startup.
- Application rollback may return to the prior backend/frontend while leaving additive tables in place. Database downgrade to `20260805_project_foundation` is safe only after confirming no Release 1.2.0 data must be retained.

PostgreSQL release-readiness verification (2026-08-01):

- Passed a fresh full-chain upgrade on disposable local PostgreSQL 18.0, followed by downgrade to `20260805_project_foundation` and re-upgrade to the single head `20260806_execution_units`.
- Preserved seeded ShipmentRequest, OperationalShipment, ShipmentTransportUnit, and Project rows across the migration round trip. No ExecutionUnit or OperationalEvent rows were backfilled, and nullable legacy relationships remained valid and readable.
- Passed all six focused execution-unit tests on PostgreSQL, including organization scoping, opaque IDs, immutable Project-local codes, optimistic concurrency, idempotency replay/conflict, append-only API behavior, customer/internal visibility separation, 404-safe cross-organization access, pagination/filter/search, and aggregate alert/status calculations.
- With one Project, 500 ExecutionUnits, and 10,000 OperationalEvents, the measured 25-item stale unit-list response was 26.10 ms, 10 SQL statements, and 4,256 bytes; the measured 20-event timeline response was 19.67 ms, 11 SQL statements, and 8,564 bytes. PostgreSQL used `ix_execution_unit_project_status_active` for the unit scan and `ix_operational_event_unit_occurred` for the timeline lookup. No N+1 behavior was detected.
- Final regression passed: backend 510 passed / 20 skipped, frontend 70 passed, ESLint 0 errors / 11 warnings, production frontend build, Python compilation, OpenAPI YAML parse, `git diff --check`, current-tree secret scan with zero findings, and migration-head check.
- Remaining non-blocking warnings are existing Python/SQLAlchemy deprecations, 11 frontend lint warnings, stale Browserslist data, and the frontend bundle-size advisory. No production SLA threshold was asserted.

### Feature: Landing Page Value Proposition Enhancement

Release metadata:

| Field | Value |
| --- | --- |
| VERSION | `1.1.0` |
| RELEASE NAME | `Landing Page Value Proposition Enhancement` |
| CHANGE TYPE | `MINOR / Feature` |
| GIT COMMIT | `PENDING — to be recorded after commit creation` |
| DATABASE REVISION | `20260804_case_documents` — unchanged, no pending migration |
| DEPLOYMENT TYPE | `Frontend-only application deployment; no database migration` |

Version decision: the repository has no separate release-version policy document; the runtime application baseline is `1.0.0`, and this backward-compatible user-facing feature increments the SemVer minor component to `1.1.0`.

Business value:

- Positions Forwardert as a workflow-management platform rather than only an online request form.
- Makes process visibility, controlled document management, reporting, and stakeholder coordination easier for prospective users to understand.
- Reduces ambiguity between process visibility and unsupported GPS or live-location tracking.
- Improves Persian and English product discovery through clearer search and social metadata.

Changes:

- Updated product positioning from a request-form-focused message to international freight workflow management.
- Added a key capability section covering process visibility, authorized document access, operational reporting, and stakeholder coordination.
- Improved SEO metadata, Open Graph title and description, keywords, document language, and dynamic title fallback behavior.
- Updated bilingual Persian and English landing-page content.

Technical scope:

- Updated the public landing-page composition and responsive capability cards.
- Updated Persian and English translation resources.
- Updated static SEO/Open Graph metadata and runtime title fallback configuration.
- Added release documentation and refreshed desktop/mobile UI evidence.
- No backend, API, database, migration, dependency, or routing changes.
- No GPS, map, live-location, or automated carrier-integration capability is claimed.

Deployment impact:

- Rebuild and deploy the frontend application assets.
- Backend restart is not required for this feature.
- No Alembic upgrade, data backfill, environment-variable change, or service dependency change is required.
- Existing request submission, public status tracking, expert access, and admin/reporting routes remain compatible.
- Browser/CDN cache invalidation should follow the normal frontend deployment procedure so updated HTML metadata is served.

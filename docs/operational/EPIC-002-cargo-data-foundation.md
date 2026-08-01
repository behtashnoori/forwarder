# EPIC-002: Cargo Data Foundation

- **Epic ID:** EPIC-002
- **Source:** RFC-002
- **Discovery evidence:** [Discovery and Domain Analysis Report](discovery-cargo-data-and-scroll-analysis-20260801.md)
- **Status:** Draft
- **Date:** 2026-08-01
- **Capability owners:** Data (CAP-013), Product (CAP-002/CAP-007), Operations (CAP-003), Security (CAP-010)
- **Decision authority:** None. This plan does not accept PDR/ADR records or authorize implementation.

## Objective and boundaries

Establish governed cargo master data, organization catalogs, immutable shipment-item meaning, quantitatively safe unit allocation, and authenticated tenant-scoped traceability through independently deployable additive slices. ShipmentRequest, Project, OperationalShipment, ExecutionUnit, TransportMode, customer/public visibility, and legacy source-of-truth boundaries remain intact. A generic EAV model, guessed backfill, destructive history edits, anonymous portfolio search, and any implementation in this documentation task are excluded.

## SLICE-B1 — Master Data Governance Foundation

- **Capability / goal:** CAP-013 / establish reusable governance conventions, stewardship, reserved values, validation, audit, and adoption controls for explicit cargo master data.
- **Dependencies / accepted decisions required:** Constitution/Baseline/Catalog review; PDR-013-D01, D04, D12 and ADR-021 Accepted.
- **Scope / out of scope:** Governance infrastructure and contracts for immutable codes, lifecycle, localization, provenance, audit, and `UNCLASSIFIED`; excludes domain administration screens, cargo records, allocations, and search.
- **Database / API / UI impact:** Additive governance columns/tables and canonical migration; bounded admin/reference contracts; minimal internal stewardship surface only if separately approved.
- **Security / migration:** CAP-013 admin permission, least privilege, audit; nullable adoption, no guessed backfill, legacy reads retained.
- **Tests / rollback:** constraints, reserved records, permission/audit, migration N/N-1 and reconciliation; disable writes/new reads and retain additive data.
- **Target version:** Next approved MINOR release; exact SemVer assigned at slice authorization.
- **Acceptance criteria:** owners and runbook named; immutable-code/deactivation rules enforced; `UNCLASSIFIED` works; no EAV; no inferred data; gates and rollback proven.

## SLICE-B2 — CargoType, ServiceType and UnitOfMeasure Administration

- **Capability / goal:** CAP-013 and CAP-009 / administer explicit bilingual taxonomies and accepted service-package references.
- **Dependencies / accepted decisions required:** B1; PDR-013-D01–D04; ADR-021.
- **Scope / out of scope:** CargoType hierarchy, ServiceType, UOM CRUD via activate/deactivate and Project/request/shipment service relationships as separately designed; excludes conversion, organization taxonomy extensions, catalog/items/allocation/search.
- **Database / API / UI impact:** Explicit tables and relationship constraints; paginated admin/reference APIs; accessible bilingual administration and separate mode/service selectors.
- **Security / migration:** governed admin permissions and audit; additive references, legacy transport/service text preserved, no automatic remap.
- **Tests / rollback:** hierarchy cycles, immutable/unique code, UOM dimension, cardinality, localization, auth, accessibility; feature flags disable admin/new links while history remains readable.
- **Target version:** Independently approved MINOR after B1.
- **Acceptance criteria:** type/mode/service axes remain distinct; inactive history renders; required structured units validate; package ownership lineage is demonstrable.

## SLICE-B3 — Cargo Catalog and Aliases

- **Capability / goal:** CAP-013 and CAP-010 / provide tenant-owned reusable cargo definitions and customer-specific aliases without cross-tenant disclosure.
- **Dependencies / accepted decisions required:** B1–B2 as applicable; PDR-013-D05/D06/D11/D12; ADR-022.
- **Scope / out of scope:** Organization CargoCatalogItem lifecycle, immutable local code, aliases, optional platform-definition link; excludes ShipmentCargoItem, allocation, customer cross-Project search, global customer catalog.
- **Database / API / UI impact:** Additive tenant-keyed catalog/alias records and indexes; paginated exact lookup/admin APIs; organization catalog stewardship UI.
- **Security / migration:** tenant-first authorization, alias conflict quarantine, audit; evidence-only manual mapping, no part-number correlation across tenants.
- **Tests / rollback:** tenant uniqueness/isolation, alias conflict, field permissions, pagination, audit, negative leakage; disable mutations/lookup and retain catalog data.
- **Target version:** Independently approved MINOR.
- **Acceptance criteria:** identical part numbers coexist across organizations; canonical local code cannot change; forbidden tenant data is absent from results/logs; legacy unaffected.

## SLICE-B4 — ShipmentCargoItem

- **Capability / goal:** CAP-002 / record cargo as an immutable OperationalShipment transaction snapshot with optional catalog lineage.
- **Dependencies / accepted decisions required:** B1 and relevant B2/B3 contracts; PDR-013-D04–D07/D11/D12; ADR-022.
- **Scope / out of scope:** Required quantity/UOM/name snapshot, optional catalog and supplied part/HS/type snapshots, audited correction; excludes allocation, conversion, customer portfolio search, destructive catalog propagation.
- **Database / API / UI impact:** Additive item/revision records under OperationalShipment; paginated item commands/reads with expected version/idempotency; shipment item entry/history UI.
- **Security / migration:** shipment/resource permissions and field classification; structure for enabled new transactions, legacy descriptions remain readable, no guessed backfill.
- **Tests / rollback:** required/precision/UOM constraints, catalog-change immutability, correction history, auth, N/N-1; stop structured writes and fall back to legacy display while retaining snapshots.
- **Target version:** Independently approved MINOR.
- **Acceptance criteria:** no unitless structured record; catalog edits do not rewrite history; corrections are auditable; existing shipment workflows remain compatible.

## SLICE-B5 — ExecutionUnitCargoAllocation

- **Capability / goal:** CAP-003 with CAP-002 / allocate exact-UOM shipment item quantity safely to eligible ExecutionUnits.
- **Dependencies / accepted decisions required:** B4 and canonical Project/ExecutionUnit readiness; PDR-013-D08/D09; ADR-023; applicable accepted Project/ExecutionUnit lifecycle decisions.
- **Scope / out of scope:** Positive exact-UOM allocations, derived remainder, same Project/shipment rules, locking/idempotency, correction/reallocation; excludes conversion, split/merge, cross-shipment allocation by default.
- **Database / API / UI impact:** Additive allocation/version/lineage constraints; explicit allocation/correction commands; staff quantity/remainder/history UI.
- **Security / migration:** Project/shipment/unit/action authorization and elevated correction audit; no inferred allocations from legacy records.
- **Tests / rollback:** concurrent ceiling races, stale version, idempotent replay, lifecycle transitions, deadlock retry, permission/audit; disable commands/projection and retain allocation history.
- **Target version:** Independently approved MINOR after B4 and ExecutionUnit gate.
- **Acceptance criteria:** active sum never exceeds item quantity under concurrency; cancelled/inactive unit fails closed; fulfilled/corrected history remains reconstructable.

## SLICE-B6 — Authenticated Customer Cross-Project Cargo Search

- **Capability / goal:** CAP-007, CAP-010, CAP-006 / let authenticated customers find authorized cargo across their organization’s Projects safely.
- **Dependencies / accepted decisions required:** B3–B4 (B5 optional for allocation display); PDR-013-D05/D06/D10/D11; ADR-024 and Security/Data review.
- **Scope / out of scope:** Tenant-first exact/trigram PostgreSQL search, pagination, safe ranking, customer allowlist, customer-visible events; excludes anonymous/public portfolio search, internal notes, unrestricted sensitive values, external engine.
- **Database / API / UI impact:** Additive scoped indexes/projection; authenticated bounded endpoint; accessible responsive search/results/detail links.
- **Security / migration:** authorization before matching, opaque IDs, rate limit/audit/no forbidden counts or logs; legacy fields included only if explicitly approved, no public-scope widening.
- **Tests / rollback:** cross-tenant/field/event negative tests, enumeration/rate abuse, relevance/Persian-English normalization, query plan/load, 360/390/412 accessibility; disable endpoint/UI and retain indexes/source data.
- **Target version:** Independently approved MINOR.
- **Acceptance criteria:** zero cross-tenant disclosure in API/cache/log/error/UI tests; accepted relevance/latency targets; public tracking unchanged; customer-safe rollback proven.

## Epic completion

EPIC-002 completes only after every delivered slice has its own accepted decisions, implementation authorization, immutable release evidence, migration/rollback proof, and operational ownership. Documentation completion alone is not capability completion.

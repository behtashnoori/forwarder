# ADR-061: Typed Document Context and Exact-Version Visibility

- **Status:** ACCEPTED — bounded Phase 3 P3-06 implementation
- **Date:** 2026-09-25
- **Decision authority:** Product Owner's sequential P3-05/P3-06 mission; Architecture and Security boundaries of LPAF v2.7
- **Scope:** tenant-owned OperationalShipment documents only; no Delivery model, ownership transfer, release, deployment or Production
- **Related:** ADR-030, ADR-047, ADR-050, ADR-057–060, PDR-020, MDPM

## Decision

Document context answers **what the exact file version is about**. Visibility answers **who may see that version**. The existing `CaseDocumentFile` remains the immutable physical file/version and private-byte authority. `OperationalDocumentContext` attaches one exact version to one typed Shipment, Cargo, RouteLeg or ExecutionUnit target. Its current visibility is separate: `INTERNAL`, `CARGO_OWNER`, or `EXPLICIT_SHARED`. An append-only event records the before/after context, audience, actor, time and reason. Explicit Customer Portal audiences are relational allowlist rows, never a client-controlled generic JSON permission map.

The owning Transport Expert alone uploads, replaces, changes context or changes visibility. Existing authorized internal reads remain governed by the Shipment parent. Organization Admin receives no management permission, and Platform Admin receives no tenant bytes. Every direct download rechecks the authenticated actor, tenant, parent, exact `CaseDocumentFile` row and audience. A file ID or storage key never grants access.

## Target and audience rules

- Shipment context belongs to the authorized OperationalShipment. Cargo must be a member of that Shipment. RouteLeg must be in one of that Shipment's RoutePlans. ExecutionUnit must participate through that Shipment's RouteStageExecution. The service resolves all targets from persistence. Composite foreign keys additionally bind the file version, Shipment, tenant, Cargo and ExecutionUnit where the schema supports them.
- `INTERNAL` is never exposed to a Customer or Public Tracking.
- `CARGO_OWNER` is valid only for Cargo context. The current canonical identity model has no approved explicit Portal Account ↔ CRM Customer entitlement. Therefore **Customer download fails closed** for this visibility until a separately governed entitlement exists. Cargo membership, Request origin, matching name, email or phone do not create that link. DN10 remains open.
- `EXPLICIT_SHARED` is available only for Shipment, RouteLeg and ExecutionUnit context. The Expert must select active Portal accounts in the same tenant. It never implies all Shipment Customers. List, page and download are filtered before a Customer receives filename or metadata. Other Customers receive the same absence result as unknown IDs.
- Customer upload, replacement, context/visibility change and private history are absent. Public Tracking receives no file access.

## Exact version, replacement and readiness

Each replacement produces a new `CaseDocumentFile` version, keeps the prior file and context/audit facts, and starts the new version as `INTERNAL` without audience inheritance. Customer routes expose only active exact versions. A stale or guessed version receives a non-disclosing denial. Internal historical access follows its existing parent authorization. Upload and context attachment commit together; a failed transaction removes newly written private bytes. A batch is processed file by file, preserving successful siblings and allowing a failed file to be corrected and retried.

MDPM `OperationalDocumentRequirement`, `ArtifactAssociation`, assessment and readiness rules remain distinct. This decision neither turns a historical version into current readiness nor invents closure policy. Existing Request-owned files and legacy Shipment files are not guessed into new contexts or Customer audiences. Their already-authorized internal behavior remains.

## DN boundaries and future extension

`DN02_DOCUMENT_VISIBILITY_STATUS=RESOLVED_FOR_P3_06`; `DN02_OWNER_TRANSFER_PORTION=OPEN_FOR_P3_13`; `DN09_STATUS=OPEN`; `DN10_STATUS=OPEN`. A future P3-08 Delivery document may extend the typed context contract after the real Delivery model exists. P3-09 owns the broader Customer Shipment projection. No P3-07/P3-08/P3-09 behavior is implemented here.

## Migration and verification

The additive P3-06 migration descends from the actual P3-05 head `20261004_phase3_cargo_allocation_trace`. It creates context, audience and history tables, plus file/Shipment tenant integrity support. It does not backfill visibility, infer context or rewrite stored bytes. Empty downgrade/re-upgrade is supported; populated downgrade refuses to erase facts. One Alembic head is required. Focused authorization, PostgreSQL 18 migration, exact-version, multi-file, normal Chrome and full regressions are P3-06 qualification gates.

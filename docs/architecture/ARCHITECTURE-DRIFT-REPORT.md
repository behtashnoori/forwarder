# Forwarder Architecture Drift Report

Status: Baseline evidence for Forwarder Architecture Governance v1
Repository baseline: Forwarder v1.9.5.1 at `b9a5d71916d99407a5762a2532939af12f2c130d`

## Purpose

This report records differences between the target architecture and the current repository before any runtime change. It authorizes no refactor, migration, seed, deployment, or Production access. The governance task that created it changes documentation and checks only.

## Canonical architecture already present

- ADR-017 and ADR-018 define `Project -> OperationalShipment -> ExecutionUnit`.
- ADR-002 keeps `ShipmentRequest` commercial and `OperationalShipment` operational.
- Organization ownership, membership permissions, opaque public identity, tenant-safe foreign keys, and quarantine fences are implemented across the newer operational modules.
- Cargo uses organization-owned `CargoCatalogItem` and immutable `ShipmentCargoItem` snapshots.
- Project and shipment document policy use explicit requirement and artifact-association records.
- New operational, cargo, logistics, project-configuration, MDPM, OIP, and economics timestamps are timezone-aware.

## Intentional legacy compatibility

| Area | Legacy state | Canonical target/bridge | Governance treatment |
| --- | --- | --- | --- |
| Commercial intake | `ShipmentRequest` contains historical route, cargo, assignment and tracking fields | Explicit lineage into `OperationalShipment` | Preserve compatibility; add no new execution ownership to the request without an Accepted ADR. |
| Tracking | `ShipmentTracking`, `ShipmentTransportUnit`, `ShipmentTransportUnitUpdate` | `OperationalShipment`, `ExecutionUnit`, `OperationalEvent` | Read/bridge only for new work unless an ADR explicitly authorizes a legacy change. |
| Locations | Current expert tracking selection uses tenant `LogisticsPoint`; `TrackingLocationReference` remains a legacy compatibility selector/history | `LogisticsPoint` is organization master data; `CanonicalLocation` is the route bridge/snapshot identity; ADR-041 adds a pending global/adoption target | Preserve snapshots and legacy reads; reviewed legacy/global mapping remains pending and must not be inferred by name. |
| Global logistics network | Phase 1 implements an empty platform `GlobalLogisticsPoint` schema and Platform-Admin-only read API; no adoption or catalog population | ADR-041 accepts tenant adoption and optional organization representation as later phases | Do not seed legacy rows, expose unadopted points to Experts, or weaken `LogisticsPoint` tenant ownership. |
| Time | Many legacy `DateTime()` columns store naive values | UTC Instant plus `timestamptz` and RFC 3339 offset | Preserve until each source contract is proven; never guess historical timezone. |
| Documents | `CaseDocumentFile` is request-owned | `OperationalDocumentRequirement` and `ArtifactAssociation` bind exact files to a shipment | Keep binary ownership and contextual use separate. |

## Accidental duplication or ambiguity

1. `TrackingLocationReference` and `LogisticsPoint` both present selectable logistics-place concepts but have different ownership and APIs.
2. Legacy `ShipmentTransportUnit` and canonical `ExecutionUnit` overlap in user language and tracking responsibility.
3. Workload has more than one definition: displayed workload counts `assigned` and `in_progress`, while referral documentation and rule capacity logic use broader active-assignment concepts.
4. Timestamp serializers return a mixture of explicit UTC, explicit offsets, and offset-less strings.
5. Project document requirements, request files, and shipment artifact associations use similar document terminology despite different ownership.

## High-risk drift

- Multi-unit tracking converts browser local time to UTC, removes timezone information for its legacy database column, then serializes without an offset. A browser may interpret the returned UTC wall-clock value as local time.
- Organization-owned legacy tables can contain quarantined or incomplete ownership; bypassing tenant/query fences would expose cross-tenant data.
- Cargo is shipment-scoped but has no accepted `ExecutionUnit` allocation implementation. Inferring unit quantities would invent operational truth.
- No direct `ExecutionUnit` document ownership exists. Adding a nullable unit foreign key to files would contradict the proposed attachment architecture and MDPM boundaries.
- The expert tracking selector now consumes tenant `LogisticsPoint` under ADR-035 while compatibility clients and historical updates may still use `TrackingLocationReference`; the catalogs remain distinct.
- ADR-041 Phase 1 provides only the empty platform catalog/read boundary. Platform global point -> Organization adoption -> Expert consumption remains unavailable until later controlled phases.

## Items that must not be auto-fixed here

- No timestamp data conversion or column alteration.
- No location catalog merge, backfill, selector switch, or deletion.
- No cargo allocation model.
- No document ownership change or file movement.
- No request/tracking/unit model removal.
- No workload algorithm change.
- No CRM permission or role change.
- No migration, seed, release artifact, deployment, tag, or push.

## Required follow-up governance

Each high-risk item needs a bounded Accepted ADR or an Accepted amendment naming compatibility, tenant/security, migration, rollback, and validation consequences. Until then the current compatibility behavior remains authoritative even where imperfect.

## Post-D2 product/reference drift register — 2026-09-20

PDR-019/PDR-020 and ADR-047/ADR-050 are now the target reference authority for the rows below. Existing runtime remains implementation evidence; reference reconciliation does not describe runtime gaps as solved.

| Intended architecture | Actual implementation evidence | Known deviation / consequence | Disposition | Target slice | Owner | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ShipmentRequest -> 0..N RequestCargoItems`; Cargo optional | Additive `RequestCargoItem` children support zero and ordered multiple items while legacy scalar Cargo remains compatible | No bounded implementation deviation; mandatory Cargo policy and operational handoff remain intentionally deferred | Preserve optional `0..N`, exact presentation, parent authorization, Cargo-less history, and no guessed backfill | Optional Multi-Cargo Request | Commercial/Product | IMPLEMENTED — QUALIFIED | PDR-019; FDD-001-033; migration `20260924_request_cargo_items`; `cargo-multi-item-build-20260920.md` |
| Operational Shipment owns one fixed responsible Expert | Both Direct and accepted-Quote creation persist a validated owner; accepted-Quote ownership comes from the exact Quote issuer; owner mutation is blocked in the application and database; Shipment/Document/Control Tower access ignores later Request reassignment | No bounded implementation deviation; ambiguous Production history remains a deployment-time fail-closed migration risk, not a Demo claim | Preserve ADR-047, immutable Shipment-owned authority, and no transfer/reassignment workflow | Responsible Expert ownership implementation gate | Product/Architecture/Security | IMPLEMENTED — QUALIFIED | ADR-047; ADR-042/043 scoped supersession; implementation commit `462d82d`; migration `20260926_fixed_shipment_responsible_expert`; `fixed-shipment-owner-closure-20260921.md` |
| User dates render `Gregorian (Jalali)` from one fact | Shared presentation renders representative Request, Quote, Shipment, Documents, Tracking, and Control Tower facts without duplicate persistence | No bounded implementation deviation; explicitly out-of-scope surfaces remain governed by the adoption ledger | Preserve Local Date versus Instant, timezone, ordering/filtering, and occurred-at versus recorded-at semantics | Dual Calendar | Product/Time Architecture | IMPLEMENTED — QUALIFIED | ADR-016 extension; TIME-BIZ-013; PDR-019; `dual-calendar-build-20260920.md` |
| Request supports scalar `حمل ترکیبی`; actual Route Legs remain separate | The canonical scalar is available through normal Request create/reopen and Expert presentation; Route Legs remain independent operational facts | No bounded implementation deviation; Customer still does not author an ordered route | Preserve idempotent catalog behavior, historical scalar values, and no inference in either direction | Combined Transport | Commercial/Product/Data | IMPLEMENTED — QUALIFIED | PDR-019; PDR-017 extension; FDD-001-034; `combined-transport-intent-build-20260921.md` |
| Customer can accept, request discussion + short message, or reject one official Quote | `ExpertQuote` now records accepted/discussion/declined response, bounded discussion message, actor/time, opaque customer response command, and bounded official Quote history; the existing expert issuance flow creates revised Quotes | No implementation deviation remains in the bounded slice; bargaining, counter-offers, and Notification activation remain intentionally excluded | Implemented and qualified; preserve the established tracking-capability Customer workflow and keep negotiation/Notifications out of scope | Quote Communication | Pricing/Commercial | IMPLEMENTED — QUALIFIED | PDR-019; FDD-001-035; `simple-quote-communication-v1.md`; migration `20260925_quote_communication`; build evidence |
| Owning Transport Expert alone manages multi-file append/targeted replace/history/known-failed retry; System preserves history | Parent-derived authorization, multi-file append, targeted replacement, immutable history, historical download, known-failure retry, and Admin read-only oversight are implemented; fixed Shipment ownership remains authoritative after Request reassignment | No bounded implementation deviation; generalized Customer visibility, unknown-outcome exactly-once recovery, retention/purge, and DMS expansion remain outside scope | Preserve PDR-020/ADR-050/ADR-047 authority, separately governed reads, and fail-closed non-owner mutation | Documents | Product/Document/Security | IMPLEMENTED — QUALIFIED | PDR-020; ADR-050; ADR-030/047; `documents-multi-file-build-20260920.md`; `fixed-shipment-owner-closure-20260921.md` |
| Control Tower works beyond launch volume without a business cap | Authorized population is filtered before server-side search, attention, aggregates, deterministic ordering, and bounded signed-cursor windowing; PostgreSQL qualification covers 500 active Shipments | Former 100-Shipment safety ceiling is removed; 500 is qualification evidence, not an unbounded Production SLA | Preserve complete global KPI, query-time consistency, bounded hydration, detail drilldown, and fail-closed invariant behavior | Control Tower scaling | Operations/Product | IMPLEMENTED — QUALIFIED | ADR-051; PDR-019 §11; `control-tower-scalability-build-20260921.md`; fixed-owner affected requalification |
| Notifications stay dormant until explicit activation policy | C1/C2 foundation/lifecycle exists with no producer/provider/API/UI activation | No deviation while dormant; risk is accidental scope expansion | Preserve dormant state | Notification activation | Product/Operations/Security | ACCEPTED DEFERRED | C1/C2 evidence; PDR-019 §7 |
| Public Request tracking requires an opaque non-enumerable capability and minimized public projection | Runtime rejects numeric/UUID/legacy/malformed authority, issues only cryptographically random `SR2-` capabilities, derives ownership server-side, and emits the fixed allowlist | No P0 identity/authorization deviation remains; rate limiting, rotation/revocation, hashed-at-rest storage, and infrastructure access-log redaction remain classified hardening | Preserve ADR-052 and the security regression/browser/PostgreSQL gates | MT-3 public tracking security closure | Product/Architecture/Security | IMPLEMENTED — QUALIFIED | ADR-052; MT-0 contract; MT-3 plan; MT-3 closure evidence |

All rows originated with `REFERENCE_IMPACT=UPDATE_REQUIRED`. Historical decision records remain preserved; this living register now reports the qualified Golden-controlled implementation state. Optional Multi-Cargo, Dual Calendar, Combined Transport, Quote Communication, Documents, Control Tower scalability, MT-3, and fixed responsible-Expert ownership are `IMPLEMENTED — QUALIFIED`. Notification activation remains `ACCEPTED DEFERRED`; no Production or deployment claim is made.

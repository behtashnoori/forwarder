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
| `ShipmentRequest -> 0..N RequestCargoItems`; Cargo optional | Request has nullable scalar Cargo fields and no RequestCargoItem collection | Multi-Cargo structure absent; submission must remain unblocked by absent Cargo | Correct in bounded Build; preserve Cargo-less history; no guessed backfill | Optional Multi-Cargo Request | Commercial/Product | OPEN | PDR-019; FDD-001-033; Post-D2 amendment v2 |
| Operational Shipment owns one fixed responsible Expert | Direct Shipment has `primary_responsible_expert_id`; accepted-Quote Shipment derives access from current Request assignee; historical reassignment behavior exists | Request reassignment can change Shipment access, contrary to fixed owner target | Supersede via ADR-047; converge both creation paths; no transfer workflow | Responsible Expert ownership implementation gate | Product/Architecture/Security | IMPLEMENTED — QUALIFIED | ADR-047; ADR-042/043 scoped supersession; preserved pre-closure service/model evidence; implementation commit `462d82d`; `fixed-shipment-owner-closure-20260921.md` |
| User dates render `Gregorian (Jalali)` from one fact | Current surfaces use existing mixed date presentation without a complete dual-calendar adoption ledger | Approved presentation is not consistently product-integrated | Correct through shared presentation slice only | Dual Calendar | Product/Time Architecture | OPEN | ADR-016 extension; TIME-BIZ-013; PDR-019 |
| Request supports scalar `حمل ترکیبی`; actual Route Legs remain separate | Current Request transport catalog lacks the combined choice; actual ordered Route Legs already exist | Customer cannot express combined intent; conflation risk remains | Idempotent catalog/intake/presentation reconciliation; no ordered JSON | Combined Transport | Commercial/Product/Data | OPEN | PDR-019; PDR-017 extension; FDD-001-034 |
| Customer can accept, request discussion + short message, or reject one official Quote | `ExpertQuote` now records accepted/discussion/declined response, bounded discussion message, actor/time, opaque customer response command, and bounded official Quote history; the existing expert issuance flow creates revised Quotes | No implementation deviation remains in the bounded slice; bargaining, counter-offers, and Notification activation remain intentionally excluded | Implemented and qualified; preserve the established tracking-capability Customer workflow and keep negotiation/Notifications out of scope | Quote Communication | Pricing/Commercial | IMPLEMENTED — QUALIFIED | PDR-019; FDD-001-035; `simple-quote-communication-v1.md`; migration `20260925_quote_communication`; build evidence |
| Owning Transport Expert alone manages multi-file append/targeted replace/history/known-failed retry; System preserves history | Request/Shipment document foundations support file/version behavior, but runtime may allow Organization Admin management, accepted-Quote Shipment access still follows current Request assignee, readiness selects one effective active association, and no target design has reconciled every path | Actor reference is resolved, but current authorization/orchestration/readiness may violate the target; schema sufficiency is not yet proven | Design against PDR-020/ADR-050 and ADR-047; preserve separately governed reads; deny Customer/Admin/other-Expert writes; prove current-set readiness and targeted lineage | Documents | Product/Document/Security | REFERENCE RESOLVED — IMPLEMENTATION OPEN | PDR-020; ADR-050; ADR-030/047; current route/service/model evidence; FWD-07 donor classification |
| Control Tower works beyond launch volume without a business cap | D1/D2 fail closed above 100 authorized active Shipments | Product becomes unavailable above the safety ceiling | Prove launch headroom or replace with server-side search/windowing before RC | Control Tower scaling | Operations/Product | OPEN — PRE-RELEASE | D1/D2 evidence; PDR-019 §7 |
| Notifications stay dormant until explicit activation policy | C1/C2 foundation/lifecycle exists with no producer/provider/API/UI activation | No deviation while dormant; risk is accidental scope expansion | Preserve dormant state | Notification activation | Product/Operations/Security | ACCEPTED DEFERRED | C1/C2 evidence; PDR-019 §7 |
| Public Request tracking requires an opaque non-enumerable capability and minimized public projection | Runtime rejects numeric/UUID/legacy/malformed authority, issues only cryptographically random `SR2-` capabilities, derives ownership server-side, and emits the fixed allowlist | No P0 identity/authorization deviation remains; rate limiting, rotation/revocation, hashed-at-rest storage, and infrastructure access-log redaction remain classified hardening | Preserve ADR-052 and the security regression/browser/PostgreSQL gates | MT-3 public tracking security closure | Product/Architecture/Security | IMPLEMENTED — QUALIFIED | ADR-052; MT-0 contract; MT-3 plan; MT-3 closure evidence |

All rows have `REFERENCE_IMPACT=UPDATE_REQUIRED`. Their project reference updates are `CLOSED_FOR_REFERENCE_PHASE`; Documents is specifically `CLOSED_FOR_DOCUMENTS_DESIGN`. Runtime/product status remains as shown above. The MT-3 and fixed responsible-Expert rows are the explicit exceptions whose implementation and qualification closures are recorded by their evidence artifacts; other reference closures are not implementation PASSes.

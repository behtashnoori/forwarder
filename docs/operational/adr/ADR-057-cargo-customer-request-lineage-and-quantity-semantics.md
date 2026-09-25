# ADR-057: Cargo Customer/Request Lineage and Quantity Semantics

- **Status:** ACCEPTED — bounded P3-02 architecture and implementation authority
- **Date:** 2026-09-25
- **Owners:** Product Owner for authorized behavior; Operational Shipment/Cargo domain for SOR; Security for tenant and owning-Expert enforcement; Data for additive migration
- **Affected domain:** Operational Shipment Cargo, Request lineage, governed references
- **Implementation state:** P3-02 qualified on Product SHA `b38a4cb952f7ad74079399991511f35f63e4fd82`; canonical integration is the next gate; Release Ready, deployment, and Production use are not established by this ADR
- **Mission authority:** [P3-02 Cargo Lineage Mission Contract](../../product/phase3/P3-02-CARGO-LINEAGE-MISSION-CONTRACT-FA.md)

## Context

The current `ShipmentCargoItem` is the operational Cargo record and stores an optional Customer plus one positive `quantity` and governed UOM snapshot. The Shipment itself can retain one commercial Request/Quote source, while `RequestCargoItem` separately preserves customer-supplied Cargo facts. That shape cannot represent multiple Customer/Request lineages inside one Shipment or distinguish what was requested, planned, and actually moved.

The approved P3-02 Product outcome requires per-Cargo Customer attribution, optional Request and Request-Cargo lineage, direct Cargo without a fake Request, distinct requested/planned/actual quantities, progressive details, governed Packaging, honest legacy unknowns, and history for meaningful corrections. It does not authorize a Shipment-customer membership aggregate, Customer Portal entitlement, lifecycle changes, UOM conversion, an HS mandatory rule, or P3-03 route behavior.

## Decision

### 1. Extend the existing Cargo SOR

`ShipmentCargoItem` remains the single operational Cargo SOR. Add nullable links to `ShipmentRequest` and `RequestCargoItem`; nullable `requested_quantity`, `planned_quantity`, and `actual_quantity`; nullable governed Packaging reference and label snapshots; and optional progressive weight, volume, HS/description, and destination details. No Shipment-level customer membership table or second Cargo aggregate is introduced.

Every newly created P3-02 Cargo has an explicitly resolved active CRM `Customer` in the Shipment tenant. A direct Cargo leaves both source links and requested quantity null. Request lineage never changes Shipment ownership, Request assignment, portal access, or the Request/Shipment separation.

The database and service require any Request-Cargo link to belong to the selected Request. The server requires the Request and Customer to be in the Shipment tenant and requires the actor to be the persisted owning Transport Expert. If the source Request has an explicit CRM Customer, it must equal the Cargo Customer. No name, email, mobile, Request contact, portal account, or other heuristic may infer the Customer.

### 2. Quantity meanings remain separate

The three semantic quantities share one governed Cargo UOM and remain independent nullable facts. A non-null value must be positive. `requested_quantity` requires a real source Request. When the selected Request Cargo already contains quantity/UOM, the requested snapshot is copied only from that exact fact and only when UOM matches; conflicting input is rejected and no conversion occurs.

New P3-02 commands use `planned_quantity` explicitly. For bounded compatibility, the pre-existing `quantity` column continues to feed older allocation/read paths and mirrors an explicitly supplied planned quantity. Existing rows and legacy commands that contain only `quantity` are not backfilled or relabeled: their new three semantic fields remain null and the API reports the legacy meaning as unknown. Actual quantity never overwrites planned or requested quantity.

### 3. Governed reference and progressive-detail boundary

Cargo Type, UOM, and Packaging selections require both an active central definition and active P3-01 organization activation. Historical rows retain stored snapshots and remain readable after deactivation. Weight and volume are optional positive values paired with an active same-tenant governed UOM of dimension `WEIGHT` or `VOLUME`; no ratio or conversion is implemented.

HS Code, weight, volume, packaging, destination detail, and actual quantity may be incomplete. Missing HS is returned and displayed as incomplete but never blocks Cargo creation or save. `DN05` remains open. No free-text Packaging base type is accepted.

### 4. Corrections, versions, and history

Cargo commands require the current optimistic version. Every creation and meaningful correction appends an `OperationalAudit` record with the Cargo identity, Shipment identity, changed field names, and bounded before/after values. The Cargo version advances once per successful update. This reuses the current audit foundation rather than introducing event sourcing.

Reference label snapshots preserve what was selected at the time of the current version; prior values remain in audit history. Catalog edits and activation changes never silently regenerate Cargo fields. Corrections are explicit commands by the owning Expert.

### 5. API and UX boundary

The authenticated Shipment Cargo API returns source lineage, Customer, all three quantity meanings, governed units/Packaging, progressive details, incomplete-field indicators, version, and timestamps. A Shipment-scoped options endpoint returns only Customers, Requests/Request Cargo visible to the owning Expert, and active organization definitions. Foreign identifiers fail without partial mutation.

The approved Forwarder UI uses simple Persian labels for کالا، مشتری، درخواست منبع، مقدار درخواستی، مقدار برنامه‌ریزی‌شده، مقدار واقعی، واحد، نوع بسته‌بندی and مشخصات ناقص. It distinguishes direct Cargo from Request-sourced Cargo, shows unknown honestly, keeps the three values adjacent, and supports later completion. Existing execution/allocation/tracking surfaces are preserved and are not extended as P3-04/P3-05 work.

## Migration and rollback

The migration is additive from `20260930_phase3_reference_catalog`. It adds nullable columns, foreign keys, positive/pair/lineage checks, and query indexes. It performs no Customer, Request, quantity-semantic, Packaging, HS, weight, volume, or destination backfill. Proven parent identity remains derivable through the existing Shipment relationship; no historical meaning is inferred.

Downgrade may remove the additive structure only when no row contains P3-02 semantic data. Once such evidence exists, downgrade refuses and the safe rollback is application rollback with the expanded schema retained until separately authorized reconciliation.

## Authorization and privacy

Read behavior keeps the existing authorized Shipment scope. Create/update additionally require an active Expert identity, one active membership, the existing mutation capability, same tenant, and exact match to `OperationalShipment.primary_responsible_expert_id`. Organization Admin oversight and Project read access do not grant Cargo edit authority. Customer accounts receive no new endpoint or projection.

## Reconciliation

- ADR-002/034 Request-versus-Shipment separation and optional commercial lineage are preserved and extended per Cargo.
- ADR-021/028/056 govern reference ownership and organization activation; P3-02 consumes Packaging without adding definition/promotion behavior.
- ADR-022 remains the Cargo SOR/snapshot foundation and is extended with explicit versioned corrections whose previous values are audit-preserved.
- ADR-042/043/047 remain authoritative for owning-Expert mutation and fixed Shipment ownership.
- ADR-046 allocation/execution remains unchanged; P3-02 planned quantity only supplies an explicit Cargo fact and does not implement allocation lifecycle.

## Required validation

Qualification must prove multi-Customer/multi-Request persistence, direct Cargo without fake lineage, requested/planned/actual separation, progressive completion, active-reference enforcement, UOM mismatch denial, owning-Expert and tenant negatives, legacy unknown rendering, audit/version conflict, additive migration round-trip and guard, PostgreSQL 18, browser normal navigation/reopen, and affected regression. Evidence binds to the exact Product SHA.

## Open decisions and exclusions

`DN01=OPEN`, `DN05=OPEN`, `DN08=PARTIAL_DECISION_NEEDED`, and `DN10=OPEN`. Out of scope are new lifecycle states, HS mandate, local reference creation/promotion, Customer projection/entitlement, routes, execution, allocation redesign, documents, events, ETA, delivery, closure, owner transfer, Production, deployment, and release.

## Reference and Product status

```text
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=UPDATE_REQUIRED_UNTIL_RECONCILED
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
SLICE_JOURNEYS=NOT_RUN
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
RELEASE_READY=NO
```

## Supersession

- **Supersedes:** none
- **Complements:** ADR-002, ADR-021, ADR-022, ADR-028, ADR-034, ADR-042, ADR-043, ADR-046, ADR-047, ADR-056
- **Superseded by:** none

# P3-05 — Cargo allocation, split, transfer and trace

**Status:** authorized bounded implementation, 2026-09-25. **Baseline:** LPAF v2.7. **Rigor:** C (tenant boundaries, transactional transfer and history). **Capability route:** Astra, because the work joins Product authority, route revisions, shared execution, concurrency, migration and browser evidence. **Owner:** Forwarder Product Owner for behavior; delivery owns internal design and verification.

## Product Authority Record

| Field | Decision |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | The Product Owner's P3-05/P3-06 sequential mission attached to this task explicitly authorizes stage-scoped `PLANNED` and `ACTUAL` allocation; incomplete and excess plans and actual reports with non-blocking warnings; plan revisions; Cargo actual corrections; split; explicit atomic transfer and end-to-end trace. No new allocation lifecycle. |
| `DELEGATED_TECHNICAL_CHOICES` | Additive relational schema on existing `ExecutionUnitCargoAllocation`, immutable revisions and transfer record, deterministic locks, version and idempotency handling, API and UI placement within approved Phase 3 UX V2.1. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | P3-01 catalog, P3-02 Cargo/Request/Customer lineage and quantities, P3-03 route, P3-04 executions, current Customer Account, Request/Quote, Public Tracking, Workspace, Control Tower, Exceptions/Actions, documents, and existing tenant-shared execution remain governed by their current contracts. No P3-06 until P3-05 is qualified and integrated; no P3-07+, Production, deployment or release. |
| `DECISIONS_NEEDED` | None for the bounded allocation behavior. DN01 remains open for later Shipment/closure meaning; a newly needed user-visible allocation status would require a new Product Owner decision and stop affected work. |
| `APPROVING_OWNER_OR_AUTHORITY` | Forwarder Product Owner, through the explicit user mission for P3-05 followed by P3-06. |
| `APPROVAL_REFERENCE` | Attached mission `Pasted text.txt`, sections 0–36; the newer non-blocking quantity decision supersedes only the earlier P3-05 planning cap. |

## Current evidence and target

`ShipmentCargoItem` owns Cargo quantities and `OperationalAudit` records Cargo updates (`backend/services/cargo_service.py`). `RoutePlan`/`RouteLeg` own stage structure; `RouteStageExecution` associates a tenant-owned `ExecutionUnit` with an exact plan and leg (`backend/operational_models.py`, ADR-058/059). `ExecutionUnitCargoAllocation` is the current allocation SOR, but `shared_transport_service.allocate` caps the sum by `cargo.quantity`, overwrites current quantity, and `release` hard-deletes. `ShipmentCargoItems.tsx` also blocks excess allocations. These observed behaviors need the specifically approved P3-05 change. Legacy allocations carry no provable stage, dimension, transfer or revision history; migration must leave those facts unknown.

The owning Transport Expert records the plan, actual operation, correction or transfer. Cargo quantity stays at Cargo scope; each stage has its own distribution. A read projection shows the original/current plan, actual, differences, history, previous and next stage, and means/equipment from P3-04. Quantity mismatches stay warnings and never create Exception, Attention, SLA or Shipment status. The target journey begins in the Expert's Shipment workspace, persists across reopen, and fails closed for a non-owner, wrong tenant or guessed parent.

## Scope, chain and verification

SOR chain: `ShipmentCargoItem → RoutePlan/RouteLeg → RouteStageExecution → ExecutionUnit → ExecutionUnitCargoAllocation → immutable revision/transfer`. The route and execution remain their respective SORs. No second Cargo or tracking SOR is introduced. Existing `shared_transport_service`, row locks, Decimal, Cargo audit and existing API adapters are extended or adapted. `UnifiedShipmentHistory` may compose reads only.

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`; affected journeys: `FWD-J04,FWD-J08,FWD-J09,FWD-IPJ-04` in Product Acceptance Journey Pack v1.1. Required evidence is focused positive/negative API checks, PostgreSQL 18 migration and rollback, atomicity/concurrency/idempotency, ordinary Chrome Expert journey with reopen and denied paths, full backend/frontend regression, static checks, reference reconciliation and exact Product SHA. Integrated global journeys and Human Product Walkthrough remain separate future gates; they are not implicitly PASS. `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`, `RELEASE_READY=NO`.

Framework reference impact: `NONE`, since this applies LPAF v2.7 without amending it. Project architecture/reference impact: `UPDATE_REQUIRED` for an allocation ADR, OpenAPI, domain/tenant inventory and Phase 3 status; reconcile them before integration.

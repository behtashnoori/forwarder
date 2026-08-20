# Forwarder End-to-End Operational Readiness

- Date: 2026-08-20
- Reviewed commit: `aefb7271d8d38affe90fbf1113a4558020608897`
- Classification: **FORWARDER END-TO-END OPERATIONAL READY WITH CONTROLLED GAPS**

## 1. Scenario reviewed

The review followed an automotive `Gearbox / گیربکس` request from Tehran into one forwarding project and two realistic shipments: an air movement with AWB and a road continuation with CMR. Cargo quantities/UOMs, execution events, latest known location projections, request-owned document files, independent shipment readiness, and external references were traced without aggregating unlike UOMs or inventing execution-unit cargo allocation.

The expert can now answer which shipments contain gearbox, the per-shipment quantity/UOM and status, enter each shipment, inspect project execution units, review independent document readiness, return to request uploads when a file is missing, and manage applicable B/L/AWB/CMR references. A single authoritative “current location” across both tracking architectures remains intentionally unsupported.

## 2. Operational chain

`ShipmentRequest → Customer context → optional Project → OperationalShipment → ShipmentCargoItem → ExecutionUnit / OperationalEvent → LogisticsPoint or explicit snapshot → shipment document readiness → external operational references → operational status/work`.

Commercial request, operational shipment, request-owned file, shipment readiness, catalog cargo, shipment cargo snapshot, and owner-specific external references remain separate authorities.

## 3. What works today

- Tenant-fenced request intake/detail, quote acceptance, bounded customer linkage, and shipment creation.
- Opaque operational-shipment navigation and a request-context list of its shipments.
- Catalog-to-shipment gearbox traceability with shipment count, per-line quantity/UOM, status, canonical event/checkpoint location projection, latest-event time, and direct shipment navigation.
- Independent execution units/events and project navigation without implying cargo allocation.
- LogisticsPoint selection for legacy expert tracking with immutable snapshots and understandable free-text fallback.
- Independently materialized shipment document requirements, exact request-file versions, replacement/removal, assessment, readiness, and shared request-file reuse where eligible.
- Internal ADR-039 workflow for certified B/L, AWB and CMR values: view, create, supersede, cancel, preserved history, and optional exact request-file evidence.
- Existing work queue, milestones, route plans/exceptions, cargo, execution, documents, economics and audit sections provide substantial shipment context without requiring a new dashboard.

## 4. What was fixed

| Finding | Before | Remediation | Authority |
| --- | --- | --- | --- |
| E2E-001 | Request detail could create but not find existing shipments | Added filtered tenant-fenced shipment list with opaque links | ADR-002/017/034 |
| E2E-002 | External references were backend-only | Added shipment V1 reference/history/evidence workflow | ADR-039 |
| E2E-003 | Cargo usage results were not enterable | Added opaque shipment navigation | ADR-022 |
| E2E-004 | Shipment printed project ID without execution navigation | Linked existing project execution-unit workspace | ADR-017/018 |
| E2E-005 | Empty eligible-file state was a text-only dead end | Linked to the current source request document context | ADR-030; no ownership change |

No migration or backend authority change was made.

## 5. Remaining P0

None.

## 6. Remaining P1

1. **E2E-007:** Legacy request-unit tracking and canonical execution events can both describe location/status. A single shipment-level source-precedence/provenance projection requires a new architecture decision; this review did not silently choose an authority.

## 7. Deferred P2/P3

- E2E-008 (P2): raw English filter names, mixed untranslated operational phrases/status codes, and inconsistent RTL/LTR treatment need a bounded terminology pass.
- P3: none recorded.

## 8. Legacy/canonical overlap

Legacy multi-unit tracking remains active under request detail and can be written independently from canonical Project → OperationalShipment → ExecutionUnit → OperationalEvent. Both are visible to experts and can overlap conceptually. This is an operational consistency risk, not a tenant breach. No convergence or authority migration occurred.

## 9. CRM status

**ON HOLD — NO EXPANSION.** Only the existing bounded request-customer context was reviewed. No CRM workspace, search, CRUD, dashboard or mutation expansion was implemented.

## 10. Deferred Iranian reference types

`COTAGE_NUMBER`, `WAREHOUSE_RECEIPT_ID`, `REGISTRATION_ORDER_NUMBER`, and `BARFARABARAN_REFERENCE` are **DEFERRED / NOT IMPLEMENTED**. The UI exposes only the three certified ADR-039 V1 codes.

## 11. Architecture decisions required

One new decision is required: define current-location/status source precedence, provenance, disagreement handling and timestamps across legacy tracking and canonical execution events. ADR-038 already authorizes opaque ShipmentRequest identity; its remaining work is implementation planning rather than a new ADR.

## 12. Recommended next three controlled Goals

1. Decide and certify the legacy/canonical tracking location/status projection, including explicit provenance and conflict behavior; do not migrate write authority in that goal.
2. Perform a bounded expert terminology/RTL first-use pass after identities and source labels are stable.
3. Tenant-certify and separately plan remaining numeric admin/CRM compatibility routes before any contraction.

## Certification evidence

- Focused frontend: 27 passed.
- Focused backend/adversarial: 35 passed.
- Full frontend: 143 passed.
- Full backend: 794 passed, 82 skipped, 1 expected failure.
- Production, production database, deployment, push and release access: none.

The detailed evidence, root causes, implementation gate and test strategies are in `docs/product/FORWARDER-END-TO-END-OPERATIONAL-GAP-REGISTER.md`.

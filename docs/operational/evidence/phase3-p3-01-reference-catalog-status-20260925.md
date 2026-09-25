# Phase 3 P3-01 — Reference Catalog Qualification Evidence

- **Record date:** 2026-09-25
- **Governing baseline:** LPAF v2.7 — ACTIVE / FROZEN / CANONICAL
- **Rigor / route:** Level B / Sol-Astra
- **Qualified slice:** P3-01 only — governed reference catalog and organization activation
- **Mission:** [P3-01 Reference Catalog Mission Contract](../../product/phase3/P3-01-REFERENCE-CATALOG-MISSION-CONTRACT-FA.md)
- **Architecture:** [ADR-056](../adr/ADR-056-governed-reference-catalog-organization-activation.md)
- **Product baseline:** `integration/golden-controlled@5ebb8c3fb54b0a18898fe04db6ec4135bf41ef7e`
- **Candidate branch:** `codex/phase3-p3-01-reference-catalog`
- **Phase 3 Product SHA:** `39c1084377e18c38dd337a79bed0d0d11b033e72`
- **Evidence SHA:** this document's evidence-only descendant, bound by the final delivery record

This record qualifies only P3-01. It does not claim full Phase 3 completion, global Product validation, Human Product Walkthrough, release readiness, deployment, or Production access.

## Qualified implementation boundary

P3-01 adds explicit central `PackagingType`, `TransportMeansType`, and `TransportEquipmentType` definitions and tenant-owned activation records for Cargo Type, UOM, Packaging, Transport Means, and Transport Equipment. It reuses the existing Cargo Type/UOM foundations; it does not introduce a parallel master-data system, polymorphic/EAV storage, or copied tenant definitions.

Platform Admin manages central definitions. Organization Admin, under server-derived tenant scope, can list and activate/deactivate approved central definitions for its organization. Existing Expert Cargo consumers can select only Cargo Type/UOM values in the intersection of active central definitions and active organization activations. Packaging, Transport Means, and Transport Equipment are foundation-only in P3-01 and have no new operational consumer.

No standard rows or organization activations are seeded or backfilled. Organization-specific definition creation/promotion remains absent and is still governed by open decision `DN08`. Experts cannot create a base definition or bypass selection with free text. An empty organization catalog is valid; a dependent Cargo action is blocked with the governed administrator guidance.

Deactivation prevents new selection but does not rewrite or remove historical Cargo snapshots. Existing `CargoCatalogItem`, Shipment Cargo, Document policy, Global Logistics, public Request Cargo options, legacy `TransportMethod`, Shared Transport, and Tracking meanings remain preserved. During qualification, the existing canonical allocation serializer call was corrected to use the owning Cargo service; this restores the established contract and does not add Product behavior.

## Product Authority and PDA-07 result

| Material observable difference | Final classification | Evidence result |
| --- | --- | --- |
| Organization Admin activates/deactivates approved central values for new tenant use | `AUTHORIZED` | Verified by API, authorization, audit, browser persistence, and two-tenant evidence |
| Expert Cargo Type/UOM choices require active central state and active tenant activation | `AUTHORIZED` | Verified by service/API tests and normal-navigation browser journey |
| Deactivation blocks new selection while historical snapshots/read remain | `AUTHORIZED` | Verified by backend and browser inactive-history checks |
| Existing Cargo ownership, Shipment Cargo snapshots, Document policy, and Global Logistics behavior | `PRESERVED` | Full regressions and bounded operational journey passed |
| Public Request Cargo options and legacy `TransportMethod` | `PRESERVED` | Compatibility tests remained green; no route/meaning replacement |
| Organization-specific definition creation/promotion | `PRESERVED_AS_ABSENT` | No route, command, or UI exists; `DN08` remains open |

No material difference was classified `UNKNOWN` or `VIOLATION` in this slice.

## Migration and PostgreSQL 18 evidence

- Migration target: `20260930_phase3_reference_catalog`.
- Parent: `20260929_operational_monitoring_reliability`.
- Alembic head count: `1`.
- PostgreSQL server: `18.0`.
- Clean upgrade from the parent, empty-table/no-seed verification, empty downgrade/re-upgrade, and populated downgrade refusal: `PASS`.
- Concurrent first activation using two real PostgreSQL threads produced one success and one uniqueness conflict, with no duplicate activation: `PASS`.
- Stale version conflict, inactive central definition rejection, append-only audit, and cleanup: `PASS`.
- Exact PostgreSQL qualification: `1 passed, 15 warnings in 12.95s`.

The migration is additive and requires no Product data backfill. A populated downgrade intentionally refuses destructive loss.

## Authorization and tenant isolation evidence

- Organization Admin-only mutation, server-derived organization scope, and Platform Admin/Expert mutation denial: `PASS`.
- Inactive or revoked organization membership denial: `PASS`.
- Tenant A activation remained invisible and inactive in Tenant B: `PASS` in API and browser evidence.
- Foreign valid identifiers, direct/guessed routes, and body/query tenant override attempts did not cross the tenant boundary or disclose foreign existence: `PASS`.
- Activation uniqueness, optimistic version conflict, central active-state enforcement, and audit ownership: `PASS`.

## Automated evidence on the frozen Product SHA

| Evidence unit | Result |
| --- | --- |
| Focused backend P3-01 tests | `4 passed` |
| Exact PostgreSQL 18 qualification | `1 passed, 15 warnings` |
| Full backend regression | `1377 passed, 108 skipped, 0 failed` |
| Focused frontend P3-01 tests | `5 files, 22 tests passed` |
| Full frontend regression | `81 files, 394 tests passed` |
| TypeScript check | `PASS` |
| Lint | `PASS` — 0 errors; 13 pre-existing warnings |
| Production build | `PASS` — advisory chunk-size/browser-data warnings only |
| Architecture governance check | `PASS` |
| Repository structure check | `PASS` |
| OpenAPI YAML and local-reference parse | `PASS` |
| Diff whitespace check | `PASS` |

Runtime identity: Python `3.13.9`, Node `v24.11.0`, npm `11.6.1`, PostgreSQL `18.0`, Chrome `154.0.8037.57`.

## Browser Product evidence

The dedicated P3-01 browser journey passed on the frozen Product SHA with runner cleanup passing. It covered Platform creation of all five reference families, role boundaries, Tenant A activation and persistence, Tenant B isolation, Expert normal navigation, governed allowed selection, retained history after deactivation, missing-definition guidance, absence of free-text bypass, and absence of unexpected page/API/console errors.

The existing integrated browser path `Catalog → operational Cargo → Shared Transport → Tracking` was also rerun on the same Product SHA and passed (`1 passed in 36.4s`), with runner cleanup passing.

| Evidence unit | Result |
| --- | --- |
| `P3-01-ADMIN` | `PASS` |
| `P3-01-EXPERT` | `PASS` |
| `P3-01-INACTIVE-HISTORY` | `PASS` |
| `P3-01-MISSING` | `PASS` |
| `P3-01-TENANT` | `PASS` |
| Automated P3-01 Product slice | `PASS` |
| `FWD-J06`, `FWD-J08`, `FWD-J09`, `FWD-IPJ-03`, `FWD-IPJ-04` P3-01 boundaries | `PASS` for this bounded slice only |
| Full affected integrated journeys | `NOT_CLAIMED` by P3-01 qualification |
| Human Product Walkthrough | `NOT_RUN` |

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`: the five named journeys consume or depend on the governed reference boundary. The P3-01 slice and its bounded integrated path are automated and green; this record does not silently convert the broader journey pack or Human gate to PASS.

## Reference reconciliation

LPAF v2.7, the Operational Shipment Product Contract, Product Acceptance Journey Pack, Phase 3 Implementation Plan, mission contract, ADR-021/022/028/036/041/056, architecture baseline, decision indexes, tenant ownership inventory, and OpenAPI were reconciled against the frozen Product SHA. Historical planning text remains historical. Current-state overlays and ownership/API references are aligned. No normative reference change is required.

```text
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
```

## Final status ledger

```text
LPAF_BASELINE=2.7
PHASE_3_IMPLEMENTATION_STARTED=YES
PHASE3_CURRENT_SLICE=P3-01
PHASE3_P3_01=PASS
REFERENCE_CATALOG_FOUNDATION=PASS
ORGANIZATION_REFERENCE_ACTIVATION=PASS
EXPERT_GOVERNED_SELECTION=PASS
INACTIVE_HISTORICAL_REFERENCE=PASS
TENANT_ISOLATION=PASS
HISTORY_PRESERVATION=PASS
FREE_TEXT_EXPERT_BASE_DEFINITION=NO
UNVERIFIED_STANDARD_SEED=NO
PARALLEL_MASTER_DATA_SYSTEM=NO
DN08_STATUS=PARTIAL_DECISION_NEEDED
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J06,FWD-J08,FWD-J09,FWD-IPJ-03,FWD-IPJ-04
BROWSER_PRODUCT_JOURNEY=PASS
FULL_BACKEND_REGRESSION=PASS
FULL_FRONTEND_REGRESSION=PASS
MIGRATION_REQUIRED=YES
ALEMBIC_HEAD=20260930_phase3_reference_catalog
ALEMBIC_HEAD_COUNT=1
MIGRATION_QUALIFICATION=PASS
PRODUCT_AUTHORITY_RECONCILIATION=PASS
PRODUCT_VALIDATION_EVIDENCE_FOR_THIS_SLICE=COMPLETE
PHASE3_PRODUCT_HEAD=39c1084377e18c38dd337a79bed0d0d11b033e72
PHASE3_EVIDENCE_HEAD=EVIDENCE_ONLY_DESCENDANT_REPORTED_IN_FINAL_HANDOFF
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
P3_02_STARTED=NO
P3_03_STARTED=NO
P3_04_STARTED=NO
AI_IMPLEMENTED=NO
GPS_IMPLEMENTED=NO
FINANCE_IMPLEMENTED=NO
CARRIER_PORTAL_IMPLEMENTED=NO
DRIVER_PORTAL_IMPLEMENTED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
CANONICAL_INTEGRATION=NOT_PERFORMED
CANONICAL_PUSH=NOT_PERFORMED
LOCAL_REMOTE_ALIGNMENT=PASS
WORKTREE_CLEAN=YES_AFTER_EVIDENCE_COMMIT
```

## Residual gates and exact next action

- `DN08` still requires a Product decision before organization-specific definitions or promotion can be introduced.
- Packaging, Transport Means, and Transport Equipment remain foundation-only until their authorized operational slices.
- Global Product validation remains `EVIDENCE_PENDING`; only an authorized human can complete the Human Product Walkthrough.
- Release readiness remains `NO`; no integration, push, deployment, release, or Production action was performed.

The exact next engineering step is a controlled review and integration decision for this P3-01 candidate. P3-02 must not start under this mission.

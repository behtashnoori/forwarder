# Forwarder Domain Roadmap Matrix

- **Status:** Accepted supporting governance artifact
- **Architecture baseline:** DA-1.0
- **Date:** 2026-08-02
- **Roadmap authority:** [PDR-015](PDR-015-forwarder-domain-development-roadmap.md)
- **Network authority:** [PDR-016](PDR-016-logistics-network-foundation.md) and [ADR-025](adr/ADR-025-logistics-network-aggregate-boundaries.md)
- **Production evidence:** [Production Deployment State 1.6.1](production-deployment-state-1.6.1.md) verifies application 1.6.1, IIS release `release-v1.6.1-20260802`, and database revision `20260809_cargo_catalog_items`.

This matrix is a navigation and sequencing aid. “Deployed” is used only where explicit operational evidence supports it. Accepted Logistics Network governance authorized the bounded Slice; implementation is complete in source but is not Production deployment evidence.

| Capability / Slice | Roadmap Layer | Current State | Governance Artifact | Implementation State | Dependency | Next Decision | Target Release |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Production 1.6.1 | Cross-cutting release | Deployed | Production Deployment State 1.6.1 | Deployed | Immutable 1.6.1 bundle; DB head 20260809 | Resolve visible UI version display separately | 1.6.1 |
| DA-1.0 Architecture Knowledge Baseline | Cross-cutting governance | Proposed documentation baseline | PP-001; AP-001; FDD-001; FDM-001; Decision Index; Handbook | Documentation only | Existing governance sources | Product/Architecture review of PP/AP | DA-1.0 |
| Command Center | Experience across Layers 3–4 | Deployed in current release lineage | PDR-012; release notes 1.3.0 | Implemented and Deployed | Existing Project/request routes | None for delivered bounded scope | 1.3.0 |
| Scroll Restoration | Cross-cutting UX | Deployed in current release lineage | Scroll restoration record; release notes 1.3.1 | Implemented and Deployed | Command Center/router | None for delivered patch | 1.3.1 |
| Project Foundation | Layer 3 | Foundation implemented | ADR-017; EPIC-001 | Implemented and Deployed | Organization and request/quote lineage | Extend configuration only through accepted Slice | Existing foundation |
| ExecutionUnit | Layer 4 | Foundation implemented | ADR-018; EPIC-001 | Implemented and Deployed | Project, OperationalShipment | Later cargo link remains deferred under PDR-013-D08/D09 and ADR-023 | Existing foundation |
| OperationalEvent | Layer 5 | Foundation implemented | ADR-019 | Implemented and Deployed in bounded model | Project/shipment/unit identity | Standardize remaining event coverage separately | Existing foundation |
| Master Data Foundation | Layers 1–2 | Foundation implemented | PDR-013 D01/D04/D12; ADR-021 | Implemented and Deployed | Administration/security | Govern future dictionaries independently | 1.4.0 |
| Initial Reference Data | Layer 1 | Catalog implemented; Production Seed not executed | PDR-014; catalog review; Production 1.6.1 record | Structure Deployed; Seed Not Executed | Master Data Foundation | New values/seed execution require separate approval | 1.5.0 |
| Cargo Catalog | Layer 2 | Implemented and Deployed | PDR-013 D05/D06/internal D11; ADR-022; 1.6.0 closure | Implemented and Deployed | Master Data Foundation | No global/customer catalog without new decision | 1.6.0; deployed in 1.6.1 lineage |
| ShipmentCargoItem | Layers 4–5 | Implemented and Deployed | PDR-013 D07; ADR-022; 1.6.0 closure | Implemented and Deployed | Cargo Catalog, OperationalShipment | Correction/supersession requires separate governance | 1.6.0; deployed in 1.6.1 lineage |
| Logistics Network | Layers 1–3 | Governance Accepted | PDR-015; PDR-016; ADR-025 | Implemented; not deployed | Bounded Slice contract and normal delivery gates | Release/deploy only under separate authority | 1.7.0 |
| 1.7.0 Logistics Network Slice Contract | Layers 1–3 | Accepted / Implemented | Release 1.7.0 Logistics Network Slice Contract | Implemented; not deployed | Normal release and deployment gates | Preserve bounded contract | 1.7.0 |
| LogisticsPointType | Layer 1 | Implemented | PDR-016 D01; ADR-025 | Implemented; catalog apply not executed | ADR-021 conventions; accepted catalog | Govern catalog lifecycle | 1.7.0 |
| LogisticsPoint | Layer 2 | Implemented | PDR-016 D02/D06–D09; ADR-025; ADR-026 | Implemented; not deployed; `region_name` deferred | LogisticsPointType; governed Country and optional Province/City; organization/security scope | Operate after separately authorized deployment; future region requires separate decision | 1.7.0 |
| ProjectLogisticsPoint | Layer 3 | Implemented | PDR-016 D03–D05; ADR-025 | Implemented; not deployed | Project, LogisticsPoint | Operate after separately authorized deployment | 1.7.0 |
| Cargo-to-ExecutionUnit Linking / Allocation | Layer 4 | Deferred | PDR-013 D08/D09; ADR-023 Proposed | Not Started | ShipmentCargoItem, ExecutionUnit, concurrency policy | Accept required allocation decisions if maturity justifies them | Deferred |
| Internal Cargo Search | Layer 6 | Proposed separately | PDR-013 internal D11 boundary; new Slice decision required | Not Started | Cargo snapshots, organization isolation | Define bounded internal scope and security/performance contract | Later MINOR |
| Customer Cargo Search | Layer 6 | Not Authorized | PDR-013 D10/customer D11; ADR-024 Proposed | Not Started | Customer visibility policy and threat/load evidence | Required PDR/ADR acceptance | Deferred |
| Operational Reporting | Layer 6 | Deferred | PDR-015 Priority 4; future metric PDR | Not Started as standardized reporting | Governed point/event/project facts | Define KPI ownership, formulas, security, and freshness | Deferred |
| Dashboards | Layer 6 | Deferred | PDR-015 | Not Started | Accepted operational reporting and data-quality evidence | Product/Data dashboard decision | Deferred |
| Optimization/AI | Layer 7 | Deferred | PDR-015; CAP-014; AI governance | Not Started for operational optimization | Mature facts, accepted policies, explainability, human authority | Capability-specific PDR/ADR and AI action policy | Deferred |

## Status rules

- `Implemented and Deployed` is supported by the Production 1.6.1 evidence record.
- `Authorized` means governance permits a bounded implementation Slice; it does not mean work started.
- `Deferred` means the capability remains absent/disabled pending maturity and governance.
- Current verified Production is application 1.6.1 on IIS release `release-v1.6.1-20260802` with database head `20260809_cargo_catalog_items`; Reference Data Seed was not executed and UI version display remains unresolved.

## Release 1.8.0 bounded authorization

| Capability | Layer | Governance state | Authority | Implementation state | Dependencies | Next gate | Candidate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Project Configuration Foundation | Layer 3 | Governance Accepted | PDR-017, ADR-027, 1.8.0 Slice Contract | Implementation Complete — Not Published — Not Deployed | 1.7.0 ProjectLogisticsPoint, ServiceType, DocumentDefinition, MilestoneType catalog | Release-publication authorization | 1.8.0 |
| ProjectService | Layer 3 | Implementation Authorized | D02–D04 Accepted | Implemented — Not Deployed | Project, ServiceType | Release-publication authorization | 1.8.0 |
| ProjectDocumentRequirement | Layer 3 | Implementation Authorized | D05–D06 Accepted | Implemented — Not Deployed | Existing DocumentDefinition | Release-publication authorization; no enforcement | 1.8.0 |
| ProjectMilestoneDefinition / target | Layer 3 | Implementation Authorized | D07–D09 and ADR-027 Accepted | Implemented — Not Deployed | MilestoneType; optional ProjectLogisticsPoint | Release-publication authorization | 1.8.0 |

The bounded Release 1.8.0 implementation is complete but not published or deployed. The MilestoneType catalog is prepared but not applied; Production and Seed remain unchanged. These entries do not authorize deployment, Seed apply, packaging, or tagging.
## Permanent Reference Data release rule

ADR-028 removes Reference Data population from every release dependency and roadmap gate. A release needs passing application and applicable migration evidence; it never waits for a Seed or catalog apply. Administrators create the first and later Reference Data records through Admin UI. Optional imports may support environment migration but do not change capability maturity or deployment readiness.

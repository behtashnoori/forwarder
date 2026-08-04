# Forwarder Platform Capability Registry

- Registry Version: 1.0
- Status: Proposed
- Detailed authority: [Platform Capability Map v1](platform_capability_map_v1.md)
- Vocabulary authority: [Canonical Business Object Catalog](canonical_business_object_catalog.md)

The registry is the compact index of canonical platform capabilities. It is not a feature backlog, release commitment, or authorization to implement. Every capability has exactly one accountable capability owner. Supporting reviewers and delivery teams do not share or replace that accountability.

| Capability ID | Capability Name | Owner | Parent | Phase | Status | Priority |
|---|---|---|---|---|---|---|
| CAP-001 | Project Management | Product | Platform Business Capabilities | Phase 1 — Core Platform | Defined | Critical |
| CAP-002 | Shipment Management | Product | Platform Business Capabilities | Phase 1 — Core Platform | Operational | Critical |
| CAP-003 | Execution Management | Operations | Platform Business Capabilities | Phase 2 — Execution Units | Architected | Critical |
| CAP-004 | Timeline Platform | Architecture | Platform Product Capabilities | Phase 3 — Timeline | Architected | High |
| CAP-005 | Document Platform | Product | Platform Product Capabilities | Phase 4 — Documents | Architected | High |
| CAP-006 | Reporting & Analytics | Data | Platform Product Capabilities | Phase 5 — Reporting | Operational | High |
| CAP-007 | Customer Portal | Product | Platform Experience Capabilities | Phase 1 — Core Platform | Operational | High |
| CAP-008 | Expert Workspace | Operations | Platform Experience Capabilities | Phase 1 — Core Platform | Operational | Critical |
| CAP-009 | Administration | Administration | Platform Governance Capabilities | Phase 1 — Core Platform | Operational | High |
| CAP-010 | Security & Identity | Security | Platform Foundation Capabilities | Phase 1 — Core Platform | Operational | Critical |
| CAP-011 | Integration Platform | Architecture | Platform Foundation Capabilities | Phase 7 — ERP Integration | Defined | High |
| CAP-012 | Notification Platform | Operations | Platform Product Capabilities | Phase 1 — Core Platform | Operational | Medium |
| CAP-013 | Master Data | Data | Platform Foundation Capabilities | Phase 1 — Core Platform | Operational | Critical |
| CAP-014 | AI Platform | AI | Platform Foundation Capabilities | Phase 6 — AI Assistant | Defined | High |

## Registry rules

- IDs are stable and never reused after capability retirement.
- Capability names follow the Canonical Catalog and Platform Constitution.
- `Owner` is one of Product, Operations, Architecture, Security, Data, AI, or Administration.
- `Parent` is a hierarchy label, not a software module or organization chart.
- `Phase` is the earliest primary roadmap focus, not a release date.
- `Status` uses the capability maturity vocabulary: Vision, Defined, Architected, Planned, In Development, Operational, Enterprise Ready, AI Ready.
- `Priority` expresses architecture/product sequencing only and does not authorize delivery.
- Status or owner changes require review of the detailed capability record and traceability sources.

Capability Registry Version: 1.0
Status: Proposed

## Accepted roadmap mapping

PDR-015, PDR-016, and ADR-025 do not add new capability IDs. Accepted logistics-network ownership maps to CAP-013 (LogisticsPointType and LogisticsPoint governance), CAP-001 (ProjectLogisticsPoint configuration), CAP-010 (organization/security isolation), and CAP-003 (operational use). See [Forwarder Domain Roadmap Matrix](forwarder-domain-roadmap-matrix.md). The bounded Slice is authorized but implementation has not started; this mapping does not change the registry's own status.

DA-1.0 business definitions and relationships are indexed in [FDD-001](FDD-001-forwarder-data-dictionary.md) and [FDM-001](FDM-001-forwarder-domain-map.md); capability IDs and owners remain authoritative here.

## Accepted Release 1.8.0 mapping

PDR-017, ADR-027, and the Release 1.8.0 Slice Contract add no capability ID and change no registry maturity status. ProjectService, ProjectDocumentRequirement, and ProjectMilestoneDefinition map primarily to CAP-001, with CAP-013, CAP-005, CAP-003, and CAP-010 as dependencies. All are **Implemented — Not Deployed**; Release 1.8.0 is not published, Production is unchanged, and Seed was not executed. Defaults, snapshots, external visibility, enforcement, reporting, and automation remain deferred or absent as specified by the Slice.

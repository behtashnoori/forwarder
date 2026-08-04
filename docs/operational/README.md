# Forwarder Architecture Handbook

## Accepted Release 1.9.0 governance

- [Security Track Completion — accepted Alembic parent](../security/forwarder_security_track_completion_20260804.md)
- [PDR-018 — Operational Execution Foundation](PDR-018-operational-execution-foundation.md)
- [ADR-029 — Operational Milestone and Event History Boundaries](adr/ADR-029-operational-milestone-event-boundaries.md)
- [Release 1.9.0 Operational Execution Slice Contract](release-1.9.0-operational-execution-slice-contract.md)
- [Release 1.9.0 Governance Closure](release-1.9.0-operational-execution-governance-closure.md)
- [Operational Execution Discovery](discovery-operational-execution-foundation-20260804.md)
- [Operational Execution Domain Matrix](operational-execution-domain-matrix.md)

Security remediation is complete. Release 1.9.0 is waiting only for bounded implementation; its first migration must descend from `security_credential_remediation`.

- **Status:** Living navigation index
- **Domain Architecture:** DA-1.0
- **Current verified Production:** 1.6.1 / `20260809_cargo_catalog_items`

This handbook links authoritative documents in place. It does not replace or change their individual status.

## 1. Vision and Philosophy

- [PP-001 — Platform Philosophy](PP-001-forwarder-platform-philosophy.md)
- [Platform Constitution](platform_constitution_v1.md)
- [PDR-015 — Domain Development Roadmap](PDR-015-forwarder-domain-development-roadmap.md)

## 2. Principles

- [AP-001 — Architecture Principles](AP-001-forwarder-architecture-principles.md)
- [Architecture Baseline](architecture_baseline_v1.md)
- [ADR-028 — Administrator-Managed Reference Data](adr/ADR-028-administrator-managed-reference-data.md)
- [AI Engineering Rules](../../../28-AI-Rules/01-AI-Engineering-Standard.md)

## 3. Domain and Data

- [FDD-001 — Business Data Dictionary](FDD-001-forwarder-data-dictionary.md)
- [FDM-001 — Domain Map](FDM-001-forwarder-domain-map.md)
- [Canonical Business Object Catalog](canonical_business_object_catalog.md)
- [Phase 0 Domain Dictionary](phase0_domain_dictionary.md)

## 4. Capabilities

- [Platform Capability Map](platform_capability_map_v1.md)
- [Capability Registry](capability_registry.md)

## 5. Governance Decisions

- [Decision Index](decision-index.md)
- [Product Decision Register PDR-001–011](phase0_5_product_decision_register.md)
- [ADR directory](adr/)

## 6. Slice Contracts

- [EPIC-001 — Project Aggregate Foundation](EPIC-001-project-aggregate-foundation.md)
- [EPIC-002 — Cargo Data Foundation](EPIC-002-cargo-data-foundation.md)
- [Release 1.7.0 Logistics Network Slice Contract](release-1.7.0-logistics-network-slice-contract.md)

## 7. Releases and Deployment Evidence

- [Release Notes](../RELEASE_NOTES.md)
- [Production Deployment State 1.6.1](production-deployment-state-1.6.1.md)
- [Release 1.6.0 Cargo Governance Closure](release-1.6.0-cargo-governance-closure.md)

## 8. Operations and Runbooks

- [Database Revision Runbook](phase0_1_database_revision_runbook.md)
- [Windows Deployment Runbook](phase0_1_deployment_runbook_windows.md)
- [Disposable PostgreSQL Runbook](phase0_2_disposable_database_runbook.md)
- [Phase 1B Operator UAT Guide](phase1b_operator_run_uat_guide.md)

## 9. Roadmaps

- [Forwarder Domain Roadmap Matrix](forwarder-domain-roadmap-matrix.md)
- [Forwarder Evolution Map](forwarder-evolution-map.md)
- [PDR-015 — Domain Development Roadmap](PDR-015-forwarder-domain-development-roadmap.md)

## 10. Glossary and Indexes

- [FDD-001](FDD-001-forwarder-data-dictionary.md)
- [Canonical Business Object Catalog](canonical_business_object_catalog.md)
- [Decision Index](decision-index.md)
- [Capability Registry](capability_registry.md)

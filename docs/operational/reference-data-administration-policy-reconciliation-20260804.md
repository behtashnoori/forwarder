# Canonical Reference Data Administration Policy — Reconciliation

- **Authority:** ADR-028
- **Date:** 2026-08-04
- **Change type:** Governance/documentation reconciliation
- **Production:** unchanged

## Classification

| Class | Canonical examples | Creation boundary |
| --- | --- | --- |
| Reference Data | LogisticsPointType, MilestoneType, ServiceType, DocumentDefinition, CargoType, UnitOfMeasure, Cargo Catalog, equivalent governed lookups | Authorized administrator through Admin UI; create/update/activate/deactivate, immutable code, duplicate protection, no hard delete, audit, organization rules where applicable |
| System Data | Roles, permissions, feature flags, internal configuration, framework/bootstrap objects | Installer-generated only when indispensable to system operation; never classified as Reference Data |
| Master Data | Project, Customer, LogisticsPoint, Carrier, Vehicle, Driver, Organization | Users create during normal administration and operation |
| Operational Data | Shipment, RoutePlan, Quote, Operational Milestone, Operational Event, Invoice, Evidence | Business execution only |

## Repository reconciliation

The repository already provides administrator CRUD/lifecycle surfaces for CargoType, ServiceType, UnitOfMeasure, DocumentDefinition, Cargo Catalog, LogisticsPointType, and MilestoneType. Startup and health do not apply Reference Data catalogs. Historical plan/apply and import/export tools remain intact as optional migration utilities.

PDR-014 and ADR-021 retain their historical release evidence but are superseded where they could imply deployment ownership. PDR-016, the 1.7.0 Slice Contract, the initial catalog review, architecture principles/baseline, FDD/FDM, Decision Index, Capability Registry, Roadmap, Evolution Map, release notes, deployment runbook, and smoke test now point to administrator ownership.

Historical evidence stating that a Seed did or did not run remains factual and is not erased. Statements that merely prohibit automatic Seed are compatible. Archived phase/UAT documents describing test-fixture seeding are evidence, not current deployment instructions. Current and future releases must not describe catalog apply as pending deployment work.

## Release rule

A release is deployable when backend, frontend, and applicable migration gates pass. Reference Data population is outside release validation. The only Reference Data smoke requirement is that an authorized administrator can create the first record from an empty administration page. Import/export remains optional and no application, migration, package, health check, or unrelated workflow may require it.

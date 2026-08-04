# Forwarder Evolution Map

- **Status:** Living evidence index
- **Architecture version:** DA-1.0
- **Date:** 2026-08-02

Release folders and notes are implementation/release evidence; Production is claimed only where an operational record explicitly verifies it.

| Release | Business theme | Main domain capability | Database revision | Deployment state | Important governance/evidence |
| --- | --- | --- | --- | --- | --- |
| 1.1.0 | Operational foundation | OperationalShipment/route foundations | Repository release evidence | Release prepared; Production not asserted here | Phase 1A records |
| 1.2.0 | Project foundation | Project aggregate | `20260805_add_project_aggregate` | Release evidence exists; Production not separately asserted | ADR-017, EPIC-001 |
| 1.3.0 | Command Center / execution foundation | Customer portal and ExecutionUnit | `20260806_execution_units` | Included in current deployed lineage | PDR-012, ADR-018 |
| 1.3.1 | Scroll restoration | Cross-cutting UX | unchanged | Included in current deployed lineage | Scroll restoration record |
| 1.4.0 | Governed Master Data Foundation | CargoType, ServiceType, UnitOfMeasure schema/admin | `20260807_master_data` | Included in current deployed lineage | PDR-013, ADR-021 |
| 1.5.0 | Initial Reference Data catalog | Versioned reference catalog and seed controls | `20260808_reference_seed` | Schema included in current lineage; Production Seed not executed | PDR-014, catalog review |
| 1.6.0 | Cargo Catalog and Shipment Cargo Foundation | CargoCatalogItem, CargoItemAlias, ShipmentCargoItem | `20260809_cargo_catalog_items` | Implemented; deployed through verified 1.6.1 lineage | ADR-022, 1.6.0 closure |
| 1.6.1 | Cache Policy Hardening | Immutable frontend cache behavior | unchanged | **Production verified** at `release-v1.6.1-20260802` | Production Deployment State 1.6.1 |
| 1.7.0 | Logistics Network Foundation | LogisticsPointType, LogisticsPoint, ProjectLogisticsPoint | `20260810_logistics_network` | Published and packaged; Production deployment not performed | PDR-016, ADR-025, ADR-026, accepted Slice contract, final RC review |

DA-1.0 is the architecture knowledge baseline accompanying the transition from governed Cargo foundations to proposed Logistics Network implementation. Planned releases are not delivery promises.

## Release 1.8.0 authorized scope

| Release | Business theme | Main domain capability | Database revision | Deployment state | Important governance/evidence |
| --- | --- | --- | --- | --- | --- |
| 1.8.0 | Project Configuration Foundation | ProjectService, DocumentDefinition-backed requirements, MilestoneType-backed definitions, elapsed targets; reuse ProjectLogisticsPoint | `20260811_project_configuration` implemented, not applied to Production | Implementation Complete — Not Published — Not Deployed | PDR-017 Accepted, ADR-027 Accepted, D01–D15 Accepted; PostgreSQL 18 disposable migration evidence passed |

This implementation closure does not change Production: 1.6.1 remains the last verified deployed version recorded by this governance baseline, 1.7.0 deployment remains pending, and Production Seed remains unexecuted. The 1.8.0 MilestoneType catalog is prepared but not applied.
## Permanent installation boundary

From ADR-028 onward, all releases install application, schema, and migrations only. Reference Data population is administrator work outside release validation. Historical Seed/catalog artifacts remain optional utilities and do not represent required evolution steps.

# FDM-001 — Forwarder Domain Map

- **Status:** Living Architecture View
- **Architecture version:** DA-1.0
- **Date:** 2026-08-02
- **Vocabulary:** [FDD-001](FDD-001-forwarder-data-dictionary.md) and [Canonical Business Object Catalog](canonical_business_object_catalog.md)

Solid relationships below represent governed/current conceptual ownership; dashed relationships are future or separately governed. Diagrams do not imply database foreign keys unless the FDD or implementation contract says so.

## 1. Maturity layers

```mermaid
flowchart LR
  RD["Reference Data"] --> MD["Master Data"] --> PC["Project Configuration"] --> OE["Operational Execution"] --> ET["Evidence and Traceability"] --> AR["Analytics"] -. deferred .-> OI["Optimization"]
```

Layers are maturity stages, not unconditional release order. Analytics and optimization remain deferred until facts and governance are mature.

Reference Data is administrator-managed and may be empty after installation. It includes LogisticsPointType, MilestoneType, ServiceType, DocumentDefinition, CargoType, UnitOfMeasure, Cargo Catalog, and equivalent governed lookups. System Data (roles, permissions, feature flags, internal/framework configuration) is a separate installer/bootstrap concern. Master Data (Project, Customer, LogisticsPoint, Carrier, Vehicle, Driver, Organization) is created through normal user administration. Operational Data (Shipment, RoutePlan, Quote, Operational Milestone, Operational Event, Invoice, Evidence) is created only by business execution. See ADR-028.

## 2. Core business flow

```mermaid
flowchart LR
  C["Customer"] --> P["Project"]
  C --> SR["ShipmentRequest"]
  P --> SR --> OS["OperationalShipment"]
  P --> EU["ExecutionUnit"]
  OS --> RP["RoutePlan"]
  OS --> SC["ShipmentCargoItem"]
  EU --> EV["OperationalEvent"]
  RP --> CP["Checkpoint / Milestone"]
  EV --> E["Evidence and Timeline"]
  CP --> E
```

This is conceptual flow: ShipmentRequest commercial state, Project coordination, OperationalShipment execution, ExecutionUnit lifecycle, planning, and evidence remain distinct sources of truth.

## 3. Cargo model

```mermaid
flowchart LR
  CT["CargoType — Reference Data"] --> CC["CargoCatalogItem — Master Data"] --> SI["ShipmentCargoItem — Transaction Snapshot"]
  SI -. "future; deferred" .-> AL["Cargo-to-ExecutionUnit Link / Allocation"]
```

Catalog changes never rewrite ShipmentCargoItem snapshots. Allocation remains deferred under PDR-013 and ADR-023 Proposed.

## 4. Logistics Network boundaries

```mermaid
flowchart LR
  LPT["LogisticsPointType — Reference Data"] --> LP["LogisticsPoint — Master Data"] --> PLP["ProjectLogisticsPoint — Project Configuration"]
  PLP -. "no automatic generation" .-> RP["RoutePlan — Operational Plan"]
  LP -. "future explicit reference only" .-> CP["Checkpoint — Plan Element"]
  LP -. "optional evidence reference only" .-> OE["OperationalEvent — Historical Evidence"]
```

Logistics Network governance is Accepted; Release 1.7.0 implementation remains Not Started until its Slice contract is accepted.

## 5. Organization and security boundary

```mermaid
flowchart TB
  U["ExpertUser"] --> M["OperationalMembership + Permissions"] --> O["Organization"]
  subgraph T["Authorized organization scope"]
    P["Project"]
    OS["OperationalShipment"]
    EU["ExecutionUnit"]
    CC["CargoCatalogItem"]
    LP["LogisticsPoint — planned"]
    PLP["ProjectLogisticsPoint — planned"]
  end
  O --> P & OS & EU & CC & LP & PLP
  X["Other organization"] -. "deny before lookup/match" .-> T
```

Organization scope is resolved before resource matching or serialization. Opaque IDs do not grant access. Reference Data may be organization-independent, but mutation remains governed and dependent Master Data remains scoped.

## Architecture meaning of DA-1.0

DA-1.0 establishes explicit Reference/Master/Configuration/Transaction/Evidence layers, governed Cargo foundations, and accepted Logistics Network boundaries. It does not claim Logistics Network implementation, dashboards, allocation, customer search, GIS, or AI optimization.

## 6. Accepted Release 1.8.0 Project configuration boundary

```mermaid
flowchart LR
  ST["ServiceType"] --> PS["ProjectService — authorized"]
  DT["DocumentDefinition — existing category"] --> DR["ProjectDocumentRequirement — authorized"]
  MT["MilestoneType — governed catalog"] --> MD["ProjectMilestoneDefinition — authorized"]
  LP["LogisticsPoint"] --> PLP["ProjectLogisticsPoint — existing 1.7.0 source"]
  P["Project"] --> PS & DR & PLP & MD
  P -. "future explicit snapshot only" .-> OS["OperationalShipment"]
  MD -. "no automatic generation" .-> M["Operational Milestone"]
```

The bounded 1.8.0 concepts are **Implemented — Not Deployed**. ADR-027 and the Slice Contract remain the accepted authority; Release 1.8.0 is implementation complete, not published, and not deployed. Production is unchanged, Seed was not executed, the MilestoneType catalog is prepared but not applied, and no automatic execution behavior is present.

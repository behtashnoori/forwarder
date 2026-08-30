# ADR-043 authorization coverage ledger

Status values are machine-checkable designations. `UNSAFE_GAP` means an active
implementation item; it is not certification.

| Domain | Route/service | Resource | Collection/detail | Target root/lineage | Query scope | Status |
|---|---|---|---|---|---|---|
| ShipmentRequest | expert console / request services | ShipmentRequest | list/detail | request / assigned_to | yes | CANONICAL_QUERY_SCOPED |
| OperationalShipment | operations / operational_service | OperationalShipment | list/detail | request or direct responsibility | yes | CANONICAL_QUERY_SCOPED |
| WorkItem | operations / operational_service | OperationalWorkItem | list/action | shipment / work-item shipment FK | yes | CANONICAL_QUERY_SCOPED |
| RoutePlan/RouteLeg | operations / route orchestration | route resources | list/detail/action | shipment / plan/leg FK | yes | CANONICAL_ENFORCED |
| Checkpoint/Milestone | operations / route orchestration | checkpoint/milestone | list/action | shipment / declared FK | yes | CANONICAL_ENFORCED |
| Tracking/events | expert console / multi-unit tracking | tracking/event | list/detail/action | ShipmentRequest / current assignment | yes | CANONICAL_ENFORCED |
| Document readiness | document readiness service | readiness | list/detail/action | shipment FK | yes | CANONICAL_ENFORCED |
| Case documents | case document routes | request document | list/detail/action | ADR-037 request root only | yes | CANONICAL_ENFORCED |
| Execution units/events | execution services | execution resources | list/detail/action | shipment FK only; project-only denies | yes | UNSAFE_GAP |
| Route exceptions | operations / route orchestration | exception | list/detail/action | shipment FK | yes | CANONICAL_QUERY_SCOPED |
| OIP | oip service | OIP situation | collection/detail | no approved independent root | n/a | CERTIFIED_FAIL_CLOSED |
| Project-only execution | execution unit routes | project resource | collection/detail | no approved root | n/a | CERTIFIED_FAIL_CLOSED |
| Dashboards/exports/reports | admin report/monitoring | aggregates | collection/export | no Basic Expert broad scope | yes | UNSAFE_GAP |
| Logistics selector | logistics network service | logistics point | selector | conditional purpose scope | yes | LEGACY_SHADOW_ONLY |

`UNSAFE_GAP_COUNT = 2`.

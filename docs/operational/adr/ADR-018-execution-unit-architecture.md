# ADR-018: Execution Unit Architecture

- Status: Accepted
- Date: 2026-07-31
- Acceptance date: 2026-07-31

## 1. Context

The legacy `ShipmentTransportUnit` supports manual multi-unit customer tracking, but is coupled to `ShipmentTracking`, supports a small type catalog, and is not connected to OperationalShipment, route execution, unified events, documents, reports, optimistic concurrency, or idempotent batch actions. A canonical operational term is required before implementation.

## 2. Decision

Select **ExecutionUnit** as the canonical domain name. It covers physical and logical units executing road, rail, sea, air, warehouse, and customs work without implying that every unit is a vehicle or only a tracking projection.

Naming evaluation:

| Option | Decision |
|---|---|
| `ShipmentTransportUnit` | Legacy persistence/model name; too transport-specific and coupled to current tracking implementation |
| `TrackingUnit` | Rejected as canonical; describes observation, not execution ownership |
| `OperationalUnit` | Viable but too broad and easily confused with organizational units |
| `ExecutionUnit` | Selected; mode-neutral, action-oriented, and bounded by OperationalShipment |

Use one base ExecutionUnit model with a controlled `unit_type` catalog and extensible metadata. Do not create a table per unit type unless a later ADR demonstrates distinct lifecycle/invariants that cannot be expressed through typed attributes or linked specialist records.

## 3. Domain definitions

- **ExecutionUnit:** independently stateful unit of work or cargo execution within one OperationalShipment.
- **Unit type:** `truck`, `trailer`, `container`, `wagon`, `sea_unit`, `air_cargo_unit`, `warehouse_lot`, `customs_lot`, or `other`. Vessel/booking and airway references are attributes or linked references, not proof that an entire vessel/aircraft is owned by the Project.
- **Project-local code:** human-facing code unique within Project; it may repeat in another Project.
- **Public ID:** immutable opaque identifier used in APIs and links.
- **Current-state projection:** rebuildable latest lifecycle, location, SLA, and alert summary.
- **Unit event history:** append-only operational facts governed by ADR-019.

## 4. Invariants

- Every canonical ExecutionUnit has an opaque public ID, project-local code, type, OperationalShipment owner, version, activation state, and timestamps.
- Unit code is unique among all units in the same Project, including inactive units unless an explicit Product policy permits reuse.
- A unit has one OperationalShipment owner at a time and inherits its Project and organization scope.
- Lifecycle is `not_started`, `ready`, `in_progress`, `arrived`, `delivered`, or `cancelled`; `delayed`, `attention_required`, and stale are alerts/conditions.
- Current state changes only through explicit commands/events; direct projection edits are forbidden.
- Every state-changing command uses expected version and idempotency identity.
- Batch operations assign one correlation/batch ID while preserving per-unit authorization, idempotency result, validation, audit, and success/failure outcome.
- Deactivation is logical and preserves history. It is not cancellation and cannot hide a unit from audit.
- Split and merge never rewrite ancestry: child/survivor units store lineage and events; quantities and identifiers must reconcile under a future approved policy.
- Unit SLA and alerts are derived from service scope, planned milestones, event freshness, exceptions, and document completeness.

## 5. Security implications

Authorization evaluates organization, Project, OperationalShipment, ExecutionUnit, action, and attributes. Possession of a unit ID is never sufficient. Batch actions must reject or explicitly report unauthorized targets without leaking their existence. Customer projections expose only allowlisted fields/events/documents. Unit transfer, cancellation, split/merge, correction, and deactivation require elevated permission, reason, and audit where policy marks them sensitive.

## 6. Data and migration implications

Future migration may evolve or bridge `ShipmentTransportUnit` to canonical ExecutionUnit. Additive fields include public ID, OperationalShipment link, version, lifecycle projection, activation/deactivation metadata, and lineage. Legacy `tracking_id`, `unit_code`, metadata, and updates remain readable. OperationalShipment link may initially be nullable for legacy records; backfill requires proven request→shipment lineage. Type values are mapped, never guessed. No schema change occurs now.

## 7. API implications

Future endpoints provide paginated/filterable unit lists, unit detail, paginated event timeline, explicit transition actions, activation/deactivation, split/merge proposals, and batch actions. Commands require `Idempotency-Key`, expected version, and stable error envelopes. Existing `/api/expert/requests/{id}/tracking/units` routes remain available through a compatibility service during rollout.

## 8. UI implications

Experts use a server-paginated table with search, type/status/alert filters, bulk selection, and a lazy unit drawer for timeline, documents, reports, SLA, and lineage. Conflicts display stale-version guidance. Customers receive paginated summaries and open one unit lazily. Split/merge and destructive-looking actions require preview and explicit confirmation.

## 9. AI-native implications

Agents receive typed unit context, state version, evidence links, alerts, and permitted actions. Recommendations must cite events/documents and indicate uncertainty. Prepared batch actions enumerate selection criteria and expected impact. Execution occurs only through authorized explicit unit actions with idempotency and correlation; direct writes are prohibited.

## 10. Alternatives considered

- Keep ShipmentTransportUnit as canonical: rejected because the name and ownership encode the legacy tracking implementation.
- TrackingUnit: rejected because tracking is a projection of execution.
- OperationalUnit: rejected due to organizational ambiguity.
- Separate truck/container/wagon/etc. tables: rejected because shared identity, lifecycle, events, visibility, and document behavior dominate current differences.
- Embed units as JSON on OperationalShipment: rejected because independent concurrency, querying, history, and access control are required.

## 11. Consequences

One extensible model supports multimodal execution and independent concurrency. Legacy tracking can migrate without a big-bang rename. Type-specific validation must be governed through catalogs/policies rather than uncontrolled metadata.

## 12. Risks

- An overly generic metadata bag could weaken constraints.
- Unit codes and quantities may not reconcile in split/merge flows.
- Large batch operations could lock many rows or produce partial failure ambiguity.
- Current-state projection may drift from events without deterministic rebuild tests.
- Confusing deactivation, cancellation, and deletion could hide operational obligations.

## 13. Backward compatibility

`ShipmentTransportUnit` remains the legacy model/table/API identity during transition. A compatibility adapter maps it to ExecutionUnit contracts and preserves unit codes, public tracking behavior, customer visibility, and existing updates. Renaming a database table is not required for initial adoption.

## 14. Rollout strategy

Add identity/version/ownership fields, backfill verified links, build shadow projections from legacy updates, compare results, expose read-only canonical endpoints, then enable cohort commands. Adopt unit types incrementally. Split/merge remains disabled until quantities and lineage policy are approved.

## 15. Rollback strategy

Disable canonical unit reads/writes and batch actions, return to legacy tracking services, stop projectors, and retain new events/links. Never reverse split/merge by deleting history. Reconciliation is required before re-enabling.

## 16. Open questions

- Product Owner: may unit codes be reused after deactivation?
- Product Owner: canonical lifecycle and whether `arrived` is required separately from `delivered` for every type.
- Operations: type-specific required attributes and SLA catalogs.
- Operations/Data: quantity, weight, volume, and custody rules for split/merge.
- Security: maximum batch size and partial-success disclosure policy.
- Architecture: evolve the existing table in place or introduce a bridge/canonical table after profiling production cardinality.

## 17. Acceptance criteria for approving the ADR

- `ExecutionUnit` is approved as the canonical term across all four ADRs.
- The unit-type catalog and extensibility rule are accepted.
- Ownership, code uniqueness, lifecycle, activation, concurrency, and idempotency invariants are approved.
- Batch semantics preserve per-unit permission and audit.
- Split/merge is explicitly deferred until quantitative invariants are approved.
- Legacy compatibility can be implemented additively without an immediate table rename or API break.
- Event and document scopes use the same ExecutionUnit public ID defined here.

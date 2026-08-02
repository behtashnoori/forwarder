# ADR-025 — Logistics Network Aggregate Boundaries

- **Status:** Accepted
- **Date:** 2026-08-02
- **Accepted:** 2026-08-02
- **Authority:** Product, Architecture, Operations, Data; Security for organization/isolation boundaries
- **Product decision:** [PDR-016 — Logistics Network Foundation](../PDR-016-logistics-network-foundation.md), Accepted D01–D10
- **Roadmap:** [PDR-015 — Forwarder Domain Development Roadmap](../PDR-015-forwarder-domain-development-roadmap.md)
- **Scope:** Aggregate boundaries for the bounded Logistics Network foundation

## Context

Forwarder requires reusable governed logistics places for Project configuration without confusing geographic Reference Data, reusable Master Data, operational plans, execution elements, or historical evidence. Existing Province/City, Project, RoutePlan, Checkpoint, Milestone, and OperationalEvent concepts have different ownership and lifecycle semantics. Free-text-only naming would prevent stable reuse and reporting, while merging these aggregates would let configuration changes rewrite operational meaning.

## Decision

- **LogisticsPointType** is governed Reference Data: an immutable-code classification with bilingual labels, definition, lifecycle, order, and governed audit metadata.
- **LogisticsPoint** is reusable Master Data: an organization-scoped-by-default real-world physical/business place with opaque public identity and immutable organization-local code.
- **ProjectLogisticsPoint** is Project configuration: a Project-specific association to one LogisticsPoint with Project sequence, bounded role, optional label/notes, and participation lifecycle.
- **RoutePlan** remains revisioned operational planning owned by an OperationalShipment.
- **Checkpoint** remains an execution-plan element. A future explicit reference to a LogisticsPoint may be designed additively, but identity is never collapsed.
- **OperationalEvent** remains append-only historical evidence of what occurred.
- **Province and City** remain geographic Reference Data used to describe geography; neither is a LogisticsPoint.
- **Customer** remains a business party. A customer site may reference Customer but is not the Customer aggregate.

## Invariants

1. Project configuration changes do not rewrite historical execution or evidence.
2. A LogisticsPoint is not automatically a Checkpoint.
3. A ProjectLogisticsPoint is not an OperationalEvent.
4. ProjectLogisticsPoint sequence does not automatically create or revise a RoutePlan in this Slice.
5. LogisticsPointType, LogisticsPoint, and ProjectLogisticsPoint use explicit domain structures; no generic EAV architecture is permitted.
6. GIS, maps, coordinates, geofencing, traffic, weather, and automated location detection are outside this scope.
7. Public point search and customer-visible point catalogs are outside this scope.
8. Organization-first authorization applies before lookup, matching, serialization, duplicate reporting, and administration.
9. Inactive referenced records remain historically readable; used points are not hard-deleted.
10. No legacy address, Province/City value, Checkpoint, or event is automatically converted into a LogisticsPoint.

## Aggregate ownership and interaction

| Aggregate/concept | Owns | May reference | Must not own or imply |
| --- | --- | --- | --- |
| LogisticsPointType | Classification semantics and lifecycle | Nothing operational | A place, Project use, route, or event |
| LogisticsPoint | Governed place identity and geographic attributes | Type, country, optional Province/City, optional Customer relationship | Project sequence, route progress, or occurrence |
| ProjectLogisticsPoint | Project selection, role, order, participation | Project and LogisticsPoint | Master place fields, RoutePlan, Checkpoint, or evidence |
| RoutePlan | OperationalShipment plan revision and ordered execution structure | A later explicitly governed point reference | Project configuration truth or historical occurrence |
| Checkpoint | Execution-plan position/control element | A later explicit LogisticsPoint reference | Master place identity |
| OperationalEvent | Occurred/recorded evidence and provenance | Authorized subjects and an optional governed point reference | Configuration or master-data mutation |

## Security and data consequences

Management is internal/admin-only and deny-by-default. Opaque public identifiers do not grant access. No global or cross-tenant discovery is implied. Duplicate candidates remain organization-filtered and are reported, never silently merged. Country is required; Province/region, City, and short address are optional. Latitude/longitude, timezone, working hours, capacity, contacts, and geofence remain deferred.

## Compatibility, migration, and rollback

Future implementation is additive. Existing Projects and operational records require no backfill; free-text addresses remain readable. Rollback disables new selection/management surfaces while retaining new referenced records for historical readability and reconciliation. No destructive contraction occurs until separately governed usage and retention gates pass.

## Consequences

The separation supplies stable dimensions and Project configuration without turning configuration into execution evidence. It adds stewardship and association complexity, but preserves auditability, organization isolation, and later reporting integrity.

## Explicit exclusions

This ADR does not authorize GIS, public search, dashboards, reporting UI, automatic RoutePlan generation, route templates, historical backfill, a generic workflow engine, or generic EAV. It does not change ADR-023 or ADR-024; allocation and customer cargo search retain their existing statuses.

## Acceptance boundary

ADR-025 is Accepted for the aggregate boundaries above. PDR-016 authorizes planning of the bounded LogisticsPointType, LogisticsPoint, and ProjectLogisticsPoint implementation Slice. Implementation, migration execution, seed execution, release, and deployment remain separately controlled.

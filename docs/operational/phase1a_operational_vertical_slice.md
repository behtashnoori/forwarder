# Phase 1A operational vertical slice

## Scope
An accepted commercial `ExpertQuote` creates one independent, organization-scoped `OperationalShipment`, one active `RoutePlan`, one `RouteLeg`, departure/arrival milestones, append-only events, and overdue work items. `ShipmentRequest` and Quote remain commercial/intake entities.

## Flow
Accepted quote → operational shipment → route/milestones → report → verify/correct → overdue reconcile → work queue → resolve. Commands write domain state, audit, and outbox in one transaction. UI routes are `/operations/shipments`, `/operations/shipments/:id`, and `/operations/work-queue`.

## Boundaries
Phase 1A is one initial leg/plan. Multi-leg planning, documents, claims, costs, GPS, external notifications, Excel import, release, and deployment are deferred.

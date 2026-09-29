# ADR-068 — Canonical geography, organization locations, and shipment workspace

## Status

Accepted for the consolidated shipment-hardening change set. Product-owned document,
stage, and closure-policy content remains deliberately unconfigured.

## Context

The existing application has a governed 249-country catalog, legacy domestic
Province/County/City rows, UN/LOCODE-oriented international locations, an
organization-scoped `LogisticsPoint` aggregate, and immutable route/delivery
history. Operators nevertheless lack one searchable Country → Admin1 → City →
Organization Location workflow. Shipment detail is also one long accordion page,
and its unified history omits several authoritative lifecycle sources.

## Decision

1. `Country` remains the ISO 3166-1 authority and is not reseeded.
2. `Province` and `City` are evolved in place for the GeoNames V1 Admin1/city
   authority. Existing rows remain readable and untouched. New canonical rows are
   distinguished by dataset and stable GeoNames identity. A canonical city may
   have no legacy `County`; its direct parent is Admin1 and its country is explicit.
3. GeoNames source bytes are prepared outside product state. A deterministic,
   checksummed package is qualified before one additive plan/apply transaction.
   No partial apply or heuristic legacy-row matching is allowed.
4. `LogisticsPoint` remains the organization-location aggregate. Expert creation
   requires only a name and canonical city, generates an immutable code, and is
   immediately selectable in `PENDING_REVIEW`. Optional type, address,
   coordinates, and notes may be enriched later. Admin approval governs catalog
   quality; it does not gate current operations. Deactivation affects only future
   selection. Duplicate candidates are flagged, never merged automatically.
5. Route reference endpoints continue to bind `CanonicalLocation` plus optional
   `LogisticsPoint`; text is an immutable display snapshot only.
6. New deliveries bind a canonical city and optional organization location and
   preserve a destination snapshot. `destination_text` remains unchanged for old
   rows and becomes an optional human note for structured writes. Delivery facts
   remain append-only.
7. Unified shipment history composes selected operator-facing facts from their
   authoritative tables. Technical maintenance events stay in audit.
8. Shipment detail becomes a route-addressable workspace with a persistent header
   and bounded task sections. Legacy hash links remain compatible.

## Authority and unresolved content

System document types, organization document policies, organization operational
stages, and closure-policy values retain their existing governed configuration
paths. This change does not invent legal requirements, stage semantics, or closure
thresholds. Those values require Product Owner decisions and are not a blocker for
the capability hardening above.

## Consequences

The migration is additive except for making the legacy city-county and logistics
point-type links nullable. Historical references remain valid. New selection APIs
only expose qualified canonical rows and active organization locations. Tenant
scope, immutable snapshots, idempotency, and route-time/ETA v2 semantics remain
unchanged.

# Shipment Operational Population v1

This contract is the reusable authority for the route-based Operational
Shipments population. It is intentionally narrower than organization-wide
aggregate analytics.

## Authority and composition

The population is composed in this semantic order:

1. the organization from the authenticated user's active membership;
2. `SHIPMENT_OPERATIONAL_ASSIGNED` visibility (`assigned_shipment_scope`);
3. the unique active route plan and a non-empty active-plan route;
4. the governed Shipment status filter;
5. the planned operational-window overlap;
6. deterministic `created_at DESC, public_id ASC` ordering;
7. bounded pagination applied by the consumer.

Client organization and user identifiers have no authority. Assignment and
tenancy are applied in SQL before ordering and pagination.

## Route envelope and operational window

Route sequence is authoritative. The Shipment planned departure is the
`planned_departure` of the lowest-sequence leg in the active plan. The Shipment
planned arrival is the `planned_arrival` of the highest-sequence leg in that
plan. Timestamp `MIN`/`MAX` does not define route order, and matching any single
leg is not Shipment operational-window semantics.

The requested window overlaps the route envelope inclusively:

```text
final planned arrival >= requested from
first planned departure <= requested to
```

Either requested bound may be omitted. A Shipment without an active plan or
without an active-plan leg is excluded from this v1 route-based population.

The existing HTTP parameters `date_from` and `date_to` remain compatible names
and are normalized at the transport boundary. Offset-aware timestamps are
converted to UTC. Legacy naive and date-only values are explicitly interpreted
as UTC only by that adapter. The internal `OperationalWindow` rejects naive
timestamps and never depends on the server's local timezone.

Operational planned time is not `OperationalShipment.created_at`. Aggregate
analytics may continue to use created time for a different analytical question.
Likewise, operational assigned visibility is not organization-wide analytics
visibility.

## Downstream contract

A future semantic ROWSET TABLE may reuse this authority with the conceptual
input below without rebuilding population rules:

```text
population = SHIPMENT
visibility = SHIPMENT_OPERATIONAL_ASSIGNED
operational_window = { from, to }
status = governed Shipment status
sort = CREATED_AT_DESC_PUBLIC_ID_ASC
limit = bounded by the caller
```

Saved View v1 remains unchanged. Its current created-time mapping is known debt;
a subsequent Saved View v2 alignment can map the UI dates to this explicit
operational window without a database migration.

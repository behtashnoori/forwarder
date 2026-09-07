# Semantic Analytics Authorization v1

Semantic Analytics derives both aggregate and drill-down populations from the
authenticated user's canonical assigned Shipment scope.

- Tenant boundary: the user's single active `OperationalMembership` and its active organization.
- Permission boundary: `operational_shipment.read` on that membership.
- Business-data boundary: `assigned_shipment_scope(current_user)`.
- Normal Expert: request-assigned and directly assigned Shipment work only.
- Organization Admin: all Shipments in the organization when the permission is present.
- Platform Admin: no implicit tenant-work authority.
- Dashboard and Saved View definitions are query configuration, not access grants.
- Semantic filters may narrow the authorized population; they never expand it.

Organization membership alone is not business-record authorization. Authorization
is applied before filtering, grouping, aggregation, coverage calculation, limits,
and drill-down identity selection.

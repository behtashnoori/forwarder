# Saved View Rowset Alignment v2

New Operational Shipment Saved Views persist `saved-view-definition-v2` with
`analytics-semantic-v2` and a governed Shipment ROWSET query. They store only
personal query configuration and LIST presentation: never result data,
authorization, or a historical access snapshot.

Persisted v1 definitions and revisions remain immutable. On read, compatible
v1 definitions are side-effect-free aligned to a runtime v2 ROWSET. The legacy
aggregate `SHIPMENT_COUNT` is removed, and its historical `created` time label
is deliberately reinterpreted as the operational route-envelope window that
the Operational Shipments UI always meant. A meaningful update persists one v2
revision; an untouched compatibility alignment creates no revision.

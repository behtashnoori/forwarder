# Saved View → Dashboard Widget Snapshot v1

A compatible personal Saved View creates an independent personal Dashboard
`TABLE` widget through the server-authoritative snapshot endpoint. The widget
copies the validated v2 ROWSET query and stores immutable provenance: source
type, public ID, version, and name snapshot. It stores neither results nor an
authorization snapshot.

Dashboard runtime has no Saved View dependency: it executes the copied query
through Semantic Analytics and current Shipment authorization. Source edits or
archive operations do not synchronize or break the widget; Project-access
revocation immediately narrows its runtime population.

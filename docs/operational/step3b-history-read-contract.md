# Step 3B history and current-route reads

`shipment_graph` and route timeline expose `scope=current_route`. Their operational
provenance contains active plan/revision, rule version, contributing legs, per-leg
occurrence IDs and timestamps, and inherited source milestone/revision. Reads do
not mutate projections. Missing/empty routes remain planned. Ambiguous evidence
returns an unresolved reason instead of choosing the latest recorded event.

`GET /api/v2/operational-shipments/{shipment_id}/history?page=1&per_page=50`
requires shipment read permission and normal shipment authorization. It returns
all retained revision records plus shipment-owned occurrence, correction,
verification and lifecycle events, bounded to 100 items per page. Inherited events
remain on their original milestones and appear only once. Recording order is a
history presentation order, never the effective-occurrence selection rule.
Legacy decision relationships are only exposed when their target is proven;
missing or invalid relationships are marked unresolved.

The existing execution-events endpoint is also bounded (default/max 100) and
supports `page` and `per_page`. It resolves references across page boundaries.
`recent_events` remains a bounded current-route feed. Shipment Detail labels it
accordingly; it is not full shipment history.

Plan/detail/timeline payloads include plan ID, route revision, active flag and rule
version. Clients making separate requests should compare these fields and refetch
on mismatch; multiple HTTP reads do not promise an atomic snapshot. Pagination is
offset-based, so refresh from page one when new history arrives.

Planned, projected and actual timestamps are separate. Convenience timestamps
carry their source, and missing timestamps are not fabricated. Raw codes and
reconciliation metadata remain available for diagnostics; history classifications
and business labels support a later UX pass without changing Summary layout.

Audit summaries use organization plus typed, proven shipment lineage. Old audit
rows are never rewritten or relabelled. Replan retains snapshots rather than
refreshing them from master data, preserves execution lifecycle and source IDs,
and synchronizes future milestone planned times. Activation rejects replacement
of executed routes outside the preserving replan path.

Supported analytics relationships remain shipment/customer/project/revision,
selected leg facilities and mapped route occurrences. No commodity/leg,
commodity/carrier, document/physical-event or governed current-carrier join is
introduced.

Step 3A's PostgreSQL bridge and append-only migration are unchanged.
POSTGRES_RUNTIME_VALIDATION=REQUIRED_AT_RELEASE_QUALIFICATION


Source occurrence corrections rebuild the source projection and every retained
active or superseded descendant that explicitly inherits that fact. Traversal
uses shipment/organization-scoped source milestone links and validates the owner
leg/checkpoint links. It follows transitive lineage; it never matches timestamps,
labels or sequence numbers. The existing organization/shipment milestone index
bounds candidate lookup; no additional schema/index is needed.

A descendant with a valid independent local occurrence chain stops propagation
for that branch. Malformed chains or inconsistent owner lineage reject the whole
command. Normal report commands still prohibit a second root over inherited
execution; this repair adds no replacement command. Other-tenant candidates are
excluded, and effective-source resolution rejects cross-tenant inheritance.

Correction event insertion, source and descendant actual/lifecycle/confidence
projections, and the single final shipment reprojection share the command
transaction. A chronology failure in any descendant rolls everything back.
Historical plan times, revision identity and master-data snapshots are unchanged.
Events stay on the original lineage, with no descendant event copies. Reads
continue to use stored projections and effective-source provenance unchanged.

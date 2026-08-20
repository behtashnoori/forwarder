# Legacy / Canonical Map

This map is normative for new development. “Legacy” means compatibility-supported, not safe to delete.

| Area | Current legacy | Current canonical | Bridge | New-development rule | Migration strategy |
| --- | --- | --- | --- | --- | --- |
| Shipment | `ShipmentRequest` carrying historical operational fields; `ShipmentTracking` | `OperationalShipment` | Explicit request/accepted-quote lineage or direct creation under ADR-034 | Put execution lifecycle, route, milestone, readiness and economics on `OperationalShipment`, never new operational status on `ShipmentRequest`. | Add canonical rows/links, verify projections, cohort switch, retain request history until deprecation gate. |
| Unit | `ShipmentTransportUnit` and updates | `ExecutionUnit` and `OperationalEvent` | `ExecutionUnit.legacy_unit_id`; optional canonical shipment link | New independently managed units use `ExecutionUnit`. Legacy unit changes require an Accepted ADR. | Preserve identifiers and event times; bridge/backfill only with tenant and semantic evidence. |
| Tracking location | `TrackingLocationReference` and free text | Organization `LogisticsPoint`; `CanonicalLocation` for route identity/snapshots | No complete mapping exists | Do not add new runtime selector dependence on `TrackingLocationReference`; do not silently swap catalogs. | Approve mapping ADR, add tenant-safe mapping, preserve snapshots/free text, shadow read, then switch. |
| Time | Naive `DateTime`, `datetime.utcnow`, offset-less ISO | UTC-aware Python, `timestamptz`, RFC 3339 offset | Field-specific serializers such as `serialize_legacy_utc_datetime` only after source proof | All new Instant columns are aware. Never globally label legacy naive data UTC. | Inventory by column, prove source contract, clone/reconcile, additive conversion, shadow compare, switch and retain rollback. |
| Documents | Request-owned `CaseDocumentRequirement`/`CaseDocumentFile` | Shipment `OperationalDocumentRequirement` plus exact-version `ArtifactAssociation` | Association requires same source request and definition | Keep file ownership separate from contextual shipment use. No direct unit file ownership without Accepted ADR. | Materialize explicitly per shipment; never copy binaries or infer approval. Add broader scopes only after ADR-020 disposition. |

## Manual compatibility checks

- A bridge must reject cross-tenant source/canonical pairs.
- Unknown lineage, timezone, or location identity remains unresolved or quarantined.
- Historical snapshots and append-only facts are not rewritten after master-data correction.
- Compatibility APIs cannot become precedent for new numeric-ID or unscoped APIs.
- Removal requires usage evidence, consumer notice, rollback rehearsal, and an Accepted contract-phase decision.

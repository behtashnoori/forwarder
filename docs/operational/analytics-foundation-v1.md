# Analytics Foundation v1

`analytics-semantic-v1` is a read-only, tenant-scoped semantic query layer over
authoritative operational projections. It exposes an immutable code-governed
metric/dimension registry, compatibility metadata, coverage definitions, and
drill-down metadata. It does not expose SQL, internal table names, or arbitrary
columns.

Route metrics use the active RoutePlan. Historical execution must follow the
explicit RouteLeg source lineage and deduplicate by its root; plan revisions are
counted separately only for `REPLAN_COUNT`. Physical-occurrence metrics use the
Step 3 effective occurrence resolver: verification is not a physical event and a
correction does not create a second business occurrence.

`NULL_UNKNOWN`, `ZERO`, `NOT_APPLICABLE`, `NOT_READY`, and `OUT_OF_SCOPE` are
distinct response states. Coverage is returned beside every query. Carrier is
descriptive text only; commodity-to-leg/carrier/facility and document-to-event
joins are rejected. The registry marks lead time, on-time, schedule delay,
stale shipment, current-stage age, and needs-attention as non-executable until
their business definitions are governed.

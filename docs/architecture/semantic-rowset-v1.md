# Semantic Analytics ROWSET v1

Semantic Analytics has two explicit query kinds. `AGGREGATE` remains the
backwards-compatible `analytics-semantic-v1` metric contract. `ROWSET` is the
additive `analytics-semantic-v2` contract for a bounded operational population.

The first ROWSET population is `SHIPMENTS`. It reuses the canonical Shipment
business authorization and the frozen operational Shipment population: tenant,
authorized Shipment scope, active-route envelope, inclusive operational window,
and deterministic ordering. Its operational time window is intentionally not
the aggregate Analytics created-time role.

Shipment columns are governed by one shared registry. A ROWSET can only narrow
the authorized population through status, operational window, governed sort,
and a 1–100 server-enforced limit. The first presentation is Dashboard `TABLE`.
`ATTENTION_LIST` and Saved View v2 remain deferred; the shared registry makes a
deterministic Saved View v1-to-v2 alignment possible in the next slice.

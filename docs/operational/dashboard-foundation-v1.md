# Dashboard Foundation v1

Dashboard Foundation is a read-only presentation layer over
`analytics-semantic-v1`:

`Semantic Registry → Dashboard Definition → Validator → Widget Query → Analytics API → Drilldown → Shipment Detail`

The first source-controlled system definition is **Operations Control Tower**.
It has no persistence, builder, report builder, custom formulas, data warehouse,
ETL, map, or real-time infrastructure. It stores no KPI values and never reads
raw database fields or computes KPIs from shipment list data.

Each widget uses registered metric and dimension keys. The validator rejects an
unknown/non-executable metric, unsupported dimension/filter/time role/grain, or
semantic-version mismatch. The dashboard can narrow registry choices but cannot
expand them.

Global filters are tenant scope plus time, customer, and project filters. A
filter must be applicable to a widget; it is never silently dropped. Coverage
and warning metadata are rendered alongside values. `ZERO`, `NULL_UNKNOWN`,
`NOT_APPLICABLE`, `NOT_READY`, `OUT_OF_SCOPE`, partial coverage, errors and
stale values remain separate UI states.

Widgets are independently queried in bounded parallelism (four at a time).
They share refresh-cycle metadata but do not claim an atomic database snapshot.
The default is page-load plus manual refresh; Control Tower can refresh every
120 seconds while its tab is visible.

Dashboard drilldown uses `POST /api/v2/analytics/drilldown/{metric}` with the
normalized Analytics query that produced the widget.  Chart selections add an
explicit semantic `segment` (`dimension`, `value`); the backend validates it and
applies it to the same governed population.  The legacy GET endpoint is only a
body-free convenience route for an uncontextualised default drilldown.  The
Dashboard never sends a GET body or reconstructs a population client-side. Open
work item and replan drilldown remain disabled pending explicit
population-equivalence coverage.

Dashboard Builder, personal dashboards, saved views and Report Builder will
share `SemanticQueryDefinition` later, while retaining separate definition
models for dashboard layout and report/export formatting.

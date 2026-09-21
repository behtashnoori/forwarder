# ADR-051: Scalable Server-Side Control Tower Read Model

- **Status:** ACCEPTED — bounded implementation authorized
- **Date:** 2026-09-21
- **Owners / decision authority:** Product Owner mission; Architecture Owner; Security/Authorization boundary; Operations/Attention owner
- **Affected domain:** Control Tower operational read model, pagination, search, aggregates, and D2 product surface
- **Implementation authority:** The 2026-09-21 Control Tower Scalability Closure mission, bounded by this ADR and `docs/architecture/control-tower-scalability-v1.md`

## Context

D1 protects correctness by evaluating the complete authorized active Shipment population before filtering and pagination, and by returning `503 EVALUATION_UNAVAILABLE` when that population exceeds 100. That ceiling is explicitly a technical safety bound, not a business or tenant-plan limit. D2 truthfully clears the page on that failure, but the product is not release-scalable.

The current cursor reduces response size only. It does not reduce source evaluation, memory, or query work because attention ranking and filtering occur after full Python evaluation. Raising the ceiling would merely move the failure point and is rejected.

## Decision

Replace complete-population Python evaluation with a bounded server-side read pipeline:

1. establish the current authorized active population in SQL before search, counts, attention evaluation, ordering, or windowing;
2. normalize the existing D1 delay, exception, operational-work, MDPM readiness, and verified OIP attention facts as a relational query;
3. derive the existing D1 deterministic rank tuple per Shipment;
4. apply optional server-side search and attention filters to that governed query;
5. compute complete matching total and global attention counts from that same governed population;
6. select one bounded deterministic page; and
7. hydrate and revalidate only those selected Shipment identities through the existing D1 presentation boundary.

Control Tower remains read-only and is not a System of Record. No risk score, Shipment state, milestone meaning, ownership state, Notification, or materialized second truth is introduced.

## Public contract

`GET /api/control-tower/shipments` remains the single endpoint. Existing `page_size`, `attention`, and opaque `cursor` parameters remain; optional `search` is additive and bounded. Existing item fields remain. The response adds:

- `summary.total`: complete authorized/search-matching displayed rows after the optional attention filter;
- `summary.attentionCounts`: complete urgent/follow-up/review counts before the optional attention filter; and
- explicit page `limit`, `offset`, `returned`, `hasMore`, and `nextCursor`.

The default page is 25 and the maximum remains 100. `items.length` is never a global total. A cursor is a signed continuation for one normalized request, not a historical snapshot.

## Ordering and changing data

The stable order is:

```text
attention rank
→ due bucket
→ earliest due
→ oldest onset
→ Shipment public identity
```

Static data therefore traverses without ambiguous ties, duplicates, or omissions. Each request is a current query-time view. When operational facts change between page requests, membership or position may change; the UI must not claim long-lived snapshot isolation.

## Authorization and disclosure

The existing D1 actor, membership, capability, tenant, eligible-lifecycle, and responsibility policy remains authoritative. Platform Admin receives no implicit tenant-work access. Another same-organization Expert receives no Shipment merely through membership. Foreign or unauthorized rows cannot influence items, totals, attention counts, search results, page fullness, cursor metadata, or error shape.

Authorization after pagination is prohibited. Selected page authority and responsibility are revalidated immediately before disclosure. Invalid scope/source/invariant evaluation fails the page closed with the existing sanitized `503 EVALUATION_UNAVAILABLE`; no partial `200` is permitted.

## Attention and aggregate semantics

The SQL reason index must remain equivalent to the current D1 attention sources and rank. Row display continues through the current D1 translators/adapters. Aggregate counts describe the complete authorized/search-matching attention population and are not page-local.

Any future attention-source or ranking change must update both relational selection and detailed evaluation under a separate governed decision/test. Silent divergence is a release blocker.

## Schema and performance

The initial schema decision is:

```text
CONTROL_TOWER_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
```

Existing source indexes are expected to support the query. PostgreSQL 18 qualification must verify query plans, query count, timing, and bounded application hydration at 0/1/99/100/101/250/500 and preferably 1000+ realistic Shipments. If an index is materially required, this ADR must be amended and only an additive index migration descending from the current head may be implemented.

## Compatibility and recovery

The response evolution is additive and D2 is upgraded in the same candidate. The old `population > 100` failure is removed only after parity, authorization, global-count, traversal, PostgreSQL, and browser evidence pass. Genuine evaluation failure remains fail-closed. There is no schema/data rollback; source rollback restores the prior ceiling behavior.

## Rejected alternatives

- Increasing `100` to another constant.
- Loading every active Shipment and slicing in Python.
- Browser-side multi-page fetching/evaluation.
- Authorization filtering after limit/offset.
- Page-length-derived KPI/counts.
- Changing attention meaning to simplify paging.
- A materialized Control Tower System of Record without separate schema/operations governance.

## Consequences

The endpoint can serve large authorized populations with response/application work bounded by page size while complete totals and ordering remain server-owned. Database work still scales with indexed matching source facts, and deep offset traversal can cost more than early pages. Those are explicit measurable release limits, not a claim of infinite scalability.

## Required evidence

Freeze requires focused parity and large-population tests; negative authorization/count non-disclosure; deterministic static traversal; genuine-failure `503`; PostgreSQL 18 query/timing/plan evidence; D2 search/filter/page/stale-response tests; normal-navigation desktop/mobile RTL browser journeys; full backend/frontend/type/lint/build/source/package regression; one Alembic head; and final reference alignment.

## Reference impact

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_BY_ADR_051
```

ADR-051 complements ADR-008/030/031/032 and preserves ADR-042/043/047 authorization and ownership boundaries. It resolves the scalability architecture required by PDR-019 §7–§9 and the Post-D2 gap review without changing product meaning.

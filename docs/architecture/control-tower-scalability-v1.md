# Control Tower Scalability — Bounded Implementation Design

- **Status:** Approved implementation design for the bounded Build slice
- **Date:** 2026-09-21
- **Governing baseline:** LPAF v2.2 plus the v2.3 Product Integration / `REFERENCE_IMPACT` strong default
- **Rigor:** Level B — release-critical operational read model
- **Starting canonical:** `2bb69bcc38ec9c8c0ffa1e27b64fcc052ee19c07`
- **Branch:** `codex/control-tower-scalability`
- **Authority:** the user-supplied Control Tower Scalability Closure Goal, PDR-019 §7–§9, ADR-008/030/031/032/042/043/047, and the Post-D2 gap review

## 1. Mission contract

| Field | Decision |
| --- | --- |
| MISSION | Remove the D1 technical ceiling that makes Control Tower unavailable when the authorized active Shipment population exceeds 100. |
| OUTCOME | A truthful, tenant-scoped, deterministic, server-windowed operational read works for large authorized populations without presenting a partial evaluation as complete. |
| SCOPE IN | Existing endpoint evolution, authorized SQL population, server-side attention/search filtering and ordering, complete matching totals/attention counts, bounded page hydration, D2 pagination/search integration, PostgreSQL/browser qualification, evidence, commits, and controlled canonical synchronization after PASS. |
| SCOPE OUT | New risk/attention meaning, Shipment lifecycle or ownership mutation, dashboard customization, Notification activation, modularization, deployment, Production access, and Product Acceptance Closure. |
| CAPABILITY_OWNER | Operations / Attention. |
| SYSTEM_OF_RECORD | Existing Operational Shipment, operational attention sources, MDPM readiness facts, and verified OIP enrichment. Control Tower remains a read model. |
| ACTORS | Active owning Expert and same-organization Organization Admin under the existing Control Tower policy. Platform Admin has no implicit tenant-operator access. |
| TENANT / DATA SCOPE | Tenant-private operational data. Current actor, membership, organization, capability, eligible lifecycle, and fixed responsibility are applied before search, aggregation, ordering, or windowing. |
| QUALITY ATTRIBUTES | Truthful totals, stable static traversal, bounded memory/query count, no N+1 page hydration, fail-closed evaluation, non-disclosure, RTL/mobile usability, and explicit query-time consistency. |
| STOP CONDITIONS | Baseline/reference conflict, authorization-after-windowing, page-derived global count, attention-semantic drift, unbounded population hydration, PostgreSQL qualification failure, browser Product Surface failure, or candidate/reference disagreement. |
| DEFINITION OF DONE | The stated 0/1/99/100/101/250/500/1000+ population, authorization, global-count, deterministic paging, PostgreSQL performance, browser, full regression, release/source/package, and final reference gates pass. |

## 2. Current-state facts, assumptions, and decisions

### Facts

- D1 first loads the complete authorized active Shipment population, rejects row 101, evaluates all sources in Python, sorts the complete result, then applies attention filtering and cursor slicing.
- D1 attention ordering is `(attention level, due bucket, earliest due, oldest onset, Shipment public id)`; a row is absent when it has no supported attention reason.
- D1 sources are active delays/exceptions, recognized open operational work, MDPM next-transition readiness blockers, and verified OIP enrichment of an existing reason.
- D2 supports only the unfiltered/urgent/follow-up/review views, an opaque continuation cursor, explicit empty/error states, and Shipment Detail navigation.
- The 100 value is a technical safety ceiling, not a business or tenant-plan limit.

### Decisions

- The canonical authorized population remains the existing active (`planned`, `in_progress`) tenant/actor/responsibility scope. Authorization is a SQL predicate before every aggregate and page operation.
- A relational attention index is derived at request time from the same authoritative source facts. It is a query, not a stored second System of Record.
- SQL selects one deterministic rank tuple per Shipment and computes complete matching totals and per-attention counts. Only selected page identities are hydrated into the existing D1 presentation rows.
- The page retains an opaque signed cursor. Its payload contains contract version, normalized search/filter, page size, and next offset. It is not a historical snapshot token.
- Each response is a truthful query-time view. Concurrent operational changes may move rows between requests; the UI does not claim snapshot isolation. Static data traverses without duplicates or omissions.
- Search is optional, server-side, normalized, and bounded to 100 Unicode code points. It uses only already-governed Shipment reference, Request reference, and responsible-Expert display name.
- Default page size remains 25 and the existing hard maximum remains 100. No unlimited page size exists.

## 3. Ownership and boundary contract

| Contract | Owner / rule |
| --- | --- |
| STATE OWNER | Existing Shipment/source domains; this capability writes nothing. |
| READ-MODEL OWNER | Control Tower service boundary. |
| ATTENTION/RISK OWNER | Existing D1 source adapters and ADR-008/030/031 semantics. SQL indexing must match them; it does not redefine them. |
| UPSTREAM | Current persisted actor/membership/capability, Operational Shipment responsibility, operational delay/exception/work, MDPM readiness, and verified OIP facts. |
| DOWNSTREAM | Existing D2 operational Control Tower cards and Shipment Detail destination. |
| ADJACENT CAPABILITIES | Shipment Detail, Dual Calendar, Combined Transport, Quote Communication, Documents, optional Cargo, and dormant Notifications are regression-only. |
| MODULE BOUNDARY | `control_tower_scope` owns actor/tenant/responsibility population; a new query module owns normalized attention/search/count/window SQL; the existing composer owns page hydration/presentation. |
| PUBLIC CONTRACT | Additive evolution of `GET /api/control-tower/shipments`; no parallel API. |
| ALLOWED DEPENDENCIES | Existing authoritative models and read-only projection helpers needed for the selected page. |
| PROHIBITED DEPENDENCIES | Browser-side population evaluation, Shipment/source writes, Notification producers, analytics fallback, new risk score, and unbounded ORM materialization. |

## 4. Scalable API/window contract

Request parameters:

```text
page_size = integer, default 25, range 1..100
cursor    = opaque signed continuation, optional
attention = urgent | follow_up | review, optional
search    = normalized server-side text, optional, maximum 100 characters
```

Additive response metadata:

```json
{
  "data": {
    "evaluatedAt": "instant",
    "state": "complete",
    "summary": {
      "total": 250,
      "attentionCounts": {"urgent": 20, "followUp": 180, "review": 50}
    },
    "page": {
      "limit": 25,
      "offset": 0,
      "returned": 25,
      "hasMore": true,
      "nextCursor": "opaque"
    },
    "items": []
  }
}
```

`summary.total` is the complete authorized/search-matching displayed population after the optional attention filter. `attentionCounts` is computed over the complete authorized/search-matching attention population before the optional attention filter, so filter controls remain truthful. Neither value is derived from `items.length`.

The cursor is valid only for the encoded normalized request contract and current signing key. Malformed or mismatched cursors return the existing stable `400 INVALID_CURSOR`. Source/invariant failures return `503 EVALUATION_UNAVAILABLE` with zero items and no misleading metadata.

## 5. Query and ordering design

The database query is layered:

1. `authorized_population`: active Shipment rows under current tenant/actor/responsibility policy, with certified owner/request lineage.
2. `searched_population`: optional case-insensitive match over allowed fields, still inside the authorized population.
3. `attention_reason_index`: normalized rows for existing delay, exception, recognized work, readiness, and verified OIP promotion facts.
4. `shipment_attention_rank`: one row per Shipment with the existing D1 rank tuple.
5. aggregate queries: complete matching total and attention counts.
6. ordered window query: deterministic order and bounded offset/limit.
7. selected-page hydration: existing reason translation, route, request intent, tracking, and owner facts in bounded batches.

Static ordering is exactly:

```text
attention_rank ASC,
due_bucket ASC,
due_at ASC NULLS LAST,
onset_at ASC NULLS LAST,
shipment_public_id ASC
```

The public Shipment identity is the final authoritative tie-breaker. The detail evaluator rechecks each selected page against current source/authority facts before disclosure; disagreement or an unsupported source invariant fails the page closed.

## 6. Global versus row-local semantics

| Signal | Classification | Strategy |
| --- | --- | --- |
| Authorized/search-matching attention total | Population-global | SQL aggregate over complete governed reason query. |
| Urgent/follow-up/review counts | Population-global | SQL conditional aggregate before selected attention filter. |
| Attention level and rank tuple | Row-local inputs, population-global ordering | SQL reason normalization plus per-Shipment rank. |
| Reason titles/explanations/times | Row-local | Existing D1 translator over selected page only. |
| Route/request transport/tracking/owner | Row-local | Bounded batched page hydration. |
| Current page range/has-more | Window-local | Explicit page metadata; never presented as global truth. |

## 7. Authorization and negative disclosure

- Actor identity, active state, canonical persona, exactly one active membership, active Organization, and `operational_shipment.read` are resolved from persistence.
- Platform Admin remains denied. Organization Admin is tenant-wide only under the existing explicit capability. Expert scope remains the existing Control Tower responsibility scope; same-organization membership alone grants nothing.
- Foreign rows cannot affect result rows, totals, attention counts, search matches, page fullness, cursor state, or error differentiation.
- Guessed owner/search values are predicates inside authorized scope, never alternate scope selectors.
- Authority and selected page responsibility are revalidated immediately before serialization. No authorization cache is introduced.

## 8. Performance and schema decision

```text
CONTROL_TOWER_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
```

The existing source indexes cover tenant/Shipment active delay/exception reads, the operational work queue, milestone sequence, MDPM readiness requirements/associations/assessments/overrides, and responsibility relationships. Qualification must verify this decision with PostgreSQL 18 `EXPLAIN (ANALYZE, BUFFERS)` on realistic data. If evidence disproves it, Build stops and the decision is revised through the required additive-index migration gate; a speculative index is not added.

The release contract is bounded, not infinite: SQL work grows with indexed authorized/source facts while application hydration and response size grow only with page size. Deep offset traversal may cost more than early pages but never materializes the full population in Python. Remaining limits and measured costs are recorded in evidence.

## 9. Frontend and browser contract

- The existing Golden route, shell, navigation, Shipment Detail destination, card language, Dual Calendar rendering, request intent/actual route distinction, owner, loading, empty, and error states remain.
- D2 adds a server-backed search input, complete match count, truthful displayed range, next/previous navigation, and per-attention counts.
- Changing search or attention resets the cursor/history to the first page.
- A monotonically increasing request generation prevents an older response from replacing newer search/filter/page state. Any failure clears items and metadata.
- Desktop and mobile Persian/RTL controls remain keyboard-usable and do not expose technical evaluation wording.

## 10. Compatibility, recovery, and reference impact

- Existing item fields and error codes are preserved. `summary` and expanded `page` are additive.
- Existing clients that send only `page_size`, `attention`, and `cursor` remain valid. D2 is upgraded in the same candidate.
- The previous `population > 100` failure is removed; genuine scope, source, invariant, or composition failure remains fail-closed.
- No migration, business-state write, backfill, deployment, or Production rollback path is introduced. Recovery is source rollback to the prior fail-closed implementation.

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
```

Rationale: PDR-019 and D1/D2 evidence intentionally preserved the 100-row, no-total architecture. ADR-051 and the decision indexes must authoritatively record the replacement read contract before runtime Build.

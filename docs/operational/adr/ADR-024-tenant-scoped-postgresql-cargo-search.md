# ADR-024: Tenant-Scoped PostgreSQL Cargo Search

- **Status:** Proposed
- **Date:** 2026-08-01
- **Blocking:** SLICE-B6
- **Evidence:** [Discovery and Domain Analysis Report](../discovery-cargo-data-and-scroll-analysis-20260801.md)

## Context

Authenticated customers need cross-Project cargo search inside their organization. Search can leak the existence or sensitive attributes of other tenants if authorization is applied after text matching or only in the UI. Current scale does not justify another search system without evidence.

## Proposed decision

Use PostgreSQL exact matching plus `pg_trgm` candidate matching for the first phase. Resolve authenticated principal, organization membership, resource scope, and field visibility first; tenant predicates are mandatory in the search query before text matching/ranking. Exact canonical code and approved alias matches rank ahead of normalized name/part-number trigram matches. Results are bounded, paginated, deterministic, and use opaque public identifiers.

Search consumes organization-owned catalog/aliases and ShipmentCargoItem snapshots but returns a dedicated customer allowlist. It includes only authorized Projects/shipments and customer-visible events. Internal notes are excluded; declared value, HS/sensitive codes, and similar fields require explicit permission. Logs, caches, metrics, exports, suggestions, counts, errors, and AI context must not disclose forbidden matches. Rate limits and abuse monitoring apply. An external search engine is deferred until measured data volume, latency, language/relevance, or operational evidence requires a superseding ADR.

## Security, data, and operations

Backend policy is deny-by-default and tenant-first; client organization IDs are never sufficient authority. Indexes begin with organization/selective scope where practical, and query plans are measured for worst-case terms. Normalized searchable text is derived reproducibly with provenance. Persian/English normalization rules require Data review and must preserve exact-code semantics.

## Consequences and alternatives

PostgreSQL minimizes infrastructure and transactional lag while requiring careful indexes, query bounds, and relevance testing. Rejected: anonymous/global search, post-filtered authorization, sequential IDs, unrestricted wildcard queries, and immediate external engine adoption.

## Migration, rollback, and acceptance

Indexes and search projections are additive; legacy rows are searchable only through authorized legacy fields explicitly approved for exposure. Rollback disables endpoint/UI and drops no source data. Acceptance requires PDR-013-D05/D06/D10/D11, Security threat model and negative tenant tests, Data normalization/relevance policy, query-plan/load evidence, rate-limit/runbook, and customer UX acceptance.

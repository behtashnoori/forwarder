# Forwarder 1.9.1 release notes

Forwarder 1.9.1 is an acceptance-correction release for the unified
`OperationalShipment` architecture. It preserves one execution aggregate while
making its origin explicit as either `accepted_quote` or `direct`.

## Delivered scope

- Direct operation creation uses a canonical customer, optional Project, and
  canonical origin/destination locations without manufacturing commercial
  request or quote lineage.
- Accepted-quote operation creation preserves request and accepted-quote
  lineage and validates the canonical customer and location relationships.
- Selector APIs provide organization-scoped customers, Projects, accepted
  quotes, and canonical locations for operation creation.
- The Operations UI supports both creation paths and source-aware list/detail
  behavior, including deep links and visible release identity.
- Existing lifecycle, multi-leg routing, MDPM, shipment economics/FX, and OIP
  behavior remains compatible with the unified shipment identity. Request-
  scoped documents and MDPM requirements apply to accepted-quote operations;
  they are explicitly not applicable to direct operations in this release.
- Release identity reports application, frontend, backend, tag, commit, and
  database revision consistently. Mismatch and unavailable states fail visibly
  instead of presenting a false match.

## Migration and recovery

The required Alembic migration is
`20260819_v191_acceptance_corrections`, applied from the v1.9.0 Production
baseline `20260818_immutable_fx_provenance` only during a separately authorized
cutover. Before migration, take coordinated PostgreSQL and private document-
storage backups and verify restore readiness. Because the migration takes
strong locks, maintain approved write quiescence for the migration window.

Forward recovery is preferred. Downgrade is conditional and fails closed when
direct operations or new canonical international-location facts would be lost;
in that case restore the coordinated pre-migration backups as one consistency
boundary. Application rollback alone does not imply database downgrade.

## Known non-blocking warnings

- Legacy backend code emits deprecation warnings, principally for naive UTC
  datetime usage.
- ESLint reports accepted warnings outside this patch's blocking gate.
- Browserslist metadata is stale.
- The production frontend build reports a large JavaScript chunk advisory.

These warnings do not disable release gates, but remain bounded maintenance
work. This release does not add shipment-scoped DMS support for direct
operations and does not authorize deployment, migration, seeding, or Production
access.

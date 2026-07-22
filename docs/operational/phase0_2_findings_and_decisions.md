# Phase 0.2 findings and decisions

## Decisions

- Use a native PostgreSQL 18 temporary cluster because Docker/Podman are unavailable.
- Isolate it from the installed Windows PostgreSQL service by using a new data directory, loopback binding, and high port.
- Treat `20260728_add_quote_customer_response` as the sole official head.
- Classify the required head/previous/head cycle as `PASS_WITH_IRREVERSIBLE_MIGRATION_NOTE`; do not claim full-chain reversibility.
- Do not create speculative migrations for production-only duplicate constraints.

## Findings

1. Fresh upgrade succeeds and leaves one Alembic version row at the expected head.
2. Head downgrade/re-upgrade succeeds and restores an identical catalog fingerprint.
3. Synthetic pre-head data is preserved.
4. Each requested Iran entry column has exactly one FK in a fresh schema.
5. A semantic scan finds 11 repeated FK shapes outside that focused pair. Their intent and production state require separate evidence before remediation.
6. `alembic check` reports broad historical ORM/migration drift. This gate records it rather than generating a destructive catch-all migration.
7. The head downgrade drops customer-response values if they exist. The tracking-reference seed downgrade is a no-op. These are irreversible-data notes.
8. Concurrent read checks are safe. Two simultaneous upgrades are not advisory-lock serialized: one succeeds and one fails explicitly; final schema and version state remain correct.

## Deferred work

- Reconcile ORM metadata and migration history in a dedicated, reviewed effort.
- Classify repeated FK shapes against an authorized non-production copy before any production migration is designed.
- Consider a PostgreSQL advisory lock around explicit upgrades if operators require both concurrent invocations to serialize successfully.
- Repair the known full-chain expert-quote downgrade ordering before treating base downgrade as supported.

No deferred item authorizes production access, migration, credential use, deployment, history rewrite, or Phase 1 implementation.

## Cleanup confirmation

The disposable database and cluster-owned role were removed with the isolated cluster. The cluster was stopped, its verified temporary directory and temporary state/log artifacts were deleted, and no PostgreSQL process remained for that directory. The installed PostgreSQL service remained running and was not restarted or reconfigured.

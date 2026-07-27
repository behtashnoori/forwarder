# Phase 1B Local Database Mapping Contract

Mapping is derived before transfer from the live source and fresh active-head
target metadata. The source is read-only. Every populated source table receives
one explicit classification in `mapping-contract.json`.

| Classification | Rule |
|---|---|
| `DIRECT_COPY` | Same-name target exists and every required target column is sourced or has a target default |
| `TARGET_BASELINE_PRESERVE` | `alembic_version` remains the fresh active-head value |
| `TARGET_BASELINE_RECONCILE` | Migration/system reference baseline remains authoritative |
| `EXCLUDE_SECURITY_SENSITIVE` | OTP, session, token, reset, challenge, API-key, or secret data is not transferred |
| `SOURCE_ONLY_REVIEW` | No active-head target table; populated instances block |
| `MANUAL_DECISION_REQUIRED` | Column compatibility cannot be proven; populated instances block |

UUID and numeric identifiers are preserved by direct copy. Schema metadata
alone is not accepted as proof of password algorithm compatibility, so password
hash columns are excluded; a required hash without a target reset/default path
blocks the run. A collision, missing required value, source-only
business table, or FK cycle is not guessed or silently transformed: it blocks
the run. `alembic_version` is never copied. Fresh `country`,
`referral_auto_assign_state`, and `tracking_location_reference` rows are not
overwritten.

The engine loads parents before children using the target FK graph, uses bounded
batches and one target transaction, and rolls the target back on any error.
Evidence records only per-table classifications and aggregate counts.
Reconciliation requires zero rejected rows, orphan FKs, constraint violations,
and unexplained variance.

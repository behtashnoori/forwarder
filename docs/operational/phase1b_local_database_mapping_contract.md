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
| `ID_REMAP_REQUIRED` | A proven successor table is populated and old-to-new identifiers are retained for dependent FKs |
| `ARCHIVE_ONLY` | Rows cannot satisfy the active-head semantic contract; they remain in the retained legacy database and verified backup and are explained in reconciliation |

UUID and numeric identifiers are preserved by direct copy. Schema metadata
alone is not accepted as proof of password algorithm compatibility; the
application's producer/verifier and a synthetic verifier check must also pass.
A required hash without that proof or a target reset/default path blocks the
run. A collision, missing required value, source-only
business table, or FK cycle is not guessed or silently transformed: it blocks
the run. `alembic_version` is never copied. Fresh `country`,
`referral_auto_assign_state`, and `tracking_location_reference` rows are not
overwritten.

The legacy `tenants` contract maps to `operational_organization`: `slug`
deterministically supplies `public_id`, `active` maps to `is_active`, and an ID
map feeds `memberships`. Legacy memberships map to
`operational_membership`; organization IDs are remapped, user IDs are
preserved, status maps to `is_active`, and the closed legacy role set maps to
the target permissions array. Unknown roles fail closed.

Legacy `audit_logs` are `ARCHIVE_ONLY`. They do not contain the target's
required entity type/id and their nullable actor cannot satisfy the required
target actor. All three rows therefore remain in the retained legacy database
and verified backup; reconciliation records three explained exclusions and
zero unexplained variance. Metadata or row payload is never printed.

`expert_user` is copied with its password hash. This is supported by the same
bcrypt producer and verifier in the legacy and active-head authentication flow,
the same `$2` hash family and a target 128-character column. A synthetic bcrypt
hash is generated and verified during mapping analysis; no real hash is
recorded in evidence. If that proof fails, the populated table remains blocked.

Countries reconcile by normalized ISO `code`. The fresh target baseline row is
preserved, its matching source ID maps to it, and only missing codes are
inserted. `alembic_version` is never sourced and must remain
`20260801_route_exception`.

The engine loads parents before children using the target FK graph, uses bounded
batches and one target transaction, and rolls the target back on any error.
Evidence records only per-table classifications and aggregate counts.
Reconciliation requires zero rejected rows, orphan FKs, constraint violations,
and unexplained variance.

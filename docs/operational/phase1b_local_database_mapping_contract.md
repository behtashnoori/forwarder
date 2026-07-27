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

Legacy `customer_tenant_links` are also `ARCHIVE_ONLY`. Static model and
migration inspection proves that Active Head has no tenant-to-customer
relation. `customer_gamification` is a separate global identity with no
organization FK, while `crm_customer_link_audit` records shipment link changes
and is not a replacement for tenant loyalty points/status. Transforming these
rows would therefore invent scope or overwrite customer state. Every source
row remains in the retained legacy database and backup and is counted as an
explained exclusion.

Legacy `export_jobs` are `ARCHIVE_ONLY`. Their progress, completion/error state,
and optional file path describe a transient export job; Active Head has no
export queue/model or durable semantic target. Counts, but never file paths,
errors, or job payloads, are recorded in reconciliation.

Legacy `tenant_owner` maps to `operational_membership.permissions`, not to an
invented Active Head role or the unrelated `expert_user.role`. Its permission
set is the closed set of operational capabilities currently enforced by the
services (shipment, route plan/leg, checkpoint, milestone, work item, and route
exception operations). It does not receive the legacy generic `admin`
permission. Unknown legacy roles remain fail-closed.

`expert_user` is copied with its password hash. This is supported by the same
bcrypt producer and verifier in the legacy and active-head authentication flow,
the same `$2` hash family and a target 128-character column. A synthetic bcrypt
hash is generated and verified during mapping analysis; no real hash is
recorded in evidence. If that proof fails, the populated table remains blocked.

Countries reconcile by normalized ISO `code`. The fresh target baseline row is
preserved, its matching source ID maps to it, and only missing codes are
inserted. `alembic_version` is never sourced and must remain
`20260801_route_exception`.

Schema mapping and runtime mapping validation are mode-independent. Before
DryRun can return, and before Rehearsal can write, the engine validates
populated source-only policy, archive policy, target mapping availability,
distinct role support, and membership tenant/user referential completeness.
Only role names and their target permission names are included in evidence;
no user identity or row payload is emitted.

The engine loads parents before children using the target FK graph, uses bounded
batches and one target transaction, and rolls the target back on any error.
Evidence records only per-table classifications and aggregate counts.
Reconciliation requires zero rejected rows, orphan FKs, constraint violations,
and unexplained variance.

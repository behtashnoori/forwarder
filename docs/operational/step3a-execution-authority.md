# Step 3A execution authority and qualification

Route-owned departure/arrival reports project physical actuals immediately.
Checkpoint reports do the same through their existing processing/dependency
commands. Verification INSERTs a decision with `related_event_id`; corrections
INSERT a replacement with `supersedes_event_id`. Original events remain immutable.
Competing roots and malformed/stale correction chains fail for reconciliation.

The shared boundary is `occurrence_projection_service`. Supporting tracking,
ExecutionUnit, OIP and document data do not supply physical route occurrence.
Project configuration milestone transitions retain their existing purpose.

## Operator upgrade

Use the existing `python -m backend.migration_cli upgrade head --confirm` after
the normal backup/maintenance review. No application startup or request runs the
bridge. Keep runtime and migration credentials separate; no privileges are granted.

When the historical backfill is pending, the CLI first upgrades to
`security_credential_remediation`, then takes an exclusive event-table lock.
For populated events only, it temporarily allows null identity/organization fields
to receive the historical metadata backfill. All other payload fields must match;
DELETE is always rejected. The historical migration and trigger restoration use
one database transaction and one Alembic connection. Failure rolls both back.
The CLI then continues to the new head. Never stamp past the failing revision.

Direct Alembic callers bypass the operator bridge and must not upgrade populated
pre-backfill databases. They should use the explicit migration CLI.

## PostgreSQL release qualification

Local unit/SQLite results do not qualify PostgreSQL. Set `STEP3A_POSTGRES_URL` to
an operator-prepared disposable database and run the script separately for:

* `empty`: a truly empty database, proving full fresh installation and replay.
* `populated`: predecessor revision with representative historical event fixtures.
* `rollback`: a separate populated predecessor fixture; injects failure after backfill.
* `already`: a current-head database containing historical occurrence fixtures.

Command: `python scripts/qualify_step3a_postgres.py SCENARIO --confirm-disposable`.
The script never deletes databases or stamps revisions. Populated fixtures must
include a valid effective occurrence; scenario preconditions fail closed. It checks
payload preservation, verification/correction INSERTs, mutation rejection, and
upgrade replay. Supplement with the existing PostgreSQL concurrency suites.

POSTGRES_RUNTIME_VALIDATION=REQUIRED_AT_RELEASE_QUALIFICATION

History pagination, complete revision-aware read models, and comprehensive replan
history presentation remain Step 3B. No Shipment Summary redesign is included.

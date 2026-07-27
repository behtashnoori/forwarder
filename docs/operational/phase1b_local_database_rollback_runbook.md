# Phase 1B Local Database Rollback Runbook

Rollback is automatic only inside the Final invocation after rename and before
post-cutover acceptance. No retry follows a failure.

1. The harness terminates only connections to the newly named local
   `forwarder_db`.
2. It renames that database to `forwarder_db_failed_<timestamp>`.
3. It renames the exact retained `forwarder_db_legacy_<timestamp>` back to
   `forwarder_db`.
4. It records aggregate rollback evidence without credentials or row payload.

The harness never drops the failed database, retained legacy database, backup,
or evidence. If the PowerShell process is interrupted between the two atomic
rename statements, do not improvise or run migrations. Inspect database names
from `postgres`, correlate the run token with `cutover-summary.json`, and apply
only the inverse rename under a local maintenance window. Server, Production,
deployment, merge, and force-push remain outside scope.

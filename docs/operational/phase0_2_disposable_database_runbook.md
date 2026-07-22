# Phase 0.2 disposable PostgreSQL runbook

## Safety boundary

Use only a newly initialized cluster under the operating-system temporary directory, bound to `127.0.0.1` on an unused high port. Never reuse the installed PostgreSQL service, production `DATABASE_URL`, `forwarder_db`, or a production role. Resource names must begin with `forwarder_phase02_test_` and `forwarder_phase02_test_role_`.

Before mutation, verify the target host is loopback, the database name has the required prefix, and PostgreSQL `data_directory` resolves to the newly created temporary directory. Keep any temporary password only in process environment or a protected temporary password file; do not print a full DSN.

## Repeatable sequence

1. Locate `initdb`, `pg_ctl`, `createdb`, `dropdb`, and `psql` from the local PostgreSQL installation.
2. Create a unique temporary directory and initialize a new cluster.
3. Start it on loopback and an unused high port; do not restart or reconfigure the installed service.
4. Create a unique temporary role and owned database.
5. Export a process-only `DATABASE_URL` and run:

   ```text
   python -m backend.migration_cli current
   python -m backend.migration_cli check
   python -m backend.migration_cli upgrade --confirm
   python -m backend.migration_cli current
   python -m backend.migration_cli check
   ```

6. Run the PostgreSQL gate tests with the same sanitized target through `FORWARDER_PHASE02_POSTGRES_URL`.
7. Perform head-to-previous downgrade with Alembic, insert only synthetic non-sensitive data, re-upgrade, and compare catalog fingerprints.
8. Run targeted/full backend tests plus frontend lint/build and the secret scanner.

## Cleanup

Terminate only sessions connected to the exact temporary database, drop that exact database and role, stop the exact temporary cluster, then resolve and verify that its directory is under the OS temporary directory with the expected prefix before deletion. Remove password files, logs, state files, and test sentinels. Confirm the installed PostgreSQL service state is unchanged and no process remains for the temporary data directory.

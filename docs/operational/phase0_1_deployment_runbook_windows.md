# Phase 0.1 Windows Deployment Runbook

This runbook is for PowerShell 5.1 and the version-controlled entrypoint. It does not authorize a Production deployment by itself.

## 1. Preflight

1. Open PowerShell in the repository root and verify the approved branch and commit with `git status --short --branch` and `git rev-parse HEAD`.
2. Confirm `.venv\Scripts\python.exe` exists and dependencies, including Waitress, are installed.
3. Confirm `DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY` are supplied through protected process configuration; do not print them.
4. Confirm a tested backup and restoration owner exist before any explicit migration.
5. Run `.\.venv\Scripts\python.exe -m backend.migration_cli current` and then `check`. Exit 2 means pending and is a NO-GO until the approved migration step finishes.
6. Run `powershell -File scripts\backend-service.ps1 -Action Status -Port 5001`.

## 2. Ownership safety

`scripts/backend-service.ps1` accepts a listener only when all checks agree:

- exactly one process owns port 5001;
- `ExecutablePath` equals this repository's `.venv\Scripts\python.exe`;
- `CommandLine` contains `backend.wsgi:app`.

Ambiguous or foreign ownership is a hard refusal. The script uses `$processId`/process properties, never the reserved `$PID` variable.

## 3. Start, status, stop, and restart

```powershell
powershell -ExecutionPolicy Bypass -File scripts\backend-service.ps1 -Action Start -Port 5001 -TimeoutSeconds 60
powershell -ExecutionPolicy Bypass -File scripts\backend-service.ps1 -Action Status -Port 5001
powershell -ExecutionPolicy Bypass -File scripts\backend-service.ps1 -Action Stop -Port 5001
powershell -ExecutionPolicy Bypass -File scripts\backend-service.ps1 -Action Restart -Port 5001 -TimeoutSeconds 60
```

Start uses Waitress with `backend.wsgi:app`, hidden window mode, repository working directory, and separate stdout/stderr files. On failure it prints the final log lines and stops only the process created by that start attempt.

## 4. Verification

The launcher polls in order:

1. `http://127.0.0.1:5001/api/health/ping` — liveness;
2. `http://127.0.0.1:5001/api/health/ready` — database, revision and critical tables.

Operators may separately check `/api/health` for DB connectivity. Pending migration, unavailable DB, or missing critical tables returns 503 or blocks Production startup.

Logs:

- `instance\logs\backend.stdout.log`
- `instance\logs\backend.stderr.log`

## 5. Failure and rollback

If entrypoint, `.venv`, ownership, liveness, or readiness fails, do not stop an unverified process and do not rerun migrations blindly. Capture commit, exit code, sanitized health output and logs. Restore the previously approved application artifact and start it with the same ownership checks. Database downgrade requires separate approval, a verified backup, and a successful disposable PostgreSQL rehearsal; application rollback does not imply database downgrade.

## Related documents

- [Backend entrypoint](phase0_1_backend_entrypoint.md)
- [Database revision runbook](phase0_1_database_revision_runbook.md)
- [Runtime migration safety](phase0_1_runtime_migration_safety.md)

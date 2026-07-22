# Phase 0.1 Backend Entrypoint

## Decision

The only version-controlled WSGI entrypoint is `backend.wsgi:app`. A root-level `wsgi.py` is neither tracked nor required. Importing the entrypoint constructs the runtime app, performs read-only readiness, and never migrates or seeds.

## Commands

| Context | Command |
|---|---|
| Development | `python -m backend.run` |
| Development with explicit reload | `python -m backend.run --reload` |
| Windows production | `python -m waitress --listen=0.0.0.0:5001 backend.wsgi:app` |
| Linux/container production | `gunicorn -w 2 -b 0.0.0.0:5001 backend.wsgi:app` |

Development reload is opt-in. Container and Windows production commands do not enable debug or a reloader.

## Host and port policy

`HOST` defaults to `0.0.0.0`; `PORT` defaults to `5001`. Environment configuration may override them for development, but deployed commands, Compose health checks, and the Windows launcher use 5001 unless the operator supplies one reviewed override consistently. The development runner refuses an occupied configured port; it does not silently select another port.

## Environment and logging

`DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY` are required by production validation. `AUTO_MIGRATE_ON_STARTUP` must remain false. Do not pass secrets on the command line. The Windows launcher writes separate `instance/logs/backend.stdout.log` and `backend.stderr.log`; containers use stdout/stderr.

## Deployment alignment

Both Dockerfiles copy the repository layout and run `backend.wsgi:app` on 5001. Development and production Compose files use the root build context with `backend/Dockerfile`; readiness is `/api/health/ready`. `package.json` invokes `scripts/run-backend.js`, which starts `python -m backend.run` from repository root.

## Failure modes

- Missing entrypoint or `.venv`: stop before process start.
- Occupied port: inspect ownership; never stop an unrelated process.
- Pending migration or missing critical tables: Production startup/readiness fails; run `migration_cli check`, then follow the database runbook.
- Failed liveness/readiness: retain and inspect separate logs; rollback the artifact, not the database, unless a database rollback was separately approved and rehearsed.

## Related documents

- [Windows deployment runbook](phase0_1_deployment_runbook_windows.md)
- [Runtime migration safety](phase0_1_runtime_migration_safety.md)
- [ADR-012](adr/ADR-012-versioned-backend-entrypoint.md)


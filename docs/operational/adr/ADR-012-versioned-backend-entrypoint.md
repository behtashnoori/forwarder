# ADR-012: Versioned Backend Entrypoint

- Status: Accepted
- Date: 2026-07-22

## Context

Deployment commands referenced multiple scripts, ports, and implicit root-level files. An untracked or server-local entrypoint cannot be reviewed, reproduced, or rolled back safely.

## Decision

`backend.wsgi:app` is the canonical version-controlled WSGI object. Development uses `python -m backend.run`; Windows production uses Waitress; containers use Gunicorn. Default host is `0.0.0.0`, default/deployment port is 5001, and Production reload/debug is disabled.

## Alternatives considered

- Root-level `wsgi.py`: rejected because it is absent and unnecessary.
- `backend/run.py` as Production WSGI server: rejected because Flask's development server is not a Production host.
- Server-local wrapper: rejected because it is outside Git and can drift.

## Consequences

Dockerfiles, Compose, package scripts, health URLs, and Windows process controls share one import target and port contract. Dependencies include Waitress for Windows and Gunicorn for containers.

## Windows considerations

The PowerShell 5.1 launcher validates port, executable path, and command line before stop/restart. It records separate logs and waits for liveness and readiness. Ambiguous ownership is a hard failure.

## Container considerations

Both Dockerfiles use repository-root build context, bind Gunicorn to 5001, and Compose checks `/api/health/ready`. Runtime startup never performs migration.

## Risks and revisit triggers

Environment overrides can create port drift; deployment configuration and probes must change together. Revisit if the hosting platform supplies a different standard port or process manager, while preserving `backend.wsgi:app` and no-startup-migration guarantees.

## Related documents

- [Backend entrypoint](../phase0_1_backend_entrypoint.md)
- [Windows deployment runbook](../phase0_1_deployment_runbook_windows.md)


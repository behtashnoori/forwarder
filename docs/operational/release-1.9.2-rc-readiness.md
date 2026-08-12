# Forwarder 1.9.2 release-candidate readiness

## Identity

- Current release target/version: `v1.9.2` / `1.9.2`
- Previous immutable public release: `v1.9.1` at `05414d7d5b17153c3f1efcb5beff0adf7a600af6`
- Expected publication artifact: `Forwarder-v1.9.2-<release-commit-short-sha>.zip`
- Database baseline/head: `20260819_v191_acceptance_corrections` -> `20260824_mt1_graph`

The patch version is required because 1.9.1 is already immutable and the current
branch adds five compatible MT-1 migrations and enforcement changes after that
release. Historical 1.9.1 evidence and artifacts are not reopened.

## Remaining requirement classification

| Requirement | Classification | Release treatment |
| --- | --- | --- |
| MT-1 implementation, local certification, and server certification | COMPLETE | Final records bind the certified snapshot and server hashes. |
| Version/package metadata and active runbooks | COMPLETE | Advanced to 1.9.2 and sole head. |
| Backend regression, architecture tests, compile, JSON, diff, security scans | REQUIRED_BEFORE_RC | Must pass on release source. |
| Frontend install/lock verification, typecheck, lint, tests, production build | REQUIRED_BEFORE_RC | Build warnings alone are non-blocking. |
| Exactly one migration head and contiguous five-revision upgrade path | REQUIRED_BEFORE_RC | No contract/destructive phase is permitted. |
| Archive, manifest, SHA-256, extracted content/secret audit | REQUIRED_BEFORE_RC | Generated only from clean tracked tagged source. |
| Production backup and verified coordinated database/document restore point | REQUIRED_BEFORE_DEPLOY | Must precede migration. |
| Confirm actual deployed revision/runtime/configuration | REQUIRED_BEFORE_DEPLOY | Stop if baseline is not the manifest baseline. |
| Stop writers, migrate, switch IIS/task paths, health/smoke | REQUIRED_BEFORE_DEPLOY | Requires separate server/change authority. |
| Browser/UAT against the deployed candidate | REQUIRED_AFTER_DEPLOY | Local synthetic browser evidence exists; deployed-environment acceptance is external. |
| Final publication acceptance/evidence sign-off | REQUIRED_AFTER_DEPLOY | No external publication is performed in this run. |
| Synthetic legacy cleanup/backfill/Organization assignment | NOT_APPLICABLE | Dataset remains quarantined; these actions are prohibited. |
| Destructive ownership contract phase | NOT_APPLICABLE | Not part of 1.9.2. |
| Redis setup | NOT_APPLICABLE | No release runtime dependency is declared. |
| Historical lint/deprecation and frontend chunk advisories | OPTIONAL | Bounded maintenance; not a build blocker. |
| MT-2 through MT-12 multi-company productization | BLOCKED_EXTERNAL | Separate master-plan milestones; second-company onboarding remains prohibited. |

## Production configuration preflight

- Match the certified/supported Python runtime (3.13 for this RC) and install the exact `requirements.txt`; verify `psycopg2-binary==2.9.11`.
- Require PostgreSQL 18 or separately certify the actual server version. Verify connectivity through protected configuration without displaying credentials.
- Preserve server-managed database, JWT/session, administrator bootstrap, mail/integration, storage/document-root, allowed-host/CORS, proxy, logging, and monitoring settings. The package contains no `.env` or secret values.
- Verify private document paths exist, are backed up, and are writable only by the service identity.
- Serve frontend and API same-origin. IIS must route `/api` before SPA fallback, trust forwarded host/protocol only from configured proxies, and apply the packaged cache policy.
- Ensure the backend Scheduled Task/service uses the immutable release WorkingDirectory, release-local virtual environment, explicit repository path, and correct `PYTHONPATH`.
- Confirm health/readiness endpoints, storage capacity, database locks/connections, backup custody, write quiescence, and rollback decision authority before migration.

## Migration audit

Alembic has exactly one head. The upgrade path from the previous release is
contiguous and additive across revisions 20260820 through 20260824. The final
graph downgrade/re-upgrade boundary was certified locally and on the authorized
disposable server clone. Production rollback remains forward-fix or coordinated
backup restore; no blind downgrade or contract-phase cleanup is authorized.

Exact deployment migration command:
`python -m backend.migration_cli upgrade 20260824_mt1_graph --confirm`


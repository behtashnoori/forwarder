# Forwarder Deployment Runbook

Status: certified in disposable PostgreSQL 18 against repair commit `61b68c0a0a8f2310ee19b2934f8c985dfea4a7b2`; incorporated without product/runtime changes into final certified Release Candidate `85fbd78b46a544367ab40144fdf8d51d422f8dcc`.

This runbook requires separate deployment authorization. It does not authorize production access, deployment, tagging, or release.

## 1. Prerequisites

- Authorized production-deployable source commit: `85fbd78b46a544367ab40144fdf8d51d422f8dcc`.
- Python 3.13-compatible environment with `requirements.txt` installed.
- Release tooling from `requirements-release.txt`.
- Node.js 24-compatible environment and npm 11-compatible package manager.
- PostgreSQL 18-compatible server and PostgreSQL client tools (`psql`, `pg_dump`, `pg_restore`).
- A private, writable document storage directory.
- A maintenance/traffic decision approved by the deployment owner.
- A tested application-artifact retention path for application rollback.

Verify source and repository migration state:

```powershell
git rev-parse HEAD
.\.venv\Scripts\python.exe -c "from alembic.config import Config; from alembic.script import ScriptDirectory; c=Config('backend/migrations/alembic.ini'); print(','.join(ScriptDirectory.from_config(c).get_heads()))"
```

Expected values are the authorized commit above and `20260903_external_operational_references`.

## 2. Deployment-time configuration checklist

Provide values through the approved secret/configuration system. Never place values in source control or command transcripts.

| Variable | Requirement |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_URL` | Required PostgreSQL URL; reviewed target; not a replica |
| `SECRET_KEY` | Required deployment-specific secret |
| `JWT_SECRET_KEY` | Required deployment-specific secret |
| `CORS_ORIGINS` | Required exact HTTPS origins; no wildcard/local placeholder |
| `CORS_ALLOW_ALL_ORIGINS` | `false` |
| `VITE_API_URL` | Correct deployed API origin/base path |
| `DOCUMENT_STORAGE_ROOT` | Private persistent storage path with backup policy |
| `HOST` / `PORT` | Environment-specific bind configuration |
| `FLASK_DEBUG` | `false` |
| `FLASK_USE_RELOAD` | `false` |
| `AUTO_MIGRATE_ON_STARTUP` | `false` or absent |

Trusted-host, HTTPS termination, proxy forwarding, secure-cookie, public hostname, certificate, DNS, and IIS/nginx configuration are `DEPLOYMENT_TIME_CHECK` items because the repository does not establish the production topology.

## 3. Build and pre-deployment gates

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-release.txt
npm ci
npm run test:frontend
npm run lint
npx tsc -b
npm run build
.\.venv\Scripts\python.exe -m pytest -q backend/tests
.\.venv\Scripts\python.exe -m compileall -q backend scripts
.\.venv\Scripts\python.exe scripts/check_architecture_governance.py
.\.venv\Scripts\python.exe scripts/scan_repository_secrets.py current
git diff --check
```

Stop on any nonzero exit. Do not run dependency upgrades during deployment.

## 4. Database connectivity and preflight

Load the approved environment without echoing secret values, then run:

```powershell
.\.venv\Scripts\python.exe -m backend.migration_cli current
.\.venv\Scripts\python.exe -m backend.migration_cli check
```

Confirm the sanitized database target, PostgreSQL primary status, available storage, active connections, maintenance decision, and backup destination.

## 5. Backup and verification

Use placeholders supplied by the deployment owner:

```powershell
$env:PGPASSWORD = '<APPROVED_DATABASE_PASSWORD>'
pg_dump -Fc -h '<DB_HOST>' -p '<DB_PORT>' -U '<DB_USER>' -d '<DB_NAME>' -f '<BACKUP_PATH>\forwarder-predeploy.dump'
pg_restore --list '<BACKUP_PATH>\forwarder-predeploy.dump'
```

Record UTC timestamp, PostgreSQL version, database identity, byte size, SHA-256, return codes, and retention location. A successful `pg_dump` without `pg_restore --list` verification is not sufficient.

## 6. Migration and application deployment

1. Apply the approved maintenance/traffic decision.
2. Retain the currently deployed application artifact and configuration reference.
3. Run the explicit migration—startup must never migrate:

```powershell
.\.venv\Scripts\python.exe -m backend.migration_cli upgrade --confirm
.\.venv\Scripts\python.exe -m backend.migration_cli check
```

4. Deploy the previously built `dist` frontend artifact using the approved static-hosting mechanism.
5. Start the backend using the repository-supported WSGI application for the approved platform. Docker environments may use the repository Docker configuration; Windows service/IIS and nginx details remain environment-specific.
6. Do not enable development reload or debug mode.

## 7. Health and smoke verification

```text
GET /api/health
GET /api/health/ready
```

Both must return HTTP 200. Then use authorized non-production-safe/operator accounts to verify:

- authentication and tenant context;
- request list and opaque request detail;
- project and operational shipment detail;
- cargo, ExecutionUnit and tracking projection;
- LogisticsPoint, documents and external references;
- RFC 3339 UTC timestamps with `Z` or explicit offset;
- cross-tenant access returns 403/404;
- no unexpected HTTP 500 responses.

Compare post-deployment row counts, public identities, tracking codes, ownership, document associations, external references and critical relationships with the pre-deployment manifest.

## 8. Success and escalation

Deployment succeeds only when migration is current, readiness is 200, smoke and integrity checks pass, logs contain no release-blocking errors, and rollback assets remain available.

Stop and invoke `FORWARDER-ROLLBACK-RUNBOOK.md` for migration failure, readiness failure, unexplained data mutation, authorization/tenant regression, repeated HTTP 500s, or unacceptable operational degradation. Escalate to the release owner, database owner and application owner; do not improvise schema changes.

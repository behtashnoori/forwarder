# Forwarder Production Topology and Configuration Checklist

Status: pre-H1 operator input contract for final certified Release Candidate `85fbd78b46a544367ab40144fdf8d51d422f8dcc`.

This checklist records sanitized identifiers only. It does not authorize or perform Production access. Values must be supplied or confirmed by the operator; historical plans and local environment values are not Production evidence.

## Production topology

| Item | Status | Sanitized value |
| --- | --- | --- |
| Production server/host | OPERATOR_INPUT_REQUIRED | — |
| Operating system | OPERATOR_INPUT_REQUIRED | — |
| Production domain | OPERATOR_INPUT_REQUIRED | — |
| Application root path | OPERATOR_INPUT_REQUIRED | — |
| Frontend/static path | OPERATOR_INPUT_REQUIRED | — |
| Backend path | OPERATOR_INPUT_REQUIRED | — |
| Backend service/process | OPERATOR_INPUT_REQUIRED | — |
| Reverse proxy | OPERATOR_INPUT_REQUIRED | — |
| IIS site/application pool, if applicable | OPERATOR_INPUT_REQUIRED | — |
| PostgreSQL host | OPERATOR_INPUT_REQUIRED | — |
| PostgreSQL port | OPERATOR_INPUT_REQUIRED | — |
| PostgreSQL database name | OPERATOR_INPUT_REQUIRED | — |
| Expected application database role | OPERATOR_INPUT_REQUIRED | — |
| Persistent document-storage path | OPERATOR_INPUT_REQUIRED | — |
| Application log destination | OPERATOR_INPUT_REQUIRED | — |
| Reverse-proxy log destination | OPERATOR_INPUT_REQUIRED | — |
| Durable backup destination | OPERATOR_INPUT_REQUIRED | — |
| Deployment account | OPERATOR_INPUT_REQUIRED | — |
| Maintenance-window decision | OPERATOR_INPUT_REQUIRED | — |
| Rollback operator/authority | OPERATOR_INPUT_REQUIRED | — |

## Deployment configuration

Verify presence and policy compliance through the approved Production configuration system after H1 authorization. Never record secret values here.

| Setting | Required? | Expected Production rule | H1/H2 verification | Secret? | Deployment-time check? |
| --- | --- | --- | --- | --- | --- |
| `DATABASE_URL` | Yes | PostgreSQL primary; exact authorized host/database/role; encrypted where applicable | Parse sanitized target and compare with confirmed topology; verify primary/read-write status at H1 | Yes | Yes |
| `SECRET_KEY` | Yes | Deployment-specific, non-placeholder value | Presence and application fail-fast validation only | Yes | Yes |
| `JWT_SECRET_KEY` | Yes | Deployment-specific, non-placeholder value | Presence and application fail-fast validation only | Yes | Yes |
| `APP_ENV` | Yes | `production` | Verify effective process environment without printing unrelated values | No | Yes |
| `FLASK_ENV` | Yes | `production`; debug and reload disabled | Verify effective process environment and startup configuration | No | Yes |
| `HOST` | Yes | Approved bind address/hostname for the confirmed process topology | Compare with service and reverse-proxy binding | No | Yes |
| `PORT` | Yes | Approved backend port | Compare with service and reverse-proxy upstream | No | Yes |
| `CORS_ORIGINS` | Yes | Exact approved HTTPS origins; no wildcard, localhost, or placeholder | Compare sanitized origins with confirmed Production domain | No | Yes |
| `CORS_ALLOW_ALL_ORIGINS` | Yes | `false` | Verify effective boolean | No | Yes |
| `AUTO_MIGRATE_ON_STARTUP` | Yes | `false` or absent; migration is explicit | Verify before backup/migration and again before cutover | No | Yes |
| `DB_CONNECT_TIMEOUT_SECONDS` | Yes | Positive operator-approved bounded timeout | Verify parsed effective value | No | Yes |
| `DOCUMENT_STORAGE_ROOT` | Yes | Private persistent path with backup policy | Compare with confirmed path; verify identity/permissions after H1 | Sensitive identifier | Yes |
| `VITE_API_URL` | Yes | Intended Production API HTTPS origin/base path | Inspect build environment and built assets; compare with confirmed domain | No | Yes |
| `FLASK_DEBUG` | Yes | `false` | Verify effective boolean/startup state | No | Yes |
| `FLASK_USE_RELOAD` | Yes | `false` | Verify effective boolean/startup state | No | Yes |
| Proxy forwarding/trusted-host settings | Topology-dependent | Match only the operator-confirmed reverse proxy and trusted public host | Inspect deployed service/proxy configuration after H1 | No | Yes |
| Secure-cookie settings | Authentication-mode-dependent | Secure transport and cookie attributes appropriate for HTTPS | Inspect effective application/proxy configuration and authenticated response headers | No | Yes |
| HTTPS termination/certificate/DNS | Yes | Approved certificate and public hostname; HTTPS termination location known | Verify topology at H1 and live behavior after cutover | No | Yes |
| Application and proxy logging | Yes | Enabled, access-controlled, retained, and secret-safe | Confirm destinations at H1; inspect bounded deployment window later | Sensitive identifier | Yes |

## H1 entry condition

H1 is not ready until every topology row is `CONFIRMED`, the authorized operator identifies the intended Production target, and the pre-H1 executable release gates pass. H1 approval authorizes read-only Production verification only; it does not authorize backup, migration, or cutover.

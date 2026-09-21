# Forwarder v1.10.0 Production Read-Only Collector Correction — 2026-09-22

## Governance and authority

LPAF v2.2 and its Agent Entry Protocol govern this Level B Production tooling correction. The reviewed v2.3 reference-impact discipline is applied as a strong default. `REFERENCE_IMPACT=NONE`: this slice changes no Product behavior, architecture/reference truth, migration, accepted Product test, Production state, or deployment decision.

The human operator's sanitized `Forwarder-v1.10.0-Production-ReadOnly-Preflight-20260921T214513Z.json` facts were treated as authoritative live topology evidence. Codex did not connect to the Production host, database, filesystem, IIS, or Scheduled Tasks.

## Returned live facts

- Host: `SRV8756807400`, Windows Server 2019 Standard.
- Active release: `C:\1-webapp\forwarder-production\release-20260914215708-20260921_shipment_evidence_ownership`.
- Listener: PID `100660`, release-local `runtime\python.exe`, Waitress `backend.wsgi:app`, `127.0.0.1:5101`.
- IIS site/app pool: `forwarder`; physical path is the active release `dist`; API proxy and SPA fallback were present.
- Local health and readiness: HTTP 200.
- External environment: `C:\1-webapp\forwarder-runtime\production.env`; mandatory configuration missing/invalid count was zero.
- External document storage: `C:\1-webapp\forwarder-data\case-documents`, present and outside the release root.
- Backup root/tooling/destination were identified, but the newest observed dump was about 530 hours old and restore evidence was absent.
- Collection remained BLOCKED with `SCHEDULED_TASK_INSPECTION_FAILED`, `RELEASE_MANIFEST_INSPECTION_FAILED`, and `DATABASE_CONNECTION_MODEL_UNAVAILABLE`.

## Root causes and correction

### Scheduled Task

The original collector queried only the hint `Forwarder Backend Production`. Revision `r2` first establishes the exact listener executable/release, then enumerates Scheduled Tasks and exports only candidates with bounded Forwarder, release-runtime, port, or Waitress evidence. It selects a task only when one candidate's action proves both the listener release and exact release-local runtime plus the port/launcher relationship. Zero matches remain UNKNOWN; multiple exact matches return sanitized candidate metadata and `SCHEDULED_TASK_IDENTITY_AMBIGUOUS`. It never selects the first candidate and never mutates or re-registers a task.

### Legacy release identity

The original collector required only `<active-release>\release-manifest.json`. Revision `r2` checks the bounded governed locations `release-manifest.json`, `RELEASE-METADATA.json`, `artifact\release-manifest.json`, and an explicitly configured in-release `RELEASE_IDENTITY_PATH`.

For the known manifest-less legacy shape, the bundle carries `legacy-production-witness.json`, deterministically derived from preserved witness `D:\1-webapp\production-reference\current-production-source-20260921.zip` (SHA256 `e9196ad9cc10dfeef44eba40d98e50520af4c505474211d5c23397bdf7774617`). Its governed metadata identifies candidate `Forwarder-Operational-Workspace-Production-CERTIFIED`, source `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`, and revision `20260921_shipment_evidence_ownership`. The collector derives identity only when all 323 declared bytes match: 309 backend files, 13 frontend files, and `requirements.txt`. Inventory SHA256 is `58baed2704b1301c749b2b194f203d6ffd68e9c8eb34536fb765c0e32297e1a5`. Missing/mismatched bytes or conflicting metadata remain BLOCKED. The legacy application version is deliberately `null`; no version is fabricated.

### Database connection

The original `[Uri]` parser admitted only `postgres://` and `postgresql://`, while the Production launcher generates the normal SQLAlchemy form `postgresql+psycopg2://`. Revision `r2` invokes the active release's exact `runtime\python.exe` and a small bridge using the launcher's own python-dotenv and SQLAlchemy URL parsing. The bridge passes only host, port, user, and database on the `psql` command line; the password exists only in the child-process environment and is never printed, serialized, logged, or written to disk. SQL is delivered over standard input. Fixed sanitized reason codes are returned on failure.

The PowerShell and Python guards both require `BEGIN TRANSACTION READ ONLY; ... COMMIT;` and reject mutation keywords before execution. The collector still attempts database identity/version, primary/recovery state, size, current Alembic revision, the exact ADR-047 classifier, migration compatibility checks, and schema-drift reduction. Failure remains BLOCKED.

## ADR-047 and backup honesty

The classifier predicates are unchanged. The exact classifier SHA256 remains `16a50c18a4e824ce35564beca18ea11131ed105d3d0d13f51e08ca021c780bae`; no Request-assignee or other fallback was introduced.

An old dump or a catalog listing is not restore proof. Revision `r2` reports catalog validation separately, leaves `fresh_deployment_window_backup_present=false`, and accepts restore evidence only as validated, sanitized metadata with an explicit PASS, source dump hash, timestamp, and disposable restore target. The collector can complete fact collection while `deployment_prerequisite_status` remains `BLOCKED_FRESH_BACKUP_AND_RESTORE_PROOF_REQUIRED`. It creates no backup.

## Regression and artifact evidence

- PowerShell parsing: PASS.
- Live-shape tooling suite: `25 passed`.
- Task-name mismatch with exact action/runtime evidence: PASS.
- Multiple exact Scheduled Task candidates: fail closed.
- Manifest-less release with complete legacy witness match: PASS.
- SQLAlchemy `postgresql+psycopg2` URL loading through python-dotenv/SQLAlchemy: PASS.
- Password absent from command line and output: PASS.
- Controlled missing-infrastructure collector execution: BLOCKED with sanitized JSON and zero mutation.
- ADR-047 exact-byte hash: PASS.
- Read-only-only bundle build: PASS; deployment bundle not emitted or changed.
- Independent deterministic `r2` bundle rebuild SHA256 match: PASS.
- Bundle inventory, checksums, and expanded/ZIP equality: PASS.

Corrected read-only bundle:

- Expanded: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157-r2\`
- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157-r2.zip`
- Size: `39574` bytes
- SHA256: `ec59de13a6d6e021f9f5f8235e78434fd078d89d4fe7cd81497973c6ab6b9543`
- Files: 9
- Deployment material present: no

The qualified Product package remains `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`. The held deployment bundle remains `acf45576c82bc04fa3a3dd02b12500690d4efeeba32c9ffb1e47322227919dbb`. Neither was rebuilt or modified.

## Facts, unknowns, and next gate

FACT: the returned live topology is internally consistent for listener, IIS, health, configuration, storage, and capacity. FACT: the first collector could not prove the task, release source, or database facts. UNKNOWN: the actual Scheduled Task identity, exact legacy byte match on the server, Production database revision/content, ADR-047 counts, migration compatibility, and schema drift remain unknown until the operator reruns revision `r2`. No missing fact is converted into PASS.

The only authorized next action is one human-run read-only collector command on the Production server and return of its newly generated sanitized JSON. Deployment remains prohibited.

`REFERENCE_IMPACT_FINAL=NONE`

## Verdict

PASS — v1.10.0 PRODUCTION READ-ONLY COLLECTOR CORRECTED FOR LIVE TOPOLOGY

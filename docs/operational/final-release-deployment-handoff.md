# Forwarder 1.9.2 final release deployment handoff

This PowerShell-oriented handoff requires separate Production/change authorization. Do not place secrets in command history or evidence.

1. Back up PostgreSQL with the approved `pg_dump -Fc` procedure and snapshot the private document root as one consistency boundary.
2. Verify both backups by hash and an approved restore-confidence check; record custody and timestamps.
3. Transfer `Forwarder-v1.9.2-<commit>.zip` into a new server staging directory.
4. Verify it: `Get-FileHash -Algorithm SHA256 -LiteralPath .\Forwarder-v1.9.2-<commit>.zip` and compare with the signed handoff value.
5. Stop/quiesce IIS/backend workers and verify no application writer remains.
6. Expand into a new immutable directory: `Expand-Archive -LiteralPath .\Forwarder-v1.9.2-<commit>.zip -DestinationPath .\release-v1.9.2-20260812`.
7. Create `.venv`, activate it, and run `python -m pip install -r requirements.txt`.
8. Reuse protected server-managed environment variables; do not copy a local `.env`. Verify required database, JWT/session, storage, CORS/host, proxy, and runtime settings without printing values.
9. From the release directory run `python -m backend.migration_cli current`, `python -m backend.migration_cli check`, then `python -m backend.migration_cli upgrade 20260824_mt1_graph --confirm`.
10. Point the backend Scheduled Task and IIS site at the immutable directory and start/recycle them.
11. Run `Invoke-WebRequest https://server.logisticmarket.ir/api/health` and readiness checks; require revision `20260824_mt1_graph`.
12. Run authenticated backend smoke for login, Customer/CRM, ShipmentRequest, Quote, tracking, documents, and error behavior.
13. Verify the frontend root, hashed assets, release identity 1.9.2, same-origin API routing, and cache headers.
14. Exercise same-tenant success and cross-tenant read/write/re-parent/document/tracking denial; confirm synthetic quarantine remains closed.
15. Run the established browser/UAT suite for public intake, expert workflow, CRM, shipment/quote/tracking/documents, language/layout, and console/network errors.
16. Trigger rollback on migration mismatch, failed health/readiness, authentication failure, tenant-isolation bypass, writable quarantine, material API/UI mismatch, or unrecoverable data/document inconsistency.
17. Prefer forward repair. If restore is selected, stop writes, restore the coordinated pre-deployment database and document snapshot, repoint IIS/task paths to `release-v1.9.1-20260811`, restart, and repeat health/security smoke. Never blindly downgrade or alter synthetic rows.
18. Accept publication only after artifact identity, backups, migration, health, backend/frontend smoke, tenant isolation, browser/UAT, operator, and timestamp evidence are complete.

Preflight requirements: supported Python 3.13 runtime (the certified local runtime must be matched or separately certified), PostgreSQL 18, `psycopg2-binary==2.9.11`, sufficient disk, existing private document storage, IIS reverse proxy with trusted forwarded-host configuration, protected environment/secrets, and a tested rollback/restore path. Redis is not a declared runtime dependency in the release package.


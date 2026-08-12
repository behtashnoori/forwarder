# Forwarder 1.9.2 deployment preparation

This runbook prepares a future authorized Windows/IIS deployment; it does not authorize one or access Production.

1. Verify the immutable archive, SHA-256, manifest, annotated `v1.9.2` tag, source commit/tree, requirements hash, and all five migration hashes.
2. Copy the verified package to a new immutable server directory.
3. Create a release-local `.venv` and install only `requirements.txt`; do not rely on global packages.
4. Run `VERIFY-PACKAGE.ps1`; confirm `psycopg2-binary 2.9.11` imports from the release-local environment.
5. Record current IIS and backend Scheduled Task paths without exposing secrets.
6. Confirm deployed database revision `20260819_v191_acceptance_corrections`, PostgreSQL version, capacity, active transactions, and approved quiescence.
7. Take and verify coordinated PostgreSQL and private document-storage backups.
8. Stop/quiesce application writers under approved change authority.
9. Run the preflight and explicitly upgrade to `20260824_mt1_graph`.
10. Confirm current/head equality and readiness before switching processes.
11. Reuse the existing production environment through protected server configuration; never copy `.env` from the package or print secrets.
12. Point the backend Scheduled Task WorkingDirectory, `--repo`, and `PYTHONPATH` consistently at the immutable 1.9.2 directory and start it.
13. Point IIS at the immutable 1.9.2 frontend and verify HTTPS, same-origin API routing, cache headers, and health.
14. Run backend, frontend, authentication, intake, tenant-isolation, quarantine, and browser/UAT smoke gates.
15. Capture artifact, backup, migration, smoke, operator, and timestamp evidence before publication acceptance.

Reference Data and OIP policy/threshold initialization are separate administrator actions. No seed or catalog apply occurs during build, migration, startup, or basic acceptance.

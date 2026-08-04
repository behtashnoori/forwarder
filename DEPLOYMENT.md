# Forwarder 1.8.0 deployment preparation

This operator runbook does not authorize deployment. The authoritative repository baseline is Production application 1.6.1 at database revision `20260809_cargo_catalog_items`; Release 1.7.0 is published but is not recorded as deployed.

1. Copy `release-v1.8.0-20260804` to a new immutable server directory.
2. Run `powershell -ExecutionPolicy Bypass -File .\VERIFY-PACKAGE.ps1` and record its hash and result.
3. Record the current IIS physical path.
4. Record the current backend Scheduled Task action, WorkingDirectory, `--repo`, and `PYTHONPATH` behavior without exposing secrets.
5. Verify the current database revision; the documented baseline is `20260809_cargo_catalog_items`.
6. Take a PostgreSQL custom-format backup and record its SHA-256.
7. Run the migration preflight and review the sanitized target and the complete two-revision path.
8. Apply the explicit chain to `20260811_project_configuration` with the supported migration CLI.
9. Confirm current/head `20260811_project_configuration` and `pending=no`.
10. Update the backend release path to the immutable 1.8.0 directory.
11. Ensure the Scheduled Task WorkingDirectory, `--repo`, and `PYTHONPATH` all point to the current release.
12. Restart the backend cleanly.
13. Verify `/api/health` returns 200 with the database connected.
14. Verify an unauthenticated protected Project Configuration route returns 401, not 404.
15. Switch the IIS physical path to the immutable 1.8.0 directory.
16. Verify new JS/CSS assets, cache headers, normal refresh, and no stale asset reference.
17. Run the authenticated smoke test.
18. Record backup, migration, task, IIS, asset, smoke, operator, and timestamp evidence.

Reference Data population is not a deployment step. Authorized administrators create MilestoneType and all other Reference Data through Admin UI after deployment as business needs arise. Optional `plan`/`apply` tooling may support a separately governed import, but basic health and release acceptance never depend on it. Never place plaintext credentials in deployment evidence.

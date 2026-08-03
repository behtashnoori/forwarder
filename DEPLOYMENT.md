# Forwarder 1.7.0 deployment preparation

This is an operator runbook only. Release publication did not contact or change Production.

1. Copy `release-v1.7.0-20260803` to a new immutable server path.
2. Run `powershell -ExecutionPolicy Bypass -File .\VERIFY-PACKAGE.ps1` and record the reproduced hash.
3. Record the current IIS physical path and backend Scheduled Task configuration.
4. Verify the database currently reports `20260809_cargo_catalog_items`.
5. Take a PostgreSQL custom-format backup and record its SHA-256.
6. Run the migration preflight and review its sanitized target.
7. Apply the explicit migration to `20260810_logistics_network`; confirm `pending=no`.
8. Switch the backend repository/runtime path to the 1.7.0 immutable directory.
9. Ensure the Scheduled Task WorkingDirectory, `--repo`, and `PYTHONPATH` all reference that directory.
10. Restart the backend cleanly and verify `/api/health` and an unauthenticated protected Logistics Network route (401, not 404).
11. Switch IIS to the immutable 1.7.0 path.
12. Verify the new JS/CSS assets, cache headers, normal refresh, authenticated admin/Project smoke tests, and tenant isolation.
13. Record migration, task, IIS, asset, smoke, and timestamp evidence.

Reference Data Seed must not run automatically. A Production catalog apply requires a separately authorized plan review, explicit confirmation, approved checksum, operator identity, and approval reference. Never place credentials in deployment evidence.

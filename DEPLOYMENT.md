# Forwarder 1.9.3 deployment preparation

Release baseline is immutable Production `v1.9.2`; target is `v1.9.3` at Alembic head `20260825_admin_multitenant`. Deployment requires separate Production authorization.

1. Verify the archive SHA-256, manifest, annotated tag, commit, and package contents with `VERIFY-PACKAGE.ps1`.
2. Back up the Production database and document storage and record restore locations before stopping services.
3. Expand the archive into a new immutable release directory; never overwrite the v1.9.2 directory.
4. Stop the IIS Forwarder site/application pool and the backend Scheduled Task/service using the server's existing controlled procedure.
5. Install the pinned Python dependencies and retain the existing secret-managed Production environment configuration.
6. Run `python -m backend.migration_cli current`, then `python -m backend.migration_cli check`.
7. Apply exactly `python -m backend.migration_cli upgrade 20260825_admin_multitenant --confirm`.
8. Re-run `current` and `check`; require sole current head `20260825_admin_multitenant` and no pending migration.
9. Point the backend working directory, `--repo`, and `PYTHONPATH` consistently at the immutable v1.9.3 directory, then start the backend.
10. Require the backend to listen only on `127.0.0.1:5101`; verify its health endpoint returns HTTP 200.
11. Point IIS at the v1.9.3 frontend, start the site/application pool, and require the public URL and `/api/health` to return HTTP 200.
12. Perform admin login, exactly-one-Organization context, normal shipment/admin page, and Platform Admin versus Organization Admin authority smoke tests. Do not onboard another company during acceptance.

If acceptance fails, stop traffic and prefer a reviewed forward fix. If recovery requires rollback across the migration, restore the coordinated pre-migration database and document-storage backups before reactivating immutable v1.9.2; do not run an ad-hoc downgrade or mutate quarantined data.

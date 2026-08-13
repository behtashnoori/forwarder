# Forwarder 1.9.3.1 deployment preparation

Release baseline is immutable `v1.9.3`; target is the frontend patch `v1.9.3.1`. Both use Alembic head `20260825_admin_multitenant`. This release contains no migration and requires separate Production authorization before deployment.

1. Verify the archive SHA-256, manifest, annotated tag, commit, and package contents with `VERIFY-PACKAGE.ps1`.
2. Expand the archive into a new immutable release directory; never overwrite the v1.9.3 directory.
3. Confirm `index.html` references hashed `/assets/` entries and never `/src/main.tsx`.
4. Preserve the existing secret-managed environment configuration.
5. Run the read-only commands `python -m backend.migration_cli current` and `python -m backend.migration_cli check`; require `20260825_admin_multitenant` with no pending migration. Do not run an upgrade for this patch.
6. Following the established controlled procedure, point the backend and IIS consistently at the immutable v1.9.3.1 directory and perform the smoke tests in `SMOKE-TEST.md`.

If acceptance fails, reactivate immutable v1.9.3 application files. No database downgrade or restore is involved.

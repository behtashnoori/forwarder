# Forwarder Product Integration RC — Operator Notes

This package is the sole authoritative application artifact: `Forwarder-Product-Integration-RC-ff09bae.zip`, qualified with its adjacent manifest JSON.

1. Copy the authoritative ZIP and manifest to the Production server; verify their hashes and manifest identity before extraction.
2. Create an immutable new release directory and verify the extracted package contents.
3. Confirm the Production database is at `20260915_project_access_foundation`; take a fresh pre-release PostgreSQL backup.
4. Run the controlled migration to `20260916_personal_dashboard_permissions`, then confirm the target revision.
5. Use the compatible release-local portable Python runtime (the existing governed Python 3.12.6 runtime is compatible with this RC).
6. Switch the existing Forwarder Backend Production Scheduled Task and verify it on the existing `127.0.0.1:5101` listener.
7. Point the existing IIS Forwarder physical path to the new release `dist`, then perform local IIS and public HTTPS smoke checks followed by browser UAT.
8. Retain package/hash, database backup, revision, smoke, and rollback evidence. Do not change topology, ports, site/task names, or production configuration.

No Production action was performed while preparing this RC.

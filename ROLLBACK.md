# Forwarder 1.9.3 rollback and recovery

The application rollback target is immutable Production `v1.9.2`. Release 1.9.3 advances the schema from `20260824_mt1_graph` to `20260825_admin_multitenant`.

Before migration, rollback is cancellation with no Production change. After migration, prefer a reviewed forward fix. If rollback across the schema boundary is authorized, stop traffic and restore the coordinated pre-migration database and document-storage backups before restoring the v1.9.2 application. Never perform an improvised Production downgrade, clear quarantine, fabricate Organizations, or synthesize ownership.

After recovery, verify IIS is Started, the backend listens on `127.0.0.1:5101`, backend and public health return HTTP 200, the database revision matches the restored v1.9.2 boundary, and existing operational data is accessible under the prior release policy.

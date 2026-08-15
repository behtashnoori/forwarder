# Forwarder 1.9.4 rollback and recovery

The application rollback target is immutable `v1.9.3.1`.

Stop v1.9.4 at `20260826_org_document_policy` before rollback. Downgrade is permitted only when the migration safety precheck finds no organization-policy snapshots or other rows incompatible with the previous schema. It intentionally refuses destructive data loss. If refused, preserve or explicitly migrate tenant records under a separately approved recovery plan; do not force or delete them. After a permitted downgrade, require `20260825_admin_multitenant` before reactivating v1.9.3.1.

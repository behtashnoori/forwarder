# Forwarder v1.9.4 handoff

Baseline: accepted Production lineage `v1.9.3.1` at database revision `20260825_admin_multitenant`.

Target: application `v1.9.4`, database revision `20260826_org_document_policy`.

Before any separately authorized deployment, verify the package checksum and manifest, take the normal database backup, confirm the database is at the baseline revision, and run the migration preflight in the target environment. Upgrade exactly one revision, restart the application, then verify release identity, Alembic head, organization-admin policy isolation, platform-admin global-definition access, and a representative readiness preview.

Rollback is application-first. Database downgrade is allowed only when Alembic's safety precheck finds no organization-policy snapshots or rows that cannot fit the previous schema. The migration intentionally refuses a destructive downgrade; preserve or explicitly migrate tenant-owned records before retrying.

No deployment, push, Production database access, seed, or backfill is part of this handoff.

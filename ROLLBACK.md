# Forwarder 1.9.3.1 rollback and recovery

The application rollback target is immutable `v1.9.3`. Release 1.9.3.1 does not change the database; Alembic remains at `20260825_admin_multitenant`.

If application acceptance fails, stop traffic using the established controlled procedure and reactivate the immutable v1.9.3 application files. No database downgrade, restore, quarantine change, Organization creation, or ownership mutation is required.

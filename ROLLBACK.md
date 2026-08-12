# Forwarder 1.9.2 rollback and recovery

The application rollback target is the immutable `release-v1.9.1-20260811` deployment. Release 1.9.2 advances the schema from `20260819_v191_acceptance_corrections` to `20260824_mt1_graph`.

Before migration, rollback is cancellation with no Production change. After migration, prefer a reviewed forward fix. A schema downgrade is a separately authorized operation and must never modify or assign the quarantined synthetic legacy rows. The locally certified boundary is downgrade from `20260824_mt1_graph` to `20260823_mt1_ownership_expand` and re-upgrade; it is not authorization for a Production downgrade to 1.9.1.

Authorized recovery sequence:

1. Stop further writes and record the failure point.
2. Decide explicitly between forward fix and coordinated restore.
3. For restore, restore the verified pre-deployment PostgreSQL backup and matching document-storage snapshot as one consistency boundary.
4. Restore backend Scheduled Task and IIS paths to `release-v1.9.1-20260811`.
5. Start/recycle only under recovery authority; verify health, schema identity, documents, authentication, quarantine, and prior frontend assets.
6. Preserve failed-release evidence and reconcile any post-backup business transactions through governed recovery work.

Never run a blind Alembic downgrade, destructive cleanup, synthetic-data reassignment, or seed rollback.

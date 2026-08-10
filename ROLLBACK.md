# Forwarder 1.9.1 rollback and recovery

The current Production application rollback target is the immutable
`release-v1.9.0-20260809` deployment.
The Release 1.9.1 schema head is `20260819_v191_acceptance_corrections`.

Application rollback does not imply database downgrade. The v1.9.1 downgrade
fails closed if direct Operational Shipments, nullable commercial lineage, or
new canonical international location data would be lost. Forward recovery is
preferred; coordinated restore is the supported fallback.

Before migration, rollback is cancellation with no Production change. After
migration but before durable use, prefer a reviewed forward fix; a conditional
downgrade is separately authorized and must satisfy every migration guard.
Once durable MDPM/OIP/Economics/FX facts exist—or whenever rollback crosses
`20260817_shipment_economics_core`—recovery requires the coordinated
pre-deployment PostgreSQL and document-storage backups.

Authorized recovery sequence:

1. Stop further writes under incident authority and record the failure point.
2. Decide explicitly between forward fix and coordinated restore.
3. For restore, restore the verified pre-deployment database and matching
   document-storage snapshot as one consistency boundary.
4. Restore the backend Scheduled Task and IIS paths to
   `release-v1.9.0-20260809`.
5. Start/recycle only under recovery authority; verify health, schema identity,
   documents, authentication, and prior frontend assets.
6. Preserve failed-release evidence and reconcile any post-backup business
   transactions through separately governed recovery work.

Never run a blind Alembic downgrade, delete durable evidence, or treat Seed
rollback as part of application rollback.

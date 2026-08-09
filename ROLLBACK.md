# Forwarder 1.9.0 rollback and recovery

The current Production application rollback target is the immutable
`release-v1.6.1-20260802` deployment. Published 1.7.0 and 1.8.0 packages are not
recorded as deployed and are not assumed rollback targets.
The Release 1.9.0 schema head is `20260818_immutable_fx_provenance`.

Application rollback does not imply database downgrade. The 1.9.0 migration
chain introduces durable Operational Execution, MDPM, OIP, Shipment Economics,
and immutable FX provenance. Several downgrades fail closed when durable facts
exist; `20260817_shipment_economics_core` is unconditionally non-downgradable.

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
   `release-v1.6.1-20260802`.
5. Start/recycle only under recovery authority; verify health, schema identity,
   documents, authentication, and prior frontend assets.
6. Preserve failed-release evidence and reconcile any post-backup business
   transactions through separately governed recovery work.

Never run a blind Alembic downgrade, delete durable evidence, or treat Seed
rollback as part of application rollback.

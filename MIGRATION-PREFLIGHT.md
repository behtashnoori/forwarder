# Forwarder 1.9.1 migration preflight

- After Slice 8 publication, confirm exact annotated tag `v1.9.1`, verified package identity, and separate
  Production change authorization.
- Confirm actual Production revision `20260818_immutable_fx_provenance` and fresh,
  coordinated PostgreSQL/document-storage backup and restore evidence.
- Review this exact forward chain:

  1. `20260819_v191_acceptance_corrections`

- Do not prune pre-baseline revision modules: Alembic requires their revision
  metadata to resolve `current`, `heads`, upgrades, and supported downgrade
  traversal. The immutable 2024 shared-credential migration remains historical
  graph evidence; step 3 disables every account retaining its exact hash before
  the application is switched.

- Inspect active connections, long transactions, locks, table scale, disk, and
  approved write-quiescence immediately before the change.
- Run `python -m backend.migration_cli current` and `check` with sanitized output.
- Apply only through the explicit authorized command:
  `python -m backend.migration_cli upgrade 20260819_v191_acceptance_corrections --confirm`.
- Confirm `current=head=20260819_v191_acceptance_corrections`, `pending=no`, critical
  tables ready, and `missing_tables=[]` before application switching.
- The v1.9.1 downgrade fails closed after direct operations or new canonical
  international locations exist. Prefer forward recovery; restore the
  coordinated pre-migration backups when a safe downgrade is refused.
- Do not run Seed, catalog apply, OIP policy creation, or business initialization
  as part of migration or startup.

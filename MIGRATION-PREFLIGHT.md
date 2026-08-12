# Forwarder 1.9.2 migration preflight

- Confirm exact annotated tag `v1.9.2`, verified package identity, and separate Production change authorization.
- Confirm the deployed revision is `20260819_v191_acceptance_corrections`. If it differs, stop and re-plan; do not skip or infer a baseline.
- Take and verify coordinated PostgreSQL and document-storage backups before stopping the application.
- Review the exact additive forward chain:

  1. `20260820_mt1c_quarantine_runtime`
  2. `20260821_mt1d_canonical_census`
  3. `20260822_mt1c1_census_fence`
  4. `20260823_mt1_ownership_expand`
  5. `20260824_mt1_graph`

- Inspect active connections, long transactions, locks, table scale, disk space, PostgreSQL 18 compatibility, and the approved write-quiescence window.
- Run `python -m backend.migration_cli current` and `python -m backend.migration_cli check` with sanitized output.
- Apply only through the authorized command:
  `python -m backend.migration_cli upgrade 20260824_mt1_graph --confirm`.
- Confirm `current=head=20260824_mt1_graph`, `pending=no`, critical tables ready, and `missing_tables=[]` before switching application processes.
- Do not assign Organization ownership to legacy synthetic rows. They remain quarantined; no mapping/backfill or cleanup is part of deployment.
- Do not execute a destructive contract phase, Seed, catalog apply, policy creation, or business initialization.

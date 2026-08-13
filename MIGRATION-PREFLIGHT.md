# Forwarder 1.9.3.1 migration preflight

- Confirm exact annotated tag `v1.9.3.1`, verified package identity, and separate Production change authorization.
- Confirm the current and target Alembic head are both `20260825_admin_multitenant`.
- This frontend patch creates no migration, changes no Alembic head, and has an empty `upgrade_revisions` manifest list.
- Run only the canonical read-only checks: `python -m backend.migration_cli current` and `python -m backend.migration_cli check`.
- Do not run a database upgrade for v1.9.3.1.

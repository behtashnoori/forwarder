# Forwarder 1.9.3 migration preflight

- Confirm exact annotated tag `v1.9.3`, verified package identity, backup evidence, and separate Production change authorization.
- Confirm Production begins at the v1.9.2 head `20260824_mt1_graph`.
- Confirm the package contains `backend/migrations/versions/20260825_admin_multitenant.py` and exactly one Alembic head: `20260825_admin_multitenant`.
- The revision directly follows `20260824_mt1_graph`. It adds explicit authority and tenant policy fields/constraints without creating Organizations, clearing quarantine, fabricating ownership, or assigning synthetic legacy rows.
- Run the canonical read-only checks: `python -m backend.migration_cli current` and `python -m backend.migration_cli check`.
- After backup and authorization, run exactly: `python -m backend.migration_cli upgrade 20260825_admin_multitenant --confirm`.
- Require `current=head=20260825_admin_multitenant`, `pending=no`, and healthy readiness before application restart.

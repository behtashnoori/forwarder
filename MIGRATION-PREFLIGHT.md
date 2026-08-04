# Forwarder 1.8.0 migration preflight

- Confirm the package verifies and a separate deployment authorization exists.
- Confirm the actual current revision and a verified PostgreSQL custom-format backup with recorded SHA-256.
- The authoritative documented Production baseline is `20260809_cargo_catalog_items`; therefore review both `20260810_logistics_network.py` and `20260811_project_configuration.py`.
- Run `python -m backend.migration_cli current` and `check` with sanitized output.
- Apply only with `python -m backend.migration_cli upgrade 20260811_project_configuration --confirm`.
- Confirm current/head `20260811_project_configuration` and `pending=no`.
- Do not run `milestone_type_catalog_cli apply` as part of migration, startup, verification, or basic health.

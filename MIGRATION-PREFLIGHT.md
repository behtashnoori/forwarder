# Forwarder 1.7.0 migration preflight

- Confirm the package verifies and the target is Production only under a separate deployment authorization.
- Confirm current revision `20260809_cargo_catalog_items`, verified custom-format backup, and recorded SHA-256.
- Run `python -m backend.migration_cli current` and `check` with sanitized output.
- Review `20260810_logistics_network.py`; it adds three tables and inserts no rows.
- Apply only with `python -m backend.migration_cli upgrade 20260810_logistics_network --confirm`.
- Confirm current/head `20260810_logistics_network` and `pending=no`.
- Do not run `logistics_point_catalog_cli apply` as part of migration or startup.

# Forwarder 1.7.0 rollback

Application rollback target: `release-v1.6.1-20260802`.

1. Restore the recorded backend Scheduled Task WorkingDirectory, `--repo`, and `PYTHONPATH` to 1.6.1.
2. Restore the IIS physical path to the immutable 1.6.1 directory.
3. Restart the backend cleanly; verify health and prior assets.
4. Retain the additive 1.7.0 database tables by default.

Database downgrade is not automatic. It requires separate authorization and an assessment for LogisticsPointType, LogisticsPoint, and ProjectLogisticsPoint rows. Export/preserve any data before downgrading only to `20260809_cargo_catalog_items`. A later Reference Data catalog apply has a separate governance/deactivation procedure.

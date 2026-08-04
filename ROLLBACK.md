# Forwarder 1.8.0 rollback

Application rollback target: `release-v1.7.0-20260803`.

1. Restore the prior backend Scheduled Task action, WorkingDirectory, `--repo`, and `PYTHONPATH`.
2. Restore the IIS physical path to the immutable 1.7.0 directory.
3. Restart the backend cleanly; verify health and prior assets.
4. Retain the additive 1.8.0 schema by default.

Database downgrade is not automatic. It requires separate authorization and a data-retention assessment for `ProjectService`, `ProjectDocumentRequirement`, `ProjectMilestoneDefinition`, and `MilestoneType` data. Export and preserve data first; downgrade only to `20260810_logistics_network`. Downgrade removes `DocumentDefinition.public_id`; do not downgrade while the application or data depends on it. If the catalog is applied separately, rollback or deactivation is distinct governed work.

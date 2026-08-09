# Forwarder 1.9.0 migration preflight

- Confirm exact annotated tag `v1.9.0`, verified package identity, and separate
  Production change authorization.
- Confirm actual Production revision `20260809_cargo_catalog_items` and fresh,
  coordinated PostgreSQL/document-storage backup and restore evidence.
- Review this exact forward chain:

  1. `20260810_logistics_network`
  2. `20260811_project_configuration`
  3. `security_credential_remediation`
  4. `20260812_operational_execution`
  5. `20260813_mdpm_readiness`
  6. `20260814_oip_situations`
  7. `20260815_oip_threshold_policy`
  8. `20260816_oip_projection_health`
  9. `20260817_shipment_economics_core`
  10. `20260818_immutable_fx_provenance`

- Inspect active connections, long transactions, locks, table scale, disk, and
  approved write-quiescence immediately before the change.
- Run `python -m backend.migration_cli current` and `check` with sanitized output.
- Apply only through the explicit authorized command:
  `python -m backend.migration_cli upgrade 20260818_immutable_fx_provenance --confirm`.
- Confirm `current=head=20260818_immutable_fx_provenance`, `pending=no`, critical
  tables ready, and `missing_tables=[]` before application switching.
- Treat rollback across Shipment Economics or consequential immutable FX facts
  as restore-required; do not bypass downgrade guards.
- Do not run Seed, catalog apply, OIP policy creation, or business initialization
  as part of migration or startup.

# Forwarder 1.9.0 — Operational Execution Foundation

- Change type: MINOR
- Previous version: 1.8.0
- Deployment type: backend-frontend-migration
- Migration: `20260812_operational_execution`
- Previous migration: `security_credential_remediation`
- Status: Implemented — Not Published — Not Deployed
- Reference Data: administrator-managed; Seed executed: false
- Production: unchanged

This candidate extends the existing operational Milestone with explicit shipment initialization, a bounded seven-state lifecycle, append-only MilestoneEvent history, governed Delay and Exception records, calculated progress, opaque internal APIs, and an Operational Execution UI. Existing Shipments receive no automatic rows.

Evidence, uploads/document approval, dashboards/reporting, automatic Shipment status derivation, notifications, escalation, analytics, maps/ETA, workflow engines, and Reference Data population are excluded.

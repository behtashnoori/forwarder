# Forwarder v1.9.4 release notes

Forwarder v1.9.4 introduces tenant-owned Organization Document Policy while preserving global document definitions as platform-owned catalog data.

- Organization administrators can configure REQUIRED, OPTIONAL, CONDITIONAL, or DISABLED policy per global document definition.
- Runtime precedence is Project override, then Organization policy, then the compatibility fallback used only while an organization has no policy rows.
- Case-document snapshots and Operational Document Readiness materialization record the effective requirement and its provenance without rewriting existing snapshots.
- Tenant context is derived from authenticated organization membership; organization identifiers in mutation payloads are rejected.
- Alembic revision `20260826_org_document_policy` is additive. Downgrade refuses to discard or invalidate tenant-owned policy snapshots.

This release does not deploy, seed, backfill, or access Production data.

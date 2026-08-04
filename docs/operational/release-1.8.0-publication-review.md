# Release 1.8.0 Publication Review

- **Release:** 1.8.0 — Project Configuration Foundation
- **Change type:** MINOR
- **Previous published baseline:** annotated tag `v1.7.0`, peeled commit `46cfc2bd359ee28968e8bdde3ed1eebfda1b1f0f`
- **Migration:** `20260810_logistics_network` → `20260811_project_configuration`
- **Production:** unchanged; authoritative repository evidence remains application 1.6.1 at `20260809_cargo_catalog_items`

## Independent review boundary

The cumulative review covers governance commits `58ca1e6` and `7a1d5b7`, implementation commit `7e333fe`, and the bounded publication-metadata commit that finalizes this record and package tooling. Included scope is `DocumentDefinition.public_id`, `MilestoneType`, `ProjectService`, `ProjectDocumentRequirement`, `ProjectMilestoneDefinition`, elapsed target/warning duration, existing `ProjectLogisticsPoint` reuse, internal selectors, and authenticated Project Configuration APIs/UI.

Numeric `DocumentDefinition` PK/FK identity and legacy numeric APIs remain intact. New APIs use opaque identity. Database constraints cover one active primary service, document duplicates, active milestone sequence, and same-Project point references. The UUID identity amendment permits only migration backfill of existing `DocumentDefinition` rows. No operational aggregate mutation, automatic milestone creation, automatic catalog apply, or other Seed execution is included.

Excluded scope remains absent: `ProjectSlaDefinition`, business calendars, defaults, visibility, snapshots, workflow/rules/BPMN, reporting/dashboard capability, allocation, GIS, ETA, optimization, AI, and public/customer Project Configuration APIs. No unrelated cleanup entered the release.

## Governance and documentation

PDR-017, ADR-027, the Slice Contract, Governance Closure, Identity Amendment, FDD/FDM, Decision Index, Capability Registry, Roadmap, Evolution Map, Acceptance Traceability, Final RC Review, performance evidence, and release notes were reconciled. They consistently describe an implemented, bounded, unpublished and undeployed capability before publication.

## Verification summary

Final publication evidence is reproduced from the exact tag candidate and includes focused and full backend/frontend regression, TypeScript, ESLint, build, Python/static checks, OpenAPI/runtime parity, one Alembic head, documentation/governance reconciliation, security scans, and disposable PostgreSQL 18 fresh/previous-head/downgrade/re-upgrade verification. The PostgreSQL matrix covers UUIDv4 backfill, numeric identity preservation, four tables, constraints and indexes, organization/project rejection, zero automatic catalog rows, and zero operational aggregate mutation. Current performance evidence remains applicable because the reviewed implementation did not change after it was recorded.

## Publication and deployment boundary

The MilestoneType catalog `milestone-types-v1.0.0.json` is packaged as prepared and is not applied. Production Seed executed is false. Production deployment is false. Version 1.8.0 is embedded in the frontend asset but is not visibly rendered; this is a known limitation and no new version API or UI redesign is introduced.

The deployment type is backend-frontend-migration. Because Production is documented at 1.6.1 / `20260809_cargo_catalog_items`, the eventual authorized upgrade must traverse both 1.7.0 and 1.8.0 migrations. Application rollback targets `release-v1.7.0-20260803` and normally retains the additive 1.8.0 schema. Database downgrade is separately authorized work requiring data-retention assessment; catalog rollback/deactivation is separate governance work.

## Recommendation

Publication is recommended only if every final gate, remote synchronization check, annotated-tag identity check, deterministic package verification, and immutable-package inspection passes. This recommendation does not authorize deployment, Production access, migration, IIS changes, service restart, or catalog apply.

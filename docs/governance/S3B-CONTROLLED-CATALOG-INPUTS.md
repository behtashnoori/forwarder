# S3-B Controlled Catalog Inputs

Cargo catalog creation previously exposed `cargo_type_public_id` and
`default_uom_public_id` as free-text inputs. `CargoCatalogAdminTab` now loads
the existing active catalog options endpoint and renders native business-facing
selectors: CargoType is required; UOM is optional. The selected public IDs are
retained as form values and submitted unchanged to the existing backend.

No active CargoType produces an explicit Persian readiness message; UOM has an
explicit empty option. Backend validation remains authoritative for forged,
unknown, or inactive IDs. Existing inactive catalog references remain visible
on edit but new selection options come only from active master data.

Local `npm ci --ignore-scripts` restored lockfile-defined Vitest without
package or lockfile changes. Focused CargoFoundation component tests passed and
the production Vite build passed.

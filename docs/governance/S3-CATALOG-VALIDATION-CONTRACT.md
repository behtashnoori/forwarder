# S3 Catalog Validation Contract

`CargoCatalogItem` (`cargo_catalog_item`) is the tenant-owned standard-goods
catalog. Organization-admin API: `POST/PATCH /api/internal/cargo-catalog`.
The create/edit UI is `CargoCatalogAdminTab`; validation is in
`backend/services/cargo_service.py`.

| Field | Rule |
| --- | --- |
| `immutable_code` | required, trimmed, max 64, unique per organization |
| `fa_name` | required, trimmed, max 160 |
| `cargo_type_public_id` | required; CargoType must be active |
| `default_uom_public_id` | optional; supplied UOM must be active |
| optional text | empty becomes null; description max 2000 |

CargoType and UOM are governed shared master data. Catalog ownership is derived
from the authenticated organization. Inactive references cannot be used for a
new create; existing catalog/shipment snapshots remain readable.

## Finding and remediation

The UAT payload is unavailable, so the original failure is
**PARTIALLY_REPRODUCED**. The service precisely rejects missing, unknown, or
inactive CargoType with HTTP 422 and rejects invalid UOM similarly. The proven
defect was UI error masking: `CargoCatalogAdminTab` discarded `ApiError.message`
and rendered generic invalid-information text. It now displays the existing
bounded backend message. No new global error envelope or data change was made.

The form still accepts public IDs as text rather than a selector. That is a
residual UX risk, intentionally deferred because no catalog-options contract
for this form was proven in scope. Frontend verification requires restoring the
lockfile-defined Vitest tooling without package changes.

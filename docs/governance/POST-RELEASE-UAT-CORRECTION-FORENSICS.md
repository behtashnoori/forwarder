# Post-release UAT correction forensic record

**Scope:** Development-only correction and forensic review.  No Production
connection, mutation, packaging, deployment, merge, or push is authorized by
this work.

## WS1 — Cargo Catalog 403

**Root cause:** `CargoCatalogAdminTab` correctly loads its catalog through the
organization-admin API, but also calls `GET /api/internal/cargo-options`.
That selector previously required only `operational_shipment.read`; a valid
`ORGANIZATION_ADMIN` with the required single active membership could therefore
open the tab yet receive 403 for its supporting selector.

**Correction:** the selector now permits exactly either (a) an active
organization administrator with a uniquely resolved active membership, or (b)
an operational user with `operational_shipment.read`.  Both derive the tenant
from server-side membership.  An authenticated user with neither remains 403;
ambiguous, inactive, and missing membership contexts fail closed.

**Regression evidence:** `test_cargo_options_authorization.py` proves both
approved paths return 200 and the negative path returns 403.

## WS2 — public international geography

**Source of truth:** public country selection is `Country` plus active
`InternationalCity`, via `/api/countries` and `/api/international-cities`.
The selector intentionally excludes GlobalLogisticsPoint and organization
LogisticsPoint because neither can be submitted as that public-form field.

**Root cause:** `seed_international_data.py` skipped its complete checked-in
catalog whenever *any* Country existed.  An Iran-only seed consequently left
Iran without its InternationalCity continuation and suppressed all remaining
catalog entries.

**Correction:** the existing checked-in catalog now reconciles country and city
rows independently.  It creates only missing rows, is repeatable, and does not
silently reactivate existing inactive records.  This restores the repository's
governed Iran data path without rewriting history or adding a migration.

**Turkmenistan status:** repository evidence establishes Turkmenistan tracking
and Global Logistics Point references, but ADR-041 expressly keeps those
separate from `Country`/`InternationalCity`.  There is no approved
InternationalCity catalog entry for Turkmenistan in this repository.  No
Turkmenistan public-selector record was invented; an approved geography source
is required before such a row can be added.

**Regression evidence:** `test_international_reference_reconciliation.py`
starts with partial Iran data, verifies Iran continuation and remaining
catalog reconciliation, preserves inactive China, and proves a second run is
non-mutating.  Existing public-selector tests retain the active-country plus
active-city invariant.

## WS3 — Logistics Reference Network

| Layer | Authority / purpose | Downstream consequence |
| --- | --- | --- |
| `GlobalLogisticsPoint` | platform canonical facility reference | none by adoption alone |
| `OrganizationGlobalLogisticsPointAdoption` | tenant approval and local metadata | permits controlled materialization only |
| `LogisticsPoint` | tenant operational facility | may be attached to project configuration |
| `ProjectLogisticsPoint` | project-specific tenant facility | exposed by the project logistics-point selector |

`global_logistics_point_adoption_service.materialize` requires an ACTIVE
adoption, an ACTIVE/VERIFIED global point, valid type/geography, and duplicate
checks before it creates `LogisticsPoint`.  `project_configuration` then
selects only active `ProjectLogisticsPoint` records.  Thus acceptance does not
create an operational point, project association, tracking event, or public
geography entry.

**Classification: B — valid governed workflow, with a clear separate
materialization boundary.**  It should not be deleted, renamed, or redesigned
on the UAT symptom alone.  The appropriate UAT explanation is that "accept"
means organization approval, not operational activation; users needing it in a
project must complete the explicit materialization/project-association flow.

## Development verification

`pytest -q backend/tests/test_cargo_options_authorization.py
backend/tests/test_international_reference_reconciliation.py
backend/tests/test_iran_destination_point.py` completed with **19 passed**.

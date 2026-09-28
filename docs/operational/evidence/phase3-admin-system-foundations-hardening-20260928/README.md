# Phase 3 Admin / System Foundations hardening evidence

Date: 2026-09-28. Governance: frozen canonical LPAF v2.7, Level B.

This pack binds the authorized Admin / System Foundations hardening to its
qualified Product commit and to the preserved Human Walkthrough runtime. It is
an automated qualification and integration receipt. It is not a completed
Human Product Walkthrough, release, deployment, or Production record.

## Identity and authority

- Product SHA: `521380b37d4c09a695cd87984f783ef5670cb127`.
- Evidence SHA: the commit containing this evidence pack; the controlled
  integration receipt and final operator report resolve its immutable hash.
- Canonical branch: `integration/golden-controlled`.
- Mission authority:
  [Admin / System Foundations Hardening](../../../product/phase3/ADMIN-SYSTEM-FOUNDATIONS-HARDENING-MISSION-AUTHORITY.md).
- Architecture decision:
  [ADR-070](../../adr/ADR-070-system-organization-admin-and-portable-reference-baseline.md).
- Migration required: **NO**.
- Alembic head: exactly one, `20261012_phase3_cargo_eta`.

## Accepted product result

- System Admin, Organization Admin, and Expert are separate capability domains.
  Tenant administration requires the explicit `organization.admin` membership
  permission; System Admin alone has neither implicit tenant access nor
  impersonation. A self-hosted operator may hold both capabilities explicitly.
- The current-release DN08 boundary is resolved: System Admin owns base
  definitions, Organization Admin controls organization availability, Expert
  selects enabled references, arbitrary tenant base-definition creation is not
  available, and promotion is never automatic.
- `FORWARDER_REFERENCE_CATALOG_V1`, version `1`, checksum
  `sha256:13a0f6361eca01286422b9ca8df165c2e616c2bc2e73919391056ec7647da45a`,
  provides 80 stable definitions: 15 Cargo Types, 12 service types, 10 units,
  9 packaging types, 4 transport means, 23 transport equipment/load-unit
  types, and 7 request transport methods.
- `FORWARDER_STANDARD_ORG_PROFILE_V1`, version `1`, checksum
  `sha256:38795e90a723eb25c1073a6a92278508e9d89c908105074ff767069d4a8bfce8`,
  activates 60 catalog definitions and verifies all 7 request transport
  methods. Plan/apply is explicit, additive, idempotent, conflict-protected,
  and requires explicit confirmation for reactivation.
- Operational Reason codes are immutable server-generated identifiers of the
  form `DLR_<32HEX>` or `EXR_<32HEX>`; Persian title is required, English title
  is optional, and deactivation preserves history.
- SLA semantic targets come only from the governed registry
  (`EXCEPTION_RESPONSE`, `ACTION_FOLLOW_UP`). Organization Admin selects a
  governed target and configures duration. Free-text semantic targets and a
  generic rule engine are absent. Route/milestone targets fail closed as
  `SLA_TARGET_NOT_CURRENTLY_SUPPORTED`.
- Organization logistics global adoption/private-point authority, route-time
  copy, document-requirement administration, closure, automatic assignment,
  reports, portal support/recovery, and Persian-first Admin UX are regression
  qualified.

The catalog baseline includes Packaging `پالت، کارتن، جعبه، صندوق چوبی، کیسه،
بشکه، باندل/بسته، رول/کلاف، فله`; transport means `کامیون/کشنده جاده‌ای، قطار،
کشتی، هواپیما`; and 23 equipment/load-unit definitions: 8 road trailer types,
5 rail wagon types, 8 container types (`20GP`, `40GP`, `40HC`, `20RF`, `40RF`,
`Open Top`, `Flat Rack`, `Tank`) and 2 air ULD types. The 10-unit baseline
includes millimetre (`mm`).

## Qualification

| Gate | Result |
| --- | --- |
| Full backend regression | PASS — 1,570 passed, 121 classified skips, 0 failed, 995.05 s |
| Full frontend regression | PASS — 461 passed in 98 files, 0 failed, 293.66 s |
| Non-release production-mode frontend build | PASS — 2,583 modules |
| TypeScript | PASS |
| ESLint | PASS — 0 errors, 14 retained warnings |
| OpenAPI | PASS — 3.0.3, 239 paths |
| Python compile | PASS |
| Structure / determinism / architecture governance | PASS |
| Current-tree secret scan | PASS — 0 findings |
| PostgreSQL 18 base-to-head migration chain | PASS |
| Phase 3 PostgreSQL 18 qualification | PASS — 15 passed |
| Public Tracking PostgreSQL regression | PASS — 1 passed |
| Real Chrome P3-01..P3-15, MT3 and IPJ-01..04 | PASS — all 21 stages |

The exact-source automated runs report `dirty_source=false` and bind Product
SHA `521380b37d4c09a695cd87984f783ef5670cb127`. Their local evidence roots are:

- `D:\1-webapp\forwarder-dev\admin-system-foundations-qualification-20260928-browser-final`
- `D:\1-webapp\forwarder-dev\admin-system-foundations-qualification-20260928-postgres-final`

The checked-in machine-readable summary is
[qualification-matrix.json](qualification-matrix.json).

## Preserved Human Walkthrough runtime

- Runtime: `D:\1-webapp\forwarder-human-walkthrough-runtime`.
- Pre-apply backup:
  `D:\1-webapp\forwarder-human-walkthrough-runtime\pre-admin-foundations-20260928.dump`.
- Backup SHA-256:
  `FB3299B63F729C9BCD7AEC2DC7C0FFF5C7B26CD137EC81195A1419D9E9A697BF`.
- Catalog apply created 37 missing definitions; the post-apply plan reports
  0 create, 80 unchanged, 0 conflict, and 0 rejected.
- Standard Profile apply created 58 activations and explicitly reactivated
  only `CARGO_AUTOMOTIVE_MECHANICAL_COMPONENTS` and `UOM_PIECE`; the post-apply
  plan reports 0 create, 0 reactivation, 60 unchanged, and 0 conflict.
- The existing organization, Admin, Expert, portal account, domestic Request,
  hostname, 11 Provinces, and Request assignment were preserved. PostgreSQL,
  backend health/readiness, and the frontend are running on the bounded local
  walkthrough environment.

## Honest boundary

```text
LPAF_BASELINE=2.7
ADMIN_SYSTEM_MODEL=PASS
DN08_STATUS=RESOLVED_FOR_CURRENT_RELEASE
REFERENCE_CATALOG_V1=PASS
STANDARD_ORG_PROFILE_V1=PASS
FULL_BACKEND_REGRESSION=PASS
FULL_FRONTEND_REGRESSION=PASS
SLICE_JOURNEYS=PASS
INTEGRATED_PRODUCT_JOURNEYS=PASS
AUTOMATED_PRODUCT_JOURNEYS=PASS
PRODUCT_AUTHORITY_RECONCILIATION=PASS
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
MIGRATION_REQUIRED=NO
ALEMBIC_HEAD=20261012_phase3_cargo_eta
ALEMBIC_HEAD_COUNT=1
NEW_PHASE3_FINAL_PRODUCT_HEAD=521380b37d4c09a695cd87984f783ef5670cb127
WALKTHROUGH_DATABASE_PRESERVED=YES
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
EXTERNAL_RECOVERY_EMAIL_DELIVERY=RELEASE_UAT_EVIDENCE_REQUIRED
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
RELEASE_READY=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
PRODUCTION_MIGRATION_PERFORMED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
NEXT_STEP=PRODUCT_OWNER_RESUME_ADMIN_WALKTHROUGH_THEN_EXPERT_REQUEST_TO_SHIPMENT_JOURNEY
```

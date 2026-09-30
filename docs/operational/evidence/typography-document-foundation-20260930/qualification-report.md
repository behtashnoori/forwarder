# Typography and Document Foundation — Qualification Report

## Candidate and authority

| Field | Result |
| --- | --- |
| Governing baseline | `LPAF v2.6 — ACTIVE / FROZEN / CANONICAL` |
| Starting canonical SHA | `4e1709f2dd50f350c69a202bbf71727a654fd3c9` |
| Source candidate SHA | `b49d46ca3c1c3b4e33fe5b36ed7e0a7d377b8dbe` |
| Extracted Product SHA | `833186409a93b100633351c702cacb941e0a4259` |
| Rigor / route | `Level B / Sol` |
| Product authority | Product Owner mission “FORWARDER — INTEGRATE QUALIFIED TYPOGRAPHY + DOCUMENT FOUNDATION ONLY”, 2026-09-30 |
| Human Product Walkthrough | `IN_PROGRESS` |
| Release Ready | `NO` |

The repository `AGENTS.md` and the canonical LPAF acceptance record govern with
v2.6. The source mission's v2.7 baseline assertion conflicts with that frozen
authority and was not applied. Product scope remains exactly the authorized
typography/presentation refinement and the four generic Document Types.

## Exact extraction and diff safety

`TYPOGRAPHY_DIFF_PATHS`

- `package.json`, `package-lock.json`, `tailwind.config.ts`
- `src/main.tsx`, `src/index.css`, `src/lib/formatQuantity.ts`
- `src/components/Header.tsx`, `src/components/OperationsNav.tsx`
- `src/components/DeliverySection.tsx`, `src/components/OccurrenceTimeAction.tsx`
- `src/components/ShipmentCargoItems.tsx`, `src/components/ShipmentDocuments.tsx`
- `src/components/ShipmentEconomicsSection.tsx`, `src/components/SiteSettingsTab.tsx`
- `src/components/ui/button.tsx`, `src/components/ui/card.tsx`
- `src/components/ui/input.tsx`, `src/components/ui/label.tsx`
- `src/components/ui/localized-file-input.tsx`
- `src/pages/CustomerPortalShipments.tsx`, `src/pages/NewOperation.tsx`
- `src/pages/OperationalShipmentDetail.tsx`
- `src/tests/components/CanonicalLocationPicker.test.tsx`, `src/tests/pages/NewOperation.test.tsx`

`DOCUMENT_PACKAGE_DIFF_PATHS`

- `backend/reference_data/documents/document-catalog-v1-operational-generic-v1.0.0.json`
- `backend/tests/test_v1_operational_document_catalog.py`

`GOVERNANCE_EVIDENCE_PATHS`

- `docs/product/phase3/TYPOGRAPHY-DOCUMENT-FOUNDATION-MISSION-AUTHORITY.md`
- `docs/operational/evidence/typography-document-foundation-20260930/qualification-report.md`
- `docs/operational/evidence/typography-document-foundation-20260930/qualification-summary.json`

`EXCLUDED_LIFECYCLE_DIFF_PATHS = NONE`

`EXCLUDED_LIFECYCLE_DIFF_PATHS_NOT_INTEGRATED = YES`

The source candidate's runtime and test tree is byte-identical to the extracted
Product SHA. The only candidate-to-extraction difference is governance: the old
broad v2.7 authority file was removed and replaced by the subset-specific v2.6
authority record. No operational-stage, Project binding, Shipment `project_id`,
stage vocabulary, closure evaluator, closure criterion, policy, or Shipment
closure-state implementation path is present.

## Document package

The governed package validates with checksum
`sha256:657625053e373a80fcb80b18e83077e0063ca44d6a04bdd122a7653ba0596820`.
Its read-only plan against the preserved walkthrough PostgreSQL database has
fingerprint
`sha256:549ec64efcc9a4dec1200c2079af7002be9128d2a56082241a12902685521353`,
zero conflicts, and exactly four `CREATE` actions:

1. `generic_transport_document` — `بارنامه` / `Transport Document`
2. `generic_invoice` — `فاکتور` / `Invoice`
3. `generic_packing_list` — `پکینگ لیست` / `Packing List`
4. `generic_delivery_receipt` — `رسید تحویل` / `Delivery Receipt`

All definitions are global, mode-independent, organization-overridable,
Product-Owner-provenanced generic operational vocabulary. They contain no
statutory, customs, legal-proof, carrier, or contractual-requirement claim.

## Qualification results

| Gate | Result | Evidence |
| --- | --- | --- |
| Font/package | `PASS` | `@fontsource-variable/vazirmatn@5.3.0`; package declares `OFL-1.1`; production build emits Arabic, Latin, and Latin-ext WOFF2 assets |
| Focused backend | `PASS` | 26 passed: V1 package, package lifecycle, organization policy |
| Focused frontend | `PASS` | 9 files / 85 tests |
| Frontend | `PASS` | 100 files / 479 tests on clean isolated rerun |
| Type-check | `PASS` | `npx tsc -b` |
| Production build | `PASS` | Vite 6.4.3; 2,588 modules; existing large-chunk warning only |
| Lint | `PASS` | 0 errors, 16 existing warnings |
| Architecture/governance | `PASS` | structural checker plus governance test |
| Diff safety | `PASS` | runtime/test tree matches source candidate; lifecycle path scan empty |
| Browser journey | `PASS` | exact Product SHA frontend against preserved local API; normal Expert login/navigation to Shipment Workspace, RTL/LTR, form, UOM/status, and localized file input verified; no Expert business action |

The first concurrently-loaded full frontend run recorded one 5-second timeout
in an unrelated `LocationForm.destination` test after 478 passes. The timed-out
file then passed 10/10 alone, and the complete suite passed 479/479 when rerun
without competing build/lint workloads. No test or timeout baseline was changed.

Browser evidence on the exact extracted Product SHA established:

- `GLOBAL_FONT_APPLIED=YES`: body and UI controls resolve to `Vazirmatn Variable`; `document.fonts.check(...)` is true.
- `NAV_TYPOGRAPHY_UPDATED=YES`: normal public and Expert navigation rendered with the qualified font.
- `SHIPMENT_WORKSPACE_TYPOGRAPHY_UPDATED=YES`: normal Expert navigation reached Shipment `c66be7ef-ee20-4d39-a985-a3db5bd611db`; `.shipment-workspace` resolves to the qualified font.
- `FORM_TYPOGRAPHY_UPDATED=YES`: localized sign-in and document input presentation rendered correctly.
- `RTL_LTR_RENDERING_PASS=YES`: Persian RTL and English LTR both had zero document horizontal overflow.
- `LOCALIZATION_POLISH_PASS=YES`: Shipment status, quantity labels, UOM `عدد`, and file-input strings `انتخاب فایل‌ها` / `فایلی انتخاب نشده است` were visible.

## Preserved runtime — pre-apply snapshot

Runtime: dedicated local PostgreSQL 18 database `forwarder_human_walkthrough`,
schema head `20261014_canonical_geography_locations`. Read-only inspection before
integration/configuration proved:

- `DOCUMENT_TYPE_COUNT=0`
- `DOCUMENT_REQUIRED_COUNT=0`
- `ORGANIZATION_DOCUMENT_POLICY_COUNT=0`
- `OPERATIONAL_STAGE_COUNT=0` (`project_milestone_definition`)
- `CLOSURE_POLICY_ACTIVE=0` (`closure_policy_version`)
- Shipment `project_id=NULL`; no Shipment upload; no operational document requirement.
- Requested `100`, Planned `100`, Actual Cargo `UNKNOWN`, Planned Allocation `100`, Actual Allocation `95`, Delivered `95`, historical destination `بندرعباس`, manual position `نزدیک مرز`.

The two existing route-plan `operational_milestone` rows are route facts, not the
excluded Project-scoped operational-stage definitions; no such definition exists.

## Product Authority Reconciliation

| Observable difference | Classification | Evidence |
| --- | --- | --- |
| Global/nav/workspace/form typography, rhythm, bidi, localized presentation | `AUTHORIZED` | explicit Product Owner mission; browser and frontend evidence |
| Four generic document vocabulary entries | `AUTHORIZED` | explicit Product Owner mission; checksum-locked package and focused tests |
| Business logic, authorization, Shipment/Route/ETA/allocation/Delivery semantics | `PRESERVED` | diff classification and 479/479 regression suite |
| Operational-stage model/configuration and Shipment Project binding | `PRESERVED` | no changed path; pre-apply runtime count remains zero |
| Closure model/evaluator/criteria/policy/state | `PRESERVED` | no changed path; pre-apply runtime count remains zero |

`PDA_07_RECONCILIATION = PASS`

`PRODUCT_BEHAVIOR_CHANGED = NO` — user-facing presentation and authorized
reference vocabulary changed; business rules, lifecycle, authority, and
transactional behavior did not.

`JOURNEY_IMPACT = AFFECTS_EXISTING_JOURNEY`

`JOURNEY_RESULT = PASS`

## Gate disposition

- Engineering Complete: `YES` for the extracted Product subset.
- Product Complete: `NO`; the Human Product Walkthrough remains in progress and the separate stage/closure Product gaps remain unresolved.
- Release Ready: `NO`.
- Release Complete: `NO`.
- Production accessed/mutated: `NO/NO`.
- Deployment performed: `NO`.
- Release created: `NO`.

Controlled canonical integration is authorized only from this independently
qualified Product SHA and its evidence commit. The preserved runtime package
apply occurs afterward using the reviewed checksum and plan fingerprint.

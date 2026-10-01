# Human Walkthrough open findings — 2026-10-01

## Mission / Product Authority Record

Baseline: tracked canonical `AGENTS.md` specifies LPAF v2.7 ACTIVE / FROZEN /
CANONICAL. The earlier untracked entry v2.6 is superseded. Entry canonical SHA:
`7a9a37613c2115e7d6e8fadf90c6e42f08a50f61`; clean, fast-forwarded from
`5f0c9bcd5579ac6d503a65fe5c3fb92ac4bd07ab`, remote verified equal. No other
active Forwarder Product mission was visible in the app at entry.

Rigor B; capability Sol for coupled diagnosis and verification. Stages M0–M6,
controlled integration and local walkthrough refresh only. No release authority.

- AUTHORIZED_PRODUCT_CHANGES: the Product Owner's supplied batch correction
  mission §§4–11: consistent canonical geography and Persian labels; immediate
  Expert Organization Location creation and later Admin review; symmetric
  Direct Operation endpoints; document information hierarchy and closed-state
  mutation denial; complete localized history; closed Summary; date/time/RTL.
- DELEGATED_TECHNICAL_CHOICES: shared adapters/components, stable-identity
  presentation corrections, existing guards and locale infrastructure, focused
  regression tests and disposable PostgreSQL 18/browser qualification.
- PROTECTED_OUT_OF_SCOPE_BEHAVIOR: all Request/Quote/Shipment/Route/Execution/
  Cargo/Allocation/Delivery/Tracking/Stage/Closure facts; ETA_RULESET_V2,
  tenant isolation, permissions, immutable history and qualified journeys.
  No new geography source, workflow engine, localization/design platform, GIS,
  UN/LOCODE integration, legal semantics, or unrelated capabilities.
- DECISIONS_NEEDED: none within the explicit supplied scope; stop for dirty or
  divergent canonical, concurrent Product mutation, or unreconciled authority.
- APPROVING_OWNER_OR_AUTHORITY: Product Owner issuing this batch mission.
- APPROVAL_REFERENCE: supplied “FORWARDER — HUMAN WALKTHROUGH OPEN-FINDINGS
  CONSOLIDATION”, 2026-10-01, §§1–23.

DoD: all HIGH findings resolved with root-cause evidence, focused frontend and
PostgreSQL 18 tests, affected integrated browser journeys, exact Product SHA,
controlled integration/push/fetch with 0/0 divergence; only then refresh the
preserved runtime and verify read-only. Human walkthrough stays IN_PROGRESS;
Release Ready stays NO. Required checks not run are not PASS.

## Current state, ownership, and verification

Read-only SQL confirmed migration `20261015_org_shipment_stages`, Shipment
`c66be7ef-ee20-4d39-a985-a3db5bd611db` is `closed`, with existing NORMAL immutable
ClosureDecision `a7eb41d7-e2f8-49b7-80b7-7a0593960c96`. Runtime:
`D:\1-webapp\forwarder-human-walkthrough-runtime`. No business action performed.

Country → Admin1 → City is Platform/Shared Reference owned by the existing
Country/Province/City SOR and governed GEONAMES_ADMIN1_CITY_V1 package. Location
is tenant master data in LogisticsPoint; PENDING_REVIEW is immediately usable.
CanonicalLocation retains operational identity and historical snapshots.
Documents retain separate storage, context and evidence requirements. Closure
history comes only from ClosureDecision; Unified History is a derived read.

The chain is source catalog / authorized command → existing SOR → shared
selector/read model → operator selection/history/readiness → canonical
reference or immutable evidence → authorization and regression verification.
Presentation fixes do not rewrite stable identities or historical snapshots.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J03/J04/J05/J06/J08/J09 and
FWD-IPJ-01/02/03/04; reference pack:
`docs/product/FORWARDER-PRODUCT-ACCEPTANCE-JOURNEYS-V1.1-FA.md`.
Affected Phase 3 slices: reference catalog, documents, reported facts, delivery,
route/ETA, closure, ownership. Regression qualification must preserve normal
navigation, Expert scope, Admin review, negative API and cross-tenant paths.

LPAF reference impact NONE: frozen baseline unchanged. Project reference impact
UPDATE_REQUIRED: this finding/authority register and affected API/architecture
contracts. Existing Product contract and ETA semantics remain protected.

## PDA-08 clarification: closed document repair

The Product Owner explicitly selected: “Preserve historical document repair,
clearly separated from the read-only closed workspace.” This reconciles §8.3
with `P3-12-POST-CLOSURE-COMMAND-MATRIX.md`. Closed Documents default to read-only;
an explicit historical-repair entry retains existing authorized document
commands. New operational commands remain denied by the backend. Closure is
immutable; no blanket document-write denial or reopen is introduced.

## Finding register (qualification pending)

| ID | Surface | Severity | Observed behavior | Root cause | Correction | Evidence | Status |
|---|---|---|---|---|---|---|---|
| HW_GEO_001 | Country selectors | HIGH | Inconsistent country lists | Investigation pending | Pending | NOT_RUN | OPEN |
| HW_GEO_002 | Canonical city | HIGH | Isfahan not found | Stored localized label is أصفهان; stable ID 418863 exists under 418862 | Pending | Read-only SQL | OPEN |
| HW_GEO_003 | Admin1 | MEDIUM | هرمزجان | Localized catalog label for stable ID 131222 | Pending | Read-only SQL | OPEN |
| HW_GEO_004 | City labels | POLISH | Mixed Persian/English | Primary option composition | Pending | Source inspection | OPEN |
| HW_GEO_005 | Shared selectors | HIGH | Different results | Multiple consumer search contracts | Pending | Source inspection | OPEN |
| HW_GEO_006 | Endpoint search | HIGH | Duplicate-looking Tehran | Investigation pending; canonical City is 112931 | Pending | Read-only SQL | OPEN |
| HW_GEO_007 | Direct Operation | MEDIUM | Asymmetric endpoints | Legacy domestic/international side branches | Pending | NewOperation.tsx | OPEN |
| HW_LOCATION_001 | Operational Location | HIGH | Missing inline creation journey | Shared picker not used on Direct Operation | Pending | CanonicalLocationPicker.tsx | OPEN |
| HW_DIRECT_OP_GEO_001 | Direct Operation | HIGH | Mixed untyped choices | Legacy selector composition | Pending | NewOperation.tsx | OPEN |
| HW_DOC_001 | Documents | HIGH/UX | Requirements/files/references/exceptions mixed | Page hierarchy | Pending | OperationalShipmentDetail.tsx | OPEN |
| HW_DOC_002 | Documents | MEDIUM | Requirement/file relation unclear | Separate upload and requirement panels | Pending | Source inspection | OPEN |
| HW_DOC_003 | Documents | MEDIUM | Technical operator wording | Presentation copy | Pending | DocumentReadinessSection.tsx | OPEN |
| HW_DOC_004 | Closed Documents | HIGH | Mutation controls visible | Closed state not passed to components; backend audit pending | Pending | Source inspection | OPEN |
| HW_HISTORY_002 | History | HIGH | Closure category empty | Client filters only current page; authoritative closure branch already exists | Pending | Source inspection | OPEN |
| HW_HISTORY_003 | History | MEDIUM | English primary labels | Incomplete display localization | Pending | Source inspection | OPEN |
| HW_HISTORY_DENSITY | History | UX | Repetitive technical metadata | All metadata expanded | Pending | Source inspection | OPEN |
| CLOSED_SUMMARY_SEMANTICS | Summary | UX | Readiness shown as unfinished objective | Shared active/closed copy | Pending | Source inspection | OPEN |
| HW_DATE_TIME_RTL | Affected surfaces | MEDIUM | Native US date placeholders, raw transport, arrows | Presentation controls | Pending | NOT_RUN | OPEN |

## Results

Engineering Complete=NO; Product Complete=NO; Release Ready=NO;
Release Complete=NO; HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS.
All implementation and qualification results remain pending.

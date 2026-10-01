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

## Finding register

Evidence root: `D:\1-webapp\forwarder-dev\human-open-findings-evidence`.
The final evidence index below binds each result to its tested candidate.

| ID | Surface | Severity | Observed behavior | Root cause | Implemented correction | Qualification evidence | Status |
|---|---|---|---|---|---|---|---|
| HW_GEO_001 | Country selectors | HIGH | Incomplete/inconsistent countries | Authenticated geography read hard-coded 14 countries rather than complete Country SOR | All active countries with explicit supported-depth flag; shared picker | PG geography; HW-GEO across Direct/Route Reference/Delivery/Admin | RESOLVED |
| HW_GEO_002 | Canonical city | HIGH | Isfahan unavailable | Existing City 418863 under Admin1 418862 stored as أصفهان; unnormalized search and silent 200-row cutoff | Normalized names/aliases, exact matches first, explicit paging, identity-based Persian display | PG search/pagination/parent test; HW-GEO Isfahan in all selectors | RESOLVED |
| HW_GEO_003 | Admin1 | MEDIUM | هرمزجان | Source localized name for GeoNames 131222 | Shared presentation erratum هرمزگان; source identity/row unchanged | PG stored-name preservation; HW-GEO | RESOLVED |
| HW_GEO_004 | City labels | POLISH | English/Persian primary labels mixed | Multiple primary option compositions | Persian-first typed labels; alternate names and IDs in details | HW-GEO desktop screenshots; picker tests | RESOLVED |
| HW_GEO_005 | Shared selectors | HIGH | Different results across surfaces | Legacy mixed endpoint reads versus bounded canonical read | Shared Country/Admin1/City picker/read contract for affected surfaces | HW-GEO same identities across five surfaces | RESOLVED |
| HW_GEO_006 | Endpoint search | HIGH | Two Tehran-looking choices | City id 17504 / GeoNames 112931 and InternationalCity id 57 / IRTHR mixed as primary cities | Primary cities from canonical City; stable-identity deduplication; physical references separately typed | Read-only source SQL; PG hierarchy; HW-GEO unique Tehran | RESOLVED |
| HW_GEO_007 | Direct Operation | MEDIUM | Asymmetric endpoints | Domestic/international side-specific branches | Both sides use Organization Location or shared canonical geography | Direct Operation tests; HW-GEO | RESOLVED |
| HW_LOCATION_001 | Organization Location | HIGH | Inline creation not discoverable | Direct Operation omitted existing shared picker flow | Inline minimum name and known geography; immediate PENDING_REVIEW selection; existing Admin review | PG create/use/enrich/approve/deactivate and frozen route snapshot; HW-GEO Admin journey | RESOLVED |
| HW_DIRECT_OP_GEO_001 | Direct Operation | HIGH | Mixed untyped endpoint choices | Legacy endpoint composition | Symmetric typed shared selectors; physical references in separate detail | Direct Operation frontend tests; HW-GEO; owner/cargo browser journeys | RESOLVED |
| HW_DOC_001 | Documents | HIGH/UX | Requirements/files/references/exceptions mixed | Page hierarchy; CSS grid overrode hidden exceptions attribute | Requirements and files primary, references collapsed; exceptions only render under Route | Closed Documents browser assertion and screenshot; document-context journey | RESOLVED |
| HW_DOC_002 | Documents | MEDIUM | File/requirement relationship unclear | Upload and readiness panels lacked contextual explanation | Independent upload explains it does not satisfy a requirement automatically; requirement shows exact associated file/version and source link | Readiness frontend tests; document-context upload/version/privacy journey | RESOLVED |
| HW_DOC_003 | Documents | MEDIUM | Technical operator wording | Materialization-oriented copy | ثبت مدارک مورد نیاز این محموله and concise relationship explanation | Frontend readiness tests; browser Documents | RESOLVED |
| HW_DOC_004 | Closed Documents | HIGH | Mutation controls visible by default | Closed state not supplied to requirements/files/references | Default read-only; explicit historical repair under clarified Product authority; existing backend new-operation denials retained | PG closed-command denial and audited historical repair with frozen ClosureDecision; closed browser toggle and no-upload default | RESOLVED |
| HW_HISTORY_002 | History | HIGH | Closure category empty | Client filtered only current unfiltered page; authoritative closure branch already existed | Server category filter/count before pagination across composed feed | PG closure beyond first 50 / category page size 1 / immutable decision identity; closure browser category | RESOLVED |
| HW_HISTORY_003 | History | MEDIUM | Reported and other primary English labels | Incomplete presentation mapping | Semantic Persian event titles without enum changes | Unified History frontend; full lifecycle PG/browser; preserved read-only PASS | RESOLVED |
| HW_HISTORY_DENSITY | History | UX | Repetitive technical metadata | Expanded recorded/source/provenance/version fields | What/when/who primary; technical audit detail retained in collapsed disclosure | Unified History tests; closure category desktop/mobile | RESOLVED |
| CLOSED_SUMMARY_SEMANTICS | Summary | UX | Closed readiness appears unfinished | Shared active/closed guidance labels | کامل بودن اطلاعات and informational warnings; no operational primary CTA; unknown cargo remains unknown | Guidance frontend; closed Summary browser; preserved read-only PASS | RESOLVED |
| HW_DATE_TIME_RTL | Affected forms | MEDIUM | US date placeholders, raw road, ambiguous direction and units | Native datetime display and inconsistent presentation helpers | Existing UTC converter with Persian digit entry and dual-calendar hint; localized transport/unit labels; explicit از…به… direction | Date converter/control tests; TypeScript/build; Route Reference/ETA/closure/browser desktop | RESOLVED |

## Group accounting

There are 18 unique findings. Group counts overlap where a single root-cause fix
serves several surfaces; they must not be summed as unique findings.

| Group | Finding mapping | FINDINGS_START | FINDINGS_RESOLVED | FINDINGS_REMAINING |
|---|---|---:|---:|---:|
| GEOGRAPHY | HW_GEO_001–007 | 7 | 7 | 0 |
| ORGANIZATION_LOCATION | HW_LOCATION_001 | 1 | 1 | 0 |
| DIRECT_OPERATION | HW_DIRECT_OP_GEO_001, HW_GEO_007, HW_DATE_TIME_RTL | 3 | 3 | 0 |
| ROUTE_REFERENCE | HW_GEO_001/002/004/005/006, HW_DATE_TIME_RTL | 6 | 6 | 0 |
| DOCUMENTS | HW_DOC_001–004 | 4 | 4 | 0 |
| UNIFIED_HISTORY | HW_HISTORY_002/003/DENSITY | 3 | 3 | 0 |
| CLOSED_SHIPMENT_SUMMARY | CLOSED_SUMMARY_SEMANTICS | 1 | 1 | 0 |
| DATE_TIME_RTL | HW_DATE_TIME_RTL | 1 | 1 | 0 |

## Architecture / Product reconciliation

- AUTHORIZED: affected picker/search/label behavior, document hierarchy,
  category filtering, closed presentation and localized datetime controls.
- PRESERVED: Country/Province/City and LogisticsPoint ownership; canonical
  identities; legacy physical reference compatibility; Request/Quote and Cargo
  lineage; permissions/tenant/owner scope; route topology; ETA_RULESET_V2;
  delivery finality; immutable closure and audit facts.
- PRESERVED: local datetime inputs are device-local wall-clock values converted
  to UTC Instants by the existing helper. No timezone or stored timestamp change.
- ADRs followed: 005 canonical location/snapshots, 030 readiness, 047 fixed owner,
  050 document management/history, 061 exact document versions/visibility,
  062 live customer entitlement, 064 delivery, 066 route-time basis, 067 ETA,
  068 closure, 074 canonical geography and 075 shipment stages.
- Architecture deviation: NONE. No new SOR, aggregate, workflow, geography source,
  legal semantics or cross-domain write. Sole migration head unchanged:
  `20261015_org_shipment_stages`; no migration or data repair required.
- Rollback: revert product source and restart the local application; no database
  rollback/reconciliation is needed or authorized.
- References updated: `docs/API.md` and the architecture baseline's bounded shared
  read-contract addendum. Frozen LPAF baseline remains unchanged.

## Qualification and integration

Failed attempts remain in the external local evidence directory. The passing
entries below supersede their earlier failed attempts, not unrelated checks.
Test-only selector updates preserve normal UI navigation and assertions for the
already-qualified Persian workspace. They do not grant new Product authority.

| Proof | Result | Evidence path relative to evidence root | Tested candidate |
|---|---|---|---|
| Frontend suite | 103 files / 493 tests PASS | `frontend-final.log` | `ffffd3d8` |
| Final Shipment detail / Documents panel render | 32 tests PASS | `detail-final.log` | `46a475bf` |
| Required + optional document read-only behavior | 4 tests PASS, including one additional case | `document-readiness-final.log` | `2f4441ec` |
| TypeScript, build, changed-source ESLint, structure | PASS | `tsc-final.log`, `build-final.log`, `lint-final.log`, `structure-final.log` | final product source |
| Existing affected PostgreSQL regressions | 17 PASS; two new fixture failures superseded below | `pg-attempt1/postgresql-phase3.log` | `ee8ca648` |
| Geography/location and full lifecycle/closure/history PostgreSQL | 2 PASS after fixture-only corrections | `pg-focused3/postgresql-phase3.log` | `ffffd3d8` |
| PostgreSQL 18 base-to-head migration / public tracking | PASS / 1 PASS | `pg-focused3/result.json`, `pg-focused3/public-tracking-postgresql.log` | `ffffd3d8` |
| Geography across shared surfaces / Expert → Admin Location | 1 PASS | `browser-hw-attempt1/HW-GEO/browser.log` | `965524a4` |
| Platform/organization Admin and reference catalog | 3 PASS | `browser-regression4/P301/browser.log` | `f14a20a7` |
| Cargo continuity and execution | 2 PASS | `browser-regression5/P304/browser.log` | `316c2665` |
| Reported facts / delivery finality and correction | 1 + 1 PASS | `browser-regression5/P307/browser.log`, `P308/browser.log` | `316c2665` |
| Document context/version/history and customer entitlement | 2 PASS | `browser-final-doc-integrated/P306/browser.log` | `0f932f88` |
| Five stages → final delivery → normal closure → closed Documents/History/Summary | 1 PASS | `browser-final-doc-integrated/HW-STAGES/browser.log` | `0f932f88` |
| Route Reference pinned basis / versions / tenant scope | 1 PASS | `browser-closure3/P310/browser.log` | `f14a20a7` |
| ETA, progress, customer privacy and pinned version | 4 PASS | `browser-final-closure/P311/browser.log` | `0f932f88` |
| Fixed owner / Direct Operation / context continuity | 1 PASS | `browser-owner-actions-final/IPJ01/browser.log` | `8a8d7651` |
| Closure blockers / authorized exception / customer privacy | 1 PASS | `browser-closure-integrated-complete/P312/browser.log` | `2a079753` |
| Action / follow-up / SLA and monitoring reliability | 3 + 1 PASS | `browser-actions-monitoring-complete/result.json` | `c6b7185b` |
| Guided Operational Workspace and Phase 1 integrated regression | 12 tests / 14 journeys PASS | `guided-final/result.json` | `146c4124` |
| FWD-IPJ-04: owner transfer → history → ETA → customer privacy → closure → post-close denial | 2 PASS on one continued Shipment | `browser-ipj04-final/result.json` | `f77bb47e` |

PostgreSQL implementation is byte-equivalent to `ee8ca648` after the new test
fixture repairs; final Product source is `46a475bf`. All later commits modify
only tests, fixtures or reference/evidence documents. The only source change
after the 493-test run was conditional rendering of the Route-only exceptions
panel; its affected 32-test detail suite and final closed browser proof pass.
The later required/optional read-only test also passes. No single uninterrupted
19-test PostgreSQL green run or 494-test frontend run is claimed.

The initial closed Documents browser proof exposed a real CSS interaction:
`display:grid` overrode the HTML `hidden` attribute. Conditional rendering fixed
the defect at `46a475bf`; the final Documents screenshot and visibility assertion
confirm exceptions are absent. Other rejected attempts involved outdated UI
selectors or disposable-fixture setup, and one excess-concurrency memory failure.
They are retained locally; selected passing evidence must be used for qualification.

Desktop visual review: Persian canonical selections, inline Location creation,
Admin review and structured Delivery share identities; closed Documents have no
default file input, an explicit historical-repair entry and collapsed transport
references; the Closure category shows one localized event with collapsed audit
metadata. Mobile checks preserve the previously-qualified layout boundaries.

PRODUCT_SHA=`46a475bf4eeece27a57d3f1a7a0e5eb004aa6482`.
Subsequent commits contain test/fixture/reference updates only.
FOCUSED_TESTS=PASS; POSTGRESQL_RESULT=PASS; FRONTEND_RESULT=PASS;
JOURNEY_RESULT=PASS (36 selected browser tests, including 12 guided tests).
All 18 unique findings, including all 9 HIGH findings, are RESOLVED.
The hash-bound proof index is `HUMAN-WALKTHROUGH-OPEN-FINDINGS-20261001-EVIDENCE.json`.
Controlled integration fast-forwarded `integration/golden-controlled` to
`58478e5b4b9f3c58903e65a347a41e584cc038a5`, pushed, fetched and verified 0/0 before
refreshing the same preserved runtime. The final evidence-only commit follows
this integration; its hash is the final EVIDENCE_SHA / FINAL_CANONICAL_SHA and is
recorded in the local runtime manifest and completion report.
Engineering Complete=YES; Product Complete=NO; Release Ready=NO;
Release Complete=NO; HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS.

## Preserved runtime verification — completed 2026-10-02 local time

Same runtime root, hostname, database, PostgreSQL 18 process (PID 266136), data
directory and migration head. Only the owned backend/frontend processes were
restarted after canonical integration. No migration, seed, Location, Route
Reference, upload or operational command was performed on the preserved runtime.

Read-only Chrome proof at 1440×1000: Closure category contains the one original
decision, titled «پرونده بسته شد»; «Reported» is absent from primary History;
closed Summary shows «کامل بودن اطلاعات», 5/5 stages and historical information
warnings with no operational primary CTA. Documents are read-only with a separate
historical-repair entry and collapsed transport references. The canonical picker
returns all 249 countries and the correct Iran/Isfahan/Hormozgan labels/identities.
Screenshots were visually inspected after the document list finished loading.

Verification used an existing active Expert session, without login/session
writes. Browser interception allowed only GET/HEAD/OPTIONS API requests:
write attempts=0, browser errors=0, API errors=0. Temporary authentication material
was deleted. Early verifier attempts corrected a runtime-key lookup and scoped
History counting to its own list; they made no database writes.

Full data-only snapshots at mission entry, immediately before refresh and after
the final read-only verification have the identical normalized SHA-256:
`CB8E7285B343EA68E632F59BBE228CEDA16C1E8EE9CAE183C032908C9736D5DB`.
Normalization excludes only random pg_dump restrict/unrestrict tokens, joins
UTF-8 lines with LF and retains a final LF. Database rows and sequence values
remain unchanged. Protected-fact JSON comparison also matches exactly.

Preserved: CLOSED Shipment `c66be7ef-ee20-4d39-a985-a3db5bd611db`; Request/Quote,
route/execution/cargo and every audit/history row; planned allocation 100;
actual allocation 95; actual cargo UNKNOWN; current explicit final delivery 95;
five completed stages; departure/arrival; manual position «نزدیک مرز»; immutable
NORMAL ClosureDecision `a7eb41d7-e2f8-49b7-80b7-7a0593960c96`. The older nonfinal
95 delivery remains historical and is not added to its superseding final 95.

Runtime evidence: `D:\1-webapp\forwarder-human-walkthrough-runtime\open-findings-20261001`.
Receipt: `preservation-receipt.json`; browser result: `readonly-browser-result.json`;
screenshots: `preserved-closed-summary.png`, `preserved-closure-history.png`,
`preserved-localized-history.png`, `preserved-documents-readonly.png`,
`preserved-geography-readonly.png`. Hashes are included in the evidence index.

WALKTHROUGH_DATABASE_PRESERVED=YES;
WALKTHROUGH_CLOSED_SHIPMENT_PRESERVED=YES;
WALKTHROUGH_BUSINESS_ACTIONS_PERFORMED=0;
PRODUCTION_ACCESSED=NO; PRODUCTION_MUTATED=NO;
DEPLOYMENT_PERFORMED=NO; RELEASE_CREATED=NO;
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS; RELEASE_READY=NO.

**PASS — HUMAN WALKTHROUGH OPEN FINDINGS CONSOLIDATED AND QUALIFIED**

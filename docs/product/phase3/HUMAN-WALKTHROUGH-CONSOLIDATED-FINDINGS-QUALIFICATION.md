# Consolidated Human Walkthrough findings — qualification and handoff

The second Shipment had already arrived. Both route occurrences were recorded at
2026-10-02 18:53:54 +03:30, with distinct event IDs and later recording times.
Its Cargo actual quantity is still unknown; the allocation of 100 is not an
actual Cargo quantity. No structured remaining-distance report exists. V2
correctly refuses a Cargo forecast with ambiguous coverage and conflicting
positions. The presentation defect hid the independently known 900 km pinned
reference and the recorded completion. These are now separate current facts;
saved estimates and their historical reasons remain unchanged.

Next manual action: open the second Shipment's Route and Tracking/ETA views to
review its recorded arrival and the current basis explanation. Do not record
another departure or progress report to make this completed route appear in
transit. An in-transit Human Walkthrough requires a separate explicitly
authorized scenario. No such scenario was created.

## Authoritative diagnosis

| Required field | Result |
|---|---|
| ETA_ROOT_CAUSE | Early unavailable-result return omitted known per-leg reference facts; UI called a structured-progress-only distance generically undefined. Forecast unavailability itself is supported by persisted facts. |
| SECOND_SHIPMENT_ACTUAL_LIFECYCLE | COMPLETED; `a2107f0a-83c4-4eb5-9b50-1ecdc59f8c8f` |
| SECOND_ROUTE_LEG_ACTUAL_STATE | COMPLETED; plan2/leg2 |
| DEPARTURE_PRESENT | YES; event3 `a8d05c7c-62f6-4bb7-9fdf-292a1946700c`, recorded 19:03:35.687731 +03:30 |
| ARRIVAL_PRESENT | YES; event4 `ec74301c-9ccb-4561-b79d-f4a883846a87`, recorded 19:04:12.605081 +03:30 |
| PINNED_BASIS_IDENTITY_AND_DISTANCE | `738413d6-ab93-4ad0-ae79-73080323c3c6`, reference version1 `e259d13a-1998-444b-991c-97677c39f528`; 900 km, movement12–16h, stop1–3h |
| STRUCTURED_PROGRESS_STATE | NONE; zero structured progress rows in preserved database |
| CARGO_COVERAGE_STATE | XU7P Cargo2 actual UNKNOWN; planned100, actual allocation100 and planned allocation100; allocation does not establish whole-Cargo coverage |
| ETA_KNOWN_BASIS_PRESENTATION | Current per-leg pin/distance/version and route completion shown independently of saved Cargo estimate |
| ETA_UNAVAILABLE_REASON_ACCURACY | PROGRESS_AMBIGUOUS is retained; current explanation discloses unknown actual Cargo, coverage ambiguity and same-time conflicting positions |
| ETA_NUMERIC_DISPOSABLE_PROOF | Full-coverage synthetic Cargo, 450/900 remaining, reference12–16h ⇒6–8h; final-arrival stop1–3h excluded. PostgreSQL18 independent expected values pass. |
| NEXT_SAFE_MANUAL_ACTION | Read recorded arrival/current route facts on second Shipment. Separate authorization is needed for a new in-transit human scenario. |

The original saved snapshot5 (`3cf5de82-62ce-4da2-b3be-10399884b7cd`)
is preserved, not recomputed by opening,
focusing or refreshing the ETA view. Explicit calculation is separately labelled
and reports new versus reused output. The exact restored human combination was
also evaluated inside a PostgreSQL READ ONLY transaction: 900 km and completion
remain known while the Cargo result remains unavailable.

A separately reproduced occurrence-form defect retained departure time when its
action became arrival, and failed to parse seconds in the displayed default.
The successor form now clears its time; seconds display correctly and duplicate
submission is guarded. This does not establish how the human events were entered.

## Location, commercial and document outcomes

| Required field | Result |
|---|---|
| GEOGRAPHY_HANDOFF_IDENTITY | Request2 `45286ca3-2d0d-48e7-9978-0c7f0bc87248` retains City2773/Shaoxing/GeoNames1795855/Zhejiang129. Explicit reuse uses that exact source identity without first-page search dependence. Shipment3 `55dfafd5-f403-4f14-b445-7061390f8641` retains the deliberately selected City4383/Sanxing/Shanghai149. |
| DEMAND_OPERATIONAL_VARIANCE_PRESENTATION | Source and operational endpoints compared in creation review and main persisted route view; unequal same-type IDs are visibly different; province/city/facility precision differences are neutral, not false mismatches or invented historical approval. |
| REQUESTER_CUSTOMER_LABELS | Optional requester name and linked Organization Customer labelled separately; absent requester name is explicit and is not replaced with CRM identity. |
| QUOTE_DATE_PICKER | Existing shared Persian/Gregorian picker; optional date-only YYYY-MM-DD retained; no timezone conversion. |
| DOCUMENT_LABELS | Persian primary, separate bidi-isolated English in Admin; optional English/acronym retained in Expert selector. |
| DOCUMENT_CONTEXT | Current Shipment is read-only context for SHIPMENT files; other context selectors and exact binding remain. |
| DOCUMENT_VISIBILITY | Eligible customer checkboxes with count and scope explanation; INTERNAL default and server permissions remain. |
| DOCUMENT_UPLOAD_HELP | Short explanation retains upload versus Request-file-version association/review versus readiness distinctions. |

Same-parent search finds Shaoxing; Shanghai filtering correctly excludes it.
HW_GEO_010's missing-data/identity-loss hypothesis is NOT_A_DEFECT_WITH_EVIDENCE.
Shanghai City4384/GeoNames1796236 already existed. Persian search failed against
the source spelling; a stable-ID presentation/search erratum now finds شانگهای.
No catalog import or persisted geography rewrite was performed.

## Qualification

| Required field | Result |
|---|---|
| UNIQUE_FINDINGS_START | 14; upload-copy alias counted once. One newly discovered occurrence-form defect makes15 total. |
| CONFIRMED_HIGH_RESOLVED | 3 — ETA presentation, location handoff (conservatively treated as HIGH), occurrence form |
| CONFIRMED_HIGH_REMAINING | 0 |
| NOT_A_DEFECT_WITH_EVIDENCE | HW_GEO_010: correct-parent retrieval and preserved unequal source identities |
| DEFERRED_NONBLOCKING_ITEMS | None among these current observations; no worldwide geography-import mission was opened. |
| UNVERIFIED_ITEMS | None in the authorized automated scope; Human Walkthrough remains IN_PROGRESS |
| FOCUSED_TESTS | Backend53 PASS; relevant changed Shipment detail32 PASS |
| POSTGRESQL_RESULT | PostgreSQL18 selected contracts8 PASS; customer-location/geography1 PASS; Public Tracking regression1 PASS; fresh base-to-head migration/check PASS |
| FRONTEND_RESULT | 109 files /518 tests PASS; TypeScript and production build PASS; ESLint0 errors/16 existing warnings; structure PASS |
| BROWSER_JOURNEY_RESULT | 7 stages /18 tests PASS: P306(2), P311(4), DOC-PHASE1(1), HW-GEO(1), P315-CORE(3), HW-CONSOLIDATED(1), HW-COMMERCIAL(6) |
| REGRESSION_GUARDS | Exact canonical IDs/parents and stale-child clearing; declared-place eligibility; immutable pins/history; V2 arithmetic/arrival-stop exclusion; ambiguity/staleness/authorization; requester/CRM separation; optional date-only Quote; eligible recipients/INTERNAL privacy/revocation/exact download bytes; closure denial/audited repair and upload-versus-requirement distinction |

| Required scenario | Evidence |
|---|---|
| E1–E3 no pin, pin/no progress, eligible governed departure | Expanded PostgreSQL ETA test and structured-progress suite. Missing progress precedence remains; governed departure can legitimately support V2 full movement without a structured-distance report. |
| E4 450/900,12–16h reference ⇒6–8h | Independent fixed-time PostgreSQL assertions; ETA browser performs real structured-progress command and shows calculated result. Final-arrival stop excluded. |
| E5–E6 actual UNKNOWN, partial/multiple coverage | PostgreSQL quantities null/2 versus allocation1; existing structured-progress ambiguity cases. No allocation-to-actual substitution. |
| E7 arrived | PostgreSQL later arrival yields DESTINATION_REACHED; exact restored human equal-time/unknown combination remains ambiguous while separately displaying completion. |
| E8–E10 newer version, wrong identity/stale, invalid/unauthorized | PG/structured-progress guards and P311 browser; old900km/version1 pin survives a later1800km reference. |
| H1–H3 exact reuse, parent switch, deliberate variance | PG creation/persisted exact-ID assertions plus consolidated browser review/reload/persistence at desktop and390px. |
| H4 declared place and tenant guards | Customer-location PG contract and P315 real intake journey. |
| H5 requester versus linked Customer | Consolidated Request view/reload checks with absent requester name and present CRM identity. |
| H6 Quote date | QuoteModal test plus real creation/reopen PASS; optional YYYY-MM-DD. |
| D1–D8 document UX and protected semantics | Document Phase1, document-context and entitlement PG suites; P306/DOC-PHASE1 browsers; byte assertions, revocation, closed-denial/audited repair and readiness regressions. |

Before failures are retained in `baseline-reproducers.log` and
`before-backend.log` against detached baseline df2cba008fb82117460c0f2f827f4c0939591a7d.
The browser qualification additionally caught a hidden comparison placement;
its failing screenshot/trace and the corrected passing journey are retained.
An old city-label assertion was updated for the new parent/country summary.
Two 5-second test timeouts under concurrent browser/database load prompted a
15-second test allowance; assertions were unchanged. Failed attempts remain in
the evidence tree and are not counted as passes.

Earlier qualification had not sampled the completed/unknown-Cargo/equal-time
combination, successor occurrence form state, exact cross-surface endpoint reuse,
this Quote control or custom bilingual labels. Previous PASS records remain
bounded to their recorded candidate and scope.

## Preservation and boundaries

The pre-change custom-format backup was restored to an owned PostgreSQL18
`recovery_check` database. All190 tables, schema, sequences and protected facts
matched the original read-only baseline. The actual I133.pdf bytes were separately
copied and verified. The live database was not used for business tests.

| Required field | Result |
|---|---|
| MIGRATION_REQUIRED | NO |
| ALEMBIC_HEAD | 20261017_document_type_ownership |
| ALEMBIC_HEAD_COUNT | 1 |
| ALL_THREE_SHIPMENTS_PRESERVED | YES at the pre-integration checkpoint; final refreshed-runtime comparison in final-receipt.json |
| REQUEST_QUOTE_HISTORY_PRESERVED | YES at the pre-integration checkpoint; final refreshed-runtime comparison in final-receipt.json |
| PINNED_REFERENCE_PRESERVED | YES at the pre-integration checkpoint; final refreshed-runtime comparison in final-receipt.json |
| ALLOCATION_AND_ROUTE_EVENTS_PRESERVED | YES at the pre-integration checkpoint; final refreshed-runtime comparison in final-receipt.json |
| CUSTOM_DOCUMENT_TYPE_AND_FILE_PRESERVED | YES at the pre-integration checkpoint; final refreshed-runtime comparison in final-receipt.json |
| WALKTHROUGH_PROTECTED_FACTS_PRESERVED | YES at the pre-integration checkpoint; final refreshed-runtime comparison in final-receipt.json |
| WALKTHROUGH_BUSINESS_ACTIONS_PERFORMED | 0 |
| PRODUCTION_ACCESSED | NO |
| PRODUCTION_MUTATED | NO |
| DEPLOYMENT_PERFORMED | NO |
| RELEASE_CREATED | NO |
| HUMAN_PRODUCT_WALKTHROUGH | IN_PROGRESS |
| PRODUCT_VALIDATION | EVIDENCE_PENDING — automated qualification does not close human Product validation |
| RELEASE_READY | NO |

Data SHA256: `a4ed5b4fe9556196a4915efc2d820cc8eada2505a02765b9e3d63411b569be69`.
Schema SHA256: `22882828c86d368b87c3643780839054964cc1319253d72132d05f052d5f29d2`.
PDF SHA256: `2b06d5229b2220e215a93890fab75a9c62e16bff26a278dd219bbb189013711b`.
Custom backup SHA256: `cc5e3275a0069ff4de7bb2b8e93ccce6d32b031419499531a1fb3b5f15ad17a4`.

## Integration identity

| Required field | Result |
|---|---|
| PRODUCT_SHA | bc167ef1285f21df76024c265028168fcb3adfbd |
| QUALIFICATION_CANDIDATE_SHA | d9487187efe72dad7ccb1f2ef6baa4a442ea2f3f |
| EVIDENCE_SHA | Recorded after this evidence commit in the external final-receipt.json |
| FINAL_CANONICAL_SHA | Recorded in final-receipt.json after controlled integration/push/fetch |
| RUNTIME_SOURCE_IDENTITY | Same D:/1-webapp/forwarder-dev/human-walkthrough-runtime-source; exact refreshed source/process identity recorded in final-receipt.json |
| AHEAD_BEHIND | Verified after push/fetch in final-receipt.json |

Qualification is complete. The post-commit integration/runtime receipt is external
to avoid a self-referencing Git SHA. The completed Product Owner handoff is
`D:/1-webapp/forwarder-dev/consolidated-walkthrough-evidence/FINAL-HANDOFF.md`.
Its final verdict follows successful runtime preservation, not merely these tests.


Source equivalence is recorded in the adjacent evidence JSON. All backend files
are unchanged after a34e3b8d. The final placement change is covered by32 rerun
Shipment-detail tests and the real persisted-handoff browser. The five core
browser stages passed together on clean32907ea1. Later changes only correct the
consolidated synthetic fixture and exact test selector; that affected journey
passed on the final clean qualification candidate. Earlier runs interrupted by
source changes are retained but excluded from final qualification.

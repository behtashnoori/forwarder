# FWD-07 continuation — controlled browser acceptance, 2026-09-16

MISSION_RESULT: BLOCKED_RECOVERY_CONTRACT (not PASS_CONTROLLED_LOCAL_FWD07).

## Candidate and authority

Resumed D:\1-webapp\forwarder-dev, feature/fwd-07-document-attachments, start HEAD 63f8431a0d01a2c4fdc96749a483617668c27905, upstream origin/feature/fwd-07-document-attachments, sole registered worktree, origin https://github.com/behtashnoori/forwarder.git. Start worktree clean. Existing commits preserved.

LPAF entry identity verified: v2.2 globally ACTIVE; v2.4 OWNER_APPROVED / PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE and SHA256 217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397. Baseline, development gate and relevant ADR-020/ADR-030 ownership reviewed. No mother-framework, schema, permission, API, document ownership or temporal contract changed. Harness elapsed times are Durations; no new persisted business timestamps. Existing request compatibility is exercised, not expanded. Canonical execution/MDPM owners untouched. ADR-020 remains PROPOSED, not implementation authority. Reference 28 deferral remains bounded to the existing FWD-07 decision; no new waiver.

FACT: role=expert / authority=EXPERT, active membership, no new permissions, assigned synthetic TENANT requests. Real candidate Flask backend, disposable SQLite browser database, private synthetic storage and local Chromium. PostgreSQL qualification uses a separate disposable PostgreSQL 18 cluster and actual migration CLI.

DECISION NEEDED: safe operation recovery described in PROPOSED-UPLOAD-RECOVERY-ADR.md. No idempotency/schema/API contract was invented to claim PASS.

## First failure before repair

### Original runner selector, bounded reproduction

- LAST_SUCCESSFUL_STEP: S3, assigned request details opened through real expert login and console.
- FIRST_FAILING_STEP: S4, locate usable documents control.
- EXPECTED_CONDITION: visible/enabled documents tab matching runner /مدارک|اسناد/.
- ACTUAL_UI_STATE: real button role=tab, accessible name «مستندات پرونده», enabled, inactive. The name did not match the regex.
- TIMEOUT_LAYER: action/assertion, locator.waitFor, 10000 ms; not an outer process window.
- ELAPSED_TIME: 25294 ms at failure; completed diagnostic result 25627 ms.
- RELEVANT_BROWSER_ERROR: locator.waitFor: Timeout 10000ms exceeded waiting for getByRole('tab', {name: /مدارک|اسناد/}); no page JavaScript error.
- RELEVANT_API_STATUS_OR_FAILURE: login 200, request list/detail 200; documents request never sent.
- Page: /expert/requests/<synthetic-public-id>; private screenshot/DOM/trace retained under $env:TEMP\forwarder-fwd07-diagnostic-20260916.
- DOM excerpt: button role="tab", aria-selected="false", data-state="inactive", text="مستندات پرونده".

The previous run's backend log independently showed successful login/detail and no documents GET. Its final window timeout was not sufficient root-cause evidence. No original trace was present in the inspected prior evidence directory.

### Mobile reachability after correcting selector

- LAST_SUCCESSFUL_STEP: S4, exact tab found visible and enabled.
- FIRST_FAILING_STEP: S5, normal selection.
- EXPECTED_CONDITION: ordinary click activates documents tab and starts documents GET.
- ACTUAL_UI_STATE: tab row did not wrap; documents control outside viewport. Playwright repeatedly completed scrollIntoView but still reported outside viewport. Screenshot browser-mobile-before-fix-20260916.png confirms clipped row.
- TIMEOUT_LAYER: action/assertion, locator.click, 10000 ms.
- ELAPSED_TIME: 22401 ms at failure.
- RELEVANT_BROWSER_ERROR: locator.click: Timeout 10000ms exceeded; element is outside of the viewport. No page JavaScript error.
- RELEVANT_API_STATUS_OR_FAILURE: detail 200; no documents GET.
- Private screenshot/DOM/trace: $env:TEMP\forwarder-fwd07-mobile-diagnostic-20260916.

An earlier mobile probe had an unhandled concurrent waitForResponse timeout masking this click error. The pending response now has an immediate rejection handler so the first failed action is recorded.

## Repairs and harness findings

- Selector uses actual semantic role and exact accessible name.
- Mobile login opens the real «منوی سامانه» before sign-in.
- RequestDetail tab row adds flex-wrap, making the existing documents control reachable on mobile without force clicks or bypasses.
- PNG changed from an intentionally rejected eight-byte signature to a complete harmless 1x1 PNG. PDF fixtures use existing accepted synthetic format.
- UI presents newest versions first. Download checks identify displayed version and compare its exact bytes, keeping same-name files independent. Chromium normalizes zero-width joiner to underscore in downloaded filenames; visible metadata retains safe Persian filename.
- Separate assigned desktop/mobile requests share valid environment setup while isolating mutable case state. Fixture max count 8 permits core, partial failure, retry and unknown-outcome probes; this changes synthetic data only.
- Existing launcher records run-id/PIDs/logs/result and stops only owned processes. Startup health/readiness has a 30-second bound per runtime, locator/assertion 10 seconds, navigation 15 seconds, scenario suite 180 seconds. No unlimited timeouts or long sleeps. Final measured startup 14.195 s, scenario 86.489 s, launcher 102.233 s; no outer interruption.

## Acceptance matrix

All current-run browser checks are in browser-results-20260916.json. Diagnostic exit 0 means the checks completed, including successful reproduction of an acceptance defect; JSON explicitly says BLOCKED_RECOVERY_CONTRACT.

| Criterion | Start evidence disposition | Final disposition | Evidence / limitation |
| --- | --- | --- | --- |
| S1 runtime/disposable DB | prior successful backend log | PASS — EXECUTED_THIS_RUN | readiness + real login |
| S2 ordinary expert login | prior log 200 | PASS — EXECUTED_THIS_RUN | desktop and mobile menu path |
| S3 authorized request details | prior log 200 | PASS — EXECUTED_THIS_RUN | assignment, no admin escalation |
| S4 usable documents control | BLOCKED selector | PASS — EXECUTED_THIS_RUN | exact semantic selector |
| S5 selected panel | NOT_RUN | PASS — EXECUTED_THIS_RUN | data-state active, mobile product repair |
| S6 related API completes | NOT_RUN | PASS — EXECUTED_THIS_RUN | real documents GET 200 |
| S7 interactive valid file-empty requirement | NOT_RUN | PASS — EXECUTED_THIS_RUN | one logical requirement, enabled input, empty-file screenshot |
| two same-name/different-byte PDFs + image | browser NOT_RUN; focused API PASS recorded | PASS — EXECUTED_THIS_RUN | 3 independently saved UI outcomes, byte downloads |
| leave/reopen + download from UI | browser NOT_RUN | PASS — EXECUTED_THIS_RUN | actual browser downloads and byte equality |
| complementary append preserves prior files | browser NOT_RUN | PASS — EXECUTED_THIS_RUN | 4 files reopened/downloaded; no replacement |
| definite one-file failure preserves success | only component partial result recorded | PASS — EXECUTED_THIS_RUN | actual invalid PDF 400 + successful PDF 201, all successes reopened/downloaded |
| retry only failed selection | NOT_RUN in browser | PASS — EXECUTED_THIS_RUN | corrected failed file alone; earlier versions/bytes preserved |
| lost response after actual save | NOT_RUN | BLOCKED — EXECUTED_THIS_RUN | real 201 then connectionreset; reported failed; saved file verified on reopen |
| no duplicate attachment for same operation retry | NOT_RUN | BLOCKED — EXECUTED_THIS_RUN | retry adds version 8 in addition to saved version 7; exact identical bytes downloaded |
| intentional same-name/same-content independent append | not separately proven | PASS — EXECUTED_THIS_RUN (API) | dedicated intentional-identical-append regression: two real submissions, distinct IDs, equal hash, one requirement, two byte-verified downloads; browser retry evidence is not relabeled as intentional append |
| desktop/mobile RTL, Persian labels, receive buttons | NOT_RUN | PASS — EXECUTED_THIS_RUN | 1280x800 and 390x844; scrollWidth=clientWidth; screenshots visually reviewed |
| loading | NOT_RUN | PASS — EXECUTED_THIS_RUN | proxy holds delivery of actual documents GET until loading text observed, then forwards unchanged real response |
| file-empty state | NOT_RUN | PASS — EXECUTED_THIS_RUN | valid requirement, missing warning, enabled upload, no download row |
| list error and UI recovery | NOT_RUN | PASS — EXECUTED_THIS_RUN | real GET forwarded then delivery reset; visible Failed to fetch; natural console/detail/tab revisit restores all files |
| zero configured requirements empty state | NOT_RUN | NOT_RUN | synthetic setup has one valid logical requirement; not claimed as zero-requirement evidence |
| direct unauthorized access | previous API tests recorded | PASS — EXECUTED_THIS_RUN | focused cross-case, unauthenticated, requirement/file mismatch and audit fail-closed tests |
| assignment revoke and direct download | gap not separately documented | PASS — EXECUTED_THIS_RUN | new real-route test: authorized 200, unassign, same token/file denied 403/404 without side effect |
| failure between storage and metadata | previous fault tests recorded | PASS — EXECUTED_THIS_RUN | inspected write/rename/flush/commit/audit rollback tests, all 13 fault tests rerun |
| PostgreSQL races | README NOT_RUN; previous commit tests available | PASS — EXECUTED_THIS_RUN | exactly five race scenarios listed below; not lost-response coverage |
| real scanner | NOT_RUN | NOT_RUN / outside controlled browser scope | no scanner certification or waiver |
| ADR-020 cross-scope adoption/customer visibility | outside scope | outside scope | remains proposed; no activation |

Operational-shipment listing emits existing 403 for this permission-free assigned request expert; request detail catches that unrelated list failure. It does not prevent documents access and no new permission was granted. Invalid-file upload emits expected 400. Delivery-reset errors are explicit test transport faults after forwarding real requests; upload/download/authorization endpoints are never mocked.

## Proven consequential blocker

For BOTH viewports: upload version 7 returns 201 to the transport proxy after actual persistence. The proxy aborts delivery with connectionreset. UI says «پاسخ-ازدست‌رفته.pdf: ثبت نشد» and advises reselecting failed files. Leaving/reopening and downloading establishes the file really exists with exact source bytes. Following that advice submits the same operation again and creates version 8 with the same name and bytes. Prior successful files survive, but safe unknown-outcome recovery fails.

Current CaseDocumentsTab catches all upload exceptions as failed. Existing upload service allocates a new immutable version for each accepted append; uploadCaseDocument carries no operation identity. Listing checksum/name is insufficient to distinguish an unknown prior operation from a legitimate identical append.

Minimum human action: Architecture/Business Owner accept or revise the bounded proposal in PROPOSED-UPLOAD-RECOVERY-ADR.md and authorize implementation of durable per-file operation identity/replay plus truthful unknown state. This is an authority/contract blocker, not a tool, login, PostgreSQL or outer-window blocker. No environment intervention is required. Existing CODEX-DEVELOPMENT-GATE says: “If architecture change is required, STOP BEFORE IMPLEMENTATION. Produce a PROPOSED ADR ... Do not treat ... passing tests as ADR acceptance.” Mission section 6 independently reserves consequential unknown-outcome repair. No new contract implemented.

## Qualification accounting

REUSED_WITH_IMPACT_REVIEW: prior ownership/append decisions and existing source/tests used for focused discovery. Prior recorded 40 backend / 3 UI / build PASS are historical only; not used to certify new product code. PostgreSQL and raw browser outcomes were not inferred from the stale README.

EXECUTED_THIS_RUN:
- Focused backend: 40 passed (27 case-document cases + 13 parametrized fault cases) before adding the revoke regression.
- New assignment-revoke and intentional-identical-append regressions together: 2 passed, 27 deselected; actual authorization/upload/download routes.
- Focused UI: 4 passed.
- PostgreSQL 18, real explicit migration to 20260916_fwd06_tracking_time: 5 passed. Scenarios: concurrent requirement initialization, first-upload unique versions, serialized replacement with safe loser, max-count race, independent miscellaneous uploads. Owned cluster stopped; private diagnostics under $env:TEMP\forwarder-fwd07-qualification-26b61768b61b43928fcc31f31b7d1af8. These five do not cover network loss or every retry/storage failure.
- Final browser: both viewports, 86.489 s scenario; no automatic scenario retries. Controlled diagnostic runner completed, mission recovery criterion BLOCKED.
- Final production build: PASS after tab-row repair. Lint: PASS, 0 errors / 12 existing warnings after correcting an intermediate harness syntax error. Structure and whitespace: PASS.
- Full frontend: 177 passed / 1 geography test timeout at unchanged 5000 ms under concurrent checks; same file isolated subsequently 2 passed, unchanged 5000 ms. No unrelated test timeout was increased; full-run failure is retained in accounting.
- Full backend mandatory gate: NON_GREEN, 4 failed / 1082 passed / 231 skipped / 1 xfailed / 3 setup errors, 589.24 s. Three obsolete assertions expect fwd05 migration head while unchanged candidate has fwd06; one unchanged materialization test omits the now-required offset-aware occurred_at. No relevant failure was suppressed.
- Broad-run safety caveat: initial full-suite command inherited pre-existing loopback TEST_DATABASE_URL database forwarder_auth_test. Unlike the document/browser/owned-PostgreSQL fixtures, this broad run was not wholly disposable. Its tenant-architecture create_all failed on missing operational_outbox composite uniqueness. This is a test setup mistake; no DB repair/cleanup was attempted. Production was not targeted. No claim that the pre-existing test database stayed untouched is made.
- Corrected setup qualification: explicit APP_ENV=test, TEST_DATABASE_URL=sqlite:///:memory:, DATABASE_URL=sqlite:///:memory:; entire tenant-architecture contract file 8 passed / 1 xfailed in 0.60 s. Four remaining gate failures reproduced separately: 4 failed in 1.96 s in this isolated environment; their source, service and migration files are byte-identical to start HEAD (git diff empty). They are known candidate regression gaps outside the requested documents repair, not an invented new documents blocker.

## Reproduction and privacy

Tested launcher from repository root, normal PowerShell (no execution-policy bypass):

```powershell
Set-Location 'D:\1-webapp\forwarder-dev'
& .\scripts\uat\run-fwd07-browser-uat.ps1 -EvidenceDirectory (Join-Path $env:TEMP 'forwarder-fwd07-review-20260916')
```

The same launcher invocation was executed with evidence directory forwarder-fwd07-final-browser-v2-20260916. Default launcher chooses a unique GUID run directory. Human-run file to return: result.json plus launcher-result.json (review for secrets before transfer); raw trace/session/capability must stay private. To reproduce original selector failure in the same runner set FWD07_UAT_DIAGNOSE_OLD_SELECTOR=1; to focus mobile set FWD07_UAT_VIEWPORT=390. Neither is enabled for final two-viewport acceptance.

Committed screenshots and JSON were reviewed: synthetic tracking codes/names/phone only, no token/cookie/private URL/capability. Raw traces, downloads, runtime logs, DB and storage remain outside Git under private temporary run directories; no public service used for debugging.

LOCAL_EXISTING_TEST_DB_EXPOSURE: initial broad gate inherited forwarder_auth_test; explicitly disclosed above.

REAL_MESSAGES_SENT: NO
LLM_APIS_CALLED_BY_PRODUCT: NO
PRODUCTION_CHANGED: NO

No reset/clean/stash/amend/history rewrite/force push/merge/release/deploy. Final tested product is exactly the tab-row repair; later evidence edits do not alter product behavior. Final commit/ref synchronization is recorded in the task delivery receipt.

## Mandatory gate failure locations

- backend/tests/test_alembic_version_table.py:95 — expected 20260916_fwd05_quote_response; actual 20260916_fwd06_tracking_time.
- backend/tests/test_operational_execution_190.py:343 — same obsolete expected head.
- backend/tests/test_project_configuration.py:137 — same obsolete expected head.
- backend/tests/test_global_logistics_point_materialization.py:187 — TrackingValidationError: occurred_at must be an offset-aware datetime (service line 211).
- Initial broad setup error backend/tests/test_tenant_architecture_contract.py:23 — psycopg2.errors.InvalidForeignKey: no unique constraint matching keys for referenced operational_outbox. Corrected isolated file passes 8 / xfails 1.

No production database, session, file, notification, LLM endpoint or deployment was targeted. The inherited existing local test database exposure is disclosed, rather than labeled disposable.

TESTED_CODE_COMMIT: 2f8f11d2e03860bc82d3509770684e00abe396b7
Product, harness and regression changes are committed together. The following evidence commit changes only reviewed evidence/decision documents and synthetic screenshots. Final LOCAL_HEAD/REMOTE_HEAD/sync are verified after push and provided in the delivery receipt.

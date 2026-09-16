# FWD-06 pre-build decision checkpoint

Recorded: 2026-09-16, Asia/Tehran. This is an ADR gate, not completion of the
requested product slice. Runtime files, historical migrations and mother LPAF
are unchanged. New test/evidence files do not constitute product implementation.

## Identity

- Actual root: `D:/1-webapp/forwarder-dev` (the initial desktop cwd was the
  separate `D:/1-webapp/15-forwarder`; no mutation was made there).
- Start branch: `feature/fwd-05-quote-response`.
- Verified start HEAD: `29630f9ee255b9b0189124b4d41fb262422e53f9`.
- Start upstream: `origin/feature/fwd-05-quote-response`.
- New branch created explicitly from that HEAD:
  `feature/fwd-06-tracking-timeline`.
- Remote: `origin`, `https://github.com/behtashnoori/forwarder.git`.
- `git worktree list`: one worktree in this repository, the intended root.
- Initial tracked/untracked status: clean; old local ignored qualification
  directories left unchanged. No AGENTS.md found by project file inventory or
  parent directory check. No reset/clean/stash/force/history rewrite/main merge.
- All four earlier FWD01/02/03/04 branch tips are ancestors of the verified
  FWD05 start; each `git merge-base --is-ancestor` returned zero. FWD05 retained.
- FWD06 remote head lookup returned no matching ref before first push.
- Sole Alembic script head read through actual project configuration:
  `20260916_fwd05_quote_response`.

## Pre-Build mission/ownership record

PRIMARY_MODULE_AND_OWNER: current compatibility tracking application service,
`backend/services/multi_unit_tracking_service.py`; legacy subject/update storage
belongs to that compatibility workflow. Canonical operational owners remain
OperationalShipment/ExecutionUnit/OperationalEvent. Commercial owns eligibility/
quote response; Geography owns place eligibility/snapshots; Presentation owns
formatting; Notification owns dispatch, not tracking state.

AFFECTED_PUBLIC_CONTRACTS: proposed internal tracking query history, legacy
create/update receipt seam and explicit public recorded-time allowlist;
existing expert/public endpoint identities preserved. No endpoint authority
changed at this checkpoint.

ALLOWED_SCOPE: evidence, safe isolated existing-contract characterization,
proposal and append-only reference decision now; proposed legacy capability/
receipt/visibility Build is BLOCKED pending named acceptance. Ordinary fixes
within existing contracts do not require a parallel ADR. No new status,
canonical migration/cohort, correction command, map/GPS/provider/auth system.

APPLICABLE_LPAF_RULES: global ACTIVE v2.2 §§3–8,10–12, rigor B scoped to local
qualification; named mission opt-in to limited v2.4 MOD-01/03, READ-01/02,
TIME-01, QUAL-01–05, ADOPT-01/02. AI-01–03 constrain future clients; no product
agent is built. Workflow/configuration/document/analytics/Attention engines and
Production release/runtime gates are N/A to this pre-build checkpoint because
none are being built/activated; relevant existing dependencies are preserved.
No v2.3 analytics adoption or global activation asserted. v2.2 main/entry,
v2.4 main/approval/re-attestation/entry/changelog/four lesson candidates inspected.
v2.4 current SHA256 matches the mission exactly; re-attestation binds original
approval to link-only repaired current bytes. No active conflict waived.

FRAMEWORK_REFERENCE_IMPACT: NONE; actual root
`D:/1-webapp/29-lpaf/29-lpaf (1)/29-lpaf/lpaf`, owner Architecture/Business Owner;
mother unchanged, v2.2 GLOBAL_ACTIVE, v2.4 OWNER_APPROVED /
PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE.

PROJECT_REFERENCE_IMPACT: UPDATE_REQUIRED; actual project baseline,
architecture ADR index, decision index and proposed ADR048 updated within this
checkpoint. Accepted ADR statuses/content unchanged. Inspected baseline,
development gate, indexes, legacy/canonical map, tracking matrix/projection
implementation, affected ADR001/002/003/006/007/010/011/015/016/018/019/035/040,
and affected time data-type guide. This is not compliance with every archival
document or the missing path28.

TARGET_ACTORS_AND_DATA_SCOPES: assigned ordinary expert + active tenant membership
for the existing request root; org-admin oversight only within actual policy;
public tracking-code read capability, not personally authenticated customer.
Tenant master LogisticsPoint; transactional tracking subject/update; immutable
historical snapshots; platform place/type vocabulary. Proposed public data is
visible-event allowlist only. Admin is not a replacement for ordinary-expert UAT.

QUALIFICATION_PLAN: after acceptance, replay the full slice with real candidate
backend, owned disposable PostgreSQL, existing synthetic startup/fixture seams,
ordinary expert login and valid assignment, formal seed/commands/transitions,
customer capability read, persisted reopen, authority/revocation/tenant/location
negatives, receipt races and timezone/browser/RTL/failure checks. Then relevant
regression/static/security gates and final commit/push/fetched-ref verification.
Expected facts must be independent of UI/array order. No APIs/permissions/
persistence mocked; only external side effects may use existing fake adapter.

## Focused discovery and reproduction

| Customer issue | Current behavior | Root cause / scope of evidence | Owner | Reuse/extend/new | Acceptance test |
| --- | --- | --- | --- | --- | --- |
| Add trackable section error | First valid create201 for all4 types; repeated code409 generic; no tracking400; empty code400 | NOT_REPRODUCED_ON_THIS_BASELINE for initial valid create; retry conflicts on uq_tracking_unit_code and route hides field/reason; UI catches all writes as generic saveError | legacy tracking service / presentation | ordinary error repair; receipt extension requires decision | Valid intake, duplicate conflict/replay, validation/input preservation, DB count |
| Code vs vehicle/container | Required operator code; optional vehicle_reference; DB numeric identity generated separately | Legacy form and canonical U-code represent different contracts; placeholder-only labeling obscures actual meanings | legacy subject / presentation | existing-contract label/help repair | Four type-specific labels/help, optional unknown reference, stable historical code |
| Clear shared Timeline | Internal query summary only; public visible timeline; public no recorded time | Missing internal presentation/query capability and public recorded-time visibility contract; no certified canonical lineage/cohort | compatibility tracking query / visibility / presentation | extension pending ADR048 | Real persisted staff/customer timeline, ordered late/tie history, recording labels and allowlist |

Actual baseline probes use existing isolated test fixtures, real Flask routes,
canonical assigned-work authorization, ORM persistence and queries; no mocked
operational API. SQLite fixture's pre-existing synthetic `won` seed is valid for
isolated characterization, NOT evidence of the required upstream operational
journey. Do not use it to claim UAT or an automatically created Shipment.

Bounded actual HTTP evidence:

- `truck/container/wagon/other`: first201, same unit_code retry409,
  `error=tracking unit could not be created`, reason code ABSENT. Root-cause field
  unit_code identified from the declared unique constraint; server does not
  identify it. Reopened persisted count1, same internal identity, reference NULL.
- No enabled tracking400, `error=tracking is not enabled`, reason code ABSENT.
- Enabled tracking + missing code400, `error=unit_code is required`, reason code
  ABSENT. Valid type-specific optional fields were not made mandatory.
- Official FWD05 journey fixture calls actual quotation owner + fake notification
  seam, not a commercial row fabricated as won. Its actual root state is
  waiting_for_customer; tracking GET200 eligiblefalse; enable400,
  `shipment must be accepted before tracking is enabled`; no Shipment created.
  Executed separately on SQLite and migrated native PostgreSQL. This tests
  publication prerequisites; it is not a new acceptance-response journey.
- Original production symptom, production identity/data and customer credentials
  were not accessed. Production fix claim is forbidden.

## Environment and observed tests

Candidate backend: actual start source, create_app(skip_startup=True), genuine
auth-session tokens and assigned-work authorization. APIs/DB not mocked.
External fake adapters: only existing FWD05 qualification config/private capture;
no real transport/provider/LLM product call. Existing token values never printed.

PostgreSQL18 binary exists at `C:/Program Files/PostgreSQL/18/bin`.
Reused `scripts/uat/run_fwd05_disposable_postgres.py` unchanged: creates its own
loopback cluster/new runtime DB, scrubs ambient database/PG variables, verifies
postmaster path/port, runs complete actual historical upgrade to FWD05 sole head
and shuts down only its owned cluster. Successful cluster diagnostics remained
outside Git at
`C:/Users/pc/AppData/Local/Temp/forwarder-fwd05-qualification-1623dd0cbb214466a49d56f32ef66236`.
No old/customer DB or unrelated process was used/stopped. No FWD06 migration or
concurrency result is claimed by this prerequisite probe.

Existing FWD04 harness/timezone runner and launcher exist. Its configured
playwright-core path and installed Chromium1228/1234 directories exist; the
project-local node_modules/playwright path is absent, so do not substitute that
assumption for the configured existing harness. Browser launch/UAT NOT_RUN.
Main operational command fixture is NOT_YET_QUALIFIED; completion is deferred
with proposed Build, not declared impossible or falsely supplied by an admin.

- Initial existing-contract characterization and four related modules:
  35PASS, 461warnings, 10.51s; no skip/XFAIL.
- Added official FWD05 journey prerequisite probe diagnostics: wrong auth import
  corrected to auth_session_service; guessed quoted state was rejected by actual
  waiting_for_customer. Tests corrected to actual owner behavior, product not
  changed. Native diagnostic2FAIL, 5deselected, 13warnings, 4.35s; retained as a
  failed test-development checkpoint, not a product regression or PASS.
- Final native launcher: 2PASS (SQLite + native PostgreSQL cases), 5deselected,
  29warnings, 5.20s. Cluster stopped, exit0. No skip/XFAIL in actual native run.
- Final focused collection: 36PASS, 1SKIP, 475warnings, 11.23s. The sole skip is
  the opt-in native journey case when its explicit cluster is not configured;
  that same case was separately executed and passed above. No XFAIL introduced.
  Native wrapper's SQLite result overlaps this collection; do not double-count.
- Imported pytest fixtures require F401 on fixture imports and F811 at matching
  injected parameters; Ruff initially reported3 fixture-shadowing diagnostics.
  Narrow F811 comments repaired lint only, AST/runtime unchanged; no product or
  test assertion changed after final native/focused PASS.
- Full backend/frontend product suites and Browser UAT: NOT_RUN at pre-build ADR
  gate. Focused PASS is not completion/Production qualification inherited from
  FWD05. Subsequent static/diff/secret outcomes are recorded in git proof.

## Reproducible commands

Run from `D:/1-webapp/forwarder-dev`:

```powershell
python -B -m pytest -q --tb=short --disable-warnings -p no:cacheprovider backend/tests/test_fwd06_tracking_characterization.py backend/tests/test_multi_unit_tracking_api.py backend/tests/test_multi_unit_tracking_service.py backend/tests/test_public_tracking_timeline.py backend/tests/test_tracking_projection.py
python scripts/uat/run_fwd05_disposable_postgres.py backend/tests/test_fwd06_tracking_characterization.py -k governed -s --disable-warnings
python -B -m ruff check backend/tests/test_fwd06_tracking_characterization.py
python -B scripts/check_architecture_governance.py
python -B scripts/scan_repository_secrets.py current
git diff --check
```

Pre-build source/evidence fingerprint is the final checkpoint commit printed in
the completion response. ADR048 SHA256 is bound in FINAL-REPORT; its file does
not embed its own hash. No new ADR acceptance or successful runtime delivery.

## Time and open gaps

Discovery/documentation/initial native failed-import launcher total duration was
not instrumented: UNKNOWN. Actual test durations above are measured runner
results; native cluster startup/wait and commands are additional wall time, not
tokens. Final checkpoint timestamp and Git operations are observable separately.
No token/credit statistic queried for this mission: UNKNOWN, not an estimate.

Historical replay BLOCKED_MISSING_EXTERNAL_EVIDENCE; Production identity UNKNOWN;
Reference28 mapping NOT_PROVEN; recipient onboarding OPEN; real customer delivery
NOT_READY; Production security NOT_RUN. No gap automatically closed. Product
scope is BLOCKED_OWNER_ADR_DECISION, not PASS_CONTROLLED_LOCAL_FWD06.

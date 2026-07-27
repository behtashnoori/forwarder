# Phase 1B Browser/Mobile UAT evidence

## Final evidence (current)

- Targeted route-contract: `P1B-UAT-20260727044111047492` — `PASS`.
- Full Browser/Mobile UAT: `P1B-UAT-20260727044204801260` — `PASS`.
- Final evidence: `evidence/phase1b_browser_mobile_uat/49-targeted-route-contract-pass.md` and `.json`.
- Final evidence: `evidence/phase1b_browser_mobile_uat/50-final-full-browser-mobile-uat-pass.md` and `.json`.
- Browser/Mobile UAT: `YES`; five viewports: `PASS`; workflows: `22/22 PASS`.
- P1B-UAT-001 through P1B-UAT-006: `CLOSED_VERIFIED`.
- Persistent applied: `NO`; production/public PostgreSQL untouched; `.backend-port`: `57065`.

All evidence and status records below are historical/blocked-attempt chronology, not current status.

## Historical and blocked attempts

P1B-UAT-006 is `RESOLVED_TEST_FIXTURE_ALIGNMENT_PENDING_FULL_UAT`.
Root-cause and targeted retest evidence are in
`phase1b_reporter_arrival_report_409_remediation.md`. Full Browser/Mobile UAT
remains `NO` and must restart from the beginning.

Status: `P1B-UAT-001_REMEDIATION_PASS`; full Browser/Mobile UAT rerun pending

All evidence is synthetic and sanitized. No password, token, cookie,
authorization header, DSN, real email, or real customer data is present.

| File | Workflow | Viewport | Role | Assertion | Sanitization |
|---|---|---|---|---|---|
| `evidence/phase1b_browser_mobile_uat/01-desktop-shipment-list-duplicate-defect.png` | Operational shipment list | 1440 x 900 | Organization A admin | The one seeded shipment is incorrectly rendered three times | PASS |
| `evidence/phase1b_browser_mobile_uat/02-mobile-390-shipment-list-duplicate-defect.png` | Operational shipment list | 390 x 844 | Organization A admin | Duplicate shipment rendering reproduces on mobile; page-level overflow and off-viewport buttons were zero | PASS |
| `evidence/phase1b_browser_mobile_uat/03-desktop-shipment-list-dedup-remediation.png` | Targeted remediation retest | 1440 x 900 | Organization A admin | Exactly one shipment card/link; next page disabled; no duplicate-key warning | PASS |
| `evidence/phase1b_browser_mobile_uat/04-mobile-390-shipment-list-dedup-remediation.png` | Targeted remediation retest | 390 x 844 | Organization A admin | Exactly one shipment card/link; zero page overflow and off-viewport buttons | PASS |
| `evidence/phase1b_browser_mobile_uat/05-full-uat-rerun-blocked-seed-guard.md` | Fresh environment / official seed | Not reached | Not reached | Mandated database name is rejected before browser UAT | PASS |
| `evidence/phase1b_browser_mobile_uat/06-final-shipment-list-1440.png` | Shipment list dedup | 1440 x 900 | Organization A admin | Exactly one shipment; sanitized | PASS |
| `evidence/phase1b_browser_mobile_uat/07-final-shipment-list-390.png` | Shipment list dedup | 390 x 844 | Organization A admin | Exactly one shipment; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/08-final-shipment-list-360.png` | Shipment list dedup | 360 x 800 | Organization A admin | Exactly one shipment; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/09-final-shipment-detail-1440.png` | Shipment detail/timeline | 1440 x 900 | Organization A admin | Multi-leg route and timeline visible | PASS |
| `evidence/phase1b_browser_mobile_uat/10-final-shipment-detail-768.png` | Responsive detail | 768 x 1024 | Organization A admin | Controlled table scroll | PASS |
| `evidence/phase1b_browser_mobile_uat/11-final-shipment-detail-390.png` | Responsive detail | 390 x 844 | Organization A admin | No page overflow or off-viewport actions | PASS |
| `evidence/phase1b_browser_mobile_uat/12-final-reconciliation-validation.png` | Reconciliation/validation | 1440 x 900 | Organization A admin | Timeline and exception actions | PASS |
| `evidence/phase1b_browser_mobile_uat/13-final-replan-exception.png` | Replan with exception | 1440 x 900 | Organization A admin | Revision 2 active; source exception resolved | PASS |
| `evidence/phase1b_browser_mobile_uat/14-final-organization-isolation.png` | Direct-ID isolation | 1440 x 900 | Organization B admin | Organization A data suppressed | PASS |
| `evidence/phase1b_browser_mobile_uat/15-final-readonly-permission.png` | Permission matrix | 1440 x 900 | Organization A read-only | No mutation actions visible | PASS |
| `evidence/phase1b_browser_mobile_uat/16-final-reporter-permission-blocker.png` | Reporter milestone lifecycle | 1440 x 900 | Organization A reporter | Detail page replaced by permission error | BLOCKED |
| `evidence/phase1b_browser_mobile_uat/17-reporter-detail-controls-desktop.png` | P1B-UAT-003 remediation | 1440 x 900 | Reporter | Detail and reporting controls visible; privileged controls absent | PASS |
| `evidence/phase1b_browser_mobile_uat/18-reporter-report-success-desktop.png` | Milestone lifecycle | 1440 x 900 | Reporter | Processing-complete report succeeds | PASS |
| `evidence/phase1b_browser_mobile_uat/19-reporter-detail-mobile-390.png` | Responsive permission retest | 390 x 844 | Reporter | Detail/reporting visible; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/20-verifier-verify-success.png` | Independent verification | 1440 x 900 | Verifier | Reporter event verified successfully | PASS |
| `evidence/phase1b_browser_mobile_uat/21-readonly-detail.png` | Permission boundary | 1440 x 900 | Read-only | Detail visible; mutation controls absent | PASS |
| `evidence/phase1b_browser_mobile_uat/22-no-permission-denial.png` | Permission boundary | 1440 x 900 | No permission | Fail-closed sanitized denial | PASS |
| `evidence/phase1b_browser_mobile_uat/23-inactive-denial.png` | Permission boundary | 1440 x 900 | Inactive membership | Fail-closed sanitized denial | PASS |

## Defect register

| ID | Severity | Workflow | Viewport | Expected | Actual | Evidence | Status |
|---|---|---|---|---|---|---|---|
| P1B-UAT-001 | HIGH | Operational shipment list | 1440 x 900; 390 x 844 | One list card for the one Organization A shipment | Remediation returns and renders one card; pagination and console retest pass | Files `03` and `04` | REMEDIATED; TARGETED RETEST PASS |
| P1B-UAT-003 | HIGH | Permission matrix / milestone lifecycle | 1440 x 900 | Reporter can open detail and report milestones | Detail page is replaced by a permission error; no report control is reachable | File `16` | OPEN; FULL UAT BLOCKER |
| P1B-UAT-003 remediation | HIGH | Reporter/Verifier lifecycle | 1440 x 900; 390 x 844 | Least-privilege detail/report/verify workflow | Files `17` through `23` prove allowed and denied boundaries | Files `17` through `23` | FIXED_PENDING_FULL_UAT |
| P1B-UAT-002 | HIGH | Fresh environment / official seed | Not reached | Harness selects the canonical name shared by the seed and direct test | Canonical `forwarder_phase1b_uat_<token>` migrated, seeded, and passed the direct test with zero skips; no guard change | File `05` is historical blocker evidence; recovery record below | RESOLVED_HARNESS_ALIGNMENT_PENDING_FULL_UAT |

The original HIGH defect is remediated, but the previously untested viewports
and downstream workflows are not retroactively claimed as PASS. Full
Browser/Mobile UAT must be rerun from the beginning and remains `NO`;
persistent applied remains `NO`.

## Backend one-shot launch recovery evidence (2026-07-26)

| File | Workflow | Assertion | Result |
|---|---|---|---|
| `evidence/phase1b_browser_mobile_uat/37-backend-one-shot-launch-recovery-environment-blocked.md` | Windows-safe backend recovery | Repository Waitress/WSGI entrypoint started once and returned health 200; Vite process creation was rejected before start | ENVIRONMENT_BLOCKED |

The backend inline-argument defect is operationally recovered, but Vite and
Chromium were not reached. Browser/Mobile UAT remains `NO`; persistent applied
remains `NO`; cleanup completed with zero current-token resources.

## Final clean rerun direct-precheck blocker (2026-07-26)

| File | Workflow | Viewport | Assertion | Result |
|---|---|---|---|---|
| `evidence/phase1b_browser_mobile_uat/35-final-clean-rerun-direct-precheck-blocker.md` | Fresh direct PostgreSQL prechecks | Not started | Dedup passed; Reporter report returned 409 rather than 200 on two independent seeded databases | BLOCKED |

The browser gate was not entered because all three mandatory direct prechecks
did not pass. Browser/Mobile UAT remains `NO`; persistent applied remains `NO`.

## Final clean rerun environment blocker (2026-07-26)

| File | Workflow | Viewport | Assertion | Result |
|---|---|---|---|---|
| `evidence/phase1b_browser_mobile_uat/36-final-clean-rerun-environment-blocked.md` | Fresh prechecks and runtime startup | Not started | All three direct prechecks passed; sole backend launch attempt failed in Windows harness argument parsing before app initialization | ENVIRONMENT_BLOCKED |

No backend restart was attempted, and Vite and Chromium were not started.
P1B-UAT-001 through P1B-UAT-006 remain pending full UAT. Browser/Mobile UAT
remains `NO`; persistent applied remains `NO`; cleanup completed with zero
current-token resources.

The 2026-07-26 clean rerun stopped at the official seed guard before Chromium
started. Consequently P1B-UAT-001 remains `FIXED_PENDING_FULL_UAT`, no new
viewport screenshot is claimed, Browser/Mobile UAT remains `NO`, and
P1B-UAT-002 was an operationally HIGH harness mismatch and is resolved pending
the full UAT rerun. It was not a product defect.

## Database-name contract recovery evidence (2026-07-26)

| Control | Result |
|---|---|
| Canonical prefix | `forwarder_phase1b_uat_` proved from seed and direct-test source |
| Guard/source/test changes | None |
| PostgreSQL | 18.0, UTF8, loopback-only, token-owned directory and port |
| Migration | Single head `20260801_route_exception`; pending zero |
| Official seed | PASS; all expected Phase 1B counts matched |
| `UAT_DATABASE_REJECTED` | 0 |
| Direct dedup PostgreSQL | 1 passed, 0 skipped, 0 failed |
| Browser/screenshots | Not run; no screenshot created |
| Sanitization | PASS |

The earlier file `05` remains historical evidence of the rejected harness
name. It is not evidence of a remaining product defect. Browser/Mobile UAT is
still `NO`, P1B-UAT-001 remains `FIXED_PENDING_FULL_UAT`, and persistent
applied remains `NO`.
## P1B-UAT-004 runtime closure evidence (2026-07-26)

- Resolver tests: 8/8 passed; frontend suite: 30/30 passed; build: PASS.
- ESLint: PASS, zero errors, existing 11-warning baseline, resolver warnings zero.
- Runtime: PostgreSQL 18/UTF8; migration head `20260801_route_exception`;
  pending zero; official seed counts matched baseline.
- Starts: backend 1, Vite 1; selected source `explicit_env`; selected target was
  the current token backend; `.backend-port` remained 57065.
- Chromium 1280 x 720: login PASS, shipment list PASS, shipment detail PASS,
  active route plan PASS, refresh PASS, logout PASS.
- Network: same-origin `/api` YES; token-backend proxy destination YES; stale
  port 57065 requests 0; port 5001 requests 0; production/cross-origin requests
  0; request loops 0; unexpected 5xx 0; CORS failures 0.
- Console: fatal errors 0, unhandled promises 0; non-fatal React Router
  future-flag warnings only.
- Cleanup: browser 0, Vite 0, backend 0, PostgreSQL 0, runtime listeners 0,
  current-token resources 0, current-token temp directory removed.
- Browser/Mobile UAT: `NO`; persistent applied: `NO`.

Result: `PHASE_1B_VITE_BACKEND_TARGET_PRECEDENCE_RUNTIME_CLOSURE_PASS_WITH_NOTES`.

## Final full rerun blocker evidence (2026-07-26)

| File | Workflow | Viewport | Role | Assertion | Sanitization |
|---|---|---|---|---|---|
| `evidence/phase1b_browser_mobile_uat/24-final-full-shipment-list-1440.png` | Shipment dedup | 1440 x 900 | Admin | Exactly one shipment; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/25-final-full-shipment-list-1280.png` | Shipment dedup | 1280 x 720 | Admin | Exactly one shipment; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/25-final-full-shipment-list-768.png` | Shipment dedup | 768 x 1024 | Admin | Exactly one shipment; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/25-final-full-shipment-list-390.png` | Shipment dedup | 390 x 844 | Admin | Exactly one shipment; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/25-final-full-shipment-list-360.png` | Shipment dedup | 360 x 800 | Admin | Exactly one shipment; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/26-final-full-detail-1280.png` | Responsive detail | 1280 x 720 | Admin | Detail usable; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/26-final-full-detail-768.png` | Responsive detail | 768 x 1024 | Admin | Detail usable; controlled table scroll | PASS |
| `evidence/phase1b_browser_mobile_uat/26-final-full-detail-390.png` | Responsive detail | 390 x 844 | Admin | Detail usable; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/26-final-full-detail-360.png` | Responsive detail | 360 x 800 | Admin | Detail usable; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/27-final-full-reporter-correct-permission-blocker.png` | Permission matrix | 1440 x 900 | Reporter | Unauthorized correction succeeded | BLOCKED |
| `evidence/phase1b_browser_mobile_uat/29-final-full-uat-blocked-reporter-correction.md` | Permission matrix | 1440 x 900 | Reporter | Permission, event, and audit evidence | PASS |

| ID | Severity | Workflow | Expected | Actual | Status |
|---|---|---|---|---|---|
| P1B-UAT-005 | HIGH | Reporter permission matrix / milestone lifecycle | Reporter cannot correct verified milestones | Six correction controls rendered and one Reporter correction committed | OPEN; FULL UAT BLOCKER |

## P1B-UAT-005 targeted remediation evidence (2026-07-26)

| File | Viewport | Role | Assertion | Result |
|---|---|---|---|---|
| `evidence/phase1b_browser_mobile_uat/30-reporter-correction-auth-desktop.png` | 1440 x 900 | Reporter | Correct controls 0; report controls visible | PASS |
| `evidence/phase1b_browser_mobile_uat/31-reporter-report-success-auth-remediation.png` | 1440 x 900 | Reporter | Report succeeds; Correct remains absent | PASS |
| `evidence/phase1b_browser_mobile_uat/32-reporter-correction-auth-mobile-390.png` | 390 x 844 | Reporter | Correct controls 0; no page overflow | PASS |
| `evidence/phase1b_browser_mobile_uat/33-authorised-correction-success-desktop.png` | 1440 x 900 | Verifier/correct-capable | Missing reason denied; valid correction succeeds | PASS |
| `evidence/phase1b_browser_mobile_uat/34-authorised-correction-mobile-390.png` | 390 x 844 | Verifier/correct-capable | Correct controls usable and within viewport | PASS |

Controlled direct API evidence against the same disposable browser database
returned `403 FORBIDDEN_OPERATION` for Reporter with event/corrected-event,
audit, and outbox deltas all zero; version, occurred, and projected values were
unchanged and no idempotency row was created. The authorised actor produced
exactly one corrected event and one matching audit. Fatal console errors and
unexpected 5xx responses were zero.

P1B-UAT-005 is `FIXED_PENDING_FULL_UAT`. Browser/Mobile UAT remains `NO`;
persistent applied remains `NO`.

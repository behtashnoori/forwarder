# Golden Production Recovery Certification — 2026-09-19

## A. Recovered Provenance

- Authoritative bundle: `D:\1-webapp\golden-forwarder-recovery-20260919\forwarder-golden-history.bundle`
- Bundle SHA256: `340B214AD106DB11D8F43141A74F6439B9B52BFFC1CE114809BDBE904738E209` — exact match.
- `git bundle verify` result: PASS; the bundle records a complete SHA-1 history and advertises `b48e51c8d0eda00bcc7582b68da85528b14547d2` at `refs/heads/feature/shipment-summary-presentation-polish`.
- Application commit: `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`, parent `e1e766df3601226919510bdc7a778428993d5e4b`, authored `2026-09-14T17:16:52+03:30`, subject `feat(operations): consolidate shipment operational workspace`.
- Tooling commit: `b48e51c8d0eda00bcc7582b68da85528b14547d2`, parent `0145eff543b6f4f5f32102fff95d3b89c9d46667`, authored `2026-09-15T00:43:24+03:30`, subject `Fix production cmd launcher quoting round trip`.
- Independent ancestry check: `git merge-base --is-ancestor e9733866... b48e51c...` passed (`GOLDEN_IS_ANCESTOR_OF_TOOLING=YES`).
- Golden source witness: `forwarder-golden-e9733866-source.zip`, SHA256 `62998EE64D0B36189019E1FDE5E20737EFDFEAFF760619B6BE5F76D34A5D85A8`. A fresh `git archive` of `e9733866...` produced the exact same byte length and SHA256.
- Tooling source witness: `forwarder-tooling-b48e51c-source.zip`, SHA256 `B7F99096284A814F5B5E7D40DA6B528C5969CC7A2ED38B562E97647A5420255C`. A fresh `git archive` of `b48e51c...` produced the exact same byte length and SHA256.
- Preserved runtime witness: `D:\1-webapp\production-reference\current-production-source-20260921.zip`, SHA256 `E9196AD9CC10DFEEF44EBA40D98E50520AF4C505474211D5C23397BDF7774617` — exact match. Its manifest names application `e9733866...`, tooling `b48e51c...`, candidate `Forwarder-Operational-Workspace-Production-CERTIFIED`, and required revision `20260921_shipment_evidence_ownership`.

## B. Isolated Golden Repository

- Location: `D:\1-webapp\15-forwarder-golden-20260921`.
- Branch: `codex/golden-production-20260921`.
- Certified source HEAD before the evidence-only certification commit: `b48e51c8d0eda00bcc7582b68da85528b14547d2`.
- The evidence commit containing this report is the direct child of `b48e51c...`; it changes documentation only. The worktree was clean at the certified source HEAD, and the post-commit cleanliness check is part of final handoff.
- The clone was imported directly from the bundle. It does not use a worktree, index, or mutable object store shared with `D:\1-webapp\15-forwarder`.
- The existing Control Tower donor repository was only inspected read-only. Its HEAD remained `d6297fdf50b27f7d69a5bf2086d11ef2eed882ed` on `codex/ct-prod-regression-rc-20260921`; its reflog tip remained the pre-existing `2026-09-18T03:07:13+03:30` commit. No reset, checkout, clean, rebase, write, or deletion was performed there.

## C. Application vs Tooling Delta

Independent `git diff --name-status e9733866... b48e51c...` inventory:

```text
M  ops/adr043-production-readonly-preflight.ps1
A  scripts/build_operational_workspace_release.py
A  scripts/deploy/deploy_windows_iis_waitress_operational.ps1
A  scripts/tests/LISTENER-PROVENANCE.md
A  scripts/tests/STATE-LIFECYCLE-AUDIT.md
A  scripts/tests/audit_release_state_lifecycle.ps1
A  scripts/tests/test_launcher_chain_contract.ps1
A  scripts/tests/test_launcher_chain_real_process.py
A  scripts/tests/test_operational_release_builder.py
A  scripts/tests/test_operational_release_pipeline.ps1
A  scripts/tests/test_real_execute_simulation.ps1
A  scripts/tests/test_real_nonfixture_validateonly.ps1
```

- Explicit diff across `src/`, `backend/`, `public/`, `contracts/`, and `e2e/`: empty.
- `PRODUCT_SOURCE_CHANGED=NO`.
- Final interpretation: application source and semantics are fixed by `e9733866...`; `b48e51c...` is the engineering base because it adds only the final release/deployment/qualification chain.

## D. Backend Equivalence

- Golden source contains 479 backend files. The preserved runtime contains 309 backend files.
- All 309 packaged backend files are present in the Golden source and are byte-for-byte SHA256-identical; there are zero missing and zero differing runtime backend files.
- The 170 Golden backend files intentionally absent from the runtime are exactly 169 test files plus `backend/Dockerfile`. There is no unexplained product delta.
- The packaged top-level `requirements.txt` is byte-identical to Golden source.
- The migration inventory contains 97 revisions, a single base `20240917_initial_schema`, and a single head `20260921_shipment_evidence_ownership`. Every packaged migration is included in the 309 exact backend matches; released migrations were not rewritten.
- A disposable SQLite database already stamped at the expected head returned `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=no` through the recovered migration CLI.

## E. Frontend Equivalence

- Build host: Windows, Node `v24.11.0`, npm `11.6.1`, Vite `6.4.3` from the recovered lockfile.
- Dependency inputs: `package.json` SHA256 `6E2EF3FAD45A30C335958F9F4D3C19AE88D94E9C9AC9EE218CF8EC1A4F4CFD72`; `package-lock.json` SHA256 `6B871F0C6D9C15EF047524790DF3B4F3D6E630CC7658B7D04308D1A922A9E5E9`.
- Commands: `npm ci`, then `npm run build` (`vite build`). The build transformed 2,536 modules and completed successfully.
- The local `dist` and preserved runtime `dist` both contain exactly 13 files, with no missing or additional files. All 13 paths, lengths, and SHA256 hashes are exactly equal.
- Deterministic primary assets:

| Asset | Bytes | SHA256 |
| --- | ---: | --- |
| `dist/index.html` | 2,131 | `E719CBBF7C67F65E4CCE5F5139133EEB424DAA23AD6AB408B2962E46D6CDC24E` |
| `dist/assets/index-CQMBWI4u.css` | 89,560 | `60F1CF360BEB96FA57919478B031B46065028BC5C1B7B740BD5795E97D2030F9` |
| `dist/assets/index-D_LzjVIP.js` | 1,676,771 | `759E11673F532F5521408D6C571E5D1A5B934D2827B9ECEE92FCD9D62A58CE22` |

- Hashed filenames were identical, so normalization or semantic-only fallback was unnecessary. The recovered editable frontend exactly reproduces the current healthy Golden Production frontend.

## F. Golden Characterization

- Router/navigation: public `/`, `/about`, `/contact`, customer/request tracking, project tracking, and email verification routes coexist with authenticated Expert, CRM, admin, shipment operations, work queue, existing Golden control-tower, dashboards, intelligence, and execution-unit routes. Unknown routes resolve to the Golden not-found page.
- Authentication and role boundaries: `ProtectedRoute` requires the stored expert identity/token; CRM is limited to `admin`, `crm_manager`, `supervisor`, and `business_expert`; admin surfaces require platform/organization authority or admin role; operational routes refuse platform-wide administrators because an organization context is required. Expert/admin operational screens are forced to the Persian locale. Backend tests additionally characterize tenant fencing, assignment authority, expert scope, membership permissions, project access, document policy, and public/private read boundaries.
- Customer and Expert request workflows: request intake/public identity, expert list/detail, assignment/referral, SLA/scope, customer quote response, customer maintenance, and CRM link/create-preview behavior are preserved as-is.
- Shipment Detail: the Golden page characterizes governed route authoring, operational history, delays/exceptions, cargo allocation, execution units, external references, evidence/document ownership, logistics points, economics, and authorization-sensitive actions. No feedback requirement was implemented during certification.
- Dates/time/localization/numeric/currency: existing tests cover legacy/UTC timestamp contracts, localized display, numeric zero-versus-missing semantics, immutable FX provenance, currency facts, quote presentation, and route/timeline timestamps. Current behavior was recorded, not remediated.
- Tracking/timeline/evidence/geography: existing backend/frontend tests cover public tracking timelines, canonical tracking locations, snapshot preservation, shipment/project propagation, case documents, document catalogs, external references, global logistics points, governed international geography, Iran destinations, and reference-data catalogs.
- Characterization evidence reused: all 57 frontend test files (279 tests) and the full backend suite. No product code or new behavior test was added solely to force a green result.

## G. Test Results

| Gate | Result |
| --- | --- |
| Backend full suite | PASS — 1,046 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failures |
| Runtime migration-safety focused rerun | PASS — 22 passed |
| Frontend suite | PASS — 57 files, 279 tests |
| TypeScript (`npx tsc --noEmit`) | PASS |
| Frontend build | PASS; exact 13/13 runtime `dist` reproduction |
| ESLint | PASS — 0 errors, 13 historical warnings |
| Release-builder/tooling unit suite | PASS — 39 passed |
| Migration graph | PASS — 97 revisions, one base, one expected head |
| Disposable database current/check at expected head | PASS — `pending=no` |
| Canonical package/tooling preview certification | PASS — layout, checksums, migration completeness, runtime verification, metadata, state lifecycle, launcher model, listener provenance, ValidateOnly zero-mutation, execute/rollback/failure injection, and corruption matrix |

- Environmental classification: a from-base Alembic upgrade on SQLite reaches the historical `20240920_add_transport_method_to_shipment_request` migration and then raises `OperationalError`; that old migration chain is not SQLite-portable. No local PostgreSQL server/container tooling was installed, so PostgreSQL-only integration cases account for most skips. This was classified without changing released migrations. The recovered migration graph, exact packaged bytes, migration-focused suite, expected-head CLI check, and canonical release-tooling simulation all passed.
- `npm ci` reported 9 dependency advisories (1 low, 4 moderate, 4 high). No audit fix or lockfile mutation was performed because that would change Golden.

## H. Later Feature-Line Inventory

The authoritative bundle advertises only the tooling ref and contains no unreachable FWD tip objects. Exact FWD refs were therefore inventoried read-only in `D:\1-webapp\forwarder-dev`. That repository does not contain commit objects `e9733866...` or `b48e51c...`; its FWD stack descends from normalized recovered baseline `38431da96c4f36ceaa07c550e594bf2d08d34e38`. Consequently, these are future semantic/patch donors, not branches to merge blindly into Golden. The stack is cumulative: each later FWD branch includes the earlier FWD work.

| Feature line | Exact tip | Purpose and relationship | Future use |
| --- | --- | --- | --- |
| `feature/fwd-01-notification-foundation` | `d7cbedf9ec7416b83aeb6313aa095462a20e441d` | Durable governed fake-email action foundation; first commit after normalized recovered baseline | Reference/donor only; reshape around channel-neutral Event → Outbox → Intent → Adapter → Attempt/Result |
| `feature/fwd-02-location-integrity` | `1714118340943f1dbbf99e4b25edc9ef41f817e6` | Governed worldwide location selection plus verification; cumulative over FWD-01 | Suitable for controlled geography reconciliation |
| `feature/fwd-03-request-intake` | `d10f6e003a684626cdb382ba25d6f5bd329150f2` | Accepted ADR-046 request transport intent; cumulative over FWD-01/02 | Suitable request-intake donor after Golden contract mapping |
| `feature/fwd-04-presentation-integrity` | `98a0364a6b6f97daf70152c7d3a5cefbb242cac0` | Time, numeric display, assignment, and browser-timezone integrity | Suitable presentation/test donor; reconcile rather than merge |
| `feature/fwd-05-quote-response` | `29630f9ee255b9b0189124b4d41fb262422e53f9` | Governed quote lifecycle and private customer response authority | Suitable security/quote donor with explicit authority traceability |
| `feature/fwd-06-tracking-timeline` | `c85ebec1b1d49599b6ebfe0811367f310932b7ac` | Bounded tracking timeline, M1 time provenance, snapshot integrity | Suitable tracking/time donor after contract freeze |
| `feature/fwd-07-document-attachments` | `a778bc8516e2d71b8665acd046191fbc5f0493e8` | Multi-file request attachments, upload safety, portability qualification | Suitable documents donor after storage/ownership reconciliation |

No FWD commit was fetched into the Golden branch, merged, cherry-picked, or applied.

## I. Deployment Tooling Certification

- Certified chain: Scheduled Task → system `C:\Windows\System32\cmd.exe /d /c` → `PYTHONPATH=<release>` → `cd /d <release>` → release-local `runtime\python.exe` → approved external `phase1b_production_cutover_runtime.py serve` → explicit `--env`, `--repo`, `--host 127.0.0.1`, `--port 5101`, and log options → release-local Waitress child `-m waitress --listen=127.0.0.1:5101 backend.wsgi:app`.
- The tooling explicitly rejects direct Python/Waitress Scheduled Task actions, unsupported shell chaining, mismatched repo/runtime/working directory, wrong launcher/host/port, multiple listener owners, and orphan or mismatched listeners.
- Allowlisted packaged runtime SHA256: `F4A8F108AA89A78D7986F01FB8F6AA8AF5E2D35E00617A8453EB1F15DF945070` — exact match.
- Certification markers included `STATE_LIFECYCLE_AUDIT=PASS`, `LAUNCHER_CHAIN_MODEL=PASS`, `DIRECT_WAITRESS_TASK_ASSUMPTIONS=0`, `LISTENER_PROVENANCE_MODEL=PASS`, `REAL_PRODUCTION_LAUNCHER_TOPOLOGY=PASS`, `REAL_NONFIXTURE_VALIDATEONLY=PASS`, `VALIDATEONLY_ZERO_MUTATION=PASS`, `FULL_EXECUTE_SIMULATION=PASS`, `ROLLBACK_MATRIX=PASS`, `REAL_ROLLBACK_MATRIX=PASS`, `ONE_PASS_OPERATOR_SIMULATION=PASS`, and `PACKAGE_CORRUPTION_MATRIX=PASS`.
- All execution was against disposable local fixtures/copies. Production was not accessed; no Production environment file, secret, process, IIS site, Scheduled Task, database, or endpoint was read or modified. No deployment occurred.

## J. Golden Baseline Decision

```text
APPLICATION_PROVENANCE =
e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4

ENGINEERING_BASE =
b48e51c8d0eda00bcc7582b68da85528b14547d2

GOLDEN_BRANCH =
codex/golden-production-20260921

DATABASE_HEAD =
20260921_shipment_evidence_ownership
```

## K. Remaining Risks

None that block recovery or certification of the exact editable Golden baseline. PostgreSQL-only execution remains a required pre-deployment/integration gate in a disposable PostgreSQL environment, but it does not create a source-provenance or runtime-equivalence ambiguity.

## L. Verdict

PASS — EXACT EDITABLE GOLDEN BASELINE RECOVERED AND CERTIFIED

## M. Next Goal

```text
GOAL

Freeze the recovered Golden application contracts and produce one controlled,
traceable integration plan. Do not implement or merge integration work yet.

Use codex/golden-production-20260921 as the only source of truth, with
APPLICATION_PROVENANCE=e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4 and
ENGINEERING_BASE=b48e51c8d0eda00bcc7582b68da85528b14547d2.

Treat S7-RC-d6297fd-ct1-frozen / d6297fdf50b27f7d69a5bf2086d11ef2eed882ed
as a Control Tower donor, never as the baseline. Treat FWD-01 through FWD-07
as feedback donors/reference implementations from their independently
normalized history, never as branches to merge blindly.

First freeze executable Golden contracts for routing/navigation, customer and
Expert request workflows, Shipment Detail, localization/time/numeric display,
request counters, quotes/currency, tracking/timeline, evidence/documents,
logistics/private points, geography/reference data, tenant isolation, and
role/authorization gates. Reuse the certified characterization tests and add
only missing contract tests; do not alter Golden behavior during the freeze.

Build a requirement-to-code-to-test traceability ledger from the authoritative
PowerPoint/user-feedback sources. For every requirement, record the Golden
behavior, acceptance decision, affected contracts, candidate donor(s), exact
donor commits/files, conflicts, security/data-migration impact, and proof
required. Do not infer acceptance from donor code alone.

Classify every Control Tower and FWD change as controlled transplant,
reconcile, reimplement, defer, or reject. Produce dependency-ordered integration
cohorts with rollback boundaries and explicit full-stack gates. Preserve Golden
as source of truth whenever donor behavior conflicts or provenance is unclear.

For notifications, freeze the channel-neutral direction:
Business Event -> OperationalOutbox -> Notification Intent -> channel/provider
adapter -> Delivery Attempt/Result. SMS, Email, API/Webhook, and future providers
must remain adapters; do not implement a provider or delivery path in planning.

Output one integration-plan report containing the frozen contracts, complete
feedback/PowerPoint traceability, donor decision matrix, cohort order,
migration/API/UI/security/test gates, unresolved decisions, and a precise first
implementation goal. Do not access Production, use Production secrets, deploy,
push, merge, cherry-pick, or begin implementation.
```

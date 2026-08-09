# PR-4A historical DMS repair and certification report

Generated 2026-08-09 (Asia/Tehran). Non-production execution only.

## 1. Executive Summary

The mandatory historical DMS gate was genuinely flaky: four of five fresh PostgreSQL 18 runs failed the independent miscellaneous-upload invariant with HTTP 201/400. The 400 originated in filesystem storage validation, not authorization, validation, or a database constraint. A bounded product fix and explicit derived historical overlay passed ten of ten repeated historical runs. The authoritative candidate lineage plus the repair then passed the complete PostgreSQL matrix (18/18). Final integrated certification remains blocked because no candidate-bound, same-tenant integrated bootstrap exists for authenticated browser/Golden Path execution; downstream backup, documentation certification, AEP sealing, and RC freeze therefore cannot truthfully pass.

## 2. Historical DMS Failure Reproduction

- Historical commit: `7ae1517fa20266116be723c8fdb8294a8b895d88`
- Historical revision: `20260804_case_documents`
- Engine: PostgreSQL `18.0`; fresh disposable database and storage per run.
- Result: iteration 1 passed; iterations 2-5 failed (`1 PASS / 4 FAIL`).
- Failing response pair: HTTP `201` and HTTP `400`.
- Exact 400 body: `{"error":"Invalid storage destination"}`.
- Requests used the same authorized expert and case, but distinct titles (`Misc 1`, `Misc 2`), filenames (`misc-1.pdf`, `misc-2.pdf`), content bytes/hashes, and generated UUID storage identities.
- Original logs and SHA-256 identities are retained under `pr-4a-dms-repair/`; the response-body diagnostic is retained under `pr-4a-dms-diagnostic/`.

## 3. Root Cause

Classification: `REAL_DMS_CONCURRENCY_DEFECT`.

`PrivateDocumentStorage.write()` called `Path.resolve()` on a generated child directory before creation. Concurrent sibling-directory materialization on Windows intermittently produced a containment comparison failure and raised `DocumentStorageError("Invalid storage destination")`. The route converted that service error to HTTP 400. No PostgreSQL error or database constraint was involved; transaction processing had not reached metadata insertion.

## 4. Historical Invariant

The test proves that two truly independent miscellaneous documents uploaded concurrently to one case both succeed. Each is a separate logical document with version `1`, a unique storage key, active status, no supersession link, and a persisted artifact. It is not a race between replacements or writes to the same requirement/version.

## 5. Repair Applied

Generated partition components remain an integer case identity plus UUID prefix. The storage root is resolved once; the generated relative partition is lexically rejected if absolute or containing `..`, then created beneath that trusted root. UUID filenames, exclusive temporary-file creation, atomic replacement, hashes, authorization, audit, tenant rules, versioning, and database constraints are unchanged. The historical runner applies the exact repair to a detached historical worktree and records that worktree as derived evidence; it does not claim the original commit contained the repair. Diagnostic assertion output was also expanded to retain response bodies on failure.

## 6. Historical PostgreSQL Result

PASS: `10/10` repaired iterations, six tests per iteration, zero skips, fresh databases/storage, real concurrent threads. Evidence: `docs/operational/evidence/pr-4a-dms-repaired/`.

## 7. Current-Head DMS Result

PASS: current-head PostgreSQL compatibility `1/1`; targeted document, fault-injection, migration, and MDPM tests `42/42`.

## 8. PostgreSQL Release Matrix

PASS: `18/18`, zero mandatory failures, zero direct skips. Both historical suites remain explicitly classified and use detached historical identities. Evidence: `docs/operational/evidence/pr-4a-postgresql-18of18/postgresql-release-matrix.json`.

## 9. Candidate Impact

The defect existed in current product code, so candidate `8a840b11fea015a6244c419fa4188c317abc1fab` / tree `ee7455a470056bf133a28b0b4287c89f605d7967` is superseded. Derived repair commit: `12fd8b56b29b7c35c5a46fbe6ca426fca1767c1`; tree: `a21d52ef3cbb75e04256530d1372773ac6aa39a8`.

## 10. Browser/Network Certification

BLOCKED for authenticated candidate binding. A pre-existing local browser target was not started from derived commit `12fd8b5`; it cannot be promoted as candidate evidence. Partial public-shell observation: Persian and English rendered; zero error-level console messages. Shipment/Route/Timeline/Documents/MDPM/OIP/Economics authenticated network identity continuity was not certified.

## 11. FE Browser Certification

Partial only: Persian `html[lang=fa][dir=rtl]` and English `html[lang=en][dir=ltr]` observed, with zero captured error-level console messages. Authenticated FE-2 certification is blocked by the same candidate-bound fixture gap.

## 12. Same-Tenant Golden Path

BLOCKED. No current harness materializes Commercial, Operational, DMS, MDPM, OIP, and Shipment Economics under one synthetic tenant with continuous opaque Shipment identity. Existing seeds are capability-specific and cannot be combined without an unreviewed fixture contract.

## 13. Security Certification

PASS for executable static/regression gates: credential policy (`findings=0`, executable defaults `0`), sole Alembic head `20260818_immutable_fx_provenance`, and shipment identity boundary (zero normative numeric leaks). Repository scan findings were redacted test/example/history fingerprints, not exposed secret values. Integrated authenticated tenant/IDOR browser security remains blocked with the Golden Path.

## 14. OpenAPI Binding

Current file SHA-256: `2537daa975cd42c44147e961c577b60f24c2b985b95e67ae1aa042252b639bb3`. Final RC binding is not sealed while integrated gates are blocked.

## 15. Backup Evidence

NOT EXECUTED. The required ordering places representative backup after a passing Golden Path.

## 16. Restore Evidence

NOT EXECUTED; no representative candidate backup was eligible for restore.

## 17. Performance Smoke

No representative restored-application performance smoke was executed. Unit/integration regression timing is not substituted for this gate.

## 18. Full Regression

PASS for available automated suites: backend `596 passed, 64 environment-gated skips`; frontend `22 files / 111 tests passed`; production Vite build succeeded. PostgreSQL mandatory tests were executed directly in the separate 18/18 matrix, so ordinary-suite skips are not used as release evidence.

## 19. Documentation Certification

NOT CERTIFIED. Technical gates have not all passed, and required named artifacts are incomplete (including System Catalog, Admin Guide, Documentation Index, Configuration Catalog, Production Initialization Checklist, Security Checklist, and Post-Release Backlog).

## 20. Integrated AEP

NOT SEALED. Mandatory authenticated Golden Path, representative recovery, performance, and documentation links are absent.

## 21. Final RC Identity

NOT FROZEN. `CAND-FWD-INTEGRATED-RC-002` is not assigned.

## 22. Git State

Branch `codex/pr-4a-dms-gate-repair`; product repair commit `12fd8b56b29b7c35c5a46fbe6ca426fca1767c1`. This report and its matrices are carried by the following evidence-only commit. Pre-existing untracked release/evidence directories were preserved and not treated as candidate inputs.

## 23. Commits Created

- `12fd8b56b29b7c35c5a46fbe6ca426fca1767c1` — `fix: repair concurrent DMS storage gate`
- Evidence-only HEAD commit — `docs: record PR-4A certification evidence`

## 24. Remaining P0

- Candidate-bound same-tenant integrated fixture and authenticated browser/Golden Path certification.
- Representative backup/SHA-256/fresh restore/restored-app validation after Golden Path.
- Restored-candidate performance smoke and documentation certification.
- Integrated AEP sealing and truthful RC freeze.

## 25. Remaining P1

- Resolve Python UTC deprecation warnings.
- Frontend bundle code splitting (current main chunk exceeds 500 kB).
- Refresh Browserslist metadata.

## 26. Production-only Evidence Gaps

Production identity, secrets delivery, capacity, monitoring, production backup custody, rollback window, and human production risk acceptance remain intentionally absent. Production was not accessed.

## 27. Human Decision Required

No architecture or business decision is required for the DMS repair. A human must authorize/provide a reviewed integrated same-tenant fixture contract or candidate-bound environment before the remaining technical gates can execute.

## 28. Production Preflight Request

NOT REQUESTED. The integrated RC is not frozen and is ineligible for Production preflight.

## 29. Final Decision

PRODUCTIZATION BLOCKED

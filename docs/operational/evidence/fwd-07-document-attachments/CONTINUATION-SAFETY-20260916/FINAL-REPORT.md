# FWD-07 safety/gate integration and named recovery decision package

Date: 2026-09-16. One primary agent; no delegation. Existing work continued, no new discovery/branch/worktree. Root D:/1-webapp/forwarder-dev; branch feature/fwd-07-document-attachments; upstream origin/feature/fwd-07-document-attachments; origin https://github.com/behtashnoori/forwarder.git. Starting HEAD d61e7bcf1780765b2c91e6796150eb3aa7c630dc. Starting dirty safety/test/evidence work preserved. No unrelated starting changes found.

MISSION_RESULT: SAFE_QUALIFICATION_PATH_VERIFIED + KNOWN_GATES_RESOLVED + COMPLETE_NAMED_RECOVERY_ADR_READY_FOR_OWNER. Not PASS_CONTROLLED_LOCAL_FWD07.

SAFETY_GUARD_INTEGRATION: VERIFIED for the qualification paths used here. Existing guard extended, no parallel framework. Explicit allowlisted child environments strip inherited URLs/provider settings. Controlled bootstrap precedes backend imports/plugins, direct pytest and direct browser fixture fail closed. Primary/secondary binds, raw drivers, storage and child bootstrap are validated. Dotenv is disabled by default in guarded children; only explicit synthetic directories/files under owned root may be loaded, with prospective environment validation and no interpolation. Normal runtime branches remain unchanged and do not require test manifests. Production-style CORS tests use owned URLs without Production connections.

CI_ADOPTION: Quality Gates backend step now uses `python -B -m scripts.uat.run_fwd07_disposable_postgres --ci`; public PostgreSQL 18 dependency install follows https://www.postgresql.org/download/linux/ubuntu/. No account, Secrets, workflow permissions, organizational runner, deployment environment or deploy trigger changed. Existing workflows are quality gates and secret scanning, triggered by push/pull_request (secret workflow also manual dispatch); no deployment step found. Linux workflow execution is not qualified by a Windows local run.

LOCAL_CI_EQUIVALENT: PASS — owned run dc370a5743d34bcb9c00f19b715a6dee, 1096 passed / 226 existing conditional skips / 1 existing XFAIL, 502.54s; current five PostgreSQL document tests included. Same owned entry-point command, Windows local platform; no remote PASS inferred.

REMOTE_CI: NOT_OBSERVED; pending delivery verification. No GitHub Actions connector or gh executable available. Never infer a remote PASS from local results.

FOUR_GATES_RESULTS: all PASS in owned boundary runs 8fceed0ecf6d412984445dfb5a279cf1, 648c2f1930404bc983b510f9a50dfec1, f7b4c220dcc447bf97abfa594aaf6088 and c446e9261c76480ead08e865997a0762. Last run also rechecks security configuration and credential verifier: 21 passed; focused document/tenant regression: 4 passed. Real PostgreSQL synthetic ownership/write/read proof PASS; eight negative unittest cases, including direct-browser rejection and disallowed adjacent/local-hostname/external endpoints, PASS before cluster creation. Owned shutdown receipts retained.

| Known gate | Correction / preserved invariant | Result |
| --- | --- | --- |
| test_alembic_version_table::test_historical_long_revision_ids_are_detected_and_graph_has_one_feature_head | Fixed FWD06 sole head, explicit FWD05 predecessor/security ancestor; long historical IDs and uniqueness preserved | PASS |
| test_operational_execution_190::test_verification_separation_and_one_migration_head | Current head only; self-verification/verification separation intact | PASS |
| test_project_configuration::test_identity_catalog_and_single_head | Current head only; opaque identity/catalog assertions intact | PASS |
| test_global_logistics_point_materialization::test_phase4b_materialized_point_uses_ordinary_tracking_and_project_contracts | Existing tracking_time.offset validates actual aware test-clock inputs and provenance; inactive/legacy point paths, snapshots, tenant/project ownership preserved | PASS |

ZERO_REQUIREMENT_BROWSER_UAT: PASS at 1280x800 and 390x844 RTL, real backend and SQLite file owned by each run. Final run b69ed76abd3449728aef580eb6ccdebf has ordinary EXPERT, active membership/valid assignment, no seeded document definitions/requirements, natural landing/login/list/detail/tab navigation, API 200 with requirements=[], explicit zero-requirement text, existing miscellaneous upload disabled until title then real POST 201, logout/login/reopen with zero requirements/one miscellaneous file, UI download matching source bytes, no page errors and no horizontal overflow. API responses were not mocked. Synthetic harmless PDF only. Browser external font requests blocked; fallback-font layout qualified. Full browser traces, tokens, uploaded bytes and runtime DB stay outside Git.

BROWSER_ENVIRONMENT_CORRELATION: VERIFIED_DISPOSABLE for these new runs only. Manifest correlates unique root, SQLite DB, private storage, owned PostgreSQL cluster, exact API/UI host/ports; correlation receipt records backend/frontend/browser-runner PIDs and teardown records process exits/owned-cluster shutdown. Python sockets permit only owned PG plus the two exact manifest endpoints; browser HTTP/WebSocket routing permits exact UI/API origins, never general loopback/network. Earlier uncorrelated browser runs remain ENVIRONMENT_IDENTITY_UNPROVEN. Guard is a cooperative test harness, not an OS sandbox for malicious code.

OTHER_NEW_FAILURES: preserved, not waived. First local CI-equivalent run e493e1f34f4045cdbb7cb42ee3bc9dae: 7 failed / 1090 passed / 225 skipped / 1 xfailed, 513.88s. Causes: accidentally providing historical DMS schema-parity fixture a current FWD07 target; credential verifier native git child rejected; guarded dotenv/CORS fixtures incompatible with owned configuration. Fixes: dedicated FWD07_DISPOSABLE_POSTGRES_URL/STORAGE_ROOT namespace for current tests, historical DMS scenario unchanged; verifier uses runner-captured complete tracked inventory rather than a native exception; synthetic dotenv prospective-validation seam and owned Production-style CORS URLs. Historical DMS release suite remains conditional on its own historical revision/checkout, as existing release_postgres_orchestrator records; no failed test was changed to skip/XFAIL, no historical scenario converted to current. Current five PostgreSQL document tests execute on the current migrated owned cluster.

Browser 0fc324f7a491428598c3ad37d71649f6 exercised both journeys but was DIAGNOSTIC due blocked-resource classification, not relabeled PASS. febc5cd41e864c9c80aa76d94a2122f3 failed on networkidle navigation timeout; retained as FAIL. Final zero scenario uses DOM load plus actual UI/API assertions; expected security resource blocks are recorded separately from page errors and final completion/page-error assertions remain mandatory. Later guarded runs independently pass.

HISTORICAL_DB_CHANGE_IMPACT: UNKNOWN.
LIVE_ACCESS_TO_FORWARDER_AUTH_TEST: NO.
EXISTING_DB_EXPOSURE: REPORTED. No new connection/introspection/count/dump/migration-current/cleanup/reset/restore against that database. Historical incident is not closed by these results. Prior report/raw failures preserved. Exact historical command/before-after remain missing; no new assurance fabricated. Historical read-only investigation still needs separate confirmed destination/role authority.

RECOVERY_ADR_ID: ADR-049 — Request document upload operation recovery.
RECOVERY_ADR_STATUS: PROPOSED — OWNER ACCEPTANCE REQUIRED; NO RECOVERY IMPLEMENTATION AUTHORITY.
RECOVERY_ADR_SHA256: 14B4B114BE9D4ACB9CC22DC4F30DF42EBD6375083F99D86FBB98DDE738016AD2.
ORIGINAL_PROPOSAL_PRESERVED: YES; SHA256 A88834429A659F7ED6A4959C5DA940D42D5D8A644C596333F138140590D72F53, matches supplied original. ADR-049 is a linked successor, no Accepted records superseded.
OPEN_OWNER_DECISIONS: named acceptance/revision of ADR-049 including its 90-day discovery/durable non-reuse retention and initiating-actor privacy choice, plus separate local implementation authority. Historical incident investigation is separately unauthorized. No safety/gate waiver requested.

Architecture rules checked: Development Gate/baseline/index; affected ADR-006/010/011/014/015/016/048/M1. Runtime canonical owners unchanged: CaseDocumentRequirement, CaseDocumentFile, private storage; existing tenant membership/request assignment remains authority. Compatibility tracking fixture only, no legacy feature/schema/history change. Operational timestamps are Instants, durations elapsed/lease/window; no new business time persistence implemented. Sole migration head is 20260916_fwd06_tracking_time with FWD05 predecessor; no migration file changed. LPAF entry confirms v2.2 GLOBAL_ACTIVE; v2.4 hash matches 217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397, OWNER_APPROVED / PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE. Mother impact NONE; project impact new PROPOSED ADR/index only. REFERENCE_MAPPING=NOT_PROVEN, existing bounded deferral, no security/data/test exemption.

COMMITS_OR_UNCOMMITTED_CHANGES: verified scoped patch authorized for delivery; see appended Git receipt. Only mission files eligible for staging after gates. Final tested-code commit and Git delivery receipt recorded below after qualification; local/remote delivery HEAD is provided in chat after fetch. Candidate identity is starting HEAD + preserved starting diff/hashes + final diff/source hashes (candidate-start/final files), not HEAD alone. Full suite precedes two added dotenv negatives and final browser pre-import hardening; final affected bounded/browser checks supplement it without another unnecessary broad run.

WORKTREE_STATUS: mission code/ADR committed; evidence prepared for its own commit. Final clean/ref synchronization verified after push in chat. No reset/clean/stash/amend/force checkout/history rewrite/force push/merge/release tag/deploy.
EVIDENCE_PATH: docs/operational/evidence/fwd-07-document-attachments/CONTINUATION-SAFETY-20260916.

Static verification: frontend lint PASS (12 existing warnings), structure PASS, build PASS (existing browsers-data/chunk-size warnings); raw logs retained. Whitespace, redacted secrets and credential policy PASS; final staged scan required before commit. No generated dist/runtime DB/data/session/token/private download URL/browser trace/customer file is staged. Manifest evidence omits bulky tracked inventory but retains its count/hash; complete manifest remains in the owned local run root.

Reproducible safe commands from D:/1-webapp/forwarder-dev, using installed Python and PostgreSQL 18 (browser also existing local Node/Playwright/Chromium):

```powershell
python -B -m scripts.uat.run_fwd07_disposable_postgres --boundary-proof --test-target backend/tests/test_security_config.py --test-target backend/tests/test_credential_policy_verifier.py
python -B -m scripts.uat.run_fwd07_disposable_postgres --ci
python -B -m scripts.uat.run_fwd07_disposable_postgres --browser
```

Each command creates its own unique resources, retains logs/exit codes and performs owned teardown. Never set URLs pointing to existing databases. Direct pytest/fixture is deliberately rejected. Ordinary CI/platform differences are not proof of remote execution. See ADR-049 and GAP-DECISION-MAP.md for the complete decision text and coverage of previously undefined gaps.

RECOVERY_RUNTIME_IMPLEMENTED: NO.
RECOVERY_ADR_ACCEPTED: NO.
FWD07_COMPLETE: NO.
REAL_MESSAGES_SENT: NO.
LLM_APIS_CALLED_BY_PRODUCT: NO.
PRODUCTION_ACCESS_OR_DEPLOYMENT: NO.

## Git delivery preparation

TESTED_CODE_COMMIT: e5e9ff7edc8ea22dbb47759b2b1e28e10895e45a.
PROPOSED_ADR_COMMIT: 6683a7ab7f81812df1a5bf7dddc5dec9b42e1a0e.
Evidence commit follows; final LOCAL_HEAD/REMOTE_HEAD and ahead/behind are verified after push/fetch in the delivery response. All mandatory affected checks passed before staging; staged whitespace/secret/generated checks passed. Only the feature branch is authorized for push; reviewed existing workflows contain no deploy action.

Raw-evidence delivery: Git whitespace checks exposed original raw pytest/diff whitespace. Exact bytes are preserved locally at the original paths, unstaged/untracked, and delivered as sibling .raw.json lossless base64 transports with original paths/SHA256. Decoded bytes were secret-scanned before encoding. No historical raw output was edited, no whitespace rule changed. raw-evidence-transport.json enumerates these files. Final worktree therefore retains only these known raw evidence originals; this is explicitly reported rather than hidden with ignore rules.

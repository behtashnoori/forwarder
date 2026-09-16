# FWD-01 discovery and architecture gate

Date: 2026-09-16. Current status: QUALIFIED_FOR_FEATURE_BRANCH_DELIVERY.
The original discovery record below is preserved; the explicit named Owner
acceptance and implementation continuation are recorded at the end.

## Mission and baseline identity

- Mission: FWD-01 — Modular Event, Notification & Agent-Action Foundation.
- Owner/authority: user issuing FWD-01; no personal/organizational title inferred.
- Repository: `D:/1-webapp/forwarder-dev`.
- Starting branch: `baseline/recovered-3a73692`.
- Starting HEAD and reachable origin branch:
  `38431da96c4f36ceaa07c550e594bf2d08d34e38`.
- Upstream: `origin/baseline/recovered-3a73692`; ahead 0, behind 0.
- Initial working tree: clean. Origin `ls-remote` succeeded.
- Requested feature branch absent locally/remotely, then created at baseline:
  `feature/fwd-01-notification-foundation`.
- No reset/rebase/clean, production action or customer messaging performed.

## FACT / ASSUMPTION / UNKNOWN / DECISION NEEDED

FACT: quote creation, expert inbox, operational outbox, ownership census,
assigned-work evaluator and explicit reconciliation CLI already exist.
ASSUMPTION: a fixed fake-only quote-availability policy can prove the slice
without changing a customer journey; implementation must verify this.
UNKNOWN: real production identity; recipient eligibility for real delivery;
PostgreSQL qualification environment availability (not yet inspected).
DECISION NEEDED: named acceptance of [ADR-045](../../adr/ADR-045-notification-action-foundation.md).

The project baseline section 2 states: "An implementation prompt is not itself
ADR acceptance unless it explicitly accepts a named ADR decision."
`docs/architecture/CODEX-DEVELOPMENT-GATE.md` requires a PROPOSED ADR and a stop
before implementation for new aggregate ownership and cross-domain writes.
FWD-01 names no accepted notification ADR. Creating action ownership triggers
this explicit gate, even though delivery and routine implementation choices
are otherwise authorized. No owner acceptance has been fabricated.

## APPLICABLE_LPAF_RULES

Framework root: `D:/1-webapp/29-lpaf/29-lpaf (1)/29-lpaf/lpaf`.
Read the index, v2.2 framework/entry protocol, v2.4 governance/entry protocol,
owner pilot decision, identity re-attestation, changelog and four linked lesson
candidates. `_review`, `_archive`, `_working` are not normative sources.

`LPAF_V2_4_PILOT = ADOPTED` explicitly by FWD-01, for this mission only.
Global ACTIVE remains v2.2. v2.4 is OWNER_APPROVED /
PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE. Verified SHA256:
`217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397`.

Rigor B, with integration/concurrency evidence proportional to this durable
action boundary. Lifecycle M0/M1 and proposed M2-M4; M5-M6 blocked at project
decision gate. M7/M8 production release/operation are outside authority.

Applicable: v2.2 sections 5-8, 10-12 (mission, value/SOR/data chain, authority,
traceability, regression, ADR and stop); v2.4 MOD-01/03, C-01, ATT-03,
READ-02, TIME-01, AI-02/03, QUAL-01..05, ADOPT-01/02 and C-03.
AI-01 applies to the bounded command interface only; retrieval and prompt
injection tests are N/A without an LLM/retrieval client. MOD-02 shared core,
PROC configurable workflows, EVD operational evidence management, ANA,
READ-01 derived read models, DOC file storage and ATT-01/02 full attention
lifecycle are N/A: no such new subsystem is in this slice. Structured action
results are a future attention source, not an implemented attention engine.
v2.3 analytics/journeys are not adopted: no analytics or new UI surface.
No framework MUST conflict identified; named project authority remains open.

Pilot review/expiry: at FWD-01 qualification or any material scope/authority
conflict. Owner may revoke adoption; retain evidence and revert application
behavior through the governed recovery path. Untested rules remain
EVIDENCE_PENDING. Exit requires the real slice, mandatory checks and verified
remote push; documentation alone cannot satisfy it.

## REUSE / EXTEND / NEW discovery map

| Area | Disposition | Repository evidence / constraint |
| --- | --- | --- |
| Quote lifecycle | EXTEND | `backend/services/quote_service.py:create_quote_for_request`; existing `waiting_for_customer`, quote and log commit |
| Customer-visible quote | REUSE | customer workflow/latest-quote payload and public tracking projection; no invented lifecycle |
| Request/shipment status | REUSE | commercial `ShipmentRequest` distinct from `OperationalShipment` under ADR-002 |
| Customer/contact | REUSE with guard | `Customer`, `CustomerContact`, `CustomerGamification`, request linkage; global email match is not tenant authority |
| Existing notifications | PRESERVE/REUSE | `notification_service.py`, `assignment_service.py`, expert inbox; not an external-delivery queue |
| Email | DO NOT REUSE simulation | registration helper logs intended address/verification URL; no delivery assurance; no actual secret values read or copied |
| SMS/provider/webhook | NEW bounded adapter | no provider execution subsystem found in focused backend services search; no live adapter needed |
| Background jobs | EXTEND pattern | `operational_cli.py` explicit reconciliation entry point; browser-independent bounded command |
| Task queue/retry | NEW action semantics | no delivery-attempt/UNKNOWN reconciliation owner found; use database, no broker |
| Event/outbox | REUSE/EXTEND | `OperationalOutbox`, census-aware `_outbox`; add public contract and dedicated consumer semantics |
| Idempotency | REUSE pattern | `OperationalIdempotency`, ADR-010; unique event/policy action and atomic dispatch claim |
| Audit | REUSE pattern | `ExpertConsoleLog`, `OperationalAudit`; new structured attempt provenance owned by action module |
| Authorization | REUSE | `assigned_work_authorization.authorize_work_action`; active persisted actor/membership/current root; do not copy legacy admin bypass |
| Tenant/org | REUSE/EXTEND | ownership service, tenant inventory, `quarantine.py`, `census_context.py`; no bypass |
| Agent | NEW bounded command contract | no external AI client required; deterministic prepare/approve/execute/result proof |
| Tests/gates | EXTEND | quote response, expert assignment/inbox, tenant/census, architecture, PostgreSQL suites; `.github/workflows/quality-gates.yml` |

Selected proof event: existing customer-visible quote availability after
successful quote creation. Design is in ADR-045. SOR chain: commercial owner
-> atomic event -> fixed policy -> action/attempt SOR -> fake adapter -> result
-> tenant-authorized audit query. Value: preserve side-effect intent through
provider/process failure without coupling commercial rules to a provider.
Data: organization/actor master references, subject-specific recipient,
transactional quote/event/action and historical attempt evidence. No new
master-data population or historical notification backfill.

## REFERENCE_IMPACT / PROJECT_ARCHITECTURE_IMPACT

| Type | Owner | Actual reference | Result | Rationale |
| --- | --- | --- | --- | --- |
| FRAMEWORK_REFERENCE_IMPACT | LPAF Architecture/Business Owner | framework root above, `LPAF-v2.2-Architecture-Framework-FA.md` and `candidates/v2.4/LPAF-v2.4-Modular-Operational-Intelligence-Governance-FA.md` | NONE | product implementation does not amend general governance |
| PROJECT_REFERENCE_IMPACT | Forwarder Architecture Owner / mission issuer | `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md`, `ADR-INDEX.md`, proposed ADR-045 | UPDATE_REQUIRED | new action ownership, transaction/command and provider boundary; proposal indexed now; normative baseline update follows named acceptance |

## EVIDENCE_PLAN

After acceptance: record environment identity and source/schema/policy versions;
implement targeted synthetic tests for all twelve mission requirements;
representative PostgreSQL concurrency and migration upgrade/recovery/re-upgrade;
affected business regression and repository mandatory gates; secret/generated
file review and diff check; atomic commit, non-force push, fetch and verify
local/remote HEAD plus ahead/behind 0/0. Detailed logs belong here, concise
summaries in conversation. No PASS from a plan or unexecuted test.

Actor matrix: assigned EXPERT/tenant A/own request allows; unassigned Expert A,
Expert B/tenant B, inactive/revoked/ambiguous membership and Platform Admin
without tenant work authority deny; customer recipient must match certified
parent relationship; prepared/approved intent must fail after relevant changes.

Product tests, migration, browser UAT, build/lint and remote push: NOT_RUN.
Browser UAT may become N/A only after confirming no user-facing journey change.
Engineering Complete: NO. Product Complete: NO. Release Ready: NO.
Release Complete: NO. Mission Complete: NO.

Preserved gaps:
`FORWARDER-HISTORICAL-REPLAY-001 = BLOCKED_MISSING_EXTERNAL_EVIDENCE`;
`PRODUCTION_IDENTITY = UNKNOWN`.

## Preparation verification

- `python scripts/check_architecture_governance.py`: PASS (exit 0).
- `git diff --check`: PASS; only line-ending conversion warnings, no errors.
- `python scripts/scan_repository_secrets.py current`: PASS, zero findings.
- Additional scanner invocation covering both new untracked Markdown files:
  PASS, zero findings. No real customer data or secrets included.
- Diff/file review: only ADR index, proposed ADR-045 and this evidence record;
  no application, schema, generated artifact or historical evidence changed.
- Commit/push: NOT_RUN; mission qualification is not complete, so the mission's
  post-qualification push condition has not been met.

## Explicit Owner acceptance and continuation

2026-09-16: Owner message “FWD-01 — ADR-045 Owner Acceptance and Autonomous
Implementation” explicitly accepted ADR-045, FWD-01 implementation only. The
full ADR was compared with the accepted summary; no material additional scope
was identified. Status/index updated with the actual source of acceptance.
The previous pending decision is closed, not inferred from the initial prompt.

Resume checks: correct repository and requested feature branch; HEAD still
`38431da96c4f36ceaa07c550e594bf2d08d34e38`, baseline ancestry confirmed. Only
the three existing mission documentation paths were dirty. LPAF current hash,
index and post-cleanup re-attestation rechecked and unchanged. No AGENTS.md
was found in the repository or previously checked parent directories.

Implementation and detailed public/ownership/dispatch contracts are maintained
in ADR-045, not in a parallel architecture document. Project baseline section
15 and tenant inventory updated; FRAMEWORK_REFERENCE_IMPACT remains NONE.

Qualification environment: Windows, Python 3.13, repository dependencies,
PostgreSQL 18 binaries; a new loopback-only cluster under ignored local
`.fwd01-qualification/pgdata`, port 55461. Synthetic database names start
`forwarder_fwd01_test_`. No deployment, installed scheduled task or real
provider/LLM connection. The normal suite is explicitly pinned to in-memory
SQLite; dedicated PostgreSQL proof uses only the new cluster.

An early generic regression run inherited `TEST_DATABASE_URL` targeting the
pre-existing loopback `forwarder_auth_test` on port 5432. Its test bootstrap
failed when current metadata met the old outbox schema; no migration was run
there. Subsequent test commands explicitly override/scrub inherited database
URLs. This environment failure is not a product PASS and no old database was
reset, cleaned or migrated to force the tests through.

### Root causes and repairs during qualification

- Runtime census protection correctly rejected raw SQLAlchemy TRUNCATE during
  disposable setup. Test-only DBAPI cleanup is guarded by explicit loopback
  and disposable database identity; runtime guards remain active.
- Legacy request/customer FK does not itself forbid a foreign customer link.
  The new notification boundary explicitly checks certified tenant ownership;
  a synthetic adversarial link is rejected before any attempt. No broad CRM
  rewrite is introduced.
- Census snapshots must have a bounded job lifetime. New transaction commands
  reject pending caller writes and use the existing `census_unit_of_work`
  lifecycle, refreshing background context between independent commands.
  Quarantined targets remain blocked without dispatch.
- Late result before a recovery scan also needs lease checking. Result handling
  now persists UNKNOWN after expiry and requires explicit reconciliation.
- New migration head updates current sole-head assertions and live package
  builder metadata; frozen historical deployment identities are unchanged.

### Verification scope and status interpretation

Targeted tests exercise both SQLite and migrated PostgreSQL. PostgreSQL-only
cases skip only their SQLite duplicate; PostgreSQL executions are the evidence
for consumer/worker/revocation ordering and physical tenant FKs. Standard suite
PostgreSQL families without their own explicit disposable URLs remain skipped;
they are not certified by FWD-01's dedicated PostgreSQL cases.

Migration proof uses an independent disposable database and actual Alembic
upgrade, empty downgrade, re-upgrade, sentinel preservation, time/constraint
inspection, real qualification CLI dispatch and populated-downgrade refusal.

No UI surface/response shape changed. Browser UAT: NOT_APPLICABLE under the
mission rule; authenticated existing quote API to durable worker is tested.
Engineering/Product completion is assessed for this fake-only foundation;
Production Release Ready/Complete are NOT_APPLICABLE and are not implied.

### Assertion-to-evidence map

All new behavior tests are in `backend/tests/test_fwd01_notifications.py`;
the independent migration/CLI proof is `test_fwd01_migration_postgresql.py`.

| Control | Test assertion |
| --- | --- |
| Existing valid quote -> event -> action -> result | `test_real_api_quote_to_independent_worker`, `test_full_chain_and_controlled_commands` |
| Business rollback has no false event | `test_business_transaction_rollback_leaves_no_event` |
| Consumer crash before/after commit, replay, unrelated outbox | `test_consumer_crash_replay_and_unrelated_event_preserved` |
| Same quote event uniqueness, different quotes remain distinct | `test_same_quote_cannot_emit_duplicate_logical_event`, `test_distinct_quotes_and_old_quote_suppression` |
| Real competing consumers/workers | `test_postgresql_competing_consumers`, `test_postgresql_competing_workers_release_locks_for_provider` |
| Provider failure, bounded retries and business preservation | `test_failure_backoff_exhaustion_and_business_preservation` |
| UNKNOWN, expiry, stale result, reconciliation before retry | `test_unknown_reconcile_and_stale_worker_fence`, `test_late_result_without_reaper_is_unknown` |
| Revocation/reassignment before final decision | `test_postgresql_revocation_commits_before_dispatch_decision` (actor, assignment, membership) |
| Changes to effective prepared input/authority | `test_execution_revalidates_prepared_intent` parameter matrix |
| Tenant/recipient and physical FK rejection | `test_cross_tenant_recipient_cannot_be_attached`, `test_postgresql_attempt_tenant_constraint` |
| Ownership census and unavailable recipient | `test_quarantined_target_cannot_dispatch`, `test_missing_recipient_preserves_business_and_observable_block` |
| Controlled authenticated command phases | `test_full_chain_and_controlled_commands` |
| Simulated outcomes, duplicate-safe results | `test_provider_outcomes_and_duplicate_results` |
| No silent fake fallback or private exception logging | `test_provider_exception_redacted_and_no_fallback` |
| Upgrade/downgrade/re-upgrade, preserved data/history, CLI | `test_fwd01_postgresql_migration_recovery_and_cli` |

The existing operational PostgreSQL regression initially failed because its
legacy `manager` fixture did not establish current tenant oversight authority.
Its intended verifier now declares ORGANIZATION_ADMIN with the existing scoped
permission list. No runtime authority rule was relaxed; the real regression
then passed on a fresh disposable database. Census PostgreSQL regression also
passed. The database bootstrap role in that existing test is separate from
the real application actors used to qualify FWD-01.

Final security review additionally restricted interactive action lookup by
server-derived tenant and initiating actor before reading the action, and
explicitly rejected unknown/Platform authority in the notification contract.
Impact is bounded to notification commands/intent validation. The complete
new SQLite/PostgreSQL tests plus existing expert quote/customer response tests
are rerun after this change; unrelated backend tests retain the complete-suite
evidence. PostgreSQL's pre-existing authority CHECK rejects unknown persisted
authority even earlier; SQLite metadata fixtures exercise the runtime guard.

## Final qualification results — run-20260916

| Gate | Actual result | Evidence |
| --- | --- | --- |
| Complete standard backend suite | PASS: 891 passed; 134 skipped; 1 existing xfailed | `run-20260916/full-backend-certified.log` |
| Final FWD-01 SQLite + PostgreSQL assertions | PASS: 68 passed; 6 SQLite duplicates of PostgreSQL-only proofs skipped | `run-20260916/fwd01-final-proof.log` |
| Affected business/authorization/census/architecture/package regression | PASS: 88 passed; 1 existing xfailed | `run-20260916/affected-regression-final.log` |
| Independent PostgreSQL migration + real CLI, final code | PASS: 1 passed | `run-20260916/migration-certified.log` |
| Existing operational PostgreSQL transaction/concurrency/outbox regression | PASS: 1 passed | `run-20260916/operational-postgres-final.log` |
| Existing PostgreSQL ownership census fence regression | PASS: 1 passed | `run-20260916/census-postgres.log` |
| Architecture structural gate | PASS | `run-20260916/architecture-final.log` |
| Frontend lint | PASS: zero errors, 12 existing warnings | `run-20260916/lint.log` |
| Frontend build | PASS; existing bundle-size warning | `run-20260916/build.log` |
| Repository structure | PASS | `run-20260916/structure.log` |
| Secret review | PASS: tracked and new files zero findings; staged scan before commit | `run-20260916/secret-tracked.log`, `secret-new.log` |
| Whitespace/generated/scope review | PASS: mission source/docs/tests only; qualification DB, node_modules, dist and bytecode excluded | final staged diff review |
| Browser UAT | NOT_APPLICABLE: no UI journey changed | rationale and real authenticated API proof above |
| Production/provider delivery/LLM | NOT_RUN / NOT_AUTHORIZED | no such actions performed |

The complete standard run started before the final bounded action-lookup and
authority guard review. Final FWD-01 proof reruns all affected notification
assertions on both engines after that review; existing quote/customer tests
also passed in that rerun. A test expectation for unknown authority was then
corrected to recognize the PostgreSQL CHECK rejecting it before dispatch, and
the final 68-pass run includes that corrected assertion. Migration/CLI was
rerun against the final code in a fresh database. This impact/retest record
does not relabel any earlier failure as a successful execution.

Six SQLite skips are only PostgreSQL physical locking/ordering/FK cases, all
executed in the PostgreSQL half. The standard suite's 134 skips include
independently gated PostgreSQL/environment suites; their reasons remain in
the full log. Relevant FWD-01, operational-outbox and census PostgreSQL gates
were separately supplied with dedicated databases and passed. The pre-existing
MT-3 numeric public-tracking characterization remains XFAIL and is not fixed
or certified by this mission. Both named historical/Production gaps stay open.

Source/environment/policy/provider identity is in `run-20260916/source-manifest.json`.
It records exact working-file SHA256 and normalized Git blob identities;
Windows Git line-ending normalization is not a change in Python semantics.
No real recipient, message body, bearer code, password URL or model reasoning
is included. Detailed unsuccessful development logs remain locally under the
ignored `.fwd01-qualification` directory; root causes are recorded above.

Engineering Complete: YES for the accepted fake-only slice.
Product Complete: YES for the bounded infrastructure contract and real API path.
Production Release Ready / Release Complete: NOT_APPLICABLE; no deployment authorized.
Ready for next slice: YES, subject to a new explicit scope for real providers.

Git completion is verified after the implementation commit and non-force push.
The resulting commit and remote HEAD receipt is written locally to
`.fwd01-qualification/remote-verification.json` and reported in the conversation;
it is intentionally outside its own commit to avoid a self-referential hash.
No baseline/main merge or release tag is part of this delivery.

# OIP-2 final closure evidence — 2026-08-08

## Result

`OIP-2 VALIDATED WITH EXPLICIT LIMITATIONS`

No production access, deployment, push, candidate commit, or immutable promotion identity was created. The weakest mandatory link is the incomplete final browser recovery matrix described below.

## Baseline and custody

- Branch and trusted HEAD: `codex/oip-2-situation-attention` at `3a2e694ca1196ffb3caa60eca1d0ed27fccd2587`.
- One Alembic head: `20260815_oip_threshold_policy`.
- Disposable database: local PostgreSQL 18, database name constrained to `forwarder_oip2_gate_*`; no production configuration or data used.
- Existing dirty-tree OIP threshold work and unrelated release evidence were preserved.

## PostgreSQL race and recovery evidence

- `backend/tests/test_oip_races_postgresql.py`: 13/13 passed on PostgreSQL 18.
- Isolation/locking: PostgreSQL READ COMMITTED, `SELECT ... FOR UPDATE` for existing Situations, and `pg_advisory_xact_lock(hashtextextended(identity, 0))` for logical identity creation.
- Invariants covered: deduplication, acknowledgement/claim/resolution/snooze preservation, deterministic stale-writer conflict, occurrence count, same-watermark terminal preservation, stale-calculation rejection, projection-worker deduplication, and rebuild versus human interaction.
- `backend/tests/test_oip_rebuild_recovery_postgresql.py`: passed. Only `OipAttentionProjection` and `OipProjectionState` were destroyed/rebuilt; Situation, history, FactReference, Signal, assignment, and disposition survived. Interrupted rebuild rollback/restart and clear/reopen recovery passed.

## OpenAPI and browser evidence

- Exact OIP runtime/OpenAPI parity test passed for all six runtime path templates and methods.
- OpenAPI SHA-256: `E4E83A4067E5F70FDA95B9BA14DD0EDCE741135B3C16BAE6CB482D1E16E3A298`.
- Removed all OIP `window.prompt` use. Added labeled, validated, cancellable, permission-aware reason and snooze controls; server remains authoritative.
- Corrected Promise-returning OIP effects and Tehran `datetime-local` conversion.
- Authenticated synthetic browser PASS: all seven families, queue ranking/explanation, detail, DecisionContext, Recommendation, evidence, acknowledge, claim, IN_PROGRESS, snooze, resolve, dismiss, UNASSIGNED, FRESH, opaque navigation, Persian RTL, English LTR.
- Clean new-tab OIP flow browser console: zero errors.
- Remaining browser limitation: controlled snooze-expiry return, browser-observed source clear/reopen, and browser-observed STALE/REBUILDING/DEGRADED were not all repeated after the final timezone fix. Backend PostgreSQL recovery and lifecycle tests cover them, but EAAF does not permit substituting those tests for the mandatory browser gate.

## Seven-family final status

- `NEXT_MILESTONE_OVERDUE`: `ACTIVE_VALIDATED`
- `CHECKPOINT_OVERDUE`: `ACTIVE_VALIDATED`
- `ROUTE_DEPENDENCY_BLOCKED`: `ACTIVE_VALIDATED`
- `REPLAN_REQUIRED`: `ACTIVE_VALIDATED`
- `DOCUMENT_READINESS_BLOCKED`: `ACTIVE_VALIDATED`
- `ACTIVE_DELAY_OR_EXCEPTION`: `ACTIVE_VALIDATED`
- `EXECUTION_UNIT_STALE`: `ACTIVE_VALIDATED`

The governed overdue/stale families also retain deterministic `INACTIVE_UNCONFIGURED` abstention when an authoritative effective threshold is absent.

## Regression and migration rehearsal

- OIP unit: 13 passed; OIP race: 13 passed; rebuild/recovery: 1 passed; OpenAPI parity: 1 passed.
- Full backend: 580 passed, 47 skipped.
- Frontend: 111 passed. Lint: zero errors, 12 pre-existing warnings. Production build passed with the existing bundle-size warning. `git diff --check` passed.
- PostgreSQL rehearsal: fresh upgrade to head passed; downgrade with durable OIP evidence failed closed as designed; explicitly safe disposable evidence cleanup allowed downgrade to `20260813_mdpm_readiness`; re-upgrade returned to the single final head.
- Migration SHA-256: base `EECA7653FFADD1F803D21CDD9B54E30FE81B7683F178FCE07080E25AD219204C`; threshold `B5DA78135E348B3604A0720B2B8EAF85E27820F31312FAE9A7DE6CAD6C855C1B`.

## Security, impossible intelligence, and framework delta

Tenant-first lookup, permission enforcement, opaque public identities, expected-version conflicts, reason validation, ACTION_GAP, and no numeric member identity remain validated. OIP does not produce financial exposure, carrier reliability/responsiveness, compliance score, predictive delay/risk, or customer criticality without authoritative facts; it abstains.

Accepted limitations remain unchanged: opaque assign/reassign identity deferred; UNASSIGNED plus Claim supported; no AI; no generic Action Engine; no financial/compliance/carrier/predictive intelligence.

Framework Delta: `CONFIRMS EAAF`; `NO FRAMEWORK CHANGE`.

## Promotion disposition

No candidate identity or commits were created because the weakest mandatory browser link remains incomplete. Human business or architecture decisions are not required; completing the remaining bounded browser recovery observations is implementation validation work.

## Final recovery-matrix attempt (2026-08-08)

Result: `HUMAN ARCHITECTURE DECISION REQUIRED`.

- Disposable environment: local PostgreSQL 18 database `forwarder_oip2_gate_20260808_181105`, migration `20260815_oip_threshold_policy`, synthetic seed `oip_uat_operator` / seven synthetic OIP facts, backend `127.0.0.1:5001`, frontend `127.0.0.1:8080`, start `2026-08-08T14:41:36Z`. No production configuration, data, deployment, or push was used.
- Snooze expiry browser PASS: Situation `2cecbca2-5960-4873-9a01-527d6c5fe4fd` was snoozed through the labeled `datetime-local` UI, displayed `SNOOZED` and the Tehran-local expiry, left the queue, then returned through the normal `observe` reconciliation contract using its supported controlled `calculated_at` fixture. The same public identity returned `OPEN`, occurrence remained `1`, and timeline displayed `SNOOZE` followed by `RETURNED_TO_ATTENTION / SNOOZE_EXPIRED`.
- Clear/reopen browser PASS using the disposable authoritative synthetic source adapter: the same Situation was cleared with source version/watermark `3`, displayed `RESOLVED`, and disappeared from attention. Source return at version/watermark `4` reopened the same public identity, returned it to attention, displayed occurrence `2`, preserved prior human/recovery history, refreshed evidence and DecisionContext, and retained the advisory Recommendation.
- Defect fixed: expired snoozes previously became queue-eligible while retaining lifecycle `SNOOZED`, exposed no snooze-until value, and recorded no return event. Reconciliation now moves an expired snooze to `OPEN`, records durable `RETURNED_TO_ATTENTION`, serializes `snoozed_until`, and the detail UI displays snooze time and occurrence count. Targeted regression was added.
- Intelligence health-state STOP: `FRESH` is browser-visible. Although `OipProjectionState` can store `REBUILDING` and Situation freshness types name `STALE`, `REBUILDING`, and `DEGRADED`, the current accepted implementation has no supported runtime/API lifecycle that propagates those states into queue/detail. Rebuild is synchronous and commits only `FRESH`; no supported degraded/failure mechanism exists. Producing the mandatory browser proof would therefore require architecture/product behavior not authorized by this closure task. No states were fabricated by direct database editing.
- Browser console PASS for the clean authenticated recovery tab: zero error-level console entries and zero uncaught errors. No prompt, React async-effect, or timezone parsing error occurred.
- Direction PASS where touched: Persian document direction `rtl`; after the real language switch, English document and OIP detail direction `ltr`.
- Targeted OIP/OpenAPI/PostgreSQL regression: `29 passed` (14 OIP unit tests including new expiry coverage, OpenAPI parity, 13-race suite, rebuild/recovery).
- Full regression: backend `581 passed, 47 skipped`; frontend `111 passed`; production build passed with the existing chunk-size advisory; lint passed with zero errors and 12 pre-existing warnings.
- Candidate freeze: prohibited. `CAND-FWD-OIP-2-PROMOTION-001` was not created or bound because the mandatory health-state browser matrix did not pass.
- Framework Delta: browser recovery results confirm the existing lifecycle/rebuild principles, but the mandatory health-state observability contract is not implemented end-to-end. Resolving that gap requires an explicitly authorized architecture decision. No Framework change was made in this attempt.

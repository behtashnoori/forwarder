# FE-2 Candidate Evidence

Candidate: `FE2-SHIPMENT-ECONOMICS-CORE-20260808`  
Decision: ADR-033  
Migration: `20260817_shipment_economics_core` after `20260816_oip_projection_health`  
Contract: `fe-2-shipment-economics-slice-contract.md`

Evidence bindings:

- Money/stages/correction/FX/abstention/security/idempotency: `backend/tests/test_shipment_economics.py`.
- API runtime: `backend/routes/economics.py`; contract: `docs/openapi/openapi.yaml`.
- UI: `ShipmentEconomicsSection.tsx` embedded in opaque OperationalShipment detail.
- Migration: additive tables only, no data update/backfill; downgrade raises a fail-closed error.
- Quote-response regression: `backend/tests/test_customer_quote_response.py`.
- MDPM/OIP regression: existing suites; no economics import in MDPM/OIP modules and no financial OIP policy/situation added.

Validation recorded on 2026-08-08:

- Focused Economics plus quote-response/MDPM/OIP regression: 33 passed.
- Disposable local PostgreSQL: full lineage upgraded to FE-2 head; five economics tables verified; downgrade failed closed; database removed.
- Frontend production build passed; ESLint passed with zero errors (12 pre-existing warnings).
- In-app browser connection was available, but the local web server was not running (`connection refused`), so interactive RTL/LTR UAT was not claimed.

Known limitations: allocation and ERP references deferred; FX supports only contractual/manual-approved facts and does not fetch rates; no per-counterparty master is invented; the broader PostgreSQL financial race matrix and interactive browser UAT remain promotion gates.

Framework delta: confirms EAAF bounded ownership and weakest-link abstention; immutable economic observation and explicit-FX provenance remain pattern candidates. No framework repository modification.

## Final gate execution — 2026-08-08

Promotion decision: **HUMAN ARCHITECTURE DECISION REQUIRED**. No candidate was frozen.

Disposable environment:

- PostgreSQL `18.0`, loopback only; databases `forwarder_fe2_gate_20260808` (migration rehearsal) and `forwarder_phase1b_uat_fe2_20260808` (synthetic browser/API UAT).
- Migration head `20260817_shipment_economics_core`; backend `127.0.0.1:5002`; frontend `127.0.0.1:8083`; application version `1.9.0`.
- Synthetic Phase-1B tenant, users, accepted quote, shipment `12eb9867-3976-417a-b174-36b7f3e27926`, and governed synthetic service. Production was not accessed, deployed, or modified.

Passed evidence:

- Fresh full-lineage upgrade reached the single FE-2 head. The FE-2 downgrade raised its expected fail-closed exception before deleting economic history.
- Authenticated in-app browser UAT loaded Shipment Economics in Persian RTL (`lang=fa`, `dir=rtl`) with zero browser error-level log entries. Empty economics rendered `Unknown` and `INCOMPLETE`, never zero. Accepted quote intent remained preview-only until explicit confirmation; confirmation produced a `120.000000 USD` commitment and visible history.
- Existing FE-2/quote regression: `16 passed`; PostgreSQL-only suites in that command were skipped because their dedicated environment variables were not supplied.
- Full backend suite: `591 passed, 47 skipped`. Full frontend suite: `111 passed`. Production build passed. ESLint passed with zero errors and 12 pre-existing warnings. `git diff --check` passed.
- OpenAPI/runtime FE path parity test passed. OIP implementation contains no financial situation/signal behavior.

Mandatory failures:

1. **FX identity is not immutable.** On real PostgreSQL, immutable observations of revenue `100 USD` and cost `50 EUR` projected through an authorized EUR/USD rate of `2` produced margin `0.000000 USD`. Adding a newer authorized rate of `3`, without mutating either observation, changed the same projection to `-50.000000 USD` and changed `applied_fx_rate_ids`. `EconomicObservation` does not bind an FX fact; projection dynamically chooses the newest applicable rate. This violates “FX reference cannot silently change after economic fact creation” and triggers the task's unsafe Money/FX architecture stop condition.
2. **No dedicated 14-scenario FE PostgreSQL race suite exists.** The mandatory race matrix therefore cannot be reported PASS. Existing service locks serialize several shipment/line writes, but FX creation has no pair/version lock or supersession command, so RACE-08/RACE-09 and the FX immutability invariant cannot be proven.
3. **Internal numeric ID is exposed.** Browser UAT shows `Service type ID` input and history text such as `Service 1`, violating the UI/OpenAPI opaque-identity gate.
4. Browser coverage of all requested write flows could not be completed because the FE-2 UI exposes only commercial commitment materialization; estimate, cost, actual, correction, reversal, FX, and evidence commands have no browser controls in this slice.

Candidate bindings (failed promotion attempt):

- Git commit: `a06ccefc0d5c57137ca58e3bf5d174440717970b`
- Git tree: `0f87e9202e1ecf19966cb19c63f9ead3e404775f`
- Branch: `codex/fe-2-shipment-economics`
- Migration SHA-256: `9a405e74e16bda0ac28cc270150b46e362dc3837d275cc4d74b7db3190c3faae`
- OpenAPI SHA-256: `473c7792c7358050d56938a76e02fb5dcbe351e40830a2dcc78e90a04e0c21a4`

EAAF weakest-mandatory-link result: **FAIL**. The passing regression and browser abstention evidence cannot compensate for the failed FX immutability/race gate. Allocation, ERP references, external FX feeds, counterparty master expansion, OIP financial intelligence, and AI economic behavior remain deferred and were not added.

## PR-D01 productization-closure attempt — 2026-08-08

Decision: **PRODUCTIZATION BLOCKED**. No integrated candidate was frozen and Production was not accessed.

Implemented, within the accepted FE-2 contract:

- immutable per-observation FX snapshots through migration `20260818_immutable_fx_provenance`; projections consume the bound snapshot and never dynamically reselect a newer fact;
- opaque ServiceType public identity at command and read/UI boundaries;
- minimum permission-gated UI commands for revenue/cost estimate, commitment, actual/additional actual, correction/supersession, reversal, authorized FX creation and exact binding, and evidence association;
- economic history now displays original money, status, timestamps, applied FX identity/rate, and evidence identity/version;
- explicit UNKNOWN/INCOMPLETE/missing-is-not-zero language.

Validated:

- focused FE-2: `7 passed`;
- full backend: `591 passed, 47 skipped` (all skips are explicit disposable-PostgreSQL suites and remain blocking until executed);
- full frontend: `22 files / 111 tests passed`;
- focused security/economics/document regression: `52 passed`;
- production build and TypeScript no-emit check: passed;
- ESLint: zero errors, 12 pre-existing warnings;
- `git diff --check`: passed;
- fresh PostgreSQL 18 full lineage: passed at `20260818_immutable_fx_provenance`, six economics tables verified, valid empty-data downgrade and FE-2 fail-closed boundary verified.

Blocking evidence gaps:

1. No dedicated real-PostgreSQL 14-scenario FE race suite exists. It was not created because RACE-08 requires FX supersession and RACE-10 requires standalone evidence association, neither of which has an accepted Domain/Service/API/Permission/OpenAPI command. Per PR-D01 these are `DEFERRED — REQUIRES FEATURE AUTHORIZATION` rather than silently invented backend behavior.
2. Authenticated A–Z browser UAT of the new closure controls is incomplete; therefore zero-console-error, Persian RTL, English LTR, and all browser-write-flow claims are not certified.
3. Representative-data backup/SHA-256/restore/revalidation rehearsal is incomplete.
4. Integrated golden path and every individually guarded PostgreSQL suite were not completed on their required named disposable baselines. A generic-database invocation was rejected by the suites' safety guards and is not counted as evidence.
5. Documentation certification and `CAND-FWD-INTEGRATED-RC-001` binding are prohibited until these mandatory gates pass.

P1 only: the existing large Vite chunk warning, stale Browserslist dataset notice, React fast-refresh warnings, hook-dependency warnings, and Python/SQLAlchemy deprecation warnings remain technical debt; no demonstrated runtime/security/release blocker was found in the passing suites.

## Revised race-contract closure — 2026-08-08

Decision: **PRODUCTIZATION BLOCKED**. The Architecture Owner's revised RACE-08
and RACE-10 contract removes the prior need for unapproved FX-supersession and
standalone evidence-association commands. No such commands were added.

Implemented and proven on a fresh, guard-compatible, loopback-only PostgreSQL
18 database migrated through the complete lineage to
`20260818_immutable_fx_provenance`:

- dedicated `backend/tests/test_fe2_races_postgresql.py`: **14 passed**;
- RACE-08 creates two eligible FX facts concurrently, then atomically binds the
  observation to one explicit fact; immutable copied provenance remains stable;
- RACE-10 races an exact-evidence correction against a competing correction;
  one writer wins, the stale writer receives `ECONOMIC_VERSION_CONFLICT`, and
  evidence is either absent with the losing transaction or attached once to the
  winning observation at the exact artifact version;
- correction locking is narrowed to `FOR UPDATE OF economic_observation` so
  PostgreSQL does not attempt to lock the nullable side of the eager FX join;
- existing shipment and line row locks serialize economic mutations; the
  existing transaction-scoped idempotency advisory lock serializes logical
  replay identity; the application uses PostgreSQL `READ COMMITTED`;
- `EconomicLine.version` now advances on append/correction and an explicitly
  supplied stale `expected_line_version` fails as
  `ECONOMIC_LINE_VERSION_CONFLICT`.

Additional results from the integrated worktree:

- fresh PostgreSQL 18 migration/downgrade gate: PASS; six economics tables,
  single head, FE-2 populated-history boundary fails closed;
- full backend: **591 passed, 61 skipped**;
- full frontend: **22 files / 111 tests passed**;
- TypeScript no-emit: PASS; production build: PASS; ESLint: zero errors and the
  accepted 12 warnings; `git diff --check`: PASS;
- browser public-shell check: Persian `fa/rtl`, English `en/ltr`, zero captured
  console error entries.

PostgreSQL skip classification:

- FE-2 fourteen-race suite: no longer skipped in its mandatory explicit run;
- the 61 skips in the generic full-backend invocation are guarded suites whose
  dedicated Phase 0.2, Phase 1A/1B, MDPM, OIP, reference-schema, tracking,
  reporter, safe-downgrade, and reconciliation baselines were not all prepared
  in this closure run: **BLOCKING** under the weakest-mandatory-link rule;
- no generic-run skip is used as release evidence or reclassified as
  `EXPECTED_NON_RELEASE` without a suite-specific justification.

Remaining mandatory evidence gaps:

1. authenticated browser A-Z economics coverage is incomplete. The live public
   shell proves directionality and zero console errors, but the available stack
   had no authenticated browser session and the repository intentionally ships
   no reusable test password;
2. representative integrated backup/SHA-256/fresh restore/revision/read/OIP/FE
   rehearsal was not executed;
3. the complete Commercial-to-FE Golden Path was not executed in one fresh
   integrated environment;
4. all other guarded mandatory PostgreSQL suites were not rerun on their
   suite-specific disposable baselines;
5. security closure and product documentation certification therefore remain
   incomplete.

No FE-2 promotion binding or `CAND-FWD-INTEGRATED-RC-001` identity was created.
Production was not accessed, mutated, or deployed.

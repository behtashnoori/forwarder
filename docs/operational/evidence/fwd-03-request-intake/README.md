# FWD-03 — accepted implementation and qualification

Date: 2026-09-16. Scope: Commercial request intake, persistence, customer summary,
expert view and reopening. Qualification is complete; the delivery response and
post-push verification record identify the final synchronized Git commit. This is
not Production deployment or release authorization.

## Authority and reference impact

The mission issuer explicitly accepted ADR-046 for this bounded slice. The proposal
was hashed before its lifecycle edit and matched
`17511D21BB275EBB6D4B9088B3608141AB842ECD2E154883D4B798E7198E71F3`.
The unchanged owner request is [acceptance-brief.txt](acceptance-brief.txt); the ADR
records status ACCEPTED, source, scope, real date and the pre-acceptance hash.
No human name or title was inferred. The earlier blocked discovery is preserved
verbatim in [discovery-before-acceptance.md](discovery-before-acceptance.md), and is
historical, not the current outcome.

Workspace `D:/1-webapp/forwarder-dev`, existing branch
`feature/fwd-03-request-intake`, start HEAD
`1714118340943f1dbbf99e4b25edc9ef41f817e6`, remote origin were verified. Initial
changes were solely this mission's ADR/index/discovery. One main agent; no delegation.
No applicable AGENTS.md was found. Searches were limited to affected routes,
services, models, callers, migrations, tests and governance documents.

Rules checked: project baseline, development gate, ADR index and affected
ADR-002/004/006/007/010/011/028/045/046. Commercial owns ShipmentRequest and its
command/query boundary. Geography canonical references and Notification/Outbox
ownership remain unchanged. Architecture deviations: NONE beyond accepted ADR-046.
The project baseline section 16 and ADR index now describe the implemented contract.
No temporal values were added or changed; existing date/instant storage and
serialization contracts remain in force.

LPAF mother reference was not edited. Global ACTIVE remains v2.2; v2.4 remains the
owner-approved limited pilot, NOT_GLOBAL_ACTIVE. Its verified current hash is
`217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397`.

## Implemented contract and boundaries

[contract.md](contract.md) is the input/normalization/validation/persistence/read/error
matrix written before validation implementation. The canonical nullable JSON is
`{"version":1,"steps":[{"mode":"road"},{"mode":"sea"},{"mode":"road"}]}`.
Order and adjacent repeats are retained. One distinct mode is single-mode; two or
more distinct modes is combined. This is initial customer intent, never a route,
feasibility decision, quote, operational aggregate or notification trigger.

The server-selected v2 create path requires explicit intent for customer_choice;
forwarder_suggestion can retain null. The legacy path retains scoped scalar
compatibility. Intent on either path invokes strict validation. Unsupported shapes,
versions, modes and contradictions fail with stable reason/field messages. Preparation
uses the same owner validation/projection without writes; final submission revalidates.
Both create paths require trimmed, nonblank cargo; historical incomplete reads remain
valid. The UI keeps entered data on errors and exposes the required cargo field.

Only documented exact catalog aliases map to modes. Duplicate Rail Transport IDs
remain in the catalog/database; the mode selector groups them into one rail option.
No fuzzy translation or unknown-name inference. Active mappings are rechecked at
submission. Legacy generic/domestic/international values remain separate, with no
fabricated order. Combined intent has an explicit legacy-display limitation; an
unchanged old client cannot be claimed to display the sequence.

Controlled customer confirmation/tracking and expert list/detail consume one shared
Commercial projection. Existing narrow status/assignment writes preserve intent.
There is no existing cargo/transport editor or persisted Draft in the examined
application, and none was invented. Explicit transport/null attempts at the status
command are rejected; omitted fields remain untouched. Tests also demonstrate
concurrent PostgreSQL status/priority ORM updates preserve the stored intent.
This does not claim a new concurrent transport-edit contract.

Trusted hostname ownership overrides body-supplied tenant identity. Assigned-work
scope, membership/capability, tenant isolation, reassignment and revocation remain
canonical; role text alone does not grant access. Public tracking retains its existing
opaque tracking capability. Future agents must use these same command/query boundaries;
no direct agent SQL authority, LLM provider or extra permission surface was introduced.

KPI and list use the same authorized scope and search filters. New is the canonical
status=new, counted once even with multiple quotes. The total-visible KPI now counts
that same authorized query instead of summing incomplete status buckets (which omitted
assigned requests). The UI consumes the server total.

## Migration and recovery

Sole new head: `20260916_fwd03_transport_intent`; sole predecessor:
`20260916_fwd01_notifications`. One nullable JSON column, no backfill, historical
migration edit, enum deletion, catalog deletion, startup migration or automatic import.
Release-package head expectations and current-head regression assertions were advanced.

Disposable PostgreSQL 18 at loopback port 55463 was used. Dedicated databases were
`forwarder_fwd03_test_migration`, `forwarder_fwd03_test_commands`,
`forwarder_fwd03_test_runtime`, `forwarder_fwd01_test_regression` and
`forwarder_fwd01_test_migration_fwd03`. Test guards reject other command-test targets.
Upgrade preserves old incomplete rows with SQL NULL; new repeated-step JSON round-trips;
empty-intent downgrade and re-upgrade pass. Populated downgrade takes an exclusive
PostgreSQL table lock and refuses BEFORE DDL, preserving column, head and data.
Application rollback retains schema/data. No customer or Production database was used.

## Qualification evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Full backend regression | 922 passed, 137 skipped, 1 xfailed | full-backend-final.log |
| Latest affected command/read tests | 41 passed, 8 skipped | affected-final.log |
| Final counter/assignment and FWD-03 tests | 43 passed, 1 skipped | counter-final.log |
| FWD-03 real PostgreSQL commands/auth/concurrent preservation | 24 passed | intent-postgresql-final.log |
| PostgreSQL migration/recovery | 1 passed | migration-final.log |
| FWD-01 PostgreSQL outbox/worker/CLI/migration regression | 69 passed, 6 skipped | fwd01-postgresql.log |
| Frontend full suite after final counter change | 37 files, 171 tests passed | frontend-final.log |
| Production frontend build | PASS | build-final.log |
| Lint | PASS, 0 errors, 12 pre-existing warnings | lint-final.log |
| Release package builder tests | 5 passed | release-builder.log |
| Structure and architecture governance | PASS | structure.log, architecture.log |
| Repository secret scan | zero findings | secrets-current.log |
| Whitespace/diff check | PASS | delivery-review.log |

The full backend run preceded the last two focused scenario additions and the small
structured-error/total-visible refinements; the affected suites above cover those
final changes. PostgreSQL-only copies skipped on SQLite are separately exercised on
PostgreSQL. No skipped result is relabeled PASS. The comparison baseline was 901 passed,
136 skipped, 1 xfailed; historical gaps do not waive a new failure. Build size/browser
metadata notices and existing lint warnings are retained in logs.

Reproduction: `python -m pytest backend/tests -q --disable-warnings` with
`TEST_DATABASE_URL=sqlite:///:memory:`; focused suites named by their log and
`test_fwd03_transport_intent.py`/`test_fwd03_migration_postgresql.py` use their guarded
FWD03 database variables. Frontend: `npm run test:frontend -- --maxWorkers=2`,
`npm run build`, `npm run lint`. Governance: `npm run check:structure`,
`python scripts/check_architecture_governance.py`; release builder:
`python -m pytest scripts/tests/test_release_package_builder.py -q`.

### Root causes and retest trail

The previous normalizer-only observation is historical discovery, not API/DB/browser
proof. Implementation added the missing owned value and final-create cargo invariant.
Initial test failures are preserved in *initial.log: successful legacy fixtures needed
nonblank cargo, additive read keys and current migration-head expectations needed
updating, and an admin projection import was missing. These were repaired without
weakening authority assertions. Disposable migration fixtures also needed actual
required timestamp/status columns, and authentication fixtures were corrected to use
real sessions. Targeted repair and full regression subsequently passed.

One frontend test timed out under parallel heavy backend execution; the same targeted
cases and then the complete frontend suite with two workers passed. Browser detail
loading exposed a stalled local Vite proxy; restarting only the verified test process
restored it. Final visual review caught the total-visible count defect and a browser
full-page image stitching artifact: the counter was repaired/tested, and affected
screenshots were replaced with stable viewport captures. No product workaround was
introduced for the test proxy or capture behavior. Test tokens in failure logs are
redacted before version control; no real credential is evidence.

## Role-realistic browser UAT

Local backend 5063 + Vite 8083 + disposable PostgreSQL, synthetic hostname organization,
actual EXPERT account/session and existing referral flow. No auth bypass in browser.
Persian RTL desktop 1280x900 and mobile 390x844 were exercised.

- Customer selected road/sea/road; invalid combined/single-distinct and whitespace
  cargo returned owner errors without losing form data. Confirmation preserved sequence.
- Final save created synthetic request `SR-ERZ7D7`; leaving and reopening through public
  tracking preserved cargo and sequence. Desktop/mobile read artifacts are stored.
- Real expert login, list and detail showed the same saved sequence. Auto-referral
  assigned the request, so new count/list are both zero; assigned list contains one.
- Mobile form permits adjacent road/road and has one rail option despite two catalog
  rows. Required cargo remains visible. Mobile document width stayed within viewport
  (385/390 for form and expert, 390/390 for tracking), direction RTL.
- Expert detail showed no operational shipment and no quote. Browser UAT does not
  stand in for the API negative/revoke/concurrency tests; those are separately recorded.

Artifacts: browser-cargo-error.txt, browser-confirmation-desktop.png,
browser-reopened-{desktop,mobile}.{txt,png}, browser-expert-list.txt,
browser-expert-detail.txt, browser-expert-{desktop,mobile}.png,
browser-form-mobile.{txt,png}, browser-counter-final.txt.

## Remaining boundaries and delivery

FORWARDER-HISTORICAL-REPLAY-001 = BLOCKED_MISSING_EXTERNAL_EVIDENCE.
PRODUCTION_IDENTITY = UNKNOWN. Both remain open; no Production release claim.
Engineering/product acceptance in this bounded FWD-03 slice is qualified. The final
mission result becomes COMPLETE only after non-force push of this existing feature
branch and fetch/live remote verification: LOCAL_HEAD=REMOTE_HEAD, ahead=0, behind=0.
The final delivery response records those identities; no main/baseline merge or tag.

REAL_MESSAGES_SENT: NO. LLM_APIS_CALLED: NO. PRODUCTION_CHANGED: NO.

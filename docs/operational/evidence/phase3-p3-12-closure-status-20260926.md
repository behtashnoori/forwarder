# P3-12 — explicit closure and approved historical repair boundary

LPAF v2.7 / rigor C. Retained Product mission, accepted ADR-068 and the Product
Owner's explicit post-closure answer govern this bounded implementation. Canonical
entry was freshly verified clean and 0/0 at
`368cd736cbffce3d62c33336868738d9086e8306`; no P3-11 runtime was imported.

- Architecture acceptance: `6259830f2a5fe94798bf4183d2643bf624529c26`.
- Product SHA: `d1574fa137017ac41331cf039117ab9c19e101a3`.
- Product tree: `e85fffa602cb51c6fd212e43e4c55a15954997c1`.
- Evidence SHA: the evidence-only descendant containing this final report;
  exact identity is recorded in the controlled integration receipt.
- Branch: `codex/phase3-p3-12-closure`.
- Sole migration: `20261010_phase3_closure`; actual parent
  `20261009_phase3_route_time`.

## Product behavior and authority

Arrival, Cargo delivery, completed and closed remain distinct. Closing is an
explicit completed→closed transaction; planned, in_progress and cancelled cannot
be closed by either command. No legacy row is backfilled closed and no close
occurs automatically. Reopening is unavailable; ordinary source projection cannot
overwrite a closed state.

Same-organization Admin explicitly creates versioned policy, with effective
dates, selected fixed criterion families and mandatory flags. There is no policy
seed, arbitrary rule/expression, guessed threshold or universal HS rule. GENERAL
and current applicable/executed modes combine by union. Overlapping mandatory
criteria remain mandatory, retaining contributing scopes. Source absence is
UNKNOWN, including missing quantity, mode or document applicability; absent policy
makes governed closure unavailable.

Current owning Expert may close only after all mandatory criteria pass. Admin
exception requires explicit same-tenant authority and reason, bypassing checklist
failure only. Both commands reread live policy, actor, memberships and source facts
after locks. Stale Shipment version, policy pin or assessment fingerprint denies
the command. Actor-bound idempotency returns one retained decision; concurrency
cannot produce two decisions or partial closed state.

Immutable ClosureDecision retains policy version, actor label, kind, reason,
assessment, missing/unknown items, source fingerprint and privately pinned source
facts. Its read allowlist omits private source payloads. Current-source links do
not rewrite the original decision. Customer receives the existing DN10-filtered
projection and closed label, no internal checklist or Admin reason.

The Product answer permits historical correction, late recording of prior facts,
and document completion/correction under existing permissions and history. The
explicit command matrix limits late occurrences/effective facts to the original
closure instant; correction paths retain reasons. New planning, Cargo, execution,
allocation, physical transfer and manual Action creation are denied. Shared-unit
commands examine all Shipment parents. There is no blanket write middleware.

Existing Action follow-up/resolution, Exception resolution, SLA evaluation,
configuration and entitlement remain independent. Closing changes no assignee,
does not resolve work/Exception/SLA, and fabricates no delivery/document facts.
Closed UI presents historical repair and hides contextual new-operation controls.

## Persistence and rollback

Four additive empty tables; immutable policy/criterion/decision history; no old
migration edits or sample policy. PostgreSQL guards enforce terminal state,
completed-only same-transaction decision and version transition. Criterion source
writes serialize against the Shipment row, including absent inserts and exact
document replacement/deletion/association paths. Ordinary fixed-owner guards remain.

Empty downgrade/re-upgrade preserves prior-head rows. Once policy/decision evidence
exists, downgrade refuses before destructive DDL. N-1 after use is unsupported;
retain history and roll forward, or use a separately approved pre-use restore.
No production operation is included.

## Exact-source qualification

| Gate | Verified final evidence |
| --- | --- |
| Full backend | 1514 passed, 119 environment-dependent skips, 0 failures/errors; all 1633 collected cases covered in two disjoint module groups |
| Full frontend | 434 passed in 91 files |
| PostgreSQL 18 | 13 tests: P3-12 plus P3-01..10 affected regression and Public Tracking |
| Real Chrome | 14 tests across P3-12 and affected existing Product/security paths |
| Static | Nine gates PASS: app/node TypeScript, lint, build, architecture, structure, backend determinism, diff, sole Alembic head |
| Visual | Four fresh original-resolution screenshots inspected: Admin policy, normal mobile closure, exceptional history and private Customer projection |

[Machine-readable qualification and hashed evidence](phase3-p3-12-closure-20260926/qualification.json)
bind every final run to the clean Product SHA/tree above. Owned processes stopped;
PostgreSQL/browser runtimes were removed. The stopped backend fixture directory
is retained after host policy refused deletion, as expressly permitted by mission §74.

The final evidence package retains machine-readable results, source/tree identity,
selected logs with hashes, four original-resolution screenshots, the exact Product
answer, prior-attempt disclosure and visual review. Raw external logs are also
identified by absolute path. All owned processes/listeners stopped; both synthetic
PostgreSQL/browser runtimes were removed. Automatic approval review rejected
deletion of the stopped backend fixture directory with `blocked by policy`.
The exact retained path and stopped-process/listener verification are in
`backend-full/cleanup.json`. No deletion workaround was attempted. Retained
mission §74 expressly permits this disclosed cleanup exception; it is not a
Product blocker.

The Chrome P3-12 path uses normal Admin/Expert/Customer navigation, explicit policy
creation, normal close, reload, exceptional reason/missing history, wrong
predecessor, private Customer status and 390px mobile layout. Scope is slice plus
affected regressions, not global integrated acceptance.

The superseded ad11390 source had PostgreSQL/Chrome/static passes but a late manual
Action gap. Its frontend had existing test timeouts under heavy concurrent load;
its full backend was explicitly interrupted before completion. Those are not
final passes. The later a7d940b attempt completed with 1513 backend passes,
119 skips and one stale migration-parent assertion failure; its frontend,
PostgreSQL, Chrome and static gates passed. The parent assertion was corrected
without changing runtime behavior, producing d1574fa; all mandatory gates were
then rerun on that final source. Neither superseded attempt is presented as the
final qualification. Final frontend ran independently without weakening any
timeout. Full backend ran in two disjoint module groups, with every collected
test accounted for once through their JUnit results and an explicit module/hash
manifest. The source stayed fixed through final runs. Warnings remain visible
in the retained logs; no assertion that all warnings predate this slice is made.
The first final-source MT3 browser attempt failed solely on a Google Fonts
`net::ERR_INTERNET_DISCONNECTED` request; three serial cases did not run.
A fresh owned MT3-only retry on unchanged d1574fa passed all four cases, without
font interception, assertion changes, relaxed request checks or timeout changes.
Both attempts and the externally selected retry harness are retained explicitly.

## Product/reference reconciliation

| Material observable difference | Classification and authority |
| --- | --- |
| Explicit completed→closed; ordinary and exceptional command | AUTHORIZED: acceptance §§5–7; retained mission; ADR-068 |
| Organization policy/version and GENERAL+mode assessment | AUTHORIZED: acceptance §7; retained DN03 decision |
| Historical correction/late facts/documents after close | AUTHORIZED: exact Product reply 2026-09-26 and command matrix |
| New operational commands denied after close | AUTHORIZED: same reply; completed terminal-state contract |
| Current UI controls, source links, private history/no-store refresh | AUTHORIZED: accepted closure UX/current-authority boundary |
| Arrival/delivery/completed meanings and source ownership | PRESERVED: independent facts; no automatic close or backfill |
| Exception, Action, WorkItem, SLA and assignments | PRESERVED: independent lifecycle; no implicit resolution/reassignment |
| Request, fixed owner, Customer DN10 and exact document permissions | PRESERVED: no new authority or Customer policy payload |
| P3-01..10 history, public tracking and legacy evidence | PRESERVED: regressions plus no historical migration rewrite |

No unapproved material Product difference is accepted. Relational constraints,
locking, idempotency, allowlists and test fixtures are delegated technical choices,
not sources of Product authority. Current baseline, ADR index/068, OpenAPI,
tenant inventory, Phase-3 plan and ADR-016 surface ledger are reconciled. Current
head assertions advance; historical slice head assertions retain their own heads.

DN01_CLOSURE_STATUS=RESOLVED_FOR_P3_12;
DN03_CLOSURE_POLICY=RESOLVED_WITHIN_THIS_MISSION;
DN05_GENERAL_CLOSURE_RULE=NOT_IMPLEMENTED;
DN05_STATUS=OPEN_FOR_FUTURE_SPECIFIC_POLICY.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J04/J05/J06/J08/J09 and
FWD-IPJ-02/IPJ-03/IPJ-04. GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN; HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN;
RELEASE_READY=NO; PRODUCTION_UNTOUCHED=YES. P3-14/P3-15 not started.

P3-11 remains retained and unqualified on the narrow stop-placement Product
question. P3-13 starts only from the actual current canonical after this slice's
controlled integration outcome. Qualification grants no deployment or release.

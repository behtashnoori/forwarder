# P3-11 — exact-source ETA qualification, 2026-09-26

P3_11_QUALIFICATION=PASS
PRODUCT_HEAD=c0e35a7845f9749ec574a3e29ed5ec81ada87979
LPAF_BASELINE=2.7
P311_STOP_PLACEMENT=ARRIVAL_POINT_BEFORE_NEXT_MOVEMENT
DN04_STATUS=RESOLVED_FOR_P3_11
PRODUCT_AUTHORITY_RECONCILIATION=PASS
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
CANONICAL_INTEGRATION=PENDING_FINAL_GUARD_AND_RECEIPT

The evidence SHA is the Git commit adding this report and its bound evidence.
Integration and push/fetch have a separate receipt; qualification alone is not
a claim that the canonical branch has moved. No runtime Product change is
permitted after the tested Product commit.

## Preservation and authority

The original P3-11 worktree and branch were resumed, preserving draft
`198d2bfb07b84e8bf35f0da67b0ef58e48872241`, accepted architecture
`6259830f2a5fe94798bf4183d2643bf624529c26`, and the original working note byte-for-byte.
Canonical `94b499340b2ed6abeefe7a4f38c95cb820dc4a72` was merged into that history;
P3-12/P3-13 migrations and prior Product contracts remain intact.
The [authority record](../../product/phase3/P3-11-RESUME-AUTHORITY.md), retained
exact request and [current ETA contract](../../product/phase3/P3-11-ETA-CONTRACT.md)
explain the explicit stop decision and verified LPAF 2.7 baseline.

## Implemented meaning

For A→B→C, ETA(B) includes movement A→B only. ETA(C) adds the whole unconsumed
stop at B and movement B→C. The final stop at C is after arrival and is excluded.
Arrival at B alone does not complete operations; elapsed hours never prorate
the stop. Completion requires every configured arrival operation to have valid
governed completion evidence, or a governed departure of the next movement.
Explicit 0/0 is zero; null is unknown. Next and final require only their own
components, so next can be available while final is unavailable.

The anchor is the latest applicable occurred-time observation on the exact
Cargo's active path. Recorded time is audit only. Origin location alone cannot
prove departure; equal-time conflict, future progress and split/partial ambiguity
return a reason instead of guessed progress. Immutable snapshots preserve source
and reference pins and A→B→A history. Customer scope and source eligibility precede
calculation; private milestones/completion cannot indirectly shorten Customer ETA
or create private-only history transitions. Planned distance remains null /
«تعریف نشده»; actual travelled distance, GPS, AI and SLA are not introduced.

## Migration

The never-canonical draft migration is retained in Git history and reconciled as
`20261012_phase3_cargo_eta`, directly after `20261011_phase3_owner_transfer`.
One head; two empty additive tables; no seed or historical backfill. PostgreSQL
proved source-row preservation, empty downgrade/re-upgrade, populated-downgrade
refusal, immutable/sealed inputs, tenant/Shipment/plan fences and concurrency.
No Production migration or deployment occurred.

## Final exact-source checks

- Full backend: 1559 passed, 121 optional environment-dependent skips; all 1680
  discovered test cases executed once across two disjoint module groups.
- Focused ETA within that full run: 24 passed. Workspace: 16 passed; Control
  Tower: 185 passed. Named P3-03/07/09/10/12/13 regressions passed.
- Full frontend: 446 passed across 93 files, including all five ETA privacy,
  independent-result, delayed-response and history cases.
- PostgreSQL 18.0: 15 passed across P3-01..13/DN10 and Public Tracking suites.
- Google Chrome: 18 passed in 11 suites; P3-11 Expert, Customers A/B, reference
  version/history, normal navigation, reopen and 390px mobile all passed.
- Both TypeScript configurations, ESLint, frontend production build,
  architecture governance, repository structure, backend determinism,
  single Alembic head and diff checks passed. ESLint has 14 recorded warnings
  and zero errors. Other warnings remain visible in their original logs.
- OpenAPI route/schema checks passed; all pre-existing canonical paths and
  schemas are structurally unchanged. Agent visual QA of four final ETA images
  passed; this is not a human walkthrough.

The [manifest](phase3-p3-11-resume-20260926/manifest.json),
[summary](phase3-p3-11-resume-20260926/qualification-summary.json),
[coverage](phase3-p3-11-resume-20260926/test-coverage-summary.json) and
[authority reconciliation](phase3-p3-11-resume-20260926/reconciliation.json)
bind checks and preserved attempts to their exact source. Replay harnesses,
raw logs, reports and screenshots are retained beside them.

The additional pre-push text secret scan returned four findings (exit 1), not a
raw scanner PASS. [The redacted review](phase3-p3-11-preintegration-review-20260926.json)
verified two synthetic test JWT values and two existing loopback ToolingSelfTest
URLs. Three findings already existed in canonical; the fourth is the copied
synthetic replay harness. No live credential was introduced or accessed, and
neither the scanner nor its baseline was changed to suppress these findings.

## Earlier attempts and cleanup

Early fixture corrections concerned synthetic identifier length and governed
execution allocation setup. The first clean candidate's three failures concerned
the explicit migration chain, UUID path normalization and a schema block placed
inside the older project-configuration text range. Parsed OpenAPI equality and
existing assertions were preserved. Another run correctly disabled P3-13 transfer
because the generic launcher omitted its required restricted DB LOGIN; the final
launcher reuses the existing approved provisioning helper. Product runtime and
browser assertions were unchanged by that launcher repair.

Concurrent disk-heavy qualification caused earlier frontend timeouts and a P3-13
five-second readiness failure. Unchanged assertions/timeouts passed after reducing
that load and then passed again in final-source qualification. Those earlier runs
never substitute for the final Product's required evidence.

The final owned backend/frontend/Chrome/PostgreSQL runtime stopped and its
temporary directory was removed. An earlier PostgreSQL shutdown exceeded the
controller's wait, then completed; a later status confirmed it stopped. Automatic
approval review rejected deletion of that earlier directory with `blocked by
policy`; it is retained without bypass. Backend fixture cleanup is separately
recorded in the final receipt. No Production credentials, data or endpoint was used.

## Boundary and next mission

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J02,FWD-J04,FWD-J06,FWD-J07,FWD-J08,FWD-J09,FWD-IPJ-02,FWD-IPJ-03,FWD-IPJ-04
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
P3_14_STARTED=NO
P3_15_STARTED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_MUTATED=NO
DEPLOYMENT_PERFORMED=NO
RELEASE_CREATED=NO
NEXT_STEP=P3_14_AND_P3_15_FINAL_IMPLEMENTATION_AND_QUALIFICATION_GATE

Stop after qualified controlled P3-11 integration and its receipt. This record
does not start P3-14/P3-15, global integrated journeys, a human walkthrough or release.

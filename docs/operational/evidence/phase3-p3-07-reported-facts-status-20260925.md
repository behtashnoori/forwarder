# P3-07 — reported facts qualified; controlled integration authorized

Date: 2026-09-25 UTC. LPAF v2.7 / rigor C; capability need Astra is recorded
without claiming a runtime model setting. Authority: the explicit five-stage
Product Owner mission §§17–30, DN06/DN07 and ADR-063.

- Product SHA: `cd83f21ca1ac0db6e940475fcd9067713831a581`.
- Canonical base: `13c0fed2d5971907d93f23860cc5689c7ebe33f8`.
- Evidence SHA: this evidence-only descendant, identified by the integration receipt.
- Branch: `codex/phase3-p3-07-reported-location`.
- Single Alembic head: `20261007_phase3_reported_facts`.
- Actual parent: `20261006_customer_entitlement`; historical migrations unchanged.

## Behavior and authority

OperationalEvent and its immutable location evidence remain the event SOR.
Legacy Event tenant is copied only from the proven existing Unit FK; an old
Unit-bound writer bridge remains constrained by same-tenant FK. New typed
Shipment/Stage/Unit/Cargo reports do not manufacture a Unit. Four approved
sources, explicit aware occurred time, backend recorded UTC, late entry,
append-only correction with actor/reason and SQL-paged history are implemented.
Latest location is ranked separately for each scope and is independent of the
history page. Inactive retained execution history can receive a late report or
correction without reactivation. No inferred GPS, confidence, whole-Shipment
location, lifecycle, Action, Exception, Attention or SLA write occurs.

Only the owning active Transport Expert commands. Org Admin oversight is
read-only; peer, Platform, foreign and inactive principals cannot command.
Customer capability support filters explicit impacts through current DN10 and
own Cargo in SQL before limits. It emits supplied safe Customer text or the
fixed generic/DELAY fallback, never synthesized internal notes. No impact means
no Customer message. A B-scoped effect on A conveys only A's safe effect; B's
identity and location stay private. Unit location additionally requires current
positive ACTUAL own-Cargo participation, Stage location requires relevant own
destination ancestry, and Cargo location requires own Cargo. Legacy/public
tracking excludes this new family. The full Customer page remains P3-09.

Exact Chrome regression uncovered a P3-05 form race: the second rapid edit
could restore the old planned quantity. The repair immediately uses the
acknowledged Cargo row/version, ignores older refresh rows and keeps that row's
controls pending through refresh. A deterministic delayed-refresh test proves
the second command preserves the saved plan. This preserves approved quantity
independence; the old browser assertion was retained unchanged.


## Exact-Product evidence

`P3_07_QUALIFICATION=PASS`. The mission authorizes controlled canonical
fast-forward, github push/fetch and 0/0 verification after this evidence commit.
The integration receipt and next slice entry record exact evidence/canonical
identities; no self-referential commit identity is invented here.

Recoverable logs, source/build identities, screenshots and SHA-256 hashes are in
[the evidence bundle](phase3-p3-07-reported-facts-20260925/qualification.json).

| Gate | Result |
| --- | --- |
| Full backend | PASS: 1437 passed, 115 skipped, zero failures/errors; 802.98 seconds. Environment-dependent skips are retained; required PostgreSQL proofs ran separately. |
| Full frontend | PASS: 87 files / 411 tests; 254.87 seconds. |
| PostgreSQL 18 | PASS: 3 report/DN10/document tests and 5 P3-01..05 regressions; migration, legacy bridge, empty roundtrip, populated rollback refusal, concurrent replay/corrections, tenant FK and immutable-history guards. |
| Normal Chrome | PASS: P3-07 two scoped Units, correction/reopen; two P3-06/DN10 journeys; P3-05, P3-04, P3-03, P3-02 and P3-01. Final browser run followed completed backend to avoid competing load. |
| Visual inspection | PASS: desktop 1280×720 and mobile 390×844; separate Unit cards and readable source/actor/times, no overflow or header overlap. |
| TypeScript / lint / build | PASS: direct app and Node projects; zero lint errors, 13 existing warnings; existing build chunk-size advisory. |
| Contract / ownership / static gates | PASS: entire OpenAPI parse, exact operational namespace and new-route parity, tenant inventory, architecture, structure, determinism, diff. |
| Source/build/secret evidence | PASS: 59 changed Git blobs hashed; 13 built files hashed; changed-scope secret scan has zero findings. |

Environment: Python 3.13.9, Node 24.11.0, PostgreSQL 18.0, Chrome
154.0.8037.57. All final results are bound to the clean Product above and owned
synthetic data. No prior Product result is substituted for this qualification.

## Retained unsuccessful attempts

Candidate `313d3dd23b4988e55c694583f97adaf4499c8b9c` had three new app TypeScript
errors, fixed before the next candidate. Its backend was stopped incomplete.
Candidate `1cfa2f5255f038794b4dba66daf8395ef3a2b6da` exposed the genuine P3-05 form
race described above; its backend was stopped incomplete. Candidate
`efa02c9a9c18e7d0ce410b94b9ee58bcd9c54c6f` completed backend with 1,436 passed,
115 skipped and one obsolete contract-test ownership assumption: it collected
only the original operations blueprint. The corrected test compares every
registered route in both API namespaces, retaining exact path/method equality
and opaque-ID checks. Runtime was unchanged by this last test correction.

That earlier browser run also exceeded P3-02's unchanged five-second list-load
assertion under concurrent backend load: the screenshot showed loading and the
server returned HTTP 200 just beyond the boundary. The unchanged P3-02/P3-01
diagnostic retry passed after backend ended. Diagnostic passes are not the final
gate: all eight journeys ran freshly on the final clean Product. Original logs,
traces and conclusive results remain in their separate external attempt folders;
summaries/hashes are retained in this bundle. No test expectation or timeout was
relaxed and no failure was waived.

## References, journeys and limits

Current architecture/ADR/decision indexes, tenant inventory, OpenAPI and Phase 3
mission/plan references are reconciled. Historical ADR/PDR/evidence is preserved.
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J01/J04/J05/J07/J08/J09 and
FWD-IPJ-02/IPJ-04. GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN; HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN;
RELEASE_READY=NO. This is slice qualification, not human Product approval.

Empty downgrade/re-upgrade and populated downgrade refusal protect facts.
Application downgrade after new reports exist is unsupported because older
readers lack the reserved-family exclusion. Owned synthetic local data only;
no Production access/mutation, deployment or release. P3-08..10 implementation
has not begun at this record; P3-11..15 are excluded.


`REFERENCE_RECONCILIATION=PASS`; `REFERENCE_IMPACT=NONE` within this slice.
Protected behavior is PRESERVED by the exact candidate regression evidence.
`DN06_STATUS=RESOLVED`; `DN07_STATUS=RESOLVED`; source taxonomy and safe-message
projection PASS; GPS/confidence/automatic side effects NO.

Final owned backend/frontend processes and PostgreSQL cluster stopped; the
exact runtime directory is absent. The prior stopped DN10 directory remains
because automatic host approval rejected deletion with reason `blocked by
policy`; no bypass was attempted. Its exact path is retained in qualification.json.

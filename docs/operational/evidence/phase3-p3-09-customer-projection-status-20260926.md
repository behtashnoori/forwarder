# P3-09 — resumed Customer Shipment projection qualified

2026-09-26; LPAF v2.7, rigor C. Explicit Product Owner resume authority is recorded
in P3-09-10-RESUME-AUTHORITY.md and ADR-065. Existing branch and all pre-interruption
work were preserved. No replacement worktree, reset, discard or restart occurred.
Canonical entry was `6a11c2e02a3103f0bc36129bd12798842b7c39cb`, clean and freshly aligned with github at 0/0.

- Product SHA: `e499eb13fccc12734b21a09c1e2bfa1b92e983ee`; source identity freeze is not a global Product Freeze.
- Evidence SHA: this evidence-only descendant, identified in the integration receipt.
- Branch: `codex/phase3-p3-09-customer-projection`.
- Migration required: NO; unchanged sole head `20261008_phase3_cargo_delivery`.

## Product behavior

Normal Customer navigation exposes «حمل‌های من» over the existing shared Shipment
SOR. Current DN10 entitlements select owned Cargo before Shipment count, literal
search, ordering and paging. A, B and unentitled C remain separate; multiple active
grants form only the authorized union. Partial revoke removes only that scope.
No account/CRM auto-link, new identity table or duplicate Shipment is introduced.

The explicit DTO includes safe identity, authorized Cargo quantities and Customer
label, simplified ancestor route to that Cargo destination, permitted documents
and exact current bytes, own Deliveries and customer-safe report/correction history.
Private logistics facility details, unrelated branch/Cargo/Carrier/internal notes,
other Customer counts and shipment-wide quantities are absent. Latest reported
locations are gated before ranking/limit and remain distinct from predicted/live
location. Public Tracking keeps its separate possession boundary and routes.

Live account/session generation and current eligibility are rechecked. An opaque
authorization revision brackets server composition and is checked after receiving
a body before browser acceptance. A delayed pre-revoke response is discarded even
without a focus event; one fresh read may replace it, otherwise the UI fails closed.
No retained private cache survives navigation, hidden/return, failed reads or denied
downloads. Response headers are private/no-store with Cookie variance. Previously
read bytes cannot be retracted; subsequent authorized use and stale-response
acceptance are the tested revocation boundary.

## Exact-Product qualification

[Recoverable evidence bundle](phase3-p3-09-customer-projection-20260926/qualification.json)
binds all results to the Product SHA, raw record hashes, source/build identities,
synthetic actors and owned runtime cleanup.

| Gate | Result |
| --- | --- |
| Full backend | PASS: 1475 passed, 117 environment-dependent skips, zero failures/errors; 3391.245 seconds. Required PostgreSQL tests ran separately. |
| Full frontend | PASS: 89 files, 420 tests. |
| PostgreSQL 18 | PASS: 5 focused P3-06..09/DN10 proofs, 5 P3-01..05 regressions, 1 Public Tracking security proof. |
| Normal Chrome | PASS: P3-09 A/B/C, union, partial revoke, exact downloads, delayed response, password generation/recovery, mobile/return; P3-08, P3-07, P3-06/DN10 and Public Tracking regressions. |
| Contract/static | PASS: strict OpenAPI route/allowlist parity, tenant inventory, architecture, structure, determinism, TypeScript app/node, build and diff checks. |
| Visual | PASS: reviewed final desktop 1280×720 and mobile 390×844; separate Cargo/quantity/document groups, readable RTL and no horizontal overflow. |

The backend emitted 20682 warnings (retained in the raw run's count); warnings are
not represented as zero. Thirteen existing lint warnings and existing build
chunk-size/Browserslist advisories remain. Prior dirty diagnostics and superseded Product `191c004` are disclosed in
prior-attempts.json; its missing strict route-inventory entries were reconciled to
the two authorized routes, with no runtime change. Its incomplete backend was not
counted. The first clean-Product browser attempt hit five-second UI timeouts during
concurrent full suites; later successful HTTP responses were observed. The retained
failure is followed by a complete unchanged-source/unchanged-assertion runtime rerun.
No failure, skip, older Product pass or authentication interruption is relabelled.

## Authority, references and limits

Current architecture, tenant inventory, ADR/decision indexes, OpenAPI, document
contract and implementation plan are reconciled. Product Authority classifications:
approved Customer projection/freshness/routes AUTHORIZED; unrelated account/Request,
Public Tracking, shared Shipment and P3-01..08 behavior PRESERVED within recorded
regression coverage. LPAF framework reference owner impact NONE; Forwarder Product
and architecture owners' affected current references updated; historical evidence
unchanged. PRODUCT_AUTHORITY_RECONCILIATION=PASS; REFERENCE_RECONCILIATION=PASS;
REFERENCE_IMPACT=NONE. The mission authorizes clean fast-forward-only integration,
canonical-only github push, fetch and 0/0 after this evidence commit.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY: FWD-J01/J02/J08/J09 and FWD-IPJ-03/IPJ-04.
This is slice-boundary evidence. GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING;
INTEGRATED_PRODUCT_JOURNEYS=NOT_RUN; HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN;
RELEASE_READY=NO. P3-10 starts separately from fresh current canonical. P3-11..15,
Production access/mutation, deployment and release remain NO.

Owned backend/frontend/PostgreSQL processes stopped; exact owned temporary runtime
removed after path validation. No credential inspection or authentication workaround.
Only safe summaries and synthetic screenshots are committed; failure traces remain
diagnostic outside the repository.

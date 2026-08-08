# FE-2 Shipment Economics Slice Contract

Candidate scope implements ADR-033 and the approved FE-2 authorization. Commands require tenant membership, explicit capability, opaque subject/line identities, authority, effective time, exact Money, idempotency, and expected version for correction. Reads return immutable history and derived stage projections. `COMPLETE` requires compatible revenue and visible cost plus explicit FX when currencies differ; otherwise values that depend on missing truth are absent with reason codes.

Commercial materialization is `accepted ExpertQuote → preview → explicit confirm → REVENUE/COMMITMENT`; there is no read-time creation or historical backfill. Cost input supports estimate, commitment, multiple actual facts and correction. Evidence points to an exact existing `CaseDocumentFile` version belonging to the shipment request; deleted evidence cannot be newly associated and historical references are retained.

Allocation and ERP references are intentionally deferred. Project aggregation sums only complete compatible shipment projections and otherwise returns incomplete coverage. Economics never blocks operational transitions. OIP has no dependency on Economics and no financial Situation is added.

Promotion gates: one migration head, disposable PostgreSQL upgrade, fail-closed downgrade proof, unit/API/security/race/regression tests, OpenAPI/runtime parity, frontend build/lint, browser RTL/LTR UAT, and retrievable evidence.

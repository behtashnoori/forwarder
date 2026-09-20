# LPAF-Governed Forwarder Project Reference Reconciliation — 2026-09-20

Scope: Forwarder project reference and architecture documentation only. No backend/frontend runtime, test, migration, generic LPAF framework file, generated output, deployment, Production system, or remote branch was changed.

Working branch: `codex/lpaf-project-reference-reconciliation`. Exact parent: `3c7ffa2092e4ecaf0dc8c6a590baaa41acad7afb`. Required ancestors `e919cd5bd07544627feaa656377167e205f1d899` and `d4268e9854f4d31234a98a94c04c37c874a751b5` were verified. The starting worktree was clean and Alembic exposed exactly one head: `20260923_notification_lifecycle`.

## A. Governing LPAF baseline

The active governing baseline is **LPAF v2.2**, together with the mandatory `LPAF-v2.2-Agent-Entry-Protocol.md`. This is Level B product/reference work. Applicable controls are historical preservation, explicit owner/SOR, domain chain and compatibility, end-to-end authorization, evidence-backed decisions, and gaps remaining visible.

LPAF v2.3 remains a **REVIEWED CANDIDATE**, not the active baseline. Its Product Integration, user-journey, RBAC reachability, architecture-drift, and `REFERENCE_IMPACT` gates were applied as strong Forwarder governance defaults. LPAF v2.4 was not adopted. No file under the generic `29-LPAF` framework was edited.

Protocol classification at entry:

- **FACT:** Post-D2 superseding Cargo evidence approves optional `0..N` Request Cargo; current ADR-042/043 contain Shipment reassignment/request-root ownership semantics; current runtime has Direct Shipment responsibility but accepted-Quote Shipment responsibility remains Request-assignee-derived.
- **ASSUMPTION:** none used to decide Documents actors or broaden runtime authority.
- **UNKNOWN:** the exact Customer / owning Transport Expert / Admin-Manager Documents action matrix.
- **DECISION NEEDED:** Product Owner Documents actor/action entitlement before Documents Build.

## B. Forwarder references changed

The reconciliation updates the existing Forwarder decision/index, baseline, dictionary/map/catalog, time, authorization, drift, and journey structures instead of inventing a parallel reference system.

| Reference class | Exact Forwarder files |
| --- | --- |
| Product decisions | `docs/operational/PDR-019-post-d2-product-reference-contract.md`; `docs/operational/PDR-013-cargo-data-foundation.md`; `docs/operational/PDR-017-canonical-operational-taxonomy.md` |
| Architecture decision | `docs/operational/adr/ADR-047-fixed-operational-shipment-responsible-expert.md`; `docs/operational/adr/ADR-016-time-and-timezone-architecture.md` |
| Decision discovery | `docs/operational/decision-index.md`; `docs/architecture/ADR-INDEX.md` |
| Domain/reference truth | `docs/operational/FDD-001-forwarder-data-dictionary.md`; `docs/operational/FDM-001-forwarder-domain-map.md`; `docs/operational/canonical_business_object_catalog.md`; `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md` |
| Authorization/current-state compatibility | `docs/architecture/ADR-043-authorization-implementation-design-package.md`; `docs/architecture/shipment-business-access-v2.md` |
| Time business policy | `docs/architecture/time/time-business-decision-register.md` |
| Drift register | `docs/architecture/ARCHITECTURE-DRIFT-REPORT.md` |
| Acceptance/journeys | `docs/governance/S6-GOLDEN-BUSINESS-JOURNEYS.md` |
| Reconciliation evidence | `docs/operational/evidence/lpaf-project-reference-reconciliation-20260920.md` |

`PDR-019` is the **NEW ACCEPTED DECISION** for Post-D2 product contracts. `ADR-047` is the **SCOPE CHANGE / scoped superseding ADR** for fixed Shipment Expert ownership. Historical amendments, ADR-042, ADR-043, and their evidence remain preserved.

## C. Cargo truth

```text
REQUEST_CARGO_REQUIRED_FOR_SUBMISSION=NO
REQUEST_CARGO_MIN_ITEMS=0
MANDATORY_CARGO_POLICY=DEFERRED
MULTI_CARGO_REQUEST_DIRECTION=APPROVED
```

`ShipmentRequest -> 0..N RequestCargoItems` is the commercial target. No Cargo field is required for submission. `RequestCargoItem` is distinct from operational `ShipmentCargoItem`; the latter remains owned by `OperationalShipment`. Historical Requests without Cargo remain valid, legacy scalars are not guessed into items, and no migration or implementation is authorized now.

Cargo implementation gate: define the additive API/schema shape if needed, traceability without automatic allocation, legacy-scalar compatibility, no-guessed-backfill policy, authorization, migration/rollback plan, owned PostgreSQL evidence, and the complete optional-Cargo browser journey before Build/Freeze.

## D. Responsible Expert ownership truth

```text
ONE_TRANSPORT_EXPERT_PER_SHIPMENT=YES
EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

ADR-047 makes `OperationalShipment` the SOR for one fixed responsible Transport Expert. Accepted-Quote creation captures the active same-tenant official Quote issuer; Direct creation validates one active same-tenant owner in the creation transaction. Request reassignment does not mutate an existing Shipment. No former/reassigned/replacement Expert state or transfer workflow is target behavior.

The target authorization matrix distinguishes same-organization Admin/Manager oversight, owning active Expert, another same-organization Expert, other tenant, and inactive/revoked actor. ADR-047 supersedes only conflicting Shipment ownership/reassignment parts of ADR-042/043; their unaffected tenant/capability/non-disclosure and Request assignment contracts remain.

Expert ownership gate: audit historical/null/ambiguous owner data, design accepted-Quote convergence on the Shipment owner SOR, prohibit owner mutation APIs, preserve fail-closed behavior, and certify detail/list/count/search/export/cache/child access plus Admin oversight and inactive/revoked denial before implementation Freeze.

## E. Dual Calendar truth

Selected business dates render `Gregorian (Jalali)` from one authoritative Local Date or Instant. ADR-016 and TIME-BIZ-013 prohibit duplicate Jalali persistence, second timestamps, alternate sorting/filtering facts, and timezone inference.

Dual Calendar gate: later Build requires a named surface ledger and shared presentation behavior with Local Date/Instant, Tehran/UTC, ordering/filtering, mobile RTL, and browser journey proof. No migration is expected.

## F. Combined Transport truth

A Request may carry one scalar intent displayed as `حمل ترکیبی`. It does not enumerate permutations or own the actual route.

```text
REQUEST_TRANSPORT_INTENT != ACTUAL_ROUTE_TRANSPORT
```

The existing Request `TransportMethod` catalog is the compatibility boundary; actual ordered modes remain `RouteLeg.transport_mode`. Historical values remain readable.

Combined Transport gate: approve the exact idempotent catalog reconciliation/apply artifact, preserve deterministic Rail presentation, round-trip all Request summaries, and prove actual Route Legs remain separate. No ordered-intent JSON or schema migration is approved.

## G. Quote Communication truth

Quotation owns the official offer/lifecycle. Customer responses are approve (`accepted`), needs discussion plus one short message (`discussion`), or reject (`declined`). Discussion is supporting history, not a counter-offer or automatic commercial-state transition. Changed terms require a new/revised official Quote; only accepted Quote is Shipment-eligible.

Quote Communication gate: later Build must define bounded message validation, API/state/errors, auth, expiry, replay/conflict/concurrency, Quote history, accepted-only Shipment eligibility, Notification inactivity, and one additive/constraint migration with PostgreSQL/rollback proof.

## H. Documents unresolved actor decision

Functional intent remains multi-file, append, targeted replace with preserved version history, and known-failed-file retry. Implementation is:

```text
BLOCKED_PENDING_DOCUMENT_ACTOR_DECISION
```

Awaiting exact action entitlements for Customer, owning Transport Expert, and same-organization Admin/Manager across discovery, upload, append, replace, history, retry, and view/download. The waiting reference sections are PDR-019 §6, PDR-008, PDR-009, ADR-020, FDD-001 document governance gaps, and the S6 Post-D2 Documents journey/API authorization contract.

## I. Control Tower scaling classification

D1/D2 remain implemented and preserved. The 100-authorized-Shipment ceiling is:

```text
PRE_RELEASE_SCALABILITY_GAP
```

It is not a business limit. Before RC, evidence must either prove launch tenants remain below it with acceptable headroom or a separately governed server-side search/windowing design must replace it. Partial client truncation is prohibited.

## J. Notification deferral

C1/C2 infrastructure and lifecycle are approved and dormant. Activation remains deferred. No business-event mapping, recipient/channel policy, SMS/Email/Webhook/provider, worker/scheduler, API, UI, delivery, or Control Tower exposure is current scope.

## K. Capability owner/SOR map

| Capability | Owner | SOR | Reference result |
| --- | --- | --- | --- |
| Requests / Request Cargo | Commercial/Request | `ShipmentRequest` + future `RequestCargoItem` | Optional `0..N`; reference closed, implementation open |
| Shipments / Operational Cargo | Operations | `OperationalShipment` + `ShipmentCargoItem` | Customer does not author operational structure |
| Documents | Document policy + owning business scope | definition/requirement/version/association chain | Actor gate blocked |
| Quotes | Pricing/Commercial | `Quotation`/`ExpertQuote` compatibility + response history | Simple communication accepted |
| Tracking | Operations/Visibility | canonical operational events/projections | Request intent never substitutes actual route |
| Control Tower | Operations/Attention | governed read projection over operational SORs | 100 ceiling pre-release gap |
| Notifications | Notification boundary | dormant action/attempt lifecycle | activation deferred |
| Calendar presentation | Presentation constrained by Time Architecture | existing authoritative date/time fact | dual rendering only |

No physical modular refactor is authorized.

## L. Journey updates

S6 now contains reference-complete target journeys for:

- A. Optional Multi-Cargo Request;
- B. Dual Calendar presentation;
- C. Combined Transport Request intent;
- D. Quote communication.

Each defines ENTRY, ACTOR, ENTITLEMENT, DISCOVERY, USE, RESULT, LEAVE, RETURN, DENIAL/ERROR, and DOWNSTREAM. Documents is explicitly blocked because ACTOR/ENTITLEMENT is unknown. Historical S6 PASS remains evidence for its old baseline and no longer supplies target Shipment reassignment authority.

## M. Reference impact closure

| Decision | REFERENCE_IMPACT | REFERENCE_IMPACT_STATUS |
| --- | --- | --- |
| Optional Multi-Cargo Request | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE |
| Fixed Responsible Expert | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE |
| Dual Calendar | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE |
| Combined Transport | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE |
| Quote Communication | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE |
| Documents actor/action | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE — product decision remains BLOCKED |
| Control Tower ceiling | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE — pre-release runtime gap remains OPEN |
| Notification activation | UPDATE_REQUIRED | CLOSED_FOR_REFERENCE_PHASE — activation DEFERRED |

Reference closure means project truth is no longer stale for this phase. It does not mean implementation, schema, migration, tests, browser acceptance, Freeze, RC, deployment, or Production is complete.

## N. Remaining blockers before Build

1. **Documents:** Product Owner must approve the actor/action matrix.
2. **Optional Cargo:** later slice must close API/schema/compatibility/lineage and acceptance design before code.
3. **Responsible Expert:** later slice must close historical ownership reconciliation, accepted-Quote materialization, immutable API/state, authorization, and acceptance design before code.
4. **Dual Calendar:** surface adoption ledger and verification matrix are required before implementation Freeze.
5. **Combined Transport:** exact controlled catalog identity/apply artifact is required before implementation.
6. **Quote Communication:** API/state and additive migration design is required before implementation.
7. **Control Tower:** pre-release launch-headroom proof or server-side scaling design remains required before RC.
8. **Notifications:** activation remains outside scope until a new accepted product/architecture decision.

Recommended future Build order remains: Optional Multi-Cargo Request -> Dual Calendar -> Combined Transport -> Quote Communication -> Documents after actor decision -> Control Tower scaling.

## O. Verdict

PASS — FORWARDER REFERENCES RECONCILED UNDER LPAF

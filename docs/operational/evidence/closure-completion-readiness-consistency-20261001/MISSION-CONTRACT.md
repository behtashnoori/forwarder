# Closure completion/readiness consistency mission contract

Date: 2026-10-01

## Authority and routing

- LPAF classification: Level B / Solution mission with Build and Product Assurance workstreams.
- Product authority: the user's narrow closure-completion consistency mission, constrained by the frozen repository baseline and accepted product records.
- Authoritative lifecycle contract: route execution occurrences project every active, non-cancelled route leg to `completed`; that projection moves the shipment to `completed`. Closing is a separate, explicit and immutable `completed -> closed` decision.
- Closure policy criteria are an independent readiness checklist. Zero policy blockers does not complete a shipment and does not waive the `completed` predecessor for closure.
- Product-owner authority remains required for the Human Product Walkthrough verdict. This mission may prepare a walkthrough-ready candidate, but it must not mark that human gate PASS.

## Authorized change

Make the existing lifecycle predecessor visible and consistent across Summary, Task, Attention, Next Action, and Closure surfaces. A shipment whose closure-policy criteria pass but whose route execution is incomplete must:

1. remain not closable;
2. show route execution as the blocking prerequisite;
3. route the user to the already-authorized occurrence workflow;
4. keep optional Actual Cargo, allocation, and ETA gaps as warnings that cannot outrank the lifecycle prerequisite.

No new `Complete Shipment` command, lifecycle state, transition, bypass, or permission is authorized.

## Discovered authority boundary

The preserved owning expert does not have `milestone_event.create`, and none of the preserved walkthrough personas currently has an equivalent route-occurrence capability. The implementation must therefore expose the incomplete execution prerequisite without advertising an inaccessible action. Assigning or remapping that capability is a Product/authorization decision outside this corrective mission; it must not be inferred from ownership or applied by mutating the preserved database.

## Protected invariants

- Do not mutate the preserved walkthrough shipment or its PostgreSQL database.
- Do not mutate production data or production services.
- Do not weaken normal or exceptional close authorization.
- Do not auto-close and do not collapse `completed` and `closed`.
- Do not redefine organization stages, delivery, cargo, documents, tracking, or closure-policy authorities.
- Keep historical events and closure decisions append-only and auditable.
- Run write-capable qualification only against an owned disposable PostgreSQL 18 database.

## Journey impact

- FWD-J04 / FWD-J05: route occurrence capture and projected execution completion become the explicit prerequisite surfaced to the operator.
- FWD-J07 / FWD-J08 / FWD-J09: delivery, warning, closure review, and history remain distinct and consistently ordered.
- IPJ-02 / IPJ-04: authorization boundaries and immutable decision/history behavior remain unchanged.

## Acceptance evidence

- Eight-case state/transition qualification matrix covering incomplete and complete lifecycle states, blockers, warnings, direct close, history, and unauthorized close.
- Backend and frontend regression tests.
- Browser proof at desktop and 390px mobile widths on the owned disposable PostgreSQL 18 stack.
- Read-only preserved-data inspection plus before/after normalized data hash equality.
- Controlled integration and exact-candidate verification before publication.

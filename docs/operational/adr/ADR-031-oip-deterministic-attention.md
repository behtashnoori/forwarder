# ADR-031 — Deterministic Operational Intelligence attention

- Status: Accepted / OIP-2 implemented with explicit limitations
- Candidate: CAND-FWD-OIP-2-001
- Base: `08b4784` (MDPM-1 promotion candidate)
- Architecture authority: approved OIP-D01 through OIP-D19 and the OIP-1 contract

## Context and decision

OIP is an additive intelligence module in the modular monolith. It stores immutable references and deterministic signals, plus durable Situation identity and human interaction history. It does not copy or mutate shipment, route, milestone, delay, exception, execution-unit, document, or MDPM truth. `OperationalWorkItem` remains the existing work queue; `OipAttentionProjection` links a Situation to an existing work item where one exists and does not create an independent operational lifecycle.

The exact pipeline is `FactReference → Signal → Situation → AttentionProjection → DecisionContext → Recommendation → existing authorized command reference → Outcome history`. Priority uses ordinal lexicographic tiers, never weights or AI. Recommendations are templates and cannot execute commands.

## Trade-offs and dependencies

Durable Situations add persistence and reconciliation complexity, but preserve acknowledgement, disposition, recurrence, and audit through rebuild. Existing operational and MDPM tenant envelopes are dependencies. Legacy Task, Activity, Document, Message, and Notification are excluded pending tenant-safe adapters.

## Scope, exclusions, evidence

Only the seven approved families exist in the catalog. Financial exposure, compliance/carrier scoring, prediction, customer criticality, AI, dashboards, action/rules/workflow engines, and operational mutation are prohibited. Evidence is in `docs/operational/assurance/oip-2/` and `backend/tests/test_oip.py`.


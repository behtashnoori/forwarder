# ADR-030 — MDPM document readiness policy

- **Status:** Accepted / MDPM-1 implementation authorized
- **Decision IDs:** MDPM-D01–MDPM-D15
- **Candidate:** CAND-FWD-MDPM-1-001
- **Implementation status:** Implemented on the MDPM-1 candidate branch; validation evidence is candidate-scoped.

## Context

Release 1.9 established `OperationalShipment` and shipment-owned `Milestone` progression. Project Configuration owns `ProjectDocumentRequirement`; the request document subsystem owns `DocumentDefinition`, requirement snapshots, immutable `CaseDocumentFile` versions, binary storage, and `DocumentAuditEvent`. Upload is not acceptance, replacement must not inherit acceptance, and documentary readiness must constrain selected commands without becoming operational status.

## Decision

`OperationalShipment` remains the executable aggregate and the existing milestone transition service remains the mutation boundary. A deterministic service-layer `TransitionReadinessPolicy` evaluates materialized requirements bound to one milestone type and target status inside the transition transaction. Readiness is a projection, never shipment or milestone status.

The domain separates definition (`DocumentDefinition`), configured requirement (`ProjectDocumentRequirement`), runtime snapshot (`OperationalDocumentRequirement`), artifact (`CaseDocumentFile`), exact-version use (`ArtifactAssociation`), append-oriented assessment (`REVIEW_STARTED`, `APPROVED`, `REJECTED`, `VERIFIED`), and derived satisfaction/readiness. Conditional requirements start `UNRESOLVED`; explicit, audited resolution chooses `APPLICABLE` or `NOT_APPLICABLE`. Conditional text is never executable. Required requirements block, optional requirements warn.

MDPM-1 artifact association is tenant-first and limited to an active typed artifact from the shipment's source request whose request requirement references the same definition. Each shipment needs an explicit association. No binary is copied. Assessments bind to that association and exact version. Replacement supersedes the association, retains historical assessment, and requires independent assessment. `VERIFIED` satisfies approval- or verification-level policy; `APPROVED` satisfies only approval-level policy.

Overrides are shipment-, requirement-, milestone-, and target-status-specific. They require explicit permission, authority and reason, support evidence/expiry/revocation, and are atomically consumed. They never alter assessment. Specialized `DocumentReadinessAudit` facts retain correlation identity; timeline unification remains projection work.

## Alternatives

Encoding readiness as `BLOCKED`, using request state directly, copying files, a workflow/rule engine, treating upload as approval, and carrying approval across versions were rejected because they violate the authorized lifecycle, ownership, audit, or bounded-scope decisions.

## Trade-offs

Explicit snapshots and associations add operator actions and rows but provide tenant isolation, reproducibility, version integrity, and deterministic behavior. Request-to-shipment eligibility is intentionally narrower than future cross-request reuse.

## Consequences

Transitions may return stable blocker codes without lifecycle mutation. Configuration changes do not silently alter shipments. No historical requirements/associations are guessed. Evidence-bearing downgrade fails closed.

## Scope

Configuration binding, explicit shipment materialization, exact artifact association, applicability, assessment, readiness, controlled override, append audit, minimum operational UI, API, tests, and additive migration.

## Exclusions

Compliance, financial processing, workflow/DSL engines, ProcessProfile, ExecutionUnit documents, a second store, arbitrary conditions, historical backfill, production/deployment, and enterprise-framework philosophy changes.

## Evidence basis

MDPM-0; MDPM-D01–D15; code reconstruction at Release 1.9 NEXT-RC `b3a4340`; ADR-002/006/010/019/020/027/029; PDR-018; Release 1.9 evidence.


# MDPM-1 Document Readiness Slice Contract

- **Status:** Accepted / bounded implementation
- **Candidate:** CAND-FWD-MDPM-1-001
- **Decision:** ADR-030; MDPM-D01–D15
- **Implementation status:** Implemented; validation is tracked in `assurance/mdpm-1`.

## Context and decision

This is the smallest auditable bridge from Project-configured document requirements to selected shipment milestone transitions. Operational lifecycle and request-owned storage remain unchanged. ADR-030 consolidates the domain, association, assessment, replacement, override, and audit policies to avoid redundant records.

## Contract

Materialization is explicit preview/confirm, copies active configuration facts, and retains source public identity/version. It never backfills or creates during readiness reads. A requirement needs a milestone type and target status binding.

Policy input includes tenant-scoped shipment/milestone identities and versions, target status, configuration versions, exact artifact version, current assessment, applicability, and override. Output contains allow decision/time, subject/version, operational/document results, blockers/warnings, evidence references, configuration versions, and applied overrides.

Stable blockers are `DOC_REQUIREMENT_UNRESOLVED`, `DOC_ARTIFACT_MISSING`, `DOC_ARTIFACT_REJECTED`, `DOC_APPROVAL_REQUIRED`, `DOC_VERIFICATION_REQUIRED`, and `DOC_ARTIFACT_SUPERSEDED`; the command uses `TRANSITION_READINESS_BLOCKED`. Stale snapshots use `STALE_REQUIREMENT_VERSION`. All MDPM API identities are opaque.

Permissions separate read, manage/associate/applicability, assess, verify, and override. The backend enforces organization and permission before resource resolution. The transition policy runs with the milestone mutation locks; a block appends evidence without milestone mutation, while an allow consumes exact overrides and performs the existing transition atomically. Reads emit no event.

## Alternatives and trade-offs

A binding table was considered. Two bounded fields on configuration and snapshot are sufficient for one transition per requirement and are smaller. Multi-binding is deferred and would require additive design.

## Consequences

Project changes cannot alter existing snapshots. Replacement re-blocks. An override cannot authorize another requirement, shipment, milestone, action, or later attempt after consumption.

## Scope and exclusions

Scope is ADR-030's bounded capability plus API/UI/tests/evidence. Excluded are workflow APIs/designers, cross-request reuse, multi-binding, a new upload store, historical materialization, compliance/financial dimensions, production, and deployment.

## Evidence basis

ADR-030 and the reconstructed Release 1.9 code/model. Candidate evidence is indexed in `docs/operational/assurance/mdpm-1/`.

## Framework Delta

**PROJECT RESULT:** deterministic parallel document readiness constrains an established operational transition without merging lifecycle state.

**FRAMEWORK DELTA:** PATTERN CANDIDATE. This is not an enterprise standard or philosophy change.


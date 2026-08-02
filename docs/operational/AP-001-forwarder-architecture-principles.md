# AP-001 — Forwarder Architecture Principles

- **Status:** Proposed consolidation; requires Product and Architecture approval
- **Date:** 2026-08-02
- **Architecture version:** DA-1.0
- **Authority sources:** Platform Constitution; accepted ADRs/PDRs; AI Engineering Rules

These principles consolidate existing governance. They authorize no feature or schema by themselves. Exceptions require a scoped Product decision and/or ADR, with Security, Data, Operations, migration, compatibility, and rollback approval where affected.

| # | Principle and statement | Rationale | Implementation implications | Exception boundary |
| --- | --- | --- | --- | --- |
| 1 | **Governance before implementation.** Settle material Product/architecture decisions first. | Code must not invent policy. | Link every Slice to accepted authority. | Accepted PDR/ADR or explicit non-applicability review. |
| 2 | **Explicit domain models.** Significant concepts use named structures. | Strong semantics and constraints improve safety. | Avoid unbounded metadata bags. | Architecture and Data approval. |
| 3 | **Reference Data before dependent Master Data.** | Stable classifications prevent drift. | Govern codes/lifecycle before dependent records. | Bounded temporary compatibility approved by Product/Data. |
| 4 | **Master Data before standardized transactions.** | Reuse and identity must precede repeatable capture. | Transactions may reference governed masters. | Manual transaction entry may remain where explicitly accepted. |
| 5 | **Structured selection before avoidable free text.** | Free text weakens validation and reporting. | Use selectors; keep bounded evidence/notes. | Product/Data approval where evidence cannot be structured. |
| 6 | **Immutable business codes.** | Codes are stable integration/reporting identities. | Never rename/reuse after creation. | Superseding record and migration decision. |
| 7 | **Opaque public identifiers.** | Numeric IDs enable enumeration. | APIs expose UUID/public IDs only. | No exception on external/internal HTTP contracts. |
| 8 | **Organization-first isolation.** | Tenant leakage is a critical defect. | Scope before lookup, matching, logs, cache, and serialization. | Explicit shared-data ADR/PDR and threat model. |
| 9 | **Soft deactivation and historical readability.** | Deletion can erase meaning. | Inactive records remain readable; block new selection. | Retention/legal decision and destructive migration approval. |
| 10 | **Transaction snapshots preserve historical meaning.** | Mutable catalogs are not transaction truth. | Snapshot approved facts at creation. | Accepted correction/supersession design. |
| 11 | **Additive migration by default.** | Expand-first evolution reduces risk. | Expand → verify → switch → contract. | Explicit breaking-change ADR and rollback proof. |
| 12 | **Backward compatibility.** | Existing users/data must remain valid. | N/N-1 and legacy read paths where applicable. | Accepted MAJOR change. |
| 13 | **Evidence before analytics.** | Metrics without reliable facts mislead. | Prove data quality and definitions first. | None for management/customer claims. |
| 14 | **Reporting uses governed operational facts.** | Reports must be reproducible. | Named dimensions, owners, formulas, security. | No inference of missing structure. |
| 15 | **Backend/API authorization is authoritative.** | UI controls are bypassable. | Deny-by-default service checks and negative tests. | None. |
| 16 | **No generic EAV without exceptional governance.** | EAV weakens contracts and discoverability. | Use explicit tables/fields. | Architecture, Product, Data, Security approval with bounded schema rules. |
| 17 | **No hidden cross-aggregate side effects.** | Implicit changes corrupt ownership. | Explicit commands/events; configuration does not create execution automatically. | Accepted orchestration design with atomicity/audit. |
| 18 | **Complexity proportional to business maturity.** | Premature automation increases failure and adoption risk. | Prefer simple workflows and measured triggers. | Evidence-backed Product/Operations decision. |
| 19 | **Bounded Slice delivery.** | Small releases improve traceability and rollback. | Explicit in/out scope and independent gates. | Release authority may group only compatible approved slices. |
| 20 | **Operational rollback and evidence are required.** | A release is incomplete without recovery. | Backup, manifest, smoke evidence, rollback plan. | No Production exception. |

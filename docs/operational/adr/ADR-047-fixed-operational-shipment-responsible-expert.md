# ADR-047: Fixed Responsible Transport Expert per Operational Shipment

- **Status:** ACCEPTED — target architecture; reference phase only
- **Date:** 2026-09-20
- **Owners / decision authority:** Product Owner; Architecture Owner; Security Owner; Operations Owner
- **Affected domain:** Operational Shipment ownership, Expert authorization, accepted-Quote lineage, direct Shipment creation
- **Implementation authority:** None. This ADR changes no runtime, schema, data, permission, test, deployment, or Production system.

## Context

ADR-042 accepted Organization Admin assignment/reassignment authority. ADR-043 accepted Request-root assigned-work inheritance and immediate transfer of accepted-Quote Shipment access when the Request assignee changes. Its implementation design later added `OperationalShipment.primary_responsible_expert_id` for Direct Shipments while accepted-Quote Shipments continued to derive responsibility from `ShipmentRequest.assigned_to`.

The current Product decision is different: every Operational Shipment has exactly one responsible Transport Expert, and no Shipment Expert reassignment workflow is approved. Historical ADRs and implementation evidence remain preserved; their conflicting Shipment-reassignment semantics are superseded only within the scope named below.

## Decision

```text
ONE_TRANSPORT_EXPERT_PER_SHIPMENT=YES
EXPERT_REASSIGNMENT_WORKFLOW_APPROVED=NO
```

`OperationalShipment` is the System of Record for its one fixed responsible Transport Expert. The ownership relation is established atomically at Shipment creation, is tenant-consistent, and is immutable for that Shipment.

- **Accepted-Quote Shipment:** the server captures the Transport Expert who issued the accepted official Quote as the Shipment's responsible Expert, after validating active identity and same-organization membership at creation time. The Customer cannot select or change this owner.
- **Direct Shipment:** an authorized creation flow supplies or server-resolves one active same-organization Transport Expert and records that owner in the same creation transaction. Creator identity alone is not ownership unless it is explicitly the validated responsible Expert.

The Request may continue to have its own commercial assignment/referral lifecycle before Shipment creation. A later Request assignment change does not change an existing Shipment owner and does not grant the new Request assignee access to that Shipment.

No API, command, state, audit event, UI action, background process, or administrative shortcut may be designed as Shipment Expert transfer, reassignment, replacement, or former-Expert access. If the owner becomes inactive or revoked, that actor is denied and the Shipment remains visible only through separately governed same-organization Admin/Manager authority; no automatic replacement occurs.

## Authorization contract

Authorization remains tenant-first, server-derived, capability-aware, and non-disclosing.

| Actor | Target Shipment result |
| --- | --- |
| Same-organization Admin/Manager with existing governed oversight | Allowed within that explicit oversight/action contract; never cross-tenant or unrestricted high-risk mutation by title alone |
| Owning active Transport Expert | Allowed for the Shipment and certified children, subject to the action capability and workflow state |
| Another Transport Expert in the same organization | Denied by default; organization membership alone never grants access. Any separately accepted explicit non-owner capability remains distinct from ownership. |
| Actor in another tenant | Denied non-disclosively |
| Inactive or revoked actor, including the recorded owner | Denied |

Children may inherit authorization only through certified, tenant-consistent lineage to the owning Operational Shipment. Possession of a Request, Project, WorkItem, OIP assignment, child identifier, stale list result, cached response, or former commercial assignment does not establish Shipment ownership.

## Supersession scope

This ADR is a scoped supersession, not a historical rewrite.

- **ADR-042:** supersedes only the statement that Organization Admin may reassign Shipment ownership and any implied Shipment Expert reassignment capability. ADR-042 remains authoritative for personas, membership, capabilities, tenant fencing, Admin oversight, audit, CRM, reporting, and legacy-role migration.
- **ADR-043:** supersedes Request-root derivation of accepted-Quote Shipment ownership, all Shipment A-to-B reassignment/transfer semantics, former/reassigned Expert certification cases, and Direct Shipment reassignment design. ADR-043 remains authoritative for tenant-first evaluation, Request-only assignment authorization, certified child lineage, collection non-disclosure, capability ordering, and fail-closed behavior where not conflicting.
- **ADR-043 implementation design package:** its reassignment matrices, cache invalidation around transfer, and request-assignee ownership of accepted-Quote Shipments are historical implementation evidence, not target product truth.

## Compatibility and migration contract

Current runtime behavior is implementation evidence and does not redefine this target.

- Direct Shipments already have an additive nullable `primary_responsible_expert_id`; future Build must prove one valid owner for every enabled Direct Shipment without guessing.
- Accepted-Quote Shipments currently leave that field null and derive access from the Request assignee. Future Build must converge them onto Shipment-owned responsibility.
- For historical accepted-Quote Shipments, the accepted official Quote issuer may be used only when the lineage is unique, same-tenant, and valid under an approved compatibility/data plan. Ambiguous, missing, foreign, or invalid lineage fails closed or remains Admin/Manager-only pending explicit adjudication.
- No guessed backfill, automatic replacement, destructive history rewrite, or migration execution is authorized here.
- Schema impact may be zero if the existing responsibility column is safely generalized, but the implementation slice must still define nullability, constraints, historical reconciliation, rollback, and owned PostgreSQL proof before coding.

## API and state contract

Target Shipment representations expose one responsible-Expert identity only to authorized audiences. Creation validates the source-specific rule above. Update APIs do not accept owner mutation. No `reassign`, `transfer`, `replace expert`, `former expert`, or equivalent Shipment state/route is part of the target contract.

Request assignment APIs remain Request-commercial APIs and must not imply Shipment-owner mutation. Quote revision remains a commercial action and does not change ownership of an already-created Shipment.

## Required future verification

Before implementation Freeze, direct backend/API and normal-navigation browser evidence must cover:

1. accepted-Quote creation captures the active same-tenant official Quote issuer exactly once;
2. Direct creation records one active same-tenant responsible Expert atomically;
3. owning Expert can discover, open, leave, return to, and act on the Shipment within entitlement/state;
4. another same-organization Expert is denied through detail, list, count, search, export, cache, child resources, and known identifiers;
5. other tenant and inactive/revoked owner are denied;
6. Admin/Manager oversight is tenant-scoped and action-specific;
7. later Request reassignment does not change Shipment ownership or access;
8. no owner-mutation route/state exists;
9. historical ambiguous/null ownership fails closed without guessed repair;
10. current Control Tower and Shipment Detail use the same owner/SOR.

## Consequences

Ownership becomes simple and stable, and accepted-Quote and Direct creation converge on one Shipment-owned authorization root. The tradeoff is intentional: an inactive/revoked owner does not trigger automated continuity through replacement; operational continuity remains an Admin/Manager concern until Product approves a different future decision.

## Reference impact

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_FOR_REFERENCE_PHASE
```

## Status history

- 2026-09-20: ACCEPTED — fixed responsible Transport Expert target recorded; no implementation authority.

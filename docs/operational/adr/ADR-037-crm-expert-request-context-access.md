# ADR-037: CRM Expert Request-Context Access

- Status: PROPOSED
- Date: 2026-08-20
- Owners: Product, Operations, Security, CRM domain owner
- Affected domain: CRM, ShipmentRequest customer context, authorization

## Context

Forwarder already contains an internal, database-backed CRM with `Customer`, `CustomerContact`, `Opportunity`, `Activity`, `Task`, and `CRMCustomerLinkAudit`. It is organization-scoped by the accepted architecture baseline and is distinct from `ShipmentRequest`, `OperationalShipment`, referral, the customer portal, and external CRM integrations.

The current API uses `@require_role("business_expert")`. Because roles are hierarchical, `business_expert`, `supervisor`, `crm_manager`, and `admin` receive the same CRM route-level access, while `expert` is rejected. The admitted surface includes organization-wide customer listing/detail and customer writes, opportunities, activities, dashboard KPIs, and request/customer create/link/relink/unlink workflows. The standalone `/crm` frontend route is an “in development” placeholder, but the backend and the request-detail CRM workflow are active.

The implementation is not consistently tenant-fenced. Newer customer, opportunity, and activity services derive tenant identity from the authenticated user, but customer-link search/read/link/unlink, customer-create preview/duplicate search, and dashboard KPIs contain unscoped queries or numeric-ID lookups. UI hiding is therefore not a security boundary.

## Problem

The product needs an explicit decision about what an operational `expert` may learn about a customer while working on a request, and whether the broad legacy authority of `business_expert` and higher roles should remain. Adding expert visibility, narrowing existing roles, or defining a new projection changes sensitive CRM authorization semantics and requires accepted architecture authority.

This ADR does not redesign CRM entities, customer identity, request/customer linkage, CRM ownership, or operational shipment semantics.

## Proposed decision

Adopt **Model B: read-only request-context customer projection** for the operational `expert` role.

1. An active expert with an active membership may read the projection only for a tenant-owned `ShipmentRequest` that the existing request authorization policy allows that expert to view. Assignment/request authority is evaluated before customer lookup.
2. The projection is parent-scoped. It has no customer-list endpoint, accepts no customer ID, and cannot be used to enumerate or directly fetch a CRM customer.
3. The allowlist is limited to operationally necessary fields already present in the request or its linked customer: display/customer name, company name, one relevant contact name when explicitly associated, operational phone, operational email, and operational address only when required by the request workflow.
4. The projection excludes CRM notes, contact notes, unrelated contacts, opportunities, pipeline values/probabilities, sales activities, tasks, customer history unrelated to the request, source/segmentation metadata, website/industry/company size unless separately justified, and all other customers.
5. The operational `expert` receives no CRM create, edit, link, relink, unlink, opportunity, activity, task, dashboard, or organization-wide search authority.
6. `crm_manager` and organization-admin CRM authority must be expressed by explicit capabilities rather than inherited accidentally from a numeric role hierarchy. The exact mutation matrix requires Product/Security acceptance before implementation.
7. Existing `business_expert` authority is compatibility behavior, not automatic approval for permanent organization-wide read/write access. Acceptance must explicitly retain, narrow, or migrate it.
8. Platform authority does not imply tenant CRM access. A platform administrator needs an explicit tenant context and separately accepted support policy; otherwise tenant CRM data fails closed.
9. All CRM queries derive organization identity from active authenticated membership or an already-authorized parent. Body/query organization identifiers never establish or broaden authority.
10. Existing optional `ShipmentRequest.customer_id`, immutable request contact text, audited link history, `Project.primary_customer_id`, and `OperationalShipment.customer_id` semantics remain unchanged.

## Alternatives

- **Model A — no expert access:** rejected as the preferred end state because an assigned expert needs customer/contact context to execute a request, though it remains the safe behavior until this ADR is accepted and implemented.
- **Model C — read-only organization CRM:** rejected for operational experts because it exposes unrelated customers, contacts, history, pipeline, and commercial context.
- **Model D — limited CRM read/write:** rejected for operational experts because customer identity and linkage mutations are commercial/governance actions, not necessary for ordinary execution.
- **Model E — current behavior:** rejected because basic experts receive no projection, business experts receive broad authority, and some admitted paths are not consistently tenant-scoped.

## Consequences

Experts receive the minimum customer context needed for assigned work without gaining a CRM browser. The projection adds a dedicated authorization and serialization contract. Existing business-expert workflows may need role/capability migration after the compatibility decision. CRM managers and organization administrators retain a separately governed management surface.

## Compatibility

Until acceptance and an authorized implementation, current routes and role behavior remain unchanged. Rollout must be additive: introduce the request-context projection, test it independently, then change any existing role access only through an explicit compatibility plan. Existing CRM response contracts, links, and audit rows are not silently rewritten.

## Migration impact

No schema or data migration is expected. If implementation discovers that a request cannot identify the relevant contact without new ownership or association data, implementation stops and returns for a separate decision rather than guessing.

## Security/tenant impact

- Authenticate the user and validate active membership before any parent or customer lookup.
- Resolve the request inside the authoritative organization and existing request-view policy.
- Resolve the linked customer through that authorized request and require matching tenant ownership.
- Return non-enumerating failures for foreign, inactive, quarantined, missing, or unauthorized resources.
- Never accept organization or customer authority from URL/body/query input.
- Apply a strict response allowlist and test absence of commercial/private fields.
- Preserve append-only link audit behavior; the read-only projection creates no CRM audit mutation.
- Remediate existing unscoped CRM paths before treating the CRM surface as tenant-certified.

## Operational impact

The projection should be bounded to one request and one linked customer, observable through safe authorization metrics, and unavailable when membership or assignment authority is removed. No external CRM, background synchronization, or production data operation is introduced.

## Rollback

Disable the projection and return to no expert CRM-derived context. Keep request-native contact information and all existing CRM/link data unchanged. Capability migration for existing roles must have an independent rollback to its prior explicitly documented matrix.

## Validation

- Expert Org A cannot obtain Org B request/customer context.
- Foreign request and customer identifiers return non-enumerating failures.
- Inactive membership, removed assignment/access, and deactivated expert fail closed.
- No organization-wide customer enumeration is available to `expert`.
- The endpoint accepts a request identity only and cannot perform unrelated customer lookup.
- Body/query organization identity cannot broaden access.
- Sensitive CRM, sales, financial, note, opportunity, activity, task, and unrelated-contact fields are absent.
- Organization-admin, CRM-manager, business-expert compatibility, and platform-authority behavior match the accepted matrix.
- Hidden frontend routes cannot bypass backend authorization.
- Existing link mutation audit remains unchanged.
- Focused authorization, tenant-negative, API contract, frontend, full regression, architecture-governance, sole-head, and secret-scan gates pass.

## Supersedes / superseded by

- Supersedes: none
- Superseded by: none

## Status history

- 2026-08-20: PROPOSED — repository census proved active CRM capability, inconsistent expert authority, and tenant-scope gaps requiring an explicit access decision.

# ADR-037: CRM Expert Request-Context Access

- Status: ACCEPTED
- Date: 2026-08-20
- Owners: Product, Operations, Security, CRM domain owner
- Affected domain: CRM, ShipmentRequest customer context, authorization

## Context and repository facts

Forwarder contains an internal CRM with organization-owned `Customer`, `CustomerContact`, `Opportunity`, `Activity`, `Task`, and `CRMCustomerLinkAudit` records. `ShipmentRequest.customer_id` is an optional many-requests-to-one-customer link. Link, relink, unlink, and create-and-link append link audit and expert-console records. Request-native contact text is descriptive input, not canonical CRM identity. ADR-034 separately governs execution customer identity; later request relinking does not rewrite an `OperationalShipment`.

Current CRM routes use hierarchical `@require_role("business_expert")`. Basic `expert` is denied, while `business_expert`, `supervisor`, `crm_manager`, and `admin` are admitted. Newer services contain tenant-scoped paths, but legacy link search/read/link/unlink, create preview/duplicate search, and dashboard paths include global queries or raw numeric lookups. The standalone `/crm` page is a placeholder although request-detail CRM workflows and APIs are active.

The concrete expert request policy at acceptance time requires an active actor, one resolvable active tenant membership, a non-quarantined `TENANT` request in that organization, and—unless the actor has separately authorized tenant-admin request authority—`ShipmentRequest.assigned_to == actor.id`. This ADR requires the projection to call the same canonical request-view decision as request detail, never a weaker copy. A later Accepted decision may replace that policy.

## Decision

Adopt a read-only, request-parented customer-context projection for basic operational `expert`:

```text
active actor and membership
  -> authorized current ShipmentRequest
    -> current same-tenant linked Customer
      -> explicit bounded projection
```

`expert -> organization -> customers` is prohibited. Same-organization membership alone never grants access.

### Parent authorization and tenant rule

Authorization runs in this order before customer lookup or disclosure:

1. Authenticate an active user and resolve one authoritative active `OperationalMembership` and active organization. Zero or ambiguous tenant contexts fail closed; client-supplied organization selection cannot resolve ambiguity.
2. Resolve the request by opaque identity inside that tenant; exclude intake, legacy-quarantined, foreign, or uncertified ownership.
3. Invoke canonical current request-view authorization. For a basic expert under current policy, the actor must be the current assignee. Role rank, same organization, former assignment, audit history, or identifier possession is insufficient.
4. Only then read `ShipmentRequest.customer_id`. Resolve the customer by ID plus the authorized request organization, require `ownership_scope == TENANT`, and reject mismatch or quarantine.
5. Serialize with an explicit projection allowlist. Never use a generic `Customer` or relationship serializer.

Every read re-evaluates current state. No standalone customer authority or access token may outlive parent access. Any cache must bind actor, tenant, request, and authorization-relevant state and be invalidated or bypassed on membership, assignment, ownership, link, and lifecycle changes.

### API and identifier contract

The new API is request-parented under the expert surface, conceptually `GET /api/expert/requests/{request_public_id}/customer-context`; implementation selects exact repository-conventional spelling.

- It accepts only an immutable opaque request identity. Existing `tracking_code` may be reused only if Security proves it suitable for authenticated internal authorization without weakening public-tracking semantics; otherwise opaque request identity needs a separate additive implementation/migration review.
- Sequential request, customer, and contact IDs are neither accepted nor emitted.
- No customer identity usable for direct lookup is returned. A non-actionable opaque correlation identity requires a proven UI need and grants no customer endpoint authority.
- Organization/customer input in path, query, body, header, or client state never selects or broadens scope.
- Missing, malformed, foreign, quarantined, unauthorized, and stale request identities use one non-enumerating not-found response. After successful parent authorization, no usable customer yields a stable empty-context shape.

Legacy numeric CRM routes may remain compatibility routes for existing roles after tenant certification. They cannot be reused for expert projection access.

### Closed-by-default field contract

New model fields are denied until an explicitly authorized amendment adds them.

| Field / value | Class | V1 rule |
| --- | --- | --- |
| derived display name from `Customer.first_name` + `last_name` | ALLOW | One display value, not generic serialization. |
| `Customer.company_name` | ALLOW | When present. |
| `Customer.phone` | ALLOW | One operational telephone. |
| `Customer.mobile` | CONDITIONAL | Fallback when phone is absent, or one explicitly distinguished operational mobile; not both by default. |
| `Customer.email` | ALLOW | Operational email when present. |
| `address`, `city`, `province`, `postal_code`, `country` | CONDITIONAL | One formatted address only when physical customer/contact handling is required; otherwise omit. |
| `Customer.status` | CONDITIONAL | Never expose raw status. Inactive/blocked yields unavailable context. |
| `id`, `operational_organization_id`, `ownership_scope` | DENY | Internal identity and tenant metadata. |
| `website`, `industry`, `company_size`, `customer_type`, `source` | DENY | Administrative/segmentation/commercial metadata. |
| `notes`, `last_contact_at`, `created_at`, `updated_at` | DENY | Private notes and CRM history/metadata. |
| requests, opportunities, activities, tasks and all counts/values/stages/probabilities/outcomes | DENY | No history, pipeline, activity, or task data. |
| request-native name, phone, route/contact fields | ALLOW under request policy | Already-authorized request data; never fuzzy-merged into CRM identity. |

Only named scalar keys, source (`request` or `linked_customer`), and stable availability may be returned. No generic/nested customer, contact, or request objects; relationship counts; CRM URLs; or sales metadata.

### Contact scope

V1 exposes **no `CustomerContact` row**. No request-to-contact association exists. `is_primary` describes an account contact, not request relevance. Returning all, first, primary, or decision-maker contacts would invent relevance and expose unrelated personal data.

V1 may expose only the linked Customer account's allowlisted values plus request-native contact fields already visible under request authorization. A future contact projection needs an explicit tenant-consistent request-contact association and ADR amendment. At most the associated contact's derived name and one operational phone/email could then be considered; `position`, `department`, `is_primary`, `is_decision_maker`, `notes`, timestamps, IDs, and other contacts remain denied.

### Read-only authority

Basic `expert` gains exactly one capability: read this current projection for a currently authorized request. It gains no customer/contact create/update, link/relink/unlink, standalone detail, list/search, duplicate search, preview, dashboard, opportunity, activity, task, pipeline, history, export, or bulk authority. Backend capability and method checks enforce this. No standalone expert CRM workspace is authorized.

### Lifecycle behavior

| Event/state | Result |
| --- | --- |
| Relink | Next read resolves only the new same-tenant customer; former customer access ends immediately. |
| Unlink | Next authorized read returns empty context; audit history is never authority. |
| Reassignment/removal | Former expert immediately fails parent access; newly authorized expert may read current context. |
| Organization transfer | Fail closed until transfer and request/customer tenant invariants are valid and current parent authority exists. |
| Closed request | Closure neither grants nor preserves access. V1 follows canonical request-view policy; if that policy still permits the assigned expert to view the closed request, projection remains readable. |
| Reopened request | Access exists only if canonical current request policy authorizes it; prior view/assignment has no effect. |
| Inactive/blocked customer | Empty/unavailable context without disclosing raw CRM status; no fallback to contacts/history. |
| No customer | Stable empty-context response after parent authorization; request-native data remains in the request contract. |

Changing request closure authorization is a separate request-policy decision, not part of this ADR.

### Role and authority boundaries

- **expert:** only the request-context read above.
- **business_expert:** current CRM compatibility behavior remains unchanged, but is not certified or endorsed as the final model. Narrowing/migration needs a separate accepted compatibility decision.
- **supervisor / crm_manager:** current hierarchical compatibility remains unchanged. Future management uses explicit capabilities, not accidental numeric inheritance.
- **Organization Admin:** CRM authority requires active membership, trusted tenant context, and explicit tenant capabilities. Role name alone never bypasses fencing.
- **Platform Admin:** platform authority alone grants no tenant CRM access. Without trusted tenant context plus a separately accepted support/impersonation policy and audit, fail closed. Client-selected tenant is not trusted context.

### Required remediation and certification

Before projection or expert UI enablement, tenant-certify the canonical request-view policy and every dependency. The projection should depend on none of these legacy APIs, but existing admitted CRM debt remains tracked:

| Legacy path | Current issue | Required certification |
| --- | --- | --- |
| customer list/detail/write | newer tenant derivation; numeric customer identity | Active membership/org, ownership/quarantine, explicit capability, tenant-scoped contacts, non-enumerating negatives. |
| link search | global query and numeric results | Tenant filter before search/pagination, lifecycle policy, capability, cross-tenant negatives; never expert-visible. |
| link read | raw numeric request lookup | Authorize tenant parent first, then same-tenant customer. |
| link/relink/unlink | numeric raw lookups | Membership, parent, mutation capability, same-tenant active customer, concurrency/idempotency as applicable, append audit. |
| create preview | raw request and global duplicates | Parent authorization first; tenant-scope candidates and omit forbidden data. |
| create-and-link | partial tenant check; global duplicates | Put all reads behind tenant scope; validate capability/link invariants atomically; retain audit. |
| dashboard | global aggregates/recent activities | Tenant-filter every aggregate/join/lookup; never expert-visible. |

Certification records tenant source, active membership, capability, ownership/quarantine filter, identifier, cross-tenant response, and negative tests. No expert UI may use an uncertified legacy API.

### Adversarial fail-closed matrix

| Threat | Required result |
| --- | --- |
| Guess foreign/missing/malformed/other expert's request | Same not-found; no customer lookup before parent authorization. |
| Guess customer | Projection accepts none; direct CRM endpoints deny expert. |
| Same-tenant unassigned request | Denied; membership is insufficient. |
| Access after reassignment/transfer/unlink/deactivation | Current-state check denies or returns empty on next read; no stale authorization cache. |
| CRM list/search/dashboard/mutation attempt | Backend denial without data/existence disclosure. |
| Organization manipulation | Reject or ignore; never authority. |
| Unrelated contacts | No contacts in V1; no generic relationship serialization. |
| Two-organization user | Require trusted unambiguous tenant context; ambiguity/client-only selection fails closed. |
| Invalid cross-tenant customer link | Do not follow; unavailable/non-enumerating result and safe security telemetry. |
| Closed/reopened request | Re-evaluate canonical request policy as above. |
| business_expert regression | Compatibility regression tests pin behavior until separately migrated. |
| Platform Admin without tenant context | Denied. |

### Privacy, audit, and errors

Existing link mutation audit remains unchanged. V1 does not require a durable domain audit row for every ordinary authorized read: no compliance requirement presently justifies the sensitive access history and load. Emit privacy-safe structured authorization/security telemetry for denied cross-tenant attempts and invalid link invariants without customer/contact values, raw identifiers, or existence distinctions. Durable read audit later requires a separate retention/access/minimization policy.

Responses and logs never distinguish foreign from missing and never echo tenant/customer IDs or sensitive values. Metrics may count outcome classes without identifying subjects.

## Compatibility and rollback

This is additive authority for one new read projection. Existing request-native fields, CRM APIs/contracts, role behavior, links, audit rows, and ADR-034 execution identity remain unchanged. No schema expansion is authorized here; opaque request identity or contact association work triggers its own bounded review and migration authority.

Rollback disables the endpoint and expert UI, returning experts to request-native data only. It never deletes or rewrites customers, contacts, requests, links, audits, or shipments. Legacy remediation and later capability migration use independent gates and rollback.

## Authorized implementation boundary and order

This acceptance authorizes a later controlled implementation goal, not runtime work in this review:

1. tenant-certify canonical expert request-view policy and projection dependencies;
2. settle opaque internal request identity without numeric IDs or weakened public tracking;
3. add one backend request-parented GET projection with the exact allowlist and no `CustomerContact` rows;
4. enforce active membership, tenant, current request policy, link, customer tenant/state, and non-enumerating errors;
5. add cross-tenant, same-tenant-unassigned, multi-membership, lifecycle, negative-field/method, role-regression, Organization Admin, and Platform Admin tests;
6. only then add a request-detail component titled as request-related customer/contact information;
7. add no expert CRM workspace/search/list/detail, writes, contact association, schema migration, or existing-role semantic changes.

Runtime implementation, migration execution, production access, production database access, deployment, release, and push are not authorized by this documentation decision.

## Validation required before implementation completion

- Explicit serializer keys and absence tests cover allowed, conditional, denied, relationship, and newly added fields.
- Parent authorization precedes customer lookup and shares canonical request-detail policy.
- All tenant, assignment, lifecycle, link, customer-state, and multi-membership negative cases match this ADR.
- No numeric request/customer/contact identity or tenant metadata is accepted or emitted.
- Expert cannot use CRM list/search/detail/dashboard/preview/link/write routes.
- Existing business-expert behavior is regression-pinned without being mistaken for tenant certification.
- Focused tests, full applicable regression, architecture governance, ADR index validation, `git diff --check`, and changed-scope secret scan pass.

## Supersedes / superseded by

- Supersedes: none
- Superseded by: none

## Status history

- 2026-08-20: PROPOSED — repository census proved active CRM capability, inconsistent expert authority, and tenant-scope gaps.
- 2026-08-20: ACCEPTED — adversarial review settled parent authorization, contact minimization, identifiers, lifecycle, tenant remediation, roles, audit, errors, compatibility, rollback, and ordering. Implementation remains pending.

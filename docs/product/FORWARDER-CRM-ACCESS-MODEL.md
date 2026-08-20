# Forwarder CRM Current State and Access Model

Status: repository-proven current-state audit; proposed future access is governed by ADR-037.

## Executive answer

CRM materially exists and is active, but its product surface is partial.

- The backend and database are implemented and active.
- Request-detail customer creation/linking is frontend-visible for `business_expert` and higher roles.
- The standalone `/crm` route exists but renders only an “in development” placeholder; its API clients are implemented but not consumed by that page.
- The basic `expert` role is denied by backend CRM routes and sees a disabled link card.
- `business_expert`, `supervisor`, `crm_manager`, and `admin` are admitted to every current CRM route through hierarchical `@require_role("business_expert")` checks.
- Some newer services are tenant-scoped; several older request-link, preview, duplicate-search, and dashboard paths are not consistently scoped and are not tenant-certified.

Therefore the correct classification is **PARTIAL**, not “absent” and not simply “switched off.”

## Capability census

| Capability | Backend/DB | API | Frontend | Visible | Current admitted roles | Tests | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Customer list/detail | Yes | GET list/detail | API client only | No standalone UI | business_expert+ | Read/security contracts | BACKEND_ONLY |
| Customer create/update | Yes | POST/PUT | API client only | No standalone UI | business_expert+ | Write contracts | BACKEND_ONLY |
| Customer contacts | Yes | Nested in customer detail | Types only | No | business_expert+ through detail | Read contract | BACKEND_ONLY |
| Opportunities | Yes | GET/POST | API client only | No | business_expert+ | Read/write contracts | BACKEND_ONLY |
| Activities | Yes | GET/POST | API client only | No | business_expert+ | Read/write contracts | BACKEND_ONLY |
| Tasks | Model/table | No CRM route | No | No | None through CRM API | Indirect model tests | PARTIAL |
| CRM dashboard KPIs | Yes | GET | API client | Placeholder page does not call it | business_expert+ | Read contract | IMPLEMENTED_BUT_HIDDEN; current query is globally scoped |
| Request customer-link read/search | Yes | GET | Request detail | Yes for business_expert+ | business_expert+ | Link contract | ACTIVE; tenant remediation required |
| Request link/relink/unlink | Yes, audited | PUT/DELETE | Request detail | Yes for business_expert+ | business_expert+ | Audit/idempotency contract | ACTIVE; tenant remediation required |
| Create customer from request | Yes, preview/review/audit | GET preview, POST create | Request detail | Yes for business_expert+ | business_expert+ | Preview/mutation contracts | ACTIVE; preview/duplicate scope remediation required |
| Standalone CRM dashboard | — | — | `/crm` component | “In development” only | frontend allows business_expert+ | Component test | PARTIAL |
| External CRM integration | No | No | No | No | None | — | NOT_IMPLEMENTED |

“business_expert+” means `business_expert`, `supervisor`, `crm_manager`, and `admin` under the current numeric role hierarchy. It does not mean the access has been approved as the final product model.

## Actual domain model

```text
OperationalOrganization
├── Customer 0..N
│   ├── CustomerContact 0..N
│   ├── Opportunity 0..N
│   │   └── Activity 0..N (optional link)
│   ├── Activity 0..N (optional link)
│   └── ShipmentRequest 0..N (optional customer_id)
├── Project 0..N (required primary_customer_id in canonical project rows)
└── OperationalShipment 0..N (canonical execution customer_id under ADR-034)

ShipmentRequest
├── optional Customer link
├── immutable/descriptive request contact fields
├── optional Activity / Task links
└── CRMCustomerLinkAudit 0..N for link/relink/unlink/create-and-link
```

`CustomerGamification` is a separate portal identity and is not CRM `Customer`.

## Entity semantics

`Customer` is deliberately broad: its `customer_type` supports prospect, customer, partner, or vendor; it can represent a person or company/account using name and company fields. The repository does not constrain it to shipper, consignee, or legal customer. Those roles must not be inferred.

`CustomerContact` is a person associated with a customer account. `Opportunity` is a sales opportunity, not a shipment request. `Activity` is a customer interaction/follow-up that may reference a request without changing request status. `Task` is an internal follow-up item and currently lacks a CRM API surface.

## Request and project relationships

- Public request creation stores descriptive customer/contact fields and does not require or automatically create a CRM customer.
- `ShipmentRequest.customer_id` is one nullable link to one CRM `Customer`; one customer can be linked from many requests.
- Link, relink, unlink, and create-and-link are explicit and audited in `CRMCustomerLinkAudit` plus the expert-console timeline.
- CRM customer edits do not rewrite the request’s descriptive contact fields; there is no CRM snapshot copied back to the request.
- `Project.primary_customer_id` is the project’s governed customer identity.
- `OperationalShipment.customer_id` is its canonical execution customer identity under ADR-034. Quote conversion copies the request’s linked customer identity at creation; later request relinking does not silently rewrite the operation.

## Current authorization matrix

| Role | Org CRM list/detail | Create/edit customer | Opportunities | Activities | Request link/create workflow | Standalone route |
| --- | --- | --- | --- | --- | --- | --- |
| expert | Denied | Denied | Denied | Denied | Denied | Denied |
| business_expert | Allowed | Allowed | Allowed | Allowed | Allowed | Placeholder |
| supervisor | Allowed by hierarchy | Allowed | Allowed | Allowed | Allowed | Placeholder |
| crm_manager | Allowed by hierarchy | Allowed | Allowed | Allowed | Allowed | Placeholder |
| admin | Allowed by hierarchy | Allowed | Allowed | Allowed | Allowed | Placeholder or admin redirect after login |

The repository has separate authority/membership concepts, but CRM route authorization is based on the legacy role hierarchy. Platform authority is not a proven tenant CRM grant; without a trusted tenant context it must fail closed.

## Expert operational need and minimization

For an expert processing an authorized request:

- **Operationally required:** requester/customer display name, company name when relevant, operational telephone/email, and the request’s own pickup/delivery/contact information.
- **Useful context:** one explicitly relevant account contact or operational address when the workflow proves it is needed.
- **Commercial sensitive:** CRM notes, opportunity stage/probability/value, pipeline totals, sales activities, outcomes, next actions, and unrelated request history.
- **Administrative:** customer status/source, segmentation, website, industry, company size, contact decision-maker flags, and link governance actions.
- **Not relevant:** unrelated customers, unrelated contacts, organization-wide CRM history, tasks/opportunities unrelated to the request, and customer-portal gamification data.

The recommended model is a read-only request-context projection, not full CRM access. Until ADR-037 is accepted and implemented, the basic expert remains denied CRM-derived data and continues to use request-native contact fields.

## Known security and completeness gaps

1. `crm_customer_link_service.search_linkable_customers` queries all customers without deriving the authenticated organization.
2. Request-link get/link/unlink use numeric `db.session.get` lookups without tenant/request authorization in the service.
3. Customer-create preview and duplicate search use unscoped request/customer queries; the create mutation adds tenant validation later, but preview must also fail closed.
4. CRM dashboard KPIs and recent activities are global rather than organization-scoped.
5. The standalone CRM page is a placeholder and does not exercise implemented API clients.
6. Route-level role inheritance grants broad write authority to `business_expert` and `supervisor`; no accepted fine-grained capability matrix exists.
7. Task CRUD, contact CRUD, delete/deactivate APIs, and a complete CRM navigation/workspace are not implemented.
8. Several public CRM contracts use sequential integer IDs; possession is not authority, but opaque public identity remains a future hardening concern.

These are current-state findings, not claims that the affected features are safe for expanded access.

## UI terminology

- Organization-admin/CRM-manager management may use «CRM».
- An operational expert projection should be titled «اطلاعات مشتری مرتبط با درخواست» or «اطلاعات تماس مرتبط با درخواست».
- The expert UI must not imply access to a full CRM account, sales pipeline, or customer history.

## Future expansion boundary

ADR-037 must be accepted before expert projection or existing-role authority changes. A later implementation goal should first remediate tenant scope on all admitted CRM paths, add capability-based authorization, and prove the adversarial matrix. External CRM integration, customer identity redesign, automatic customer creation, opportunity/request equivalence, and Customer/CustomerGamification convergence remain out of scope and require separate authority.

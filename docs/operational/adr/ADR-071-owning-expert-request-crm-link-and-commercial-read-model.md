# ADR-071 — Owning Expert Request CRM Link and Commercial Read Model

- **Status:** ACCEPTED — bounded Human Walkthrough hardening authority
- **Date:** 2026-09-28
- **Decision authority:** Product Owner Expert Request Commercial Hardening mission
- **Affected domain:** ShipmentRequest commercial review, CRM Customer link,
  Quote-response projection, Expert navigation
- **Migration:** none

## Context

The existing Request detail authorizes a basic Expert to read a bounded linked
Customer projection through ADR-037, but denies search/link and points the UI
at broad legacy CRM routes available only to higher legacy CRM roles. Those
legacy routes query globally or use unparented numeric lookups and therefore
cannot be exposed to the basic owning Expert.

The data model already has the necessary facts: `ShipmentRequest.customer_id`,
same-tenant Customer ownership, active membership and assignment scope,
append-only `CRMCustomerLinkAudit`, Quote-specific immutable Customer response,
and explicit accepted-Quote Shipment creation. No schema is needed.

## Decision

### Request-parented CRM Customer selection and link

The current owning Transport Expert gains one bounded commercial-review
capability under the authorized Request:

```text
active actor + active single tenant membership
  -> current assigned Request in that tenant
    -> active tenant-owned CRM Customer candidates
      -> explicit link or audited relink
```

Candidate search, current-link read and link/relink commands are all parented
by the opaque Request identity. Parent authorization and exact current
assignment run before Customer search, lookup or disclosure. Candidate queries
apply tenant, ownership and active-state predicates before search, ordering and
pagination. A missing, guessed, inactive or foreign Customer fails closed.

The Expert receives no standalone CRM list/detail/create/update/delete,
duplicate search, contact, opportunity, activity, dashboard, export or bulk
authority. The Request UI offers no Customer creation or unlink operation.
Organization Admin remains the normal CRM Customer creator.

Existing relink semantics may be used because current canonical persistence
already preserves old/new Customer identity, actor, role, Request state,
assignment snapshot, reason, source, time and IP in append-only audit. Relink
never rewrites existing `OperationalShipment.customer_id` snapshots. If that
history invariant fails at runtime, the command fails rather than overwriting.

### DN10 separation

Request Customer link and Portal Account entitlement remain different facts.
The command does not read, infer, create, revoke or update
`CustomerEntitlement`; it never matches by name, email, phone, Request creator
or portal account. ADR-062 remains fully authoritative.

### Commercial read projection

`ShipmentRequest.status` remains the Request commercial lifecycle SOR.
`ExpertQuote.customer_response` remains the response SOR for the exact Quote.
A derived next-action projection combines the current Request status and the
latest Quote only:

- latest Quote has no response: waiting for Customer is valid;
- latest response `accepted`: Expert commercial action is required;
- latest response `discussion`: Expert must review negotiation and may issue a
  newer Quote, after which waiting for Customer becomes valid again;
- latest response `declined`: Expert must determine the commercial result;
- terminal Request status (`won`, `lost`, `closed`) means the commercial result
  is already recorded.

The derived `needs_action` list bucket is a read projection, not a stored
status. Counts and rows use the same authorized population and predicates.

### Timeline and presentation

The primary Expert Request timeline narrates Quote issuance, Customer response,
Request status transition, assignment, messages and CRM Customer linking in
simple Persian. Raw event codes, database fields, model names and internal IDs
are not rendered. Stored logs, Quotes and link audits remain unchanged.

Cargo and Quote formatting are display-only: meaningful Cargo description,
then governed Persian Cargo Type, then `قلم کالا N`; governed Persian UOM;
trimmed non-significant decimal zeros; grouped monetary amount; and currency
labels that preserve the authoritative code (`ریال ایران (IRR)`,
`دلار آمریکا (USD)`). No conversion or arithmetic change occurs.

## Authorization and negative behavior

- Non-owner, former owner, inactive member, ambiguous tenant, foreign tenant,
  inactive Customer and guessed Customer fail before disclosure or mutation.
- UI visibility is not authority; direct API tests are required.
- Existing DN10 grants, Customer Portal ownership, Quote history, Request
  history and operational Shipment facts are unchanged.
- Quote acceptance never creates Shipment. Existing explicit creation remains
  idempotent and independently reauthorizes current facts.

## Compatibility and supersession

ADR-071 extends ADR-037 only for the specific Request-parented candidate
search/link/relink capability authorized here. ADR-037's projection allowlist,
parent authorization, no-contact rule and denial of general CRM authority stay
in force. ADR-034 Request/Shipment customer snapshots, ADR-053 portal/CRM
identity separation, ADR-062 DN10 and ADR-002/007 Request/operation status
separation are preserved.

Legacy CRM routes remain compatibility behavior for their existing roles and
are not reused by the basic Expert UI. They gain no certification from this
decision.

## Required verification

- owning Expert positive link/reopen and audited relink;
- non-owner, foreign tenant, inactive Customer and guessed-ID negatives;
- search tenant filtering before pagination/disclosure;
- zero `CustomerEntitlement` changes;
- latest-Quote response and newer-Quote waiting semantics;
- bucket row/count parity for every persisted Request status;
- Persian timeline with immutable Quote/link/status history;
- Cargo/UOM/currency/amount presentation;
- normal navigation, active state, desktop/mobile/RTL/keyboard and states;
- Customer/Admin/Workspace/Control Tower regressions and exact-candidate
  integrated journeys.

Release, Production, deployment and Human Walkthrough PASS remain separate.


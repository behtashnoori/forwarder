# ADR-053: Optional Customer Account and Private Quote Authority

- **Status:** ACCEPTED — implementation candidate; release authority separate
- **Date:** 2026-09-23
- **Decision authority:** Product Owner mission and subsequent Organization Admin clarification
- **Affected domain:** Customer Portal identity, Request ownership, private Quote access, password lifecycle
- **Preserves:** ADR-052 Public Tracking; CRM Customer; Operational Shipment; Expert/pricing authority

## Context

Forwarder must support both a low-friction anonymous Request journey and an
optional Customer Account. Public Tracking is an opaque bearer capability with
a deliberately small projection; it is not identity and must never authorize
Quote reads or writes. The prior donor implementation proved useful session,
ownership, discovery, and Quote-history concepts but was not commit-bound,
predated current Golden contracts, and exposed a broader public projection.

The existing `CustomerGamification` identity is separate from CRM `Customer`.
`ShipmentRequest.gamification_customer_id` expresses private portal ownership;
`ShipmentRequest.customer_id` remains the independent CRM relationship.

## Decision

1. Customer Account is optional. `POST /api/shipment-request` remains available
   without authentication and creates no portal ownership when anonymous.
2. A signed Customer session is accepted only while the account is ACTIVE and
   its server-side session generation still matches. Account disable, password
   change, reset, and enrollment completion increment that generation as
   applicable, invalidating older sessions.
3. When an ACTIVE Customer submits a Request, portal ownership is derived only
   from the authenticated server session. Client-supplied portal owner IDs are
   ignored/rejected and never trusted.
4. Private Request list/detail and Quote current/history/response require the
   current account owner. Cross-account lookup is non-disclosing.
5. Quote amount/currency remain Expert-owned. Customer response targets the
   exact current immutable Quote using its opaque identity and expected
   response version. Golden `accepted | discussion | declined` semantics and
   the bounded discussion message remain authoritative.
6. Password reset/enrollment capabilities are high-entropy, digest-only at
   rest, purpose-bound, expiring, and single-use. Public forgot-password
   responses do not reveal account existence. Automated delivery remains a
   separate Product decision; no local/UAT message is sent.
7. Portal accounts have explicit server-owned organization scope. Routine
   support is authorized only to the Organization Admin whose active membership
   matches that scope. Platform Admin is not routine tenant account support.
8. Legacy enrollment may target only an exact scoped portal identity selected
   through governed authority. No CRM-to-portal or anonymous-Request claim is
   inferred from name, email, mobile, or similarity.
9. Profile v1 is read-only for identity/contact information. Changing login
   email is deferred until verification and identity-transfer policy is
   specifically authorized.

## Public/private separation

ADR-052 remains unchanged. Public Tracking accepts only its versioned opaque
capability and returns its fixed allowlist. It exposes no account identity,
contact detail, exact address, cargo value, Expert identity/contact, Quote,
Quote history, response, discussion, document, or internal provenance.

## Data and migration

The Golden migration chain is extended linearly after
`20260926_fixed_shipment_responsible_expert`. Historical portal/gamification
rows remain compatible with nullable credentials. No identity or organization
backfill is inferred. The Product Owner confirmed there are currently no real
Customers; migration/enrollment evidence therefore uses synthetic records, but
the no-inference rule remains a permanent control.

## Open decisions

- automated recovery delivery channel (email, SMS, or another governed
  provider);
- the future SOR/evidence for any explicit CRM Customer to portal identity link.

These open decisions block only their affected Product journeys. They do not
authorize weakening token security or making an inferred link.

## Consequences and verification

- Customer-facing session, password, Request, and Quote routes gain positive,
  anonymous, cross-account, CSRF, stale-version, disabled, expiry, and replay
  tests.
- Organization Admin support gains same-tenant positive and cross-tenant
  negative tests and exposes no password material or ownership-transfer action.
- Anonymous Request and ADR-052 projection receive preservation regressions.
- Release, Production migration, and deployment are outside this decision.

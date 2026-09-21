# ADR-052: Public Tracking Opaque Capability Authority

- **Status:** ACCEPTED — bounded MT-3 implementation authorized
- **Date:** 2026-09-21
- **Owners / decision authority:** Product Owner mission; Architecture Owner; Security/Authorization boundary; Customer Tracking owner
- **Affected domain:** unauthenticated Request tracking, public projection, request tracking-code issuance, public navigation
- **Implementation authority:** the 2026-09-21 MT-3 Public Tracking Identity / Authorization Security Closure mission

## Context

`GET /api/public/track/{identifier}` currently accepts a decimal
`ShipmentRequest.id` or a global `tracking_code`.  The numeric branch makes an
internal sequential database identity public authority.  The current request
code generator provides only about 31 random bits and has a predictable
ID-derived error fallback.  Historical migrations also created sequential
`SR000001`-style codes.  The response includes internal numeric identity and a
broader set of Customer, Expert, Cargo, and Quote data than tracking requires.

MT-1 has already established a server-owned Request ownership envelope and
quarantine/current-authority checks.  `ShipmentRequest.tracking_code` is
globally unique and can hold a stronger versioned capability without a schema
change.  Public users must not supply or know a tenant, organization, Request,
Shipment, or database identity.

## Decision

The only authority for this Request public-tracking route is a versioned bearer
capability with this exact shape:

```text
SR2-<22 base64url characters>
```

The payload is generated from 16 cryptographically secure random bytes (128
random bits).  Generation has no deterministic fallback.  The existing unique
index remains collision protection.

Resolution is ordered as follows:

```text
normalize and validate the capability shape
-> exact ShipmentRequest.tracking_code lookup
-> current ownership/quarantine validation
-> derive the Request's TENANT or governed INTAKE scope server-side
-> emit the fixed public tracking allowlist
```

The capability is the complete public authority context for this shared public
route.  Hostname remains an intake-routing and future branding concern; it is
not a second caller-supplied authorization key.  A caller cannot combine one
capability with another tenant or resource identity because the route accepts
no such identity.  This bounded decision supersedes the MT-0/roadmap proposal
that required a public tenant hostname/path in addition to the capability.

Numeric database IDs, authenticated `ShipmentRequest.public_id` UUIDs,
Project tracking codes, malformed values, unknown capabilities, and all legacy
Request codes outside the `SR2-` contract are invalid on this route.  The
public response for each is the same non-disclosing 404 envelope.

## Public projection

The fixed Request public-tracking allowlist is:

- opaque `tracking_number`, commercial `status`, creation time, and shipping
  type;
- bounded origin/destination geography labels without street/address data;
- existing Request transport-intent presentation fields;
- assignment time and the simple four-step public workflow; and
- the existing customer-visible unit-tracking projection when tracking is
  enabled, including its established public dates, geography labels, and
  customer-visible event text.

The projection excludes database IDs, tenant/organization IDs, Customer name
and contact data, exact address, Cargo/value/instructions, Expert identity and
contact data, Customer-touch metadata, Quote/commercial history, Quote
discussion, Documents/storage/history, internal notes, Notification state, and
internal provenance.  Public data is reduced only; no new field is authorized.

## Eligibility and non-disclosure

Existing Request public-tracking eligibility remains: the exact capability
must exist and the Request must pass the current ownership/quarantine guard.
Existing unit detail remains additionally gated by the tracking-enabled and
customer-visible rules.  MT-3 does not make every Request or internal event
public.

Success and not-found responses use `Cache-Control: no-store` and
`Referrer-Policy: no-referrer`; public tracking is not indexed.  Application
logs must not record the plaintext capability.  Missing generalized rate
limiting remains a separately classified defense-in-depth risk and does not
justify retaining numeric authority.

## Compatibility and recovery

Unsafe compatibility is rejected.  Existing numeric URLs and legacy weak or
predictable codes fail closed; they are not redirected or translated.  New
Request submission returns and navigates with the `SR2-` capability only.  No
QR producer exists in the current product.  The existing copy action copies
only the newly issued opaque tracking code.

Source rollback may restore prior code but is not an authorized security
rollback.  Numeric public lookup must never be re-enabled.  A future governed
rotation/revocation UI or hashed capability store may be additive, but it is
not required to remove the present numeric-ID authority and must not weaken
this contract.

## Schema decision

```text
MT3_SCHEMA_DECISION=NO_SCHEMA_CHANGE_REQUIRED
```

`ShipmentRequest.tracking_code` is already unique, indexed, nullable for
historical compatibility, and wide enough for the 26-character versioned
capability.  No data backfill is authorized: generating capabilities for old
rows would silently grant public access and require business interpretation.

## Required evidence

PASS requires positive resolution of a newly issued capability; rejection of
known Request/Shipment IDs and sequential numeric probes; indistinguishable
numeric/malformed/unknown failure; exact-resource and cross-tenant isolation;
an exact response allowlist; absence of Customer/Expert/Quote/Document/internal
identity data; generated-link navigation; desktop and mobile RTL browser
journeys; PostgreSQL 18 qualification; full regression; one Alembic head; and
final reference alignment.

## Reference impact

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
REFERENCE_IMPACT_STATUS=CLOSED_BY_ADR_052_DESIGN
```

ADR-052 narrows and implements the public Request tracking authority boundary.
It does not change authenticated internal Request lookup, Project public
tracking, tracking event ownership, Quote response semantics, Documents,
Notifications, Dual Calendar, Combined Transport, or retired tracking actions.

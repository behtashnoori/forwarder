# PDR-012 — Forwarder Command Center

- **Status:** Accepted
- **Date:** 2026-08-01
- **Target release:** 1.3.0 — Forwarder Command Center
- **Primary capability:** CAP-007 Customer Portal
- **Supporting capabilities:** CAP-010 Security & Identity, CAP-001 Project Management
- **Decision owner:** Product Owner — Customer Portal
- **Decision source:** Approved implementation contract for this slice

## Accepted decision

1. `/` is the operational Command Center rather than the primary promotional or educational page.
2. Its primary first-glance intents are registering a shipment request and tracking a request/Project/shipment. Staff login remains immediately available from the compact header menu without competing in the main composition.
3. Promotional workflow, capability, repeated service, and large contact sections are removed from root rendering. Secondary information is available through the real `/about` and `/contact` routes.
4. Desktop targets a single normal viewport. Mobile may scroll where touch size and readable content require it.
5. Existing domestic/international request forms remain unchanged and are entered from the primary CTA.
6. Existing request tracking remains at `/customer/track/:requestId`; Project tracking remains at `/project/track/:trackingCode`. Current `SR-…` request codes and legacy numeric request identifiers use the request route; other opaque public tracking codes use the Project route.
7. Staff authentication, ProtectedRoute behavior, public projections, APIs, and backend security remain unchanged.

## 2026-09-21 MT-3 security amendment

ADR-052 supersedes only the legacy numeric/public-request identity clause in
decision 6 and the unchanged-security assumption in decision 7.  Request
tracking remains at `/customer/track/:requestCapability`, but only a valid
versioned `SR2-` Request capability can resolve.  Numeric Request IDs and
legacy weak/predictable codes may still reach the stable unavailable page when
typed into the Command Center, but they are not public authority and are never
translated to a database row.  Project tracking remains a separate route and
authority outside MT-3.

## Consequences

The original Command Center composition was a backward-compatible MINOR
release.  The MT-3 amendment is an intentional security/API-contract change
governed by ADR-052: the Request route now accepts only the `SR2-` capability
and returns a reduced allowlist.  It requires no schema migration, data
backfill, authentication-model change, deployment, backend restart, or
environment change in this mission.  A later deployment remains separately
authorized and must publish rebuilt frontend and backend artifacts together.

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

## Consequences

This backward-compatible customer-facing change is a MINOR release. No ADR or RFC is required because no business object, API contract, backend architecture, authentication model, or persistence design changes. No migration, backend restart, or environment change is required. The frontend must be rebuilt and later deployed immutably; deployment is not authorized by this record.

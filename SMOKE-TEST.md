# Forwarder 1.9.0 smoke test

## Platform and security

- HTTPS root and same-origin API succeed; external HTTP redirects to HTTPS.
- `/api/health/ping`, `/api/health`, and `/api/health/ready` return the approved
  healthy responses with revision `20260818_immutable_fx_provenance`.
- Release-local Python imports `psycopg2-binary 2.9.11`.
- Unauthenticated protected routes return 401 and cross-tenant reads remain 404.
- HTML is no-store/revalidate; hashed assets are immutable; manifest/icons
  revalidate; API routing precedes SPA fallback.

## Integrated application

- Existing request, Project, Shipment, and document reads remain available.
- Operational Execution initialization, milestones, events, delays, exceptions,
  progress, and work queue use opaque Shipment identity.
- MDPM requirements, exact document versions, assessments, applicability,
  overrides, and readiness render without fabricating historical rows.
- OIP situations, attention state, history, policies, and projection health are
  deterministic; absence of initialization is reported truthfully.
- Shipment Economics lines/observations, evidence, projections, and immutable FX
  provenance render; incomplete historical coverage abstains rather than
  inventing values.

## Initialization boundary

- Basic health passes without Seed/catalog apply.
- Reference Data and OIP policies/thresholds remain administrator-managed and
  are changed only under separate authorization.
- Existing shipments receive no automatic Operational Execution, MDPM, OIP, or
  Economics rows.
- Confirm manifest-named JS/CSS assets; version 1.9.0 is embedded but is not
  visibly rendered in the UI.

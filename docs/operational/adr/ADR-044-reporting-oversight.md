# ADR-044: Reporting Oversight Companion to ADR-043

- Status: ACCEPTED
- Date: 2026-09-02
- Companion to: ADR-043 and ADR-042

## Decision

`ORGANIZATION_ADMIN` may view the management dashboard, report overview,
assignment summary, and XLSX export only for the one active organization
resolved by the server from `OperationalMembership`. A client-supplied
organization identifier is rejected for this authority.

`PLATFORM_ADMIN` may view platform-wide reporting and may narrow it with the
validated `organization_public_id` query parameter. This authority does not
create an operational membership. Unknown or inactive organization identifiers
fail explicitly and never fall back to platform-wide output.

`EXPERT` and every unknown or unauthorized authority are denied management
reporting. No role hierarchy or frontend visibility grants reporting access.

## Rationale and invariants

Organization management needs tenant-fenced oversight, while platform
administration requires explicitly authorized global aggregation. Server-side
authority and tenant resolution are mandatory; URL, body, and frontend state
are not authority evidence. A reporting failure is not zero statistics: the
client must distinguish loading, successful empty data, successful data, and
failure.

## Deferred work and verification

No delegated Expert reporting, new reporting personas, break-glass support
flow, or broad RBAC redesign is authorized. Verification must prove tenant
isolation, Platform Admin filtering, Expert denial, valid empty responses,
accurate aggregation, and that query failures are rendered as errors.

# ADR-070 — System/Organization Admin separation and portable reference baseline

- **Status:** ACCEPTED — current-release Product authority
- **Date:** 2026-09-27
- **Owners:** Product Owner; Architecture/Security for authority boundaries; System Admin for system definitions; Organization Admin for tenant availability and configuration
- **Extends:** ADR-021, ADR-025, ADR-028, ADR-041, ADR-042, ADR-054, ADR-056
- **Mission authority:** [Admin/System Foundations Hardening](../../product/phase3/ADMIN-SYSTEM-FOUNDATIONS-HARDENING-MISSION-AUTHORITY.md)

## Context

The Human Walkthrough exposed four connected defects: the user-facing System
Admin and Organization Admin responsibilities were not explicit enough for a
self-hosted installation; the approved reference baseline was not portable as
one Product-owned versioned package; operational-reason and SLA administration
still exposed technical/free-text semantic inputs; and Organization Admin
logistics commands were blocked by a permission mismatch.

The existing schema already provides distinct system authority, tenant
membership, explicit reference tables and activation rows, reason models, SLA
process codes, logistics adoption/private-point models, versioning, history and
audit. No schema change is needed.

## Decision

### Separate capabilities, explicit composition

`SYSTEM_ADMIN` is the Product term for the compatible internal
`PLATFORM_ADMIN` authority. It governs system definitions and never implies a
tenant. Organization administration requires exactly one active membership.
Legacy `ORGANIZATION_ADMIN` remains compatible. A self-hosted Super Admin is
composed only by an explicit operator command that gives a System Admin one
same-organization membership carrying `organization.admin`; the transition is
idempotent and audited. No tenant selector or impersonation capability exists.

The dual-capability actor can use system configuration and its own organization
configuration. It does not become a Transport Expert and does not bypass
fixed-owner operational commands.

### DN08 and reference ownership

For the current release:

- `ORG_ADMIN_ARBITRARY_BASE_DEFINITION=NO`;
- `SYSTEM_ADMIN_BASE_DEFINITION=YES`;
- `AUTO_PROMOTION=NO`.

Organization Admin activates/deactivates approved system definitions. Expert
consumes active definitions. Organization-owned concepts remain in their
bounded models: Cargo Catalog/SKU, private Logistics Point, Operational Reason,
and tenant policy. This current decision supersedes only the earlier open DN08
possibility of organization-created base definitions; it does not rewrite old
evidence.

### Portable Product-owned baseline

`FORWARDER_REFERENCE_CATALOG_V1`, version `1`, is the source-controlled
composition of the frozen P3-01 base catalog and approved additive millimetre,
Packaging, Transport Means, Equipment/Load Unit and existing Request Transport
Method definitions. Stable codes are authoritative. The file contains Persian
Product presentation copy without overwriting already-persisted compatible
descriptions.

Catalog execution is explicit and checksum-pinned:

1. plan performs validation and comparison with no writes;
2. apply requires confirmation, named operator, approval reference and the
   reviewed checksum;
3. same-code semantic drift, duplicate title under another code, or an
   intentionally inactive existing definition fails closed;
4. catalog apply is additive and idempotent, with no deletion, reactivation, or
   startup side effect.

`FORWARDER_STANDARD_ORG_PROFILE_V1` references only stable catalog codes. It
activates the approved baseline for one explicitly named organization by a
same-tenant Organization Admin. It does not include SKU, private point, reason,
SLA, document, route-time or closure configuration. An intentionally inactive
activation is a distinct plan item rather than a silent reactivation; apply
refuses it without explicit reactivation confirmation.

### Operational reasons and SLA targets

Operational-reason family semantics remain system-defined while each
organization manages its reasons. Persian title is required; English name is
optional; the server generates an immutable UUID-backed `DLR_…` or `EXR_…`
code. Deactivation preserves used history.

SLA semantic targets are code-governed. The current registry exposes only
`EXCEPTION_RESPONSE` and `ACTION_FOLLOW_UP`, each with deterministic read-only
start/end facts. Organization Admin selects a target and configures duration,
warning, active state and an optional presentation-only alias. No arbitrary
semantic name, start/end selector, generic rule engine or fake event is added.
Current route/milestone models do not establish an additional generic target
with one unambiguous start and end, so such targets remain
`SLA_TARGET_NOT_CURRENTLY_SUPPORTED`.

### Logistics authority

System Admin continues to manage global/reference logistics definitions and
system point types. Organization Admin can search/adopt a permitted global
point and manage its organization-private points. Tenant scope is always
server-derived. System-only authority has no private tenant point access;
foreign tenant access and promotion of a private point remain denied.

## Compatibility, migration and rollback

There is no role rename and no schema migration. Existing authority values,
stable codes, historical activations, reasons, SLA rules, snapshots and
business records remain readable. The sole Alembic head remains
`20261012_phase3_cargo_eta`.

Application rollback removes the new capability projection, catalog/profile
operator flows and Persian presentation while retaining all compatible rows.
Catalog/profile writes are additive and can be deactivated only through their
existing governed lifecycle; they are never hard-deleted by rollback.

## Validation and release boundary

Qualification must prove the role matrix, negative tenant cases, catalog and
profile plan/apply/idempotency/conflict protection, PostgreSQL 18 behavior,
affected browser journeys, full backend/frontend regressions, and FWD-J01..J09
plus FWD-IPJ-01..04 on the frozen Product SHA. Human Walkthrough remains
`IN_PROGRESS` and Release Ready remains `NO`. Production access, migration,
deployment and release are not authorized.

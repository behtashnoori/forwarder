# ADR-062 — Explicit Portal Account to CRM Customer entitlement

Status: ACCEPTED within the explicit DN10 decision and delegated relational
design in the Product Owner's five-stage mission §§3–16, dated 2026-09-25.
Rigor C / LPAF v2.7. This is no approval of owner transfer, public tracking,
P3-09 full projection, Release or human walkthrough.

## Decision and authority

The Product Owner explicitly approved a separately granted and revocable
many-to-many relationship and delegated its minimal relational representation.
`CustomerEntitlement` owns that authorization fact. Portal `CustomerGamification`
and CRM `Customer` remain independent identities and SORs. Only an active
Organization Admin with active same-organization membership may inspect,
grant or revoke. The command service rechecks this authority, and database
composite foreign keys bind account and CRM customer to the recorded tenant.
Platform Admin, Expert and Customer receive no entitlement management grant.

Each grant records tenant, portal account, CRM customer, granting actor and UTC
time. Revocation records its actor/time on that grant. Regrant creates a new
row: no deletion or reuse of a historical grant. A partial unique index permits
one current grant per relationship. Account-row locking serializes commands;
a unique organization/command key provides retry safety. An old grant replay
returns that grant even after revocation; an old revoke cannot affect a regrant.
Inactive/unowned targets are rejected. Disabled targets may still be revoked.

## Capability and lifecycle chain

Business purpose: an Org Admin explicitly authorizes a customer account to
represent a CRM customer. Producer: Admin's visible access tab. Command owner
and SOR: customer entitlement service and relational grant. Persistence:
single database transaction, same-tenant constraints and current uniqueness.
Consumer: current authorized-customer SQL subquery used by P3-06 Cargo document
policy; P3-09 may consume it later. Transformation: live grants intersect active
tenant/account/CRM state; document context then intersects Cargo ownership,
tenant, current exact version and visibility. No grant is a file permission,
write permission, full Shipment permission, or authorization snapshot.

List authorization occurs in SQL before pagination. Download uses the same
predicate and private-storage parent/version checks. Responses are no-store;
the document page re-reads after focus, return, pageshow and page changes, and
clears stale rows while loading or on failure. Explicit sharing remains an
independent selected-account rule, with no automatic sharing to Cargo owners.

## Compatibility and supersession

Grant/revoke timestamps are UTC Instants (`timestamptz` on PostgreSQL), emitted
as RFC 3339 with `Z`, including SQLite's known UTC timezone-stripping behavior.
The Admin surface uses the existing dual-calendar Instant formatter; no new
calendar, business-time policy, local-naive assumption or timezone migration.

This resolves only ADR-061's DN10 dependency and its fail-closed own-Cargo
boundary. ADR-061 remains unchanged as historical decision evidence. No
Request pairing, name, email, phone, Shipment membership or Cargo source is
entitlement. Migration backfill is deliberately absent. Existing Request and
account journeys, public tracking, owner commands and Admin oversight remain.

Replacement versions must begin INTERNAL, as already recorded by ADR-061.
DN10 tests exposed a direct-command gap in that rule. Non-internal replacement
payloads are now rejected; their exact visibility can be granted by a separate
authorized command. Replacement identity participates in retry fingerprinting.

## Migration and verification

Additive `20261006_customer_entitlement` follows unchanged
`20261005_phase3_contextual_documents`. Empty downgrade/re-upgrade is supported;
populated downgrade refuses to erase authorization history. No production
migration, historical migration edit, inferred backfill or Alembic branch.
Required proof: no-inference legacy migration, PostgreSQL 18 tenant constraints,
concurrent grant/revoke and replay, multi-account/multi-CRM grants, current
revocation, exact-version A/B document isolation, normal Admin→Expert→Customer
Chrome journey, mobile return/reopen, and full affected regressions.

Global Product validation remains EVIDENCE_PENDING. Integrated Product Journeys
and Human Product Walkthrough remain separately NOT_RUN; this is a slice gate.

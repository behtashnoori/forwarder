# ADR-073: Governed Platform Maintenance Admin Provisioning

- Status: ACCEPTED
- Date: 2026-09-29
- Owners / decision authority: Product Owner; Architecture and Security authority
  through the accepted ADR-042/ADR-070 boundaries
- Affected domain: account identity, canonical authority, tenant membership,
  operational audit, bootstrap operations
- Approval reference: `PLATFORM-ADMIN-BOOTSTRAP-MISSION-AUTHORITY.md`

## Context

The Product has canonical `PLATFORM_ADMIN` authority and an explicit audited
command that composes tenant administration for an already-existing System
Admin. It has no governed atomic path for creating the dedicated first
maintenance actor. Combining unaudited user creation with later promotion does
not provide authoritative creation, authority, and membership evidence.

## Decision

Add the CLI-only `provision-platform-maintenance-admin` command. Its trust root
is the established self-hosted offline-operator pattern: explicit command
possession, `--confirm`, a bounded named operator, a bounded Product approval
reference, and a password supplied through the dedicated process environment
value rather than a command-line argument. The command is never exposed over
HTTP and never runs at startup. It does not require a pre-existing Product
administrator, avoiding a circular first-admin requirement.

The command accepts an explicit username, full name, active organization public
ID, operator, and approval reference. In one database transaction it locks the
organization, refuses an inactive or missing organization, refuses every
pre-existing username, creates one active legacy-compatible account with
canonical `PLATFORM_ADMIN` authority, creates exactly one active membership
containing only `organization.admin`, records three audit facts, and records one
idempotency mapping. It grants no Expert assignment or operational ownership.

The deterministic idempotency identity is organization plus normalized
username. The request hash binds every non-secret governed input. Password
equivalence is checked with the stored bcrypt verifier; the password is never
written to audit, idempotency evidence, or output. A complete exact retry
returns `UNCHANGED`. Any mismatched identity, authority, membership, approval,
operator, audit, or ledger evidence fails explicitly. Locking the organization
serializes concurrent first creation on PostgreSQL so simultaneous equivalent
commands return one `CHANGED` and one `UNCHANGED`.

The existing models are sufficient. No migration, outbox event, UI, API, bulk
mode, automatic startup hook, existing-user promotion, or authority-policy
change is introduced.

## Audit contract

The transaction writes exactly these Product audit actions:

1. `platform_maintenance_admin.actor_created`;
2. `platform_maintenance_admin.authority_assigned`;
3. `platform_maintenance_admin.membership_assigned`.

Every row carries the target actor ID/username, `PLATFORM_ADMIN`, organization
public ID, membership ID, named operator, approval reference, resulting active
state, a specific governance-fact label, and the shared action time in
`recorded_at`.

## Consequences and verification

- Existing identities can never be silently elevated or repurposed.
- Platform authority and the explicit single tenant membership remain separate;
  `effective_authority()` and ordinary ownership rules are unchanged.
- A missing confirmation, password, operator, approval reference, active
  organization, complete audit set, or idempotency evidence fails closed.
- Verification covers success, all three audits, exact tenant membership,
  inactive organization, exact retry, identity/authority/membership conflicts,
  malformed approval, bootstrap-trust refusal, rollback, unrelated-data
  preservation, and PostgreSQL 18 concurrency.
- `JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY` for `FWD-J06`, `FWD-J08`, and
  `FWD-IPJ-03`; no UI surface or Release Ready claim is added.

# Platform Maintenance Admin Bootstrap Mission Authority

Local date: 2026-09-29, Asia/Tehran. Governed canonical repository:
`D:\1-webapp\15-forwarder-golden-20260921`. Isolated worktree:
`D:\1-webapp\forwarder-dev\platform-admin-bootstrap`.

This record captures the Product authority supplied by the Product Owner for
the “Resolve LPAF Baseline and Close Platform Admin Bootstrap Gap” mission. It
does not authorize Production access, deployment, release, Cargo repair APPLY,
or mutation of preserved walkthrough business data.

## Entry evidence and mission contract

- Outcome: prove the controlling LPAF baseline, add one governed mechanism for
  provisioning a dedicated maintenance System Admin, qualify it, integrate it
  through the canonical process, provision the named walkthrough actor, and
  rerun Cargo Continuity Repair PLAN only.
- Problem: no Product-owned command atomically creates the dedicated actor,
  canonical authority, exact tenant membership, audit facts, and idempotency
  evidence. The existing composition command requires a pre-existing user.
- Scope in: CLI-only provisioning service and command, audit/idempotency,
  concurrency and rollback proof, controlled non-Production walkthrough use.
- Scope out: UI/API, startup execution, mass provisioning, existing-user
  promotion, authority weakening, operational ownership, Cargo repair APPLY,
  Production, deployment, and release.
- Actors: authorized offline installation operator; newly provisioned dedicated
  maintenance System Admin; exact active target organization.
- Owner/authority: Product Owner issuing the attached mission dated 2026-09-29.
- Rigor/capability route: Level C / Sol because security authority,
  transactionality, PostgreSQL concurrency, controlled integration, and
  preserved-runtime evidence are coupled.
- Stop conditions: unresolved baseline authority, missing bootstrap trust root,
  schema need, authorization weakening, preservation failure, failed mandatory
  qualification, Production contact, or any proposed Cargo repair APPLY.
- Definition of Done: explicit transactional/idempotent provisioning, three
  durable audit facts, exact membership, deterministic concurrent replay,
  focused/PostgreSQL/governance/full-backend PASS, controlled integration,
  walkthrough provisioning proof, preservation proof, and PLAN-only result.

## Baseline resolution

`AUTHORITATIVE_LPAF_BASELINE=2.7`.

Normative precedence is established by the active v2.7 framework §1, the root
LPAF index, the v2.7 Baseline Acceptance record, the zero-mismatch 53-entry
v2.7 SHA-256 manifest, and tracked `AGENTS.md` at canonical SHA
`87471aedcf144c0ab635de74f77f1a02aa68b2da`. Those artifacts explicitly
supersede v2.6. The current task checkout's v2.6 instruction is stale project
context and cannot override the globally activated successor.

## Product Authority Record

| Field | Authority |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Add the smallest Product-owned explicit command that creates one new dedicated active `PLATFORM_ADMIN` maintenance actor, gives it exactly one active membership in the explicitly named active organization, records actor/authority/membership audit evidence, and returns deterministic `CHANGED`/`UNCHANGED`. After controlled integration, use it once for `walkthrough_platform_admin`, then rerun Cargo Continuity Repair PLAN only. |
| `DELEGATED_TECHNICAL_CHOICES` | Service/module placement, CLI syntax, password transport through a secret environment value, reuse of existing `ExpertUser`, `OperationalMembership`, `OperationalAudit`, and `OperationalIdempotency` stores, deterministic request hashing that excludes the password, organization-row locking, test/evidence layout, and exact internal action names. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | No existing-user elevation; no change to `effective_authority()`; no inferred tenant/actor; no extra membership; no Shipment/Request/Expert ownership; no Cargo/Shipment/Route/Execution mutation; no startup automation; no bulk provisioning; no raw SQL mutation; no UI; no schema migration; no Production access/mutation; no deployment/release; no Cargo repair APPLY; preserve all named walkthrough records and `walkthrough_admin=ORGANIZATION_ADMIN`. |
| `DECISIONS_NEEDED` | `NONE` after baseline and trust-root discovery. Stop if the existing confirmed offline-operator pattern proves insufficient or a schema/security-policy change becomes necessary. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing the explicit attached governance mission. |
| `APPROVAL_REFERENCE` | Attached `Pasted text.txt`, “GOVERNANCE MISSION — Resolve LPAF Baseline and Close Platform Admin Bootstrap Gap”, dated 2026-09-29. |

## Trust, data, journey, and reference impact

- Bootstrap trust is the established self-hosted pattern: possession of the
  offline Product command plus explicit confirmation, bounded named operator,
  bounded Product approval reference, and secret password supplied outside the
  command line. It does not require an already-existing `PLATFORM_ADMIN`.
- The target organization row is locked before identity inspection. The single
  physical transaction creates the user, membership, three audit facts, and
  idempotency record. Existing usernames always fail; they are never elevated.
- Data scopes: actor identity is platform/account master data; membership is
  organization master data; audit and idempotency are historical evidence.
- SOR: existing Product tables remain authoritative; no parallel store or
  schema change is introduced.
- `JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`: `FWD-J06`, `FWD-J08`, and
  `FWD-IPJ-03` because authority/membership and tenant isolation are affected.
  No UI behavior is added. This mission qualifies the command and authorization
  boundaries; Human Product Walkthrough remains `IN_PROGRESS` and Release Ready
  is not claimed.
- LPAF reference impact: `NONE`; this mission applies v2.7 without changing it.
- Project architecture impact: `UPDATE_REQUIRED`; ADR-073 records the new
  security, transaction, audit, and idempotency boundary.

## Entry disposition

```text
LPAF_BASELINE=2.7
GOVERNANCE_LEVEL=C
CAPABILITY_ROUTE=SOL
PRODUCT_AUTHORITY_RECONCILIATION=PASS
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J06,FWD-J08,FWD-IPJ-03
MIGRATION_REQUIRED=NO
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
RELEASE_READY=NO
PRODUCTION_UNTOUCHED=YES
```

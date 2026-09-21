# ADR-047 Fixed Operational Shipment Owner — Implementation Design

Date: 2026-09-21

Status: implementation-authorizing design for the separately approved P1
Customer Demo blocker closure

Starting canonical: `2cadaefef8e5d44163ac92a45dce5ac2cb769269`

Feature branch: `codex/adr047-fixed-shipment-owner-closure`

## 1. LPAF governance gate

The active governing baseline is LPAF v2.2 and its mandatory Agent Entry
Protocol. The reviewed v2.3 Product Integration and `REFERENCE_IMPACT` controls
are applied as the Forwarder strong default. LPAF v2.4 is not adopted and no
generic 29-LPAF framework file is in scope.

This is a Level B product/runtime change with elevated authorization, lineage,
migration, PostgreSQL, concurrency, and browser evidence because it changes the
authoritative root used by Shipment, Documents, and Control Tower access.

```text
REFERENCE_IMPACT=UPDATE_REQUIRED
```

ADR-047, ADR-050, PDR-019, and PDR-020 already state the required product
truth. No target behavior is being redefined. The update is limited to closing
the matching OPEN implementation row in the project Architecture Drift Report
after runtime qualification passes, while preserving the fact and evidence that
the drift existed.

## 2. Mission contract

### Mission and outcome

Close the single P1 blocker by making the one persisted
`OperationalShipment.primary_responsible_expert_id` authoritative for Direct
and accepted-Quote Operational Shipments. An accepted-Quote Shipment captures
the issuer of the exact accepted official Quote. Later Request assignment
changes affect only the Request and never transfer Shipment ownership, Shipment
access, Shipment Document management, tracking/event authority, or Expert
Control Tower population.

### Scope in

- accepted-Quote creation and exact Quote-issuer validation;
- Direct creation validation against the same owner contract;
- Shipment list/detail/command authorization;
- Shipment-owned Documents management through the existing fail-closed parent
  authorization;
- Control Tower Expert scope and responsible-Expert projection;
- deterministic legacy reconciliation and a non-null/write-once database
  invariant;
- focused, PostgreSQL, concurrency, full-regression, and integrated browser
  evidence;
- the one relevant Architecture Drift Report status/evidence cell.

### Scope out

- Shipment owner reassignment, transfer, replacement, handoff, former-owner
  access, ownership-history UI, or a public owner-mutation field;
- broader Admin, Manager, Platform Admin, Customer, or public authority;
- Request assignment behavior itself;
- Quote response/revision semantics, Cargo, Combined Transport, Dual Calendar,
  MT-3 public tracking, Notifications, modularization, deployment, Production,
  Product Acceptance Retry, or Customer Demo freeze.

### Facts, assumptions, unknowns, and decisions

- **FACT:** the canonical local and GitHub refs both equal `2cadaefef8e5d44163ac92a45dce5ac2cb769269`, ahead/behind is `0/0`, and the
  starting canonical worktree was clean.
- **FACT:** `ExpertQuote.created_by_expert_id` persists the exact official Quote
  issuer and `OperationalShipment.accepted_quote_id` uniquely identifies the
  accepted Quote used for Shipment creation.
- **FACT:** Direct creation already persists the responsibility field;
  accepted-Quote creation does not.
- **FACT:** general Shipment authorization and Control Tower still use mutable
  `ShipmentRequest.assigned_to` for accepted-Quote Shipments.
- **FACT:** Shipment Document management already uses the persisted Shipment
  owner and fails closed when it is null.
- **ASSUMPTION:** no Production row is safe to repair merely because a current
  Request assignee exists. The implementation never uses that value for repair.
- **UNKNOWN:** Production legacy-row contents are unknown and will not be
  inspected in this mission.
- **DECISION:** unknown Production history is handled by a deterministic,
  fail-closed migration. Unresolved nulls or contradictory persisted owners
  abort before the non-null invariant is applied.
- **DECISION NEEDED:** only an operator/data-owner adjudication outside this
  mission can resolve a row rejected by that migration. The migration will not
  choose an owner.

### Authority and stop conditions

This Goal authorizes product code, tests, a deterministic additive migration,
owned disposable PostgreSQL, project design/evidence/reference-status updates,
meaningful commits, and conditional fast-forward synchronization of the
canonical branch. It does not authorize Production access, deployment,
temporary-branch push, history rewrite, force push, Product Acceptance Retry,
or modularization. Any unresolvable conflict with ADR-047 or ambiguous data
that cannot be represented by a safe fail-closed migration stops PASS.

## 3. Capability, owner, SOR, and data chain

| Concern | Owner / System of Record | Contract |
| --- | --- | --- |
| Request commercial assignment | Request workflow / `ShipmentRequest.assigned_to` | Mutable Request-level concern only |
| Official Quote issuer | Pricing/Commercial / exact `ExpertQuote.created_by_expert_id` | Immutable lineage source for an accepted-Quote Shipment at creation |
| Shipment responsible Expert | Operations / `OperationalShipment.primary_responsible_expert_id` | Exactly one persisted fixed Transport Expert |
| Shipment authorization | Operations authorization boundary | Tenant first, then active actor/capability, then persisted Shipment owner or separately governed oversight |
| Shipment Documents mutation | Document service plus Shipment parent authority | Active owning Expert only; null owner fails closed |
| Control Tower | Governed read model over Shipment SOR | Authorization before search/windowing; owner projection from Shipment only |
| Historical reconciliation | Migration and retained persisted lineage | Exact accepted Quote only; no Request-assignee inference |

The applicable chain is:

```text
Customer accepts exact official Quote Q
-> Q.created_by_expert_id identifies issuer E
-> creation validates E, Q, Request, and Organization lineage
-> Shipment.primary_responsible_expert_id = E in the creation transaction
-> Shipment authorization / Documents / Control Tower consume that field
-> Request reassignment remains isolated to Request workflows
-> regression and browser evidence verify the whole chain
```

Shipment ownership is tenant-scoped transactional data and historical business
evidence. Quote issuer and accepted-Quote linkage are its authoritative
provenance. The owner is neither a projection nor current assignment state.

## 4. Creation contract

### Accepted-Quote Shipment

`create_from_accepted_quote` must lock and resolve the exact Quote identified by
`accepted_quote_id`; require `customer_response == accepted`; require Quote,
Request, Customer, and Shipment organization consistency; load the issuer from
`created_by_expert_id`; and require that issuer to be an active canonical
`EXPERT` with exactly one active membership in the same operational
organization. It then passes that issuer id into aggregate initialization before
flush/commit.

The current creator still needs its existing create capability and Request
authority. Creator identity is not substituted for the owner. Missing, inactive,
non-Expert, cross-tenant, or ambiguous issuer identity fails closed. Idempotent
replay returns only a Shipment still visible under current governed authority.

The Quote row is the owner source even if Request reassignment commits before,
during, or after creation. The creation transaction locks the Quote; Request
assignment cannot alter Quote issuer.

### Direct Shipment

Direct creation keeps its current explicit/default owner behavior but validates
the selected owner through the same active same-organization Transport Expert
validator. Admin/Manager/Platform identities cannot be persisted as the
responsible Expert. The owner is written in the creation transaction.

## 5. Authorization and owner immutability

For an active `EXPERT`, every Shipment action governed by ownership uses
`OperationalShipment.primary_responsible_expert_id`. The accepted-Quote
Request is lineage only and supplies no Shipment authority. Request list/read,
Quote issuance, and other pre-Shipment workflows continue to use Request
assignment.

Same-organization Admin/Manager keeps only the existing capability-based
oversight/action contract and is never recorded or projected as the owner.
Platform Admin remains denied tenant work authority. A same-organization peer,
foreign tenant, inactive/revoked owner, forged child id, stale response, or
guessed Shipment id remains denied.

Existing project-derived Shipment read is a distinct accepted read capability.
It does not confer ownership, Documents mutation, tracking mutation, or owner
projection. No public representation is expanded.

There is no owner mutation route. The database migration makes the owner
non-null and write-once: changing it after insert is rejected. The application
continues to re-read current actor and owner state on each authorization
decision; actor inactivity/revocation denies operation but does not rewrite the
historical owner.

## 6. Control Tower and Documents

Control Tower candidates for an Expert are selected by tenant, active Shipment
state, and persisted Shipment owner before search, attention evaluation,
ordering, counts, and windowing. Responsibility contexts always use the
Shipment as root and the persisted owner as responsible Expert. Admin/Manager
organization scope, signed opaque cursor, server-side search/filter, complete
global KPI, deterministic ordering, and bounded hydration are unchanged.

Shipment Documents retains ADR-050/PDR-020 behavior. The service already asks
the parent authorization boundary for `document.manage`; once creation persists
the owner, the original owner may manage, the new Request assignee may not, and
Admin/Manager remains read-only where existing oversight allows. Null-owner
fallback is not introduced.

Tracking/event and Execution Unit commands that use Shipment parent authority
inherit the corrected authorization root. MT-3 public tracking remains an
opaque SR2 capability and exposes no owner detail.

## 7. Schema and historical reconciliation

```text
FIXED_SHIPMENT_OWNER_SCHEMA_DECISION=ADDITIVE_MIGRATION_REQUIRED
```

The existing column is nullable and therefore cannot guarantee the approved
new-data invariant or fixed ownership independently of one service path. A
linear revision descending from `20260925_quote_communication` will:

1. classify every Shipment as Direct, accepted-Quote, or invalid/other from
   persisted `source_type` and lineage;
2. reject any already-owned accepted-Quote Shipment whose persisted owner
   contradicts the exact accepted Quote issuer;
3. repair a null accepted-Quote owner only when the exact
   `accepted_quote_id` resolves one accepted Quote whose Request id,
   organization, issuer identity, Expert authority, and same-organization
   membership are consistent;
4. never read `ShipmentRequest.assigned_to` as an owner candidate;
5. reject null Direct/other owners because creator or current assignment is not
   authoritative ownership evidence;
6. reject malformed, missing, foreign, ambiguous, or otherwise conflicting
   lineage with safe row identifiers only;
7. set the column `NOT NULL`; and
8. install a database write-once guard that rejects owner changes while
   permitting ordinary Shipment updates.

The reconciliation runs in the migration transaction, so a rejection leaves no
partial backfill or constraint change. H1 uniquely valid accepted-Quote null is
repaired; H2 ambiguous/missing lineage aborts without guessing; H3 valid Direct
owner is unchanged; H4 already-correct accepted-Quote owner is unchanged; H5
contradictory accepted-Quote owner aborts without rewrite.

Downgrade removes the write-once guard and relaxes nullability but retains all
owner evidence, including deterministic backfill. Re-upgrade must be safe. An
unresolved Production row therefore blocks migration for explicit adjudication;
unknown Production history is never claimed clean.

## 8. Concurrency contract

Owned PostgreSQL must prove actual overlapping transactions, not sequential
calls:

- accepted-Quote creation racing Request reassignment still records the exact
  Quote issuer;
- Request reassignment racing Shipment authorization does not transfer access;
- the next Control Tower query after reassignment retains the Shipment in the
  original owner's population only;
- Document mutation after reassignment remains allowed only for the persisted
  owner; and
- attempted concurrent owner mutation is rejected by the database guard.

Existing accepted-Quote uniqueness and idempotency locking continue to prevent
duplicate Shipment creation.

## 9. User journey and acceptance contract

Target roles are active Transport Expert owner E1, peer E2, Customer C, and
same-organization Admin/Manager. The normal journey starts in the existing
Request/Quote surfaces: E1 issues Q1, C accepts Q1, an authorized operational
actor creates S, and E1 opens S through normal Shipment navigation. After the
existing Request assignment workflow moves R to E2, E1 can still reopen S,
manage S Documents, and see S in owner-scoped Control Tower; E2 gains none of
those owner-derived capabilities. Admin/Manager oversight remains reachable and
read-only for Documents. Denied paths are non-disclosing. Representative RTL
desktop/mobile affected surfaces remain usable.

The browser run must use the real frontend/backend and owned disposable
PostgreSQL. Direct-route API proof alone is insufficient. There is no new UI or
owner selector because Product has approved no owner decision after creation.

## 10. Verification and Definition of Done

Qualification includes focused creation/authorization/Control Tower/Documents/
tracking tests; migration H1-H5 lifecycle on PostgreSQL 18; true concurrency;
representative >100 Control Tower population; Quote, Request Documents, Shipment
Documents, Cargo, Combined Transport, Dual Calendar, and MT-3 regressions; full
backend; full frontend, TypeScript, ESLint, and production build; integrated
browser journeys; release/source/package checks; one Alembic head; secret and
artifact safety; and exact clean source identity.

PASS requires all requested fixed-owner markers, the relevant drift entry
changed to RESOLVED with evidence, `REFERENCE_IMPACT_FINAL=UPDATE_REQUIRED`
with the required project reference update completed, and no unresolved
runtime/reference contradiction. Only then may canonical be fast-forwarded and
the annotated tag be created/pushed. The temporary branch is never pushed.

## 11. Remaining risk boundary

The migration is deliberately fail-closed for unknown Production history. A
future operator may have to adjudicate rejected legacy rows before deployment;
this design neither performs that deployment nor weakens the invariant. An
inactive owner remains historical truth and may require separately governed
operational continuity in the future, but no automatic transfer is introduced.

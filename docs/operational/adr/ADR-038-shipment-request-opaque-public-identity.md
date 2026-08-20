# ADR-038: ShipmentRequest Opaque Public Identity

- Status: ACCEPTED
- Date: 2026-08-20
- Owners: Architecture, Security, Commercial Request domain owner
- Affected domain: ShipmentRequest identity, authenticated APIs, tenant authorization

## Context

`ShipmentRequest` currently has a sequential integer primary key and a nullable unique `tracking_code`, but no authenticated opaque API identity. Numeric IDs remain necessary for database primary and foreign keys, yet are enumerable and cannot be the identity of new public API contracts.

`tracking_code` is a different identity. It is deliberately customer-facing and used by public tracking. Existing rows include deterministic `SR000001`-style backfills and compatibility fallbacks, while newer values have a short random suffix. Reusing it for authenticated routing would conflate public tracking with internal request identity and would not give all rows a consistently non-enumerable contract.

Accepted ADR-037 requires an authenticated, request-parented customer-context endpoint that accepts neither numeric request IDs nor customer IDs. A separate stable request identity is therefore required before ADR-037 implementation can proceed.

The repository convention for opaque identities is UUID v4 serialized into a `String(36)` `public_id` column with uniqueness and application-side generation. This decision extends that convention to the legacy-compatible `ShipmentRequest` aggregate without replacing its primary key or tracking contract.

## Decision

Add an immutable `ShipmentRequest.public_id` containing a canonical lowercase hyphenated UUID v4 string. It is the opaque identity for authenticated/internal request navigation and request-parented APIs.

It supports:

- authenticated request-detail navigation;
- request-parented expert/internal APIs, including ADR-037;
- stable opaque routing across renames, assignment, status, and tenant-safe lifecycle changes;
- non-enumerable external request references where an authenticated contract explicitly adopts it.

It is not a tracking code, shipment number, commercial request number, external integration reference, tenant identifier, authorization token, database primary key, or replacement for numeric foreign keys.

Possession of `public_id` grants zero authority. Every lookup still requires trusted tenant context, ownership/quarantine fencing, and action-specific request authorization.

### Identifier type

Use UUID v4 rather than UUID v7, ULID, or a new scheme.

- UUID v4 provides approximately 122 random bits, strong enumeration resistance, mature collision behavior, and no embedded tenant, business, or creation-time semantics.
- UUID v7 and ULID encode sortable time and would introduce a new repository convention plus unnecessary creation-time leakage.
- Canonical lowercase hyphenated text is simple to validate and matches existing `String(36)` public IDs.
- PostgreSQL native `uuid` is technically valid, but selecting it only for this legacy aggregate would diverge from current cross-database models and migration/test conventions without a demonstrated storage or performance need.

### Schema contract

The final model contract is:

```text
ShipmentRequest
  id         BIGINT/VARCHAR-compatible existing primary key; unchanged
  public_id  VARCHAR(36), NOT NULL, globally UNIQUE, immutable
```

- ORM generation uses `default=lambda: str(uuid4())`; clients never supply the value.
- Store only canonical lowercase hyphenated UUID v4 text. Service and migration tests validate UUID version, canonical rendering, and uniqueness.
- A named global unique constraint or unique index enforces collision defense. Global uniqueness avoids tenant ambiguity and matches repository public-ID conventions.
- The unique structure is also the lookup index. Do not add a redundant second single-column index.
- Tenant lookups filter `operational_organization_id`, `ownership_scope`, and `public_id`. A later measured performance review may add a composite tenant/public-ID index only if query evidence requires it.
- Final `NOT NULL` prevents any completed-rollout creation path from silently omitting identity.
- No request API accepts `public_id` in create or update payloads, and generic mass assignment must exclude it.

### Two-phase additive migration and rollout

Implementation uses two additive migrations separated by compatible application deployment and certification. Both extend the current sole Alembic head; implementation must resolve the actual head at that time.

**Expand migration:**

1. Add nullable `shipment_request.public_id` as `String(36)` with no client-controlled or deterministic server default.
2. Backfill every null row with Python `uuid.uuid4()` values inside the explicitly executed Alembic migration. Never derive values from `id`, `tracking_code`, organization, timestamps, names, or hashes of business data.
3. Update only rows whose `public_id IS NULL`. On retry/reconciliation, preserve already assigned values.
4. Handle the theoretical collision by generating another UUID before update; the migration verifies canonical UUID v4 form, no nulls, and no duplicates before adding the uniqueness structure.
5. Add the named global unique constraint/index while the column remains nullable for N/N-1 application compatibility.

**Compatible application deployment:**

6. Add the ORM UUID v4 default, creation-path tests, immutability guard, tenant-fenced resolver, and compatibility reads. Old application versions remain valid while the database column is nullable.
7. Inventory and exercise standard public intake, imports, admin/system creation, test factories, scripts, and compatibility creation paths. New code must generate the identity internally and must never accept it from a client.
8. Observe and certify that no new nulls are created. Any direct SQL/import path without identity generation fails the completion gate and must be corrected or explicitly retired.

**Contract migration:**

9. Lock/bound writes as required by the migration plan, backfill any remaining null stragglers with fresh UUID v4 values, and repeat null/duplicate/canonical-form verification.
10. Alter `public_id` to `NOT NULL` while retaining the unique constraint/index. The database then rejects uncaught legacy writers instead of silently manufacturing an identity.

Backfill is transactional for the supported PostgreSQL migration path. For a large table, implementation may use bounded batches with persisted progress, but each row's assigned identity must be durable and retry-stable. SQLite test compatibility may use batch-alter mechanics; it must preserve equivalent uniqueness and non-null final behavior. No database extension such as `pgcrypto` is required.

### Creation and immutability

Every new request receives `public_id` from trusted application code before persistence. This applies to public intake, admin/system commands, imports, bootstrap/test factories, referral-related creation, and legacy compatibility paths. The final `NOT NULL` constraint is defense in depth and intentionally fails any missed path.

After initial insertion, identity never changes:

- serializers expose it only on explicitly adopted authenticated response contracts and never accept it on writes;
- create/update services reject or ignore client attempts according to the endpoint's stable validation policy, but never persist the supplied value;
- a SQLAlchemy attribute-history guard rejects ordinary ORM mutation of a persisted row;
- focused tests cover API mass assignment and direct ordinary ORM mutation;
- no database trigger is required initially because schema uniqueness/non-null plus application immutability guards match repository practice. Bulk SQL remains a privileged operational concern and is outside ordinary product authority.

If correction is ever required because of proven corruption, it needs a separately authorized, audited remediation command; routine regeneration is forbidden.

### Tenant-fenced resolution and non-enumeration

Canonical authenticated resolution applies predicates before serialization:

```text
trusted organization_id
AND ownership_scope = TENANT
AND operational_organization_id = trusted organization_id
AND public_id = canonical supplied UUID v4
```

The resolved row then passes the canonical action-specific request authorization policy, such as current-assignee request view for ADR-037. Platform authority, organization membership alone, a remembered URL, or global uniqueness does not bypass authorization. Intake and legacy-quarantined rows are unavailable to ordinary tenant product resolution.

Malformed UUID, nonexistent ID, foreign-tenant ID, quarantined/ambiguous request, and unauthorized same-tenant request return the same externally non-enumerating not-found behavior wherever the consuming ADR requires non-enumeration. Parsing must fail without falling back to numeric ID or `tracking_code`. A service may internally classify outcomes for privacy-safe metrics without returning existence or tenant distinctions.

Do not implement a product flow that globally resolves `public_id` and then reveals its tenant. A tightly encapsulated internal query may rely on global uniqueness only when it immediately applies trusted tenant and authorization checks and exposes indistinguishable failures; tenant-first query semantics remain preferred.

### Tracking and compatibility boundary

`tracking_code` remains the public/customer-facing tracking identity and current compatibility contract. This ADR does not change its generation, backfill, URLs, lifecycle, or security semantics. Values are never copied between `tracking_code` and `public_id`, and an API expecting one never silently accepts the other.

Existing numeric authenticated routes may remain temporarily where already authorized. They are not made safe by this ADR and are not automatically removed or broadened. New request APIs prefer `public_id`; migration of existing routes is incremental, consumer-inventoried, tested, and separately controlled. Database relationships continue using numeric foreign keys.

### Threat model

| Threat | Required protection |
| --- | --- |
| Attacker guesses a public ID | UUID v4 entropy plus tenant/action authorization; non-enumerating failure. |
| Public ID leaks or former expert retains URL | Possession grants nothing; every read re-evaluates current membership, tenant, assignment, and action policy. |
| Cross-tenant public ID supplied | Tenant-first lookup cannot return it; same not-found behavior. |
| User changes organization context | Only trusted active membership context applies; client organization input cannot broaden access. |
| Numeric legacy route remains | Compatibility authority remains unchanged and separately tracked for migration/remediation. |
| Tracking code used as public ID | Strict canonical UUID v4 parser rejects it with no fallback. |
| Duplicate generation | Global database uniqueness plus retry on pre-persistence collision; migration verifies no duplicates. |
| Partial backfill | Nullable expand phase, null-only retry-safe generation, verification gates, then final contract migration. |
| Client supplies or mutates identity | Write allowlists, service/model guard, and final constraints prevent adoption or mutation. |
| Identity reveals tenant/time/business facts | UUID v4 embeds none; responses omit tenant metadata. |

### Observability and audit

Ordinary identity creation needs no separate domain audit event; it is infrastructure metadata created with the request. Existing request-creation audit remains authoritative.

Authorization failures may emit bounded security metrics for malformed, unavailable, and denied outcomes, but logs do not record raw `public_id`, tracking code, customer data, tenant identifiers, or existence distinctions. If correlation is operationally required, use the request correlation ID or an approved keyed/redacted fingerprint with defined retention, never the raw identity by default.

## Consequences

Authenticated request APIs gain a stable opaque route identity consistent with the repository, enabling ADR-037 without exposing numeric IDs or overloading public tracking. Costs include one new immutable field, secure backfill, two migration gates, creation-path inventory, route adapters, and negative authorization tests. UUID v4 randomness sacrifices index locality, but the request-detail access pattern is point lookup and the repository already accepts this tradeoff for public identities.

## Compatibility

The integer primary key, all numeric foreign keys, tracking code, public tracking, existing numeric routes, request ownership, assignment, audit, and business semantics remain unchanged. The expand phase supports N/N-1 application compatibility. No existing response automatically gains `public_id`; each consumer must explicitly adopt it and retain its own authorization contract.

## Rollback

- Before any runtime/API adoption, application code and the expand migration may be rolled back; dropping the unused column is permitted only after proving no consumer stores or references it.
- After any authenticated API or client adopts `public_id`, rollback disables new routes but preserves the column, values, uniqueness, and readable compatibility. Dropping or regenerating identities is prohibited because URLs/references may exist.
- Contract migration downgrade from `NOT NULL` to nullable is allowed only for a tested N/N-1 rollback and must not clear values or remove uniqueness.
- Re-upgrade reuses existing identities. It never regenerates them.

## Authorized implementation boundary and adoption order

This acceptance authorizes a later controlled implementation to:

1. create the nullable expand migration from the then-current sole head, securely backfill, verify, and add global uniqueness;
2. add `ShipmentRequest.public_id` UUID v4 generation and immutability enforcement;
3. add a tenant-fenced canonical public-ID resolver and non-enumerating tests;
4. update all request creation paths and factories, with PostgreSQL and SQLite migration evidence;
5. run N/N-1 compatibility and null-creation certification;
6. create the final `NOT NULL` contract migration only after that evidence;
7. then resume ADR-037 using `public_id` as the request route identity.

It does not authorize changing tracking codes, replacing numeric primary/foreign keys, globally migrating all numeric routes, changing request authorization, implementing CRM access in the identity slice, production migration, deployment, release, or push.

## Validation required for implementation

- UUID v4 canonical form, entropy source, global uniqueness, automatic creation, immutability, and client-input rejection tests.
- Backfill proves every legacy/intake/tenant/quarantined row receives a random identity without deriving business or tenant facts.
- Expand/contract upgrade, downgrade, re-upgrade, retry, duplicate/null verification, sole-head, PostgreSQL, and SQLite evidence.
- Tenant-negative and non-enumeration tests for malformed, missing, foreign, quarantined, same-tenant unauthorized, former-assignee, inactive-membership, and multi-membership cases.
- Existing tracking and numeric-route compatibility tests remain unchanged.
- Architecture governance, `git diff --check`, and changed-scope secret scan pass.

## Alternatives rejected

- Reuse `tracking_code`: rejected because it is public-facing, semantically distinct, inconsistently non-enumerable, and includes deterministic legacy/fallback values.
- Expose numeric `id`: rejected because it is enumerable and violates the baseline/ADR-037 public API contract.
- UUID v7 or ULID: rejected because they introduce a new convention and expose ordering/time information without need.
- PostgreSQL native `uuid`: deferred because `String(36)` matches current ORM, SQLite, migration, and serialization conventions.
- Deterministic UUID/name-based backfill: rejected because it risks inference/correlation and violates the random opaque requirement.
- Database trigger: rejected as unnecessary complexity for ordinary creation/immutability; final constraints and application guards fail closed.
- Big-bang numeric route replacement: rejected as an avoidable compatibility break.

## Supersedes / superseded by

- Supersedes: none
- Superseded by: none

## Status history

- 2026-08-20: ACCEPTED — bounded authenticated ShipmentRequest UUID v4 identity, additive rollout, tenant-fenced resolution, and compatibility contract approved; implementation pending.

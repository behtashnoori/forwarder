# Phase C1 — Inactive Channel-Neutral Notification Foundation

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/phase-b7-private-point-selector-reachability` |
| Slice branch | `codex/phase-c1-notification-foundation` |
| Starting HEAD / B7 commit | `b783052beead6fb5fb69fc34f796991208737b15` |
| Required parent / B6 commit | `b623f7fa7135caac69798def574556140f78191f` |
| Starting worktree | clean |
| Phase A commit | `953a67ff5820864c08bc8727f34f49ed66237527` |
| B1 geography commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| B2 numeric commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| B3 transport-summary commit | `d1dd6b60abc27846d563816c34b9aa4de190161a` |
| B4 count/list commit | `02acad646e2349296653bf0cf0bc5fe38519fb98` |
| B5 EUR commit | `49e2ceecee6b6ddbead7ae735fe15ecb63ed4869` |
| B6 retired-tracking-action commit | `b623f7fa7135caac69798def574556140f78191f` |
| B7 private-point commit | `b783052beead6fb5fb69fc34f796991208737b15` |
| Previous database head | `20260921_shipment_evidence_ownership` |

The controlled integration plan, Phase A Markdown/JSON freeze evidence, B7 report, and the B1-B6 evidence needed for regression selection were present. The starting repository had one base, one head, 97 revisions, the exact required HEAD and parent, and no worktree changes. The C1 branch was created directly from B7. Neither donor repository was changed.

## B. Existing Notification Architecture

- `OperationalOutbox` is the existing tenant-owned transactional business-event boundary. Domain services already record operational facts there. C1 preserves its producers, publication meaning, payloads, and transaction boundaries.
- `ExpertConsoleNotification` is the existing in-app Expert attention/inbox record. Assignment, referral, quote, and Expert Console services continue to create/read/mark those rows under their existing contract.
- `ExpertConsoleMessage` is an existing request/Expert messaging record, not an external-delivery queue.
- No pre-C1 general external notification action or delivery-attempt model existed in Golden.

The new foundation does not replace, migrate, consume, project, or reinterpret any existing inbox/message/outbox row.

## C. FWD-01 Donor Analysis

Read-only donor authority:

- repository: `D:\1-webapp\forwarder-dev`;
- branch line: `feature/fwd-01-notification-foundation`;
- commit: `d7cbedf9ec7416b83aeb6313aa095462a20e441d`;
- subject: `feat(notifications): add durable governed fake-email action foundation`.

Files directly inspected:

- `backend/notification_models.py`;
- `backend/migrations/versions/20260916_fwd01_notifications.py`;
- `backend/tests/test_fwd01_notifications.py`;
- `backend/tests/test_fwd01_migration_postgresql.py`;
- the complete donor commit file inventory.

Channel-neutral concepts reimplemented against Golden:

- tenant-owned action and attempt records;
- composite same-tenant action/attempt fencing;
- opaque identities and idempotency;
- infrastructure lifecycle states, including attempt `UNKNOWN` for future reconciliation;
- positive, unique attempt numbering;
- provider/result audit fields and protected audit deletion;
- populated-downgrade refusal.

Rejected donor behavior:

- fixed `EMAIL` channel;
- required fake-email provider and provider reference;
- quote event consumer and quote-specific policy;
- automatic recipient lookup and verified-email assumptions;
- provider adapter, provider calls, credentials, CLI, worker, retries, leases, and scheduling;
- quote/request status coupling;
- donor outbox event uniqueness and donor migration revision/topology.

No merge or cherry-pick occurred. The donor revision was not copied or registered.

## D. Final Foundation Model

`NotificationAction` is one tenant-owned durable statement that notification work may exist. It has:

- internal numeric identity and opaque `public_id`;
- mandatory `organization_id`;
- optional, tenant-fenced `source_event_id` to an existing `OperationalOutbox` row;
- mandatory per-tenant `idempotency_key` and optional `correlation_key`;
- a neutral `purpose` string;
- infrastructure-only status: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, or `CANCELLED`;
- nullable `recipient_reference` and `channel`;
- created/updated audit timestamps.

`NotificationAttempt` is one tenant-owned future delivery-attempt audit row. It has:

- internal and opaque identities;
- a composite same-tenant foreign key to `NotificationAction`;
- positive, per-action unique `attempt_number`;
- infrastructure-only status: `PENDING`, `IN_PROGRESS`, `SUCCEEDED`, `FAILED`, or `UNKNOWN`;
- nullable channel/provider/provider-reference/result/failure fields;
- attempted/completed/delivered timestamps plus created/updated audit timestamps.

Action deletion is restricted while attempts exist. There is no delete cascade that can erase delivery audit accidentally. A migration downgrade refuses to remove populated foundation history.

## E. Channel Neutrality

Both action and attempt channel fields are nullable. Attempt provider is nullable. Neither model nor migration has a channel/provider server default, and model tests prove newly created rows leave all of them `NULL`.

```text
DEFAULT_CHANNEL_SELECTED=NO
DEFAULT_PROVIDER_SELECTED=NO
```

## F. Recipient Neutrality

The action has only a nullable neutral `recipient_reference`; no phone, email, customer, Expert, preference, consent, locale, or fallback inference exists. No service populates it.

```text
RECIPIENT_POLICY_IMPLEMENTED=NO
RECIPIENT_INFERENCE_IMPLEMENTED=NO
```

## G. OperationalOutbox Boundary

C1 adds only a redundant composite uniqueness contract on `(operational_outbox.id, organization_id)` so an explicitly supplied future source-event relationship can be physically tenant-fenced. The primary key already made `id` unique, so this does not change event identity or producer semantics.

No outbox query, producer, consumer, publication flag, hook, service, worker, or transaction boundary changed. A future separately authorized slice may use allowlisted outbox events to create idempotent actions; C1 does not.

```text
OUTBOX_CONSUMER_ADDED=NO
BUSINESS_EVENT_HOOK_ADDED=NO
```

## H. Migration

```text
PREVIOUS_HEAD =
20260921_shipment_evidence_ownership

NEW_HEAD =
20260922_notification_foundation
```

Exactly one fresh additive migration was added. It creates:

- `uq_operational_outbox_tenant` on `(id, organization_id)`;
- `notification_action` with organization/source-event foreign keys, public identity, per-tenant idempotency, lifecycle check, correlation and status indexes;
- `notification_attempt` with organization/action foreign keys, public identity, positive and unique attempt numbering, lifecycle check, and tenant/status index.

The migration changes no existing column, rewrites no row, creates no notification row, and drops no business structure. Its downgrade removes only the two C1 tables/indexes and the new redundant outbox constraint when the foundation is empty. It refuses a populated destructive downgrade.

## I. PostgreSQL Proof

Owned disposable environment, without secrets:

- PostgreSQL `18.0`;
- loopback `127.0.0.1:55431`;
- database `phase_c1_disposable`;
- independent cluster storage `C:\Users\pc\AppData\Local\Temp\codex_phase_c1_pg_20260920`;
- fresh `initdb` cluster created solely for C1 with local trust authentication;
- cluster stopped, storage deleted, and port listener count returned to zero after qualification.

Executed proof:

1. initialized an empty PostgreSQL cluster and database;
2. upgraded the full Golden graph to `20260921_shipment_evidence_ownership`;
3. inserted preserved `OperationalOrganization` and `OperationalOutbox` sentinels;
4. upgraded to `20260922_notification_foundation`;
5. asserted tables, columns, timezone-aware timestamps, indexes, unique/check/foreign-key constraints, nullable neutral fields, and zero foundation rows;
6. proved cross-tenant outbox/action and action/attempt relationships fail physically;
7. proved attempt number zero fails and an action with attempt audit cannot be deleted;
8. removed only synthetic C1 rows, downgraded to the previous Golden head, and proved both pre-C1 sentinels remained unchanged;
9. re-upgraded to C1 and proved both foundation tables were still empty;
10. ran official `migration_cli current` and `check`, plus two independent status reads: `current=head`, `pending=no`;
11. proved one base, one head, and 98 total revisions.

A generic exploratory Alembic autogenerate comparison also surfaced the repository's pre-existing broad legacy ORM/schema drift. It is not reported as the project migration gate and no generated migration was accepted. C1-specific physical parity was asserted directly; the project's official current/check gate passed.

## J. Inactive-by-Default Proof

The explicit regression test creates a tenant request fixture, publishes an EUR quote, accepts it through the existing customer endpoint, creates a canonical execution unit, and records a customer-visible execution event. It then asserts:

```text
notification_action rows = 0
notification_attempt rows = 0
```

The PostgreSQL upgrade/re-upgrade proof independently asserts both tables remain empty. No request, quote, customer response, assignment, tracking event, document, or logistics-point producer was added.

## K. Existing Inbox Integrity

`ExpertConsoleNotification`, its services/routes, assignment/referral hooks, quote in-app attention behavior, unread semantics, and UI/API projections were untouched. The inactive regression deliberately permits the existing quote flow to create its normal Expert inbox attention while proving the new foundation remains empty.

```text
EXPERT_INBOX_SEMANTICS_CHANGED=NO
```

## L. Product Changes

Runtime/model/schema files:

- `backend/notification_models.py` — new dormant action/attempt models;
- `backend/models.py` — model registration/export only;
- `backend/operational_models.py` — composite tenant uniqueness metadata for outbox source-event fencing;
- `backend/migrations/versions/20260922_notification_foundation.py` — one fresh Golden-based migration;
- `docs/architecture/tenant-ownership-inventory.yaml` — classifies both new models as directly tenant-owned.

Focused test files:

- `backend/tests/test_notification_foundation.py`;
- `backend/tests/test_notification_foundation_migration_postgresql.py`.

Existing migration-contract tests updated only to expect the new sole head:

- `backend/tests/test_alembic_version_table.py`;
- `backend/tests/test_browser_migration_contract.py`;
- `backend/tests/test_case_documents_migration.py`;
- `backend/tests/test_execution_units.py`;
- `backend/tests/test_expert_sla_migration.py`;
- `backend/tests/test_global_logistics_point_adoption_migration.py`;
- `backend/tests/test_global_logistics_point_materialization_migration.py`;
- `backend/tests/test_logistics_network.py`;
- `backend/tests/test_master_data_migration.py`;
- `backend/tests/test_milestone_upgrade_bridge.py`;
- `backend/tests/test_operational_execution_190.py`;
- `backend/tests/test_project_aggregate_foundation.py`;
- `backend/tests/test_project_configuration.py`;
- `backend/tests/test_reference_data_seed_migration.py`;
- `backend/tests/test_release_publication_contract.py`;
- `backend/tests/test_shipment_request_update_trigger_migration.py`.

No frontend runtime, route, API, provider, service, worker, scheduler, launcher, or production-release file changed.

## M. Regression Status

```text
GCF-A-001 = PASS
GCF-A-002 = PASS
GCF-A-003 = PASS
GCF-A-004 = PASS
GCF-A-005 = PASS
GCF-A-006 = PASS
GCF-A-007 = PASS
GCF-A-008 = PASS
GCF-A-009 = PASS
GCF-A-010 = PASS
GCF-A-011 = PASS
GCF-A-012 = PASS
GCF-A-013 = PASS
GCF-A-014 = SOURCE CONTRACT PASS; PACKAGED REAL-PROCESS REHEARSAL NOT AVAILABLE

PHASE_B1_GEOGRAPHY = PASS
PHASE_B2_NUMERIC = PASS
PHASE_B3_TRANSPORT_SUMMARY = PASS
PHASE_B4_REQUEST_COUNT_LIST = PASS
PHASE_B5_EUR = PASS
PHASE_B6_TRACKING_ACTION = PASS
PHASE_B7_PRIVATE_POINT_SELECTOR = PASS
```

Authorization/tenant, request workflow, quote/EUR, canonical tracking, geography/private points, migration contracts, and tenant-architecture inventory all passed. Frontend runtime had no diff and its complete test inventory passed.

## N. Tests

| Qualification | Result |
| --- | --- |
| Focused C1 model/inactive + migration graph | PASS — 17 passed |
| Real disposable PostgreSQL C1 proof | PASS — 1 passed; not skipped |
| Focused Phase A/B1-B7 backend regression | PASS — 152 passed, 1 unrelated environment-dependent skip |
| Tenant architecture + C1 model rerun | PASS — 11 passed, 1 expected xfail |
| Full backend suite, authoritative isolated run | PASS — 1,065 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failed/errors; 626.40 seconds |
| Full frontend inventory | PASS — 66 files, 308 tests in seven non-overlapping batches |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,540 modules; output outside repository and removed |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Release/package source contracts | PASS — 51 passed |
| PostgreSQL official current/check | PASS — current/head `20260922_notification_foundation`, pending `no` |
| Static migration graph | PASS — 98 unique revisions, one base, one head, donor revision absent |
| Worktree whitespace check | PASS — `git diff --check` |

B7 recorded 1,061 backend passes and 308 frontend tests. C1 adds four backend tests, producing exactly 1,065 backend passes; frontend remains exactly 308. There is no unexplained reduction.

One preliminary full-backend run inherited the host's unrelated `TEST_DATABASE_URL` (`forwarder_auth_test`) and reached 1,062 passes before three tenant-architecture setup errors: `db.create_all()` encountered an already-existing stale `operational_outbox` table without the new composite constraint. No C1 assertion failed. The authoritative rerun explicitly restored the suite's documented `sqlite:///:memory:` default while retaining the separate real PostgreSQL URL only for the C1 migration test; it passed completely with the counts above.

The 93 skips remain existing suites requiring their own explicitly named disposable PostgreSQL/socket/browser environments. The C1 PostgreSQL test has its own supplied environment and executed. The xfail remains the existing strict public numeric tracking characterization.

The optional real-process launcher rehearsal was invoked but the frozen local release-candidate directory does not contain its packaged `artifact/runtime/python.exe` or deployment script, so that artifact-dependent test cannot execute on this checkout. It is not claimed as a pass. The 51 source-level release/package builder contracts passed, no launcher/release source changed, and C1 changes no production launcher behavior.

## O. Database Contract

```text
PREVIOUS_DATABASE_HEAD =
20260921_shipment_evidence_ownership

DATABASE_HEAD =
20260922_notification_foundation

ALEMBIC_HEAD_COUNT =
1

MIGRATION_ADDED =
YES

MIGRATION_COUNT_ADDED =
1

DONOR_MIGRATION_REUSED =
NO
```

## P. Scope Integrity

```text
NOTIFICATION_FOUNDATION_CREATED=YES
NOTIFICATION_DELIVERY_ACTIVATED=NO
BUSINESS_EVENT_PRODUCER_ADDED=NO
OUTBOX_CONSUMER_ADDED=NO
RECIPIENT_POLICY_IMPLEMENTED=NO
DEFAULT_CHANNEL_SELECTED=NO
DEFAULT_PROVIDER_SELECTED=NO
SMS_PROVIDER_ADDED=NO
EMAIL_PROVIDER_ADDED=NO
WEBHOOK_PROVIDER_ADDED=NO
EXPERT_INBOX_SEMANTICS_CHANGED=NO
CUSTOMER_NOTIFICATION_UI_ADDED=NO
CONTROL_TOWER_NOTIFICATION_EXPOSURE_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

No deploy, push, Production endpoint/database/process/task/environment/credential, provider credential, or secret was accessed or changed. The only database created was the owned disposable local C1 cluster, which was destroyed after proof.

## Q. Remaining Risks / Decisions

The following remain deliberately unresolved for future approval:

- recipient selection, eligibility, consent, locale, and preferences;
- channel selection, order, and fallback rules;
- provider configuration and credential management;
- retry/backoff limits and reconciliation operations;
- templates and customer-facing content;
- event-to-notification allowlist/mapping;
- customer quiet hours and delivery preferences.

None is required to keep the C1 schema meaningful and dormant.

## R. Verdict

PASS — INACTIVE CHANNEL-NEUTRAL NOTIFICATION FOUNDATION COMPLETE

## S. Next Goal

Exactly one next controlled-integration goal is derived without activation:

**Phase C — Slice 2: inactive notification lifecycle service hardening.** Add an internal-only, provider-free action/attempt invariant service and focused PostgreSQL concurrency/reconciliation tests for idempotent creation, claim fencing, lease expiry, late results, and `UNKNOWN` handling. Keep all business-event producers, outbox consumers, recipient/channel policy, provider adapters, workers/schedulers, API/UI exposure, and real delivery absent. Do not execute this goal without separate approval.

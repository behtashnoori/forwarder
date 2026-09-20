# Phase C2 — Inactive Notification Lifecycle Service Hardening

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Canonical integration branch | `integration/golden-controlled` |
| Evidence baseline / parent | `92456545cdfedfb74d9b290660c8e1884230c784` |
| C1 product commit | `2d36f35d37a24d817a21c4e263ee59b6f19d0966` |
| C2 branch | `codex/phase-c2-notification-lifecycle-hardening` |
| Starting database head | `20260922_notification_foundation` |
| Starting worktree | clean |
| Canonical upstream | `github/integration/golden-controlled` |
| Fresh upstream comparison | `0/0`; local and remote both at the evidence baseline |

The C1 product commit was an ancestor, the repository had exactly one Alembic
head, and the C2 branch was created directly from the required evidence commit.
No push, merge, cherry-pick, history rewrite, or canonical-branch movement
occurred.

## B. C1 Foundation Reused

C1 already supplied tenant-owned `NotificationAction` and
`NotificationAttempt` records, opaque public identities, per-tenant action
idempotency, positive per-action attempt numbering, action/attempt lifecycle
checks, same-tenant foreign keys, nullable channel/recipient/provider fields,
audit timestamps, deletion restrictions, and an inactive-by-default product
boundary.

C2 preserves that architecture. It adds only an internal lifecycle service and
the minimum persisted claim fence needed to make a future claimant safe.

## C. FWD-01 Lifecycle Donor Analysis

Read-only donor authority:

- repository: `D:\1-webapp\forwarder-dev`;
- commit: `d7cbedf9ec7416b83aeb6313aa095462a20e441d`;
- inspected files: `backend/services/notification_action_service.py`,
  `backend/notification_models.py`, `backend/tests/test_fwd01_notifications.py`,
  and `backend/tests/test_fwd01_migration_postgresql.py`.

Reused concepts were database-backed row locking, opaque claim fencing, bounded
lease expiry, UNKNOWN as an ambiguous result requiring reconciliation, and
late-result rejection. Rejected concepts were fixed Email, fake Email,
recipient lookup, quote/outbox consumption, provider code, credentials, worker,
scheduler, CLI delivery, provider retry/backoff policy, and donor migration
topology.

No merge or cherry-pick occurred. The donor repository was read with `git show`
only and was not changed. Its pre-existing untracked evidence files were left
untouched.

## D. Lifecycle Service

`backend/services/notification_lifecycle_service.py` is an internal-only,
provider-free command service. In simple terms it:

- creates or returns one equivalent action for a tenant/idempotency key;
- creates one pending next attempt while locking its action;
- claims an attempt with an opaque token and bounded lease;
- rotates the token when an expired claim is explicitly reclaimed;
- marks an explicitly expired unresolved claim UNKNOWN;
- records success, failure, or UNKNOWN only for the current valid fence;
- reconciles current UNKNOWN evidence to success or failure;
- permits a new attempt after FAILED only through an explicit call;
- cancels only safe non-active action states.

Every lookup combines tenant ownership with an opaque public identity. The
service chooses no event, recipient, channel, template, provider, retry timing,
or delivery behavior.

## E. Schema Decision

```text
C2_SCHEMA_CHANGE_REQUIRED=YES
```

C1 did not persist claim identity or lease expiry. Process-local state could not
prevent an expired claimant from overwriting a newer result. The fresh additive
revision `20260923_notification_lifecycle` therefore adds only nullable
`claim_token` and `claim_expires_at` columns to `notification_attempt`, plus a
unique token constraint and a check requiring the two values to be both present
or both absent. The token is opaque and provider-neutral.

No action, recipient, channel, provider, policy, retry, worker, or scheduling
schema was added.

## F. Idempotency

Sequential proof shows an equivalent repeat returns the same durable action,
while reuse of the same key with different immutable action inputs raises a
predictable `IdempotencyConflict`. Different tenants may use the same key.

The PostgreSQL race starts two callers together. Both resolve to the same public
action identity and the database contains exactly one action. Correctness relies
on `uq_notification_action_idempotency` plus savepoint/unique-conflict handling,
not an unsafe check-then-insert alone.

## G. Claim / Fence

Claims are serialized with PostgreSQL row locks and persisted as an opaque UUID
token plus expiry. Two concurrent claimants produce exactly one winner; the
second observes an active lease and fails with `ClaimUnavailable`.

When claim A expires, explicit claim B rotates the durable token. Any later
write carrying A is rejected with `StaleClaim`; B remains authoritative. The
service never relies on process memory or a process-local lock.

## H. Lease Expiry

A lease is active only before `claim_expires_at`. Expiry is evaluated when the
internal service is explicitly called; there is no scheduler. An expired
unresolved claim becomes UNKNOWN, because a future delivery may already have
occurred, and its old token loses authority. A later explicit claim may fence a
reconciliation owner without sending or automatically retrying anything.

## I. Attempt Numbering

Attempt creation locks the parent action and reads only the latest indexed
attempt for that action. It never scans all attempts in Python and does not use
an unlocked `MAX()+1` calculation. Two concurrent initial creators both resolve
to the same pending attempt number 1, leaving one durable row and the unique
valid sequence `[1]`. After an explicitly recorded failure, the next explicit
attempt is number 2. Historical rows are never renumbered or deleted.

## J. UNKNOWN / Late Result

Attempt transitions are:

```text
PENDING -> IN_PROGRESS
IN_PROGRESS -> SUCCEEDED | FAILED | UNKNOWN
UNKNOWN -> SUCCEEDED | FAILED  (authoritative reconciliation only)
```

UNKNOWN is neither failure nor success. It keeps the action `IN_PROGRESS`,
creates no retry, and sends nothing. A current UNKNOWN attempt can reconcile to
either authoritative success or failure. The same result repeated with the
same fence and fields is idempotent.

A result from an expired token is rejected. A result for an older attempt after
a newer attempt exists is rejected with `StaleAttempt`. Neither case can
complete or fail the current action incorrectly.

Action transitions implemented by infrastructure are:

```text
PENDING -> IN_PROGRESS | CANCELLED
IN_PROGRESS -> COMPLETED | FAILED
FAILED -> PENDING          (explicit new attempt only)
FAILED -> CANCELLED
COMPLETED and CANCELLED -> no reopening
```

An UNKNOWN attempt leaves its action `IN_PROGRESS`; this is the non-terminal C1
action state that represents unresolved infrastructure work.

## K. Tenant Isolation

Tests prove tenant B cannot create an attempt for tenant A's action, claim tenant
A's attempt, or record/reconcile its result. Passing a guessed numeric database
ID where an opaque public ID is required also fails closed. C1 composite foreign
keys remain the physical same-tenant backstop.

## L. Inactive Product Proof

The retained C1 flow covers a request fixture, quote creation, EUR quote
acceptance, canonical execution-unit creation, and a customer-visible execution
event. The B7 flow now also explicitly asserts inactivity after selecting a
same-tenant private logistics point and recording its canonical event. Both end
with:

```text
notification_action = 0
notification_attempt = 0
```

Only tests that directly invoke the C2 internal service create lifecycle rows.

```text
BUSINESS_EVENT_PRODUCER_ADDED=NO
OUTBOX_CONSUMER_ADDED=NO
```

## M. Provider / Policy Neutrality

```text
RECIPIENT_POLICY_IMPLEMENTED=NO
DEFAULT_CHANNEL_SELECTED=NO
DEFAULT_PROVIDER_SELECTED=NO
PROVIDER_ADAPTER_ADDED=NO
WORKER_ADDED=NO
SCHEDULER_ADDED=NO
```

All C2 lifecycle tests run with recipient, channel, and provider configuration
absent. Existing nullable C1 audit fields remain nullable.

## N. PostgreSQL Concurrency Proof

Owned disposable environment, without secrets:

- PostgreSQL `18.0`;
- loopback `127.0.0.1:55432`;
- C2 database `phase_c2_disposable`;
- C1 companion database `phase_c1_disposable_c2`;
- final cluster storage
  `C:\Users\pc\AppData\Local\Temp\codex_phase_c2_pg_20260920_02`;
- cluster stopped, storage deleted, and listener count returned to zero.

Real concurrent results:

| Race | Result |
| --- | --- |
| A. two action creators | one durable logical action; both returned one public ID |
| B. two claimants | exactly one winner; one active token |
| C. two attempt creators | one durable pending attempt; valid sequence `[1]` |
| D. expired claim | claim B replaced expired claim A |
| E. stale result | A's late success rejected; B remained authoritative |
| F. UNKNOWN reconciliation | current B fence reconciled UNKNOWN to SUCCEEDED |

No concurrency result above was simulated sequentially.

## O. Migration Proof

```text
PREVIOUS_HEAD=20260922_notification_foundation
NEW_HEAD=20260923_notification_lifecycle
ALEMBIC_HEAD_COUNT=1
REVISION_COUNT=99
```

On owned PostgreSQL, the test upgraded C1 to C2, verified the two timezone-aware
nullable fields and constraints, and preserved a pre-C1 organization sentinel
plus existing C1 action/attempt rows. Downgrade correctly refused while a claim
was populated. After explicitly clearing only the synthetic transient claim,
downgrade removed only C2 fields and preserved C1 rows and foundation tables;
re-upgrade succeeded.

The official commands reported:

```text
current=20260923_notification_lifecycle
heads=20260923_notification_lifecycle
pending=no
```

## P. Regression Status

Phase A, B1 geography, B2 numeric presentation, B3 transport summary, B4
count/list, B5 EUR, B6 tracking-action removal, B7 private-point selector, and
C1 foundation tests all remained green in the final full backend and frontend
runs. OperationalOutbox producer behavior, ExpertConsoleNotification semantics,
quote behavior, tracking behavior, and Customer-safe projections were not
changed.

## Q. Tests

| Qualification | Result |
| --- | --- |
| Focused C2/C1/inactive/model checks | PASS — 19 passed |
| Expanded migration/head/C1/C2 set | PASS — 86 passed |
| Final B7 private-point + C1/C2 focused set | PASS — 16 passed |
| Real PostgreSQL C2 migration and race suite | PASS — 3 passed; not skipped |
| Full backend, final tree | PASS — 1,076 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failed; 521.33 seconds |
| Full frontend inventory | PASS — 66 files, 308 tests |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,540 modules; output created outside the repository and deleted |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Release/package source contracts | PASS — 72 passed |
| Alembic current/check | PASS — current=head, pending=no |
| Static migration graph | PASS — 99 revisions, one head |
| Worktree whitespace check | PASS |

The artifact-dependent real packaged launcher rehearsal was not claimed as a
pass because no newly built approved runtime artifact was in scope. Source and
package contracts passed and launcher/release runtime source did not change.

## R. Scope Integrity

```text
NOTIFICATION_LIFECYCLE_SERVICE_CREATED=YES
REAL_NOTIFICATION_DELIVERY_ACTIVATED=NO
BUSINESS_EVENT_PRODUCER_ADDED=NO
OUTBOX_CONSUMER_ADDED=NO
RECIPIENT_POLICY_IMPLEMENTED=NO
DEFAULT_CHANNEL_SELECTED=NO
DEFAULT_PROVIDER_SELECTED=NO
PROVIDER_ADAPTER_ADDED=NO
WORKER_ADDED=NO
SCHEDULER_ADDED=NO
NOTIFICATION_API_ADDED=NO
NOTIFICATION_UI_ADDED=NO
CONTROL_TOWER_NOTIFICATION_EXPOSURE_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

## S. Remaining Product Decisions

C2 does not resolve which events notify, who receives, which channel is used,
channel fallback, provider, templates, quiet hours, user preferences, or retry
policy.

## T. Verdict

PASS — INACTIVE NOTIFICATION LIFECYCLE HARDENING COMPLETE

## U. Next Goal

Exactly one next controlled-integration goal is derived from the approved plan:

**Phase D — isolated Control Tower backend.** Port only the feature-local
Control Tower read route, authorization scope, safe sources/translation, read
model, and OIP with no schema change and no notification exposure. Preserve
shared Shipment Detail/economics behavior and do not begin frontend shell work.

Do not execute this goal without separate approval. Notification event mapping,
recipient policy, channel policy, provider selection, and activation are not the
automatic next step.

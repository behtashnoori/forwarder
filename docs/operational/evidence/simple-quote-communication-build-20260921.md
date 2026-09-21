# Simple Quote Communication — Build and Qualification Evidence

Date: 2026-09-21

Candidate branch: `codex/simple-quote-communication`

Starting canonical: `39287f4bc44ab7d92a8a38f24a8029fae91b46a0`

Design commit: `1272e1af5fe5d69aa3fdbeffd9f7a70e27f2383a`

Reference-status reconciliation commit: `a92e4447b5b4345462805d58140ff38eaa84910e`

## A. LPAF Governance Gate

The active governing baseline is LPAF v2.2 and its mandatory Agent Entry Protocol. The reviewed-but-not-active v2.3 Product Integration and `REFERENCE_IMPACT` controls were applied as the Forwarder strong default. LPAF v2.4 was not adopted and no generic `29-lpaf` file was changed.

This is a Level B product change. Mission, outcome, scope, actor/authority, owner/SOR, data scope, user journey, module/public-contract boundaries, migration and compatibility impact, authorization, replay/concurrency, negative acceptance, browser qualification, release/recovery, and stop conditions were closed in `docs/architecture/simple-quote-communication-v1.md` before runtime code was built.

The initial product-reference decision was `REFERENCE_IMPACT=NONE`: PDR-019, FDD-001-035, FDM-001, the Canonical Business Object Catalog, and Golden Journey D already authorized the exact capability. The final re-check found only a stale implementation-status row in the architecture drift register. That row was reconciled in the separate reference-status commit without changing historical PDR/ADR truth.

## B. Starting State

- Canonical branch: `integration/golden-controlled`.
- Required and observed starting SHA: `39287f4bc44ab7d92a8a38f24a8029fae91b46a0`.
- Local and `github/integration/golden-controlled` started equal with ahead/behind `0/0`; the worktree was clean.
- Starting Alembic head was the single revision `20260924_request_cargo_items`.
- Ancestry included Optional Multi-Cargo, Documents, Dual Calendar, Combined Transport, EUR Quote support, fixed Expert ownership, and the LPAF product-reference reconciliation.
- The bounded design was committed before the implementation and the temporary feature branch was not pushed.

## C. Existing Quote Lifecycle

`ExpertQuote` was already the compatibility implementation of canonical `Quotation` and owned official amount, currency, validity, issuer, `customer_response`, and `responded_at`. The previous response command supported `accepted` and `declined`, locked the Request and current Quote, returned exact replay idempotently, rejected conflicts, left Request status unchanged, marked the assigned Expert unread, and wrote an audit record.

The established official revision mechanism creates another `ExpertQuote`. The current official Quote is selected deterministically by `(created_at DESC, id DESC)` and earlier Quotes remain commercial history. No parallel Quote or revision architecture was added.

## D. Product Contract

For an eligible current official Quote, the Customer has exactly three actions:

1. approve (`accepted`);
2. needs discussion (`discussion`) with one short message;
3. reject (`declined`).

Discussion is communication context only. It is not an amount/currency proposal, price mutation, acceptance, rejection, automatic Request-state transition, Notification, chat, or negotiation round. Changed commercial terms require an explicit new official Quote from the existing Expert issuance workflow. Only an accepted Quote is eligible for the existing Shipment-creation path.

## E. Response State Design

The specific `ExpertQuote` owns one non-reversible Customer response fact. `customer_response` accepts `accepted | discussion | declined`; `responded_at` and `responded_by_customer_id` identify when and by which governed Customer relationship it was recorded. The response controls are available only for the latest, unexpired, unanswered Quote on a non-terminal Request.

Exact response/message replay is safe. A different response, or the same response with a different normalized discussion message, returns `QUOTE_RESPONSE_CONFLICT` and never overwrites the first business fact. Expired and superseded Quotes return stable `QUOTE_EXPIRED` and `QUOTE_SUPERSEDED` errors. No withdrawn/cancelled state was invented where the current model has none.

## F. Needs Discussion Message

`discussion` requires a trimmed, non-empty, plain-text message of at most 500 Unicode code points. Control characters are rejected. `accepted` and `declined` reject any discussion message. The system neither parses prices nor trusts HTML in this field. The frontend uses ordinary escaped text rendering and a compact bounded textarea, with explicit copy that the message does not change the official amount or currency.

The message is tenant-private commercial content. It is present only in the governed Customer workflow and authorized Expert Request/Quote projection. It is absent from public tracking, Notification payloads, and audit/log content; audit records contain safe response metadata only.

## G. Official Quote Revision

The Expert reads the current response, message, and response time in Request detail and uses the existing Quote issuance modal/action to issue Q2. The issuance service creates Q2 and never mutates Q1 amount, currency, response, or history. Q2 becomes current by the existing deterministic ordering; Q1 remains in the bounded 20-row newest-first history. The Customer can then respond independently to Q2.

No discussion response automatically creates a Quote and no second revision mechanism was introduced.

## H. Actor / Authorization

The canonical command is `POST /api/customer/quotes/{quote_public_id}/response`. It uses an opaque Quote UUID together with the established opaque Request tracking capability. Server-side traversal derives Quote, Request, Organization, and the Request-to-Customer relationship; a client-supplied tenant is never accepted. The Customer handle must equal that derived relationship and is not authority by itself.

Unknown/malformed Quote, wrong Customer, unrelated same-organization Customer, foreign tenant, missing/revoked Customer relationship, and Quote/Request organization mismatch fail through the same non-disclosing not-found contract. The existing Customer model has no separate active-session flag, so revocation is represented by removal/absence of the established Customer relationship; no identity lifecycle was invented.

Expert read and issuance remain behind the existing operation-time Request authorization and active tenant membership checks. Existing Admin/Manager oversight reads are unchanged. Platform Admin receives no Customer response path and no new tenant-commercial edit authority. Public tracking exposes neither the opaque internal database id nor the discussion message.

## I. Schema Decision

```text
QUOTE_COMMUNICATION_SCHEMA_DECISION=ADDITIVE_MIGRATION_REQUIRED
```

The existing columns could not safely identify an opaque Quote command target, persist discussion text, or preserve the Customer actor. The smallest model change therefore extends the existing Quote row rather than creating a negotiation/conversation aggregate.

## J. Migration if Applicable

Revision `20260925_quote_communication` descends linearly from `20260924_request_cargo_items`. It adds:

- non-null unique UUID `public_id`, generated without interpreting business state;
- nullable `customer_response_message` with a 500-character constraint;
- nullable indexed `responded_by_customer_id` foreign key with `ON DELETE SET NULL`;
- the additive `discussion` value and response/message combination checks.

No historical response, message, timestamp, or actor is fabricated. Existing accepted/declined rows are preserved. An empty downgrade is reversible. A populated downgrade refuses if discussion/message/new actor evidence exists, because silently deleting new commercial evidence is prohibited. Upgrade, preservation, constraints, empty downgrade, refusal with populated evidence, and re-upgrade were proven on PostgreSQL. The final graph has exactly one head: `20260925_quote_communication`.

## K. Idempotency / Replay

The command normalizes its discussion message once. A replay with the same response and normalized message returns HTTP 200 with `REPLAYED` and creates no second audit fact. A different state or message returns HTTP 409 with `QUOTE_RESPONSE_CONFLICT`. Browser double submission and direct API replay cannot create duplicate response facts.

## L. Concurrency

Both Customer response and Expert Quote issuance lock the Request row before locking/selecting the current Quote. This common lock order serializes response against revision and prevents deadlocks caused by inverted parent/child locking. PostgreSQL race tests proved:

- approve versus reject: one winner, one stable conflict;
- approve versus discussion: one winner, one stable conflict;
- exact concurrent replay: one business fact and replay-safe success;
- discussion versus Expert revision: serialized outcome with Q1 protected from a post-Q2 response;
- response at expiry boundary: deterministic rejection when expired.

No contradictory active state or silent overwrite was observed.

## M. Historical Compatibility

Historical Quotes remain valid. Existing accepted/declined meanings and accepted-Quote Shipment eligibility are unchanged. No missing Customer actor is guessed. The prior tracking-code route remains a compatibility adapter to the same canonical command service, while new frontend traffic uses the opaque Quote-specific route. Prior Quotes remain readable in bounded history and no historical amount/currency is overwritten.

## N. EUR / Currency

IRR, USD, and EUR remain the only governed Quote currencies from `contracts/quote-currencies.v1.json`. Response commands carry no structured amount or currency. No FX conversion, recalculation, precision, or display contract changed. Free-text numbers in a discussion message remain text. Focused currency/role tests passed for all three response paths.

## O. Cargo / Combined Transport Regression

Response availability is independent of Cargo cardinality and Request transport intent. Tests cover zero-Cargo and multi-Cargo Requests and Combined Transport with approve/discussion/reject. The response command neither reads nor mutates Cargo items, Request transport intent, Route Legs, or actual route modes. The full backend/frontend suites also retained the existing Cargo and Combined Transport regressions.

## P. Documents / Dual Calendar Regression

No Documents model, API, permission, file/version/history/retry behavior, or UI was changed. The full regression suite retained expert-only multi-file, append, targeted replacement, history, retry, and unknown handling.

New response timestamps use the existing shared Dual Calendar formatter and render `Gregorian (Jalali)` from the one authoritative stored instant. No persistence, ordering, timezone, or second date formatter was introduced. Browser desktop/mobile RTL evidence verified the presentation.

## Q. Notifications

Quote response creates no `NotificationAction` or `NotificationAttempt`, calls no provider, and schedules no delivery. The owned browser database audit observed zero response-driven Notification actions and attempts. The one local-console notification in the seeded journey was the pre-existing Quote issuance surface and did not activate the dormant C1/C2 lifecycle.

## R. Browser Evidence

Playwright ran against a real frontend/backend and the owned disposable PostgreSQL database `forwarder_integrated_cert_quote_communication_e2e`, bound to loopback with `APP_ENV=uat`. Result: **5 passed in 16.0 seconds**.

The journeys proved Customer approve and persistence/reopen; Persian RTL mobile needs-discussion with bounded message; Expert message/time visibility and explicit Q2 issuance; Q1 retained as history while the Customer responds to Q2; reject persistence; and stable conflicting-response handling. Representative desktop RTL, mobile RTL, and Expert revised-Quote screenshots were inspected. The audit result was:

```json
{"local_console_notifications":1,"notification_actions":0,"notification_attempts":0,"quote_count":4,"response_audit_count":4,"result":"PASS"}
```

No unexpected console/page/network errors were present. The owned processes and database were destroyed by the cleanup path.

## S. PostgreSQL Evidence

The dedicated loopback-only PostgreSQL 18 database `forwarder_quote_communication_build` was used; no developer or Production database was qualification authority. `backend/tests/test_quote_communication_postgresql.py` completed **2 passed** and proved the migration lifecycle plus the response/revision/replay/expiry races listed above. The disposable database was removed after qualification.

## T. Full Regression

- Focused backend Quote/migration/currency/contract cohort: **35 passed**.
- Focused response/Expert contract follow-up: **10 passed, 1 xfailed**.
- Focused frontend Quote communication/currency cohort: **2 files, 5 tests passed**, including terminal-Request control suppression.
- Full backend: **1312 passed, 100 skipped, 1 xfailed** in 626.74 seconds.
- Full frontend: **72 files, 354 tests passed**.
- TypeScript: `tsc --noEmit` passed.
- ESLint: passed with zero errors and 13 pre-existing warnings.
- Production frontend build: passed; the existing chunk-size advisory remained non-blocking.
- Release publication contract: **6 passed**.
- Source-contained package builders: **51 passed**.
- Alembic graph: exactly one head, `20260925_quote_communication`.
- `git diff --check`: no whitespace errors (Git emitted only configured LF/CRLF conversion advisories).

The broad historical Windows deployment-rehearsal collection was not used as candidate authority because part of it requires frozen release-candidate artifacts outside this isolated worktree. Candidate-relevant, source-contained publication and package-builder cohorts passed **57/57** without Production access.

## U. Reference Re-check

Immediately before Freeze, the following were re-read against final runtime, tests, PostgreSQL behavior, and browser journeys:

- active LPAF v2.2 Architecture Framework and mandatory Agent Entry Protocol;
- v2.3 Product Integration / `REFERENCE_IMPACT` strong default;
- PDR-019 §§5, 7, 8, 9 and the post-D2 reference reconciliation;
- FDD-001-035 and FDM-001 Quote/owner/SOR flow;
- Canonical Business Object Catalog `Quotation`, `Comment`, `TrackingCode`, and `QuotationDiscussionRequest` definitions;
- operational and Forwarder architecture baselines;
- S6 Golden Business Journey D;
- IRR/USD/EUR currency contract;
- ADR-042/ADR-043 authorization and assigned-work boundaries plus the tracking authority matrix;
- bounded implementation design and the architecture drift register.

Product/reference truth did not require amendment. The drift register's stale runtime-status cell was updated in a separate documentation commit to match qualified implementation. Runtime, database, tests, journey, authorization, Quote lifecycle, and authoritative references now agree.

## V. Scope Integrity

```text
QUOTE_RESPONSE_APPROVE_ENABLED=YES
QUOTE_RESPONSE_NEEDS_DISCUSSION_ENABLED=YES
QUOTE_RESPONSE_REJECT_ENABLED=YES
NEEDS_DISCUSSION_MESSAGE_ENABLED=YES
CUSTOMER_CAN_EDIT_OFFICIAL_QUOTE_PRICE=NO
CUSTOMER_CAN_EDIT_OFFICIAL_QUOTE_CURRENCY=NO
AUTOMATIC_COUNTER_OFFER_ENABLED=NO
NEGOTIATION_ENGINE_ENABLED=NO
EXPERT_REVISED_OFFICIAL_QUOTE_FLOW=YES
PRIOR_QUOTE_HISTORY_PRESERVED=YES
NOTIFICATION_ACTIVATION_CHANGED=NO
CARGO_OPTIONALITY_CHANGED=NO
COMBINED_TRANSPORT_BEHAVIOR_CHANGED=NO
DOCUMENTS_BEHAVIOR_CHANGED=NO
DUAL_CALENDAR_BEHAVIOR_CHANGED=NO
CONTROL_TOWER_SEMANTICS_CHANGED=NO
EXPERT_OWNERSHIP_CHANGED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
QUOTE_COMMUNICATION_SCHEMA_DECISION=ADDITIVE_MIGRATION_REQUIRED
```

No deployment, Production access/change, Notification activation, Control Tower scaling, generic chat, counter-offer, bargaining state machine, Customer Quote editing, or feature-branch push occurred.

## W. Remaining Risks

- The Customer surface retains the established opaque tracking-capability model; a separate authenticated Customer session/active-state redesign remains outside this approved slice.
- API history is intentionally bounded to the newest 20 Quotes. Unbounded archival/reporting remains a separate product decision if ever required.
- Downgrade after new communication evidence is intentionally fail-closed; recovery is roll-forward or an explicitly governed evidence-preserving migration.
- The pre-existing frontend chunk-size advisory remains and is unrelated to this capability.
- Control Tower's known scaling gap remains the next separate goal; this work changes none of its semantics.

## X. Verdict

```text
REFERENCE_IMPACT_FINAL=NONE
```

PASS — SIMPLE QUOTE COMMUNICATION COMPLETE

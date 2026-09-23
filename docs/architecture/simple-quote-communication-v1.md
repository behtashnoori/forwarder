# Simple Quote Communication — Bounded Implementation Design

> **Current authority note (2026-09-23):** the Quote state/history rules in this
> document remain applicable, but its Customer tracking-code authority,
> client-supplied Customer handle, public Quote projection, compatibility writer,
> and “no Customer session model” assumptions are superseded by
> [ADR-053](../operational/adr/ADR-053-optional-customer-account-private-quote-authority.md)
> together with [ADR-052](../operational/adr/ADR-052-public-tracking-opaque-capability-authority.md).
> Public Tracking never reads or mutates Quote state. Customer Quote access and
> response now require an ACTIVE, scoped Customer session.

- **Status:** Approved implementation design for the bounded Build slice
- **Date:** 2026-09-21
- **Historical governing baseline:** LPAF v2.2 plus the v2.3 Product Integration / `REFERENCE_IMPACT` strong default; current changes use LPAF v2.6
- **Rigor:** Level B — product / release-critical commercial state
- **Starting canonical:** `39287f4bc44ab7d92a8a38f24a8029fae91b46a0`
- **Branch:** `codex/simple-quote-communication`
- **Authority:** the user-supplied Simple Quote Communication Goal, PDR-019 §5/§8/§9, FDD-001-035, and Golden Business Journey D

## 1. Mission contract

| Field | Decision |
| --- | --- |
| MISSION | Add the three governed Customer responses to one current official Quote: approve, needs discussion with one short message, or reject. |
| OUTCOME | A Customer records one non-reversible response per official Quote; an authorized Expert can understand it and, when terms change, explicitly issue a separate revised Quote through the existing workflow. |
| SCOPE IN | Additive Quote schema, canonical response command, compatibility adapter, bounded Quote history, Expert and Customer UX, tests, PostgreSQL/browser qualification, evidence, and canonical synchronization after PASS. |
| SCOPE OUT | Negotiation/counter-offers, Customer price/currency editing, chat, automatic revised Quote, Notification activation, Control Tower redesign/scaling, deployment, and Production access. |
| CAPABILITY_OWNER | Pricing / Commercial. |
| SYSTEM_OF_RECORD | Existing `ExpertQuote` compatibility model (`Quotation` in canonical vocabulary) and its per-Quote response fields. |
| ACTORS | Customer-side Request/Quote capability records the response. The authorized owning Expert reads the response/history and issues later official Quotes. Existing Admin/Manager read behavior is preserved; no editing grant is added. |
| TENANT / DATA SCOPE | Tenant-private commercial transaction/history. Server derives the Request, Customer relationship, and Organization from the Quote parent; client tenant identifiers are not trusted. |
| QUALITY ATTRIBUTES | Non-disclosure, immutable commercial history, deterministic replay/conflict behavior, row-lock concurrency, historical compatibility, RTL/mobile usability, and no dormant-Notification activation. |
| STOP CONDITIONS | Baseline/reference conflict, more than one Alembic head, unsafe/destructive migration, authorization ambiguity requiring a new role model, PostgreSQL race failure, browser Product Surface failure, or candidate/reference disagreement. |
| DEFINITION OF DONE | Acceptance contract, negative authorization, PostgreSQL migration/races, browser journeys, full regression, source/package cohort, evidence, clean commits, and final reference re-check all pass. |

## 2. Current-state facts, assumptions, and resolved decisions

### Facts

- `ExpertQuote` already owns amount, currency, validity, creator, `customer_response`, and `responded_at`.
- Existing response values are `accepted` and `declined`; the current service row-locks the Request and latest Quote, makes exact replay idempotent, rejects conflicting replay, preserves Request status, sets the assigned-Expert unread flag, and appends an audit log.
- A revised Quote is already represented by creating another `ExpertQuote`; latest `(created_at, id)` is the current official Quote and prior rows remain history.
- Existing persistence already supports IRR/USD/EUR and integer amounts; no conversion is performed.
- The Customer surface uses an opaque tracking-code capability plus the Request-to-`CustomerGamification` relationship. There is no separate active/revoked Customer-session model in the authoritative baseline.
- Expert Request reads use canonical operation-time authorization. Quote creation is limited by the existing assigned-Expert/Admin plus active Organization membership checks.
- Public tracking currently projects the latest Quote response state but does not need or receive private discussion text.

### Assumptions

- The established tracking code remains the Customer capability secret for this slice; inventing a new Customer authentication/session lifecycle is outside the approved Quote boundary.
- `CustomerGamification.id` is used only as the asserted actor handle and is accepted only when it equals the server-derived parent relationship. It is never sufficient by itself.

### Unknowns resolved by conservative rules

- The model has no Quote withdrawn/cancelled flag. A Quote is response-eligible only when it is the latest Quote, unexpired, unanswered, and the parent Request is not in a terminal commercial state.
- The model has no Customer active/revoked state. Missing/deleted/mismatched Customer capability fails non-disclosively; no new identity state is invented.

## 3. Ownership and boundaries

| Contract | Owner / rule |
| --- | --- |
| QUOTE STATE OWNER | `ExpertQuote`; no parallel Quote aggregate. |
| COMMUNICATION STATE OWNER | The same `ExpertQuote`, extended additively with `discussion` and its bounded message/actor. |
| MESSAGE HISTORY OWNER | The specific official `ExpertQuote`; one immutable message only when response is `discussion`. |
| OFFICIAL QUOTE REVISION OWNER | Existing Expert Quote issuance command. It creates Q2; it never mutates Q1 amount/currency/response. |
| HISTORY OWNER | The ordered Request Quote collection. API projections are bounded to the 20 most recent rows. |
| UPSTREAM | Customer Request detail and Expert Request detail. |
| DOWNSTREAM | Accepted-Quote Operational Shipment eligibility only; discussion/reject never qualify. |
| ADJACENT CAPABILITIES | Request/Cargo/transport intent, economics/currency, Dual Calendar, public tracking, Documents, dormant Notifications, and Control Tower remain behaviorally unchanged. |
| MODULE BOUNDARY | `customer_gamification_service` owns Customer response command; `quote_service` owns official Quote issue/read serialization; `expert_request_detail_service` owns authorized Expert history projection. |
| PUBLIC CONTRACT | Canonical `POST /api/customer/quotes/{quote_public_id}/response`; opaque Quote identity plus tracking capability and Customer handle. Existing tracking-code route remains a compatibility adapter. |
| PROHIBITED DEPENDENCIES | Notification producers/providers, Control Tower attention logic, Document workflow, FX/conversion, generic message/chat modules, and Customer-auth redesign. |

## 4. State and schema decision

```text
QUOTE_COMMUNICATION_SCHEMA_DECISION=ADDITIVE_MIGRATION_REQUIRED
COMMUNICATION_STATE_OWNER=EXPERT_QUOTE
MESSAGE_HISTORY_OWNER=EXPERT_QUOTE
OFFICIAL_QUOTE_REVISION_OWNER=EXISTING_QUOTE_ISSUANCE_WORKFLOW
RESPONSE_REVERSIBILITY=NON_REVERSIBLE_PER_OFFICIAL_QUOTE
EXPIRED_QUOTE_RESPONSE_BEHAVIOR=REJECT_WITH_QUOTE_EXPIRED
SUPERSEDED_QUOTE_RESPONSE_BEHAVIOR=REJECT_WITH_QUOTE_SUPERSEDED
```

Exactly one migration descends from `20260924_request_cargo_items` and adds:

- non-null unique UUID `public_id`, safely generated for historical Quotes without interpreting commercial facts;
- nullable `customer_response_message` with a 500-character database bound;
- nullable `responded_by_customer_id` FK to `customer_gamification`, `ON DELETE SET NULL` so actor deletion never deletes Quote evidence;
- the additive `discussion` response value and combination constraints.

No accepted/declined/discussion response, message, timestamp, or actor is manufactured for historical rows. Existing accepted/declined facts remain unchanged. The actor column stays nullable for historical evidence whose actor was not persisted.

Empty downgrade is reversible. Downgrade refuses when a discussion response/message or newly captured actor exists, because dropping it would destroy business evidence.

## 5. Command, validation, and error contract

Canonical command body:

```json
{
  "tracking_code": "opaque Request capability",
  "customer_id": 123,
  "response": "accepted | discussion | declined",
  "message": "required only for discussion"
}
```

- `discussion` message is trimmed, non-empty, at most 500 Unicode code points, and rejects control characters. It is stored/rendered as plain text; no HTML trust or price parsing exists.
- `accepted` and `declined` reject a supplied message.
- Server resolution requires the opaque Quote ID, tracking code, Customer parent relationship, and Quote/Request Organization agreement in one non-disclosing chain.
- Stable codes cover `QUOTE_NOT_FOUND`, `INVALID_QUOTE_RESPONSE`, `DISCUSSION_MESSAGE_REQUIRED`, `DISCUSSION_MESSAGE_INVALID`, `DISCUSSION_MESSAGE_NOT_ALLOWED`, `QUOTE_EXPIRED`, `QUOTE_SUPERSEDED`, `QUOTE_RESPONSE_NOT_ALLOWED`, and `QUOTE_RESPONSE_CONFLICT`.
- Unknown, foreign-tenant, wrong-Customer, and malformed opaque identity return the same 404 contract.

## 6. Idempotency and concurrency

```text
IDEMPOTENCY_STRATEGY=EXACT_RESPONSE_AND_NORMALIZED_MESSAGE_REPLAY
CONCURRENCY_STRATEGY=REQUEST_ROW_LOCK_THEN_CURRENT_QUOTE_ROW_LOCK
```

- Exact replay of the same response and normalized message returns the recorded representation and does not append a second audit event.
- Same state with different message, or any different state, returns stable conflict and never overwrites.
- Customer response and Expert Quote issuance acquire the Request lock first. Quote issuance therefore serializes with response; after Q2 exists, a Q1-targeted command fails as superseded.
- Ordering is deterministic by `(created_at DESC, id DESC)`.
- PostgreSQL tests cover approve-vs-reject, approve-vs-discussion, discussion-vs-revision, same-command replay, and the expiry boundary supported by deterministic fixtures.

## 7. Authorization and privacy

- Customer command derives all scope from the Quote parent and verifies the supplied Customer handle only against the parent relation; wrong Customer, same-Organization unrelated Customer, foreign Organization, missing Customer, and Quote/Request Organization mismatch are non-disclosing denials.
- Expert response/history reads continue through canonical Request authorization. Expert Quote issue authority is unchanged.
- Platform Admin is not introduced into the Customer command and receives no new tenant-commercial editing grant.
- Discussion text appears only in Customer workflow and authorized Expert Request/Quote projections. Public tracking, logs, Notifications, and customer-unsafe projections never include it.
- Audit stores only response code, Quote internal audit reference, and capability metadata—not the discussion text.

## 8. Product surface and acceptance

- Customer normal journey: panel → Request → current official Quote → one of `تأیید`, `نیاز به گفتگو`, `رد` → truthful confirmation → leave/reopen.
- Needs Discussion reveals one small 500-character textarea and explicitly says the message does not change official price/currency.
- Expert normal journey: Request detail → current Quote response at a glance → discussion message/time → `صدور پیشنهاد بازنگری‌شده` through the existing Quote modal → Q2 current, Q1 retained in bounded history.
- Response timestamps use the existing Dual Calendar formatter. Internal enum names are localized.
- Response controls are hidden for expired, answered, or terminal-parent Quotes; the backend remains authoritative.

## 9. Compatibility, recovery, and reference impact

- Historical accepted/declined rows remain readable and eligible exactly as before.
- Existing tracking-code response route remains a compatibility adapter to the same command service; new frontend traffic uses the Quote-specific opaque route.
- IRR/USD/EUR, Cargo optionality/multiplicity, Combined Transport intent, Documents, Notifications, Control Tower, and fixed Expert ownership are regression-only.
- Recovery is migration downgrade only when no new response evidence exists; otherwise roll forward. No destructive evidence removal is authorized.

```text
REFERENCE_IMPACT=NONE
```

Rationale: PDR-019 §5/§8/§9, FDD-001-035, Golden Business Journey D, the Canonical Business Object Catalog, and the architecture drift register already state the exact target state, ownership, compatibility values, revised-Quote rule, bounded history, authorization/tracking preservation, and dormant-Notification boundary. This design resolves implementation choices without changing authoritative product truth.


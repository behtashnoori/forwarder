# FE-1 Shipment Economics Architecture Contract

Status: **PROPOSED — READY FOR HUMAN APPROVAL**  
Scope: architecture/product contract only; no Shipment Economics implementation is authorized by this document.  
Inputs: approved FE-D01–FE-D15 decisions, `FE-0-shipment-economics-discovery-gap-analysis.md`, and repository evidence revalidated on 2026-08-08.

## 1. P0 Security Revalidation

The finding was confirmed. `POST /api/customer/quote-response/<int:customer_id>` had no authentication decorator and accepted a numeric `request_id` in its body. Ownership matching prevented a customer/request mismatch but did not authenticate the caller; both identifiers were enumerable. The React customer flow stored and transmitted the numeric customer and request identities. Tests characterized the route as intentionally unauthenticated. The wider customer dashboard and public tracking surfaces also retain legacy numeric exposure, but only the quote-response mutation is in this bounded closure.

## 2. Root Cause

The customer gamification area uses identification by database key as if it were authorization. Quote response inherited that legacy flow without a customer session or a narrowly scoped capability. It also selected “latest quote,” mutated it in place, lacked a durable response audit, did not serialize concurrent responses, and treated every replay as a conflict.

## 3. Chosen Identity/Auth Model

Model **B: intentionally unauthenticated opaque capability** is selected from repository evidence. Customer login does not exist; introducing it would be a product redesign. `ShipmentRequest.tracking_code` is already generated with `secrets`, unique, indexed, customer-safe, and used as the public request capability. Quote response now accepts that value only and grants one operation: respond to the latest quote for that request. Numeric values are rejected. Quote `valid_until` supplies response expiry. A new quote naturally changes the target while the old quote remains historical; response revocation beyond expiry or removal/rotation of the request capability is a remaining platform concern.

## 4. Changes Made

- Replaced the numeric customer route with `POST /api/customer/quote-response/<tracking_code>`; the body contains only `response`.
- Resolved and locked the request by opaque tracking code, then locked its latest quote.
- Made same-payload replay return the stable success representation; a changed replay remains `409`.
- Added an append-only `ExpertConsoleLog` event with action, response, quote lineage, time, and source IP.
- Removed internal quote ID from customer workflow/response payloads and changed the frontend to use `tracking_code`.
- Added focused valid, invalid/numeric, replay, changed replay, expiry, cross-scope, no-ID, and audit tests.

## 5. Security Validation

Required behavior: valid accept/decline succeeds; invalid, numeric, and foreign capability return indistinguishable `404`; expiry fails closed; same replay is idempotent; changed replay is `409`; no request/quote selector can be supplied to cross scope; response payload has no quote ID; successful mutation is audited. PostgreSQL row locks serialize request/quote response races. The repository’s `rate_limit` decorator is a non-enforcing placeholder, so it was not represented as protection.

## 6. Git Commit / State

The closure is a bounded working-tree change. No commit is created automatically because the repository already contains unrelated untracked user work, including FE-0 and release evidence. Economics implementation is not mixed into this change.

## 7. Remaining Security Limitation

The broader legacy customer dashboard/profile/workflow and public-tracking read boundaries still expose numeric identities and customer/quote information. They require a separate security review and capability migration. Tracking codes are bearer capabilities and are not independently revocable per quote; production-grade distributed rate limiting is absent. These do not reopen the closed numeric-ID quote-response mutation, but should be scheduled as P1 defense-in-depth.

**PART A FINAL STATE: P0 SECURITY CLOSED**

## 8. Executive FE-1 Summary

Create a dedicated **Shipment Economics** bounded context in the modular monolith. Its authoritative unit is an `EconomicLine` containing append-only staged `EconomicObservation` facts. Original Money is inseparable from currency; FX application is explicit; correction preserves history; cross-subject amounts require allocations; margin and completeness are derived and abstain when truth is missing. Forwarder owns operational commercial economics, not statutory accounting. FE-1 is a contract only.

## 9. Economics Bounded Context

Economics owns economic lines, observations, allocations, applied FX bases, evidence associations, authority metadata, external financial references, and rebuildable projections. Commercial owns quotes and acceptance; Operational Execution owns shipment lifecycle; Project aggregates; MDPM owns document readiness; master-data domains own governed parties/services; ERP owns ledger, journals, tax accounting, bank reconciliation, and—unless business owners decide otherwise—formal invoice/payment/settlement truth. Dependencies point from source-domain contracts into Economics, then projections to future consumers. OIP and AI may consume but never create economic truth.

Initial primary subject is `OperationalShipment`; `Project` is an explicit aggregation/allocation subject. A legitimate project/shared charge may be project-scoped and allocated. `ExecutionUnit` is deferred.

## 10. Current Quote Integration

`ExpertQuote` is reusable only as commercial intent: amount/currency, note, validity, creation time/actor, request lineage, and customer response. On admission, Economics snapshots the exact quote identity/version-equivalent fingerprint, amount and currency, terms available, accepted-at evidence, source organization/subject resolution, and adapter version. The mutable legacy row remains the source reference, not Economics truth.

Insufficient data includes line-item breakdown, governed category, canonical counterparty, tax/gross-net semantics, acceptance authority, organization completeness, terms, evidence version, and correction lineage. An offered quote may create an `ESTIMATE` candidate. An accepted quote may create commitment only after FE-B01 defines the commitment event and an admission policy validates all mandatory data. It must never silently become `ACTUAL`, recognized revenue, invoice, collection, or margin. `estimated_value`, CRM `Opportunity.value`, and cargo value are rejected as authoritative economics; adapters may retain them as labeled source references only.

## 11. Economic Line Contract

Repository naming supports `EconomicLine` and `EconomicObservation`.

`EconomicLine` requires: opaque UUID `public_id`; `organization_id`; primary subject `{type, public_id}`; `side` (`REVENUE|COST`); governed economic category/service reference; counterparty reference and role; optional decimal quantity plus governed UOM; lifecycle (`ACTIVE|CANCELLED`); integer `version`; creator and recorded time. It is the durable identity of one meaningful charge/revenue component, not an account or journal entry.

Amounts do not live as a mutable line total. Each `EconomicObservation` requires opaque identity; line; stage; Money; effective and recorded times; source type plus opaque source identity/fingerprint; authority type/actor; status (`PROPOSED|AUTHORIZED|SUPERSEDED|REVERSED` as applicable); reason; version/predecessor or supersedes identity; approval time where policy requires it; and evidence associations. Quantity/UOM belongs on the observation if it changes economically; otherwise it may be the line classification basis. Cross-tenant references are structurally forbidden.

## 12. Estimate / Commitment / Actual Contract

| Stage | Meaning | Cause | Multiplicity/current selection | Correction |
|---|---|---|---|---|
| `ESTIMATE` | best authorized expectation, not obligation | quote, forecast, or authorized manual estimate admitted under policy | many over time; current is latest effective authorized non-reversed observation in one explicit lineage | supersede wrong/outdated estimate; adjustment for a separate additive component |
| `COMMITMENT` | commercially binding obligation/right | only the business event approved under FE-B01/FE-B03 | multiple commitments may exist for distinct components; one lineage cannot have two current versions | changed price is a new superseding commitment or additive line, never an edit |
| `ACTUAL` | approved/incurred operational economic fact | evidence and authority defined under FE-B03, independent of invoicing | multiple actual components may accumulate; projection sums compatible current facts | adjustment, reversal, or supersession according to error semantics |

Actual may exist without commitment (for example an emergency surcharge), but must be flagged `commitment_gap` and authorized under policy. Commitment may differ from estimate; variance explains the difference. No automatic stage promotion exists. “Current” is a deterministic projection, not a mutable pointer accepted without validation.

## 13. Revenue Contract

- Quoted customer amount: Commercial Intent, source-owned.
- Customer-accepted/agreed amount: commercial decision evidence; candidate input to commitment.
- Committed revenue: Economics fact only after the approved commitment event and authority policy.
- Actual/recognized revenue: unresolved business/accounting semantics; ERP recognition is an external reference by default.
- Invoiced amount: external invoice fact/reference, not revenue.
- Collected amount: external payment/allocation reference, not revenue.

The initial slice may support estimated and committed revenue but must defer recognized revenue unless FE-B01 is approved.

## 14. Cost Contract

Supplier/carrier estimate and quotation are estimate observations with distinct source/evidence. A purchase order, carrier booking, accepted supplier offer, or other approved event may produce commitment only under FE-B03 policy. Actual cost is an approved/incurred fact, not merely an invoice arrival. Supplier invoices and settlement remain external references by default. Multiple actuals are normal: freight, handling, demurrage, surcharge, correction, and credits remain separate lines or explicit adjustments. A late surcharge appends truth; it never rewrites the original commitment.

## 15. Party / Service Classification

Economics references governed opaque party identities; it does not create a party master. Roles include `CUSTOMER`, `CARRIER`, `FORWARDER`, `AGENT`, `SUPPLIER`, and `OTHER_COUNTERPARTY`. Existing CRM Customer and governed carrier/agent/supplier identities may be referenced through typed adapters when organization ownership and lifecycle are reliable. A temporary external-party reference may be allowed only by an approved gap policy and cannot masquerade as canonical master data.

Use governed `ServiceType`/Project service when its semantics match. Add a small governed economic charge-category catalog only for missing economic classifications and link it to service type. Free text is explanatory, never the category key. No chart of accounts is introduced.

## 16. Money Contract

`Money = {amount: decimal string, currency: ISO-4217 uppercase code}`. Persist fixed/variable precision decimal, never float; currency metadata defines allowed minor units, while storage must preserve supplied precision needed for logistics rates. API accepts/returns canonical non-exponent decimal strings and rejects numbers where precision could be lost. Rounding is explicit, purpose-specific, deterministic (default mechanism: decimal half-even only after policy approval), and records pre-rounded value/basis when consequential.

Money compares or aggregates only when currencies match. Original transaction Money is immutable. Storage does not normalize currency. Zero is valid only when explicitly recorded and authorized; absence is null/unknown, never zero. Currency code authority and exceptional/non-ISO currencies require governance.

## 17. FX Contract

Separate `FXRateObservation` from `FXApplication`. A rate observation identifies from/to currencies, decimal rate, rate kind, source, source identity, effective time, recorded time, authority, evidence, status/version and supersession. An application binds one economic observation/projection purpose to one exact rate observation, direction, calculation/rounding rule, original Money and converted Money.

Initial supported kinds should be only those approved for the slice: likely `CONTRACTUAL` and `MANUAL_APPROVED`, with `MARKET_REFERENCE` optional for expected projections. `SETTLEMENT` and `REPORTING` remain separate future purposes. Missing, stale, disputed, reversed, or unauthorized rates cause abstention. No rate inversion or triangulation occurs unless explicitly recorded by the application policy. FE-B04 must name authorities and freshness rules.

## 18. Temporal Model

All system instants are timezone-aware UTC; business dates retain their declared zone where relevant. Every fact has `effective_at` (when economically true) and `recorded_at` (when Forwarder learned/stored it). Source-specific times are retained only when justified: `quoted_at` on admitted quote source; `committed_at` for commitment event; `incurred_at` and optional `approved_at` for actual; `invoiced_at`/`paid_at` only on external references; `superseded_at` on history transition. Recorded time never substitutes for effective time. As-of projections filter both temporal dimensions explicitly.

## 19. Correction / Reversal Model

- **Supersede** when the same fact/lineage was wrong or replaced (wrong estimate, changed supplier price before separate performance, currency correction). New fact points to old; old remains visible.
- **Adjustment** for a legitimate additive/subtractive later economic event (late surcharge, discount, variance component). It has its own Money, reason, authority, and lineage.
- **Reversal** negates/cancels a fact that should no longer contribute while preserving that it once existed (credit note, cancelled service release, erroneous actual). It references the target and records reversal Money/rationale.

Wrong estimate → supersede. Changed supplier price → supersede commitment if replacement, adjustment if additional scope. Late surcharge → adjustment/new line. Incorrect actual → supersede or reversal plus corrected actual. Credit note → reversal/negative adjustment linked to original. Cancelled service → policy-driven reversal; never deletion. Currency error → supersede both observation and affected FX applications. Consequential records are never hard-edited.

## 20. Allocation Model

`EconomicAllocation` assigns source observation/external-document Money to typed `OperationalShipment` or `Project` targets. It records opaque identity, organization, source identity/version, target, allocated Money, currency basis/FX application if conversion was authorized, method/reason, actor/authority, effective/recorded times, version/status and predecessor/reversal.

Invariants: same-currency allocations sum no greater than source amount except an explicitly versioned tolerance; converted allocation reconciles through exact FX applications; no implicit equal split; unallocated amount is derived and visible; concurrent writes lock source/version and use expected version; reallocation reverses/supersedes old allocations then appends new ones; target and source must be tenant-safe. Partial allocation makes affected aggregate completeness explicit.

## 21. Economic Projections

Rebuildable shipment/project projections provide `EXPECTED`, `COMMITTED`, and `ACTUAL` views. Each reports compatible revenue, cost, derived margin, margin percentage only under approved denominator policy, estimate-to-commit/actual variances, and completeness. Output includes as-of/basis, `calculated_at`, input fingerprint, stage/category coverage, original currencies, reporting currency and exact FX applications, missing inputs, policy version, and freshness/health.

A projection is never authority. It sums current authorized observations and allocations only. Project totals aggregate shipment and project-scoped allocations without double counting.

## 22. Economic Completeness

Create an Economics-owned `EconomicReadinessProjection`, separate from operational status and MDPM document readiness. Dimensions may include revenue terms known, required cost categories covered, currencies valid, FX available for requested basis, mandatory economic evidence satisfied, unresolved material estimates, allocation reconciliation, and actual-cost completion. States are `COMPLETE|INCOMPLETE|UNKNOWN|NOT_APPLICABLE` with reasons and policy version. Recommend exposing it to MDPM/OIP as a consumed dimension later; do not make MDPM its owner.

## 23. ERP / Accounting Boundary

An anti-corruption adapter exchanges only bounded records: external system and opaque ID, document/reference type, status, original Money, relevant dates, external version, sync state/version, idempotency identity, payload hash, reconciliation state and last verified time. Outbound export may include authorized economic facts; inbound imports create/update versioned external references, never economic observations merely because import succeeded.

ERP wins for ledger, statutory tax, journal, invoice/payment/settlement and bank-reconciliation truth unless FE-B02 assigns a bounded exception. Economics wins for its staged operational facts and allocations. Conflicts create `RECONCILIATION_REQUIRED`; neither side silently overwrites the other. ERP unavailability marks references stale/unknown and queues retry.

## 24. Security / Visibility Model

Define capabilities independently: `economics.sale.view/manage/approve`, `cost.view/manage/approve`, `margin.view`, `fx.view/apply/approve`, `actual.create/approve`, `adjustment.create/approve`, `allocation.manage/approve`, `erp.sync/view`, and sensitive export. Tenant-first opaque lookup is mandatory. Existing role machinery may map to these permissions but current coarse quote/operational roles are insufficient. Supplier cost and margin are not visible to every operational user. Material changes should support separation of duties per FE-B03. Every mutation and sensitive export is audited; logs/errors redact Money/evidence where access is absent.

## 25. Concurrency / Idempotency Contract

Commands carry opaque idempotency key, payload hash, aggregate `expected_version`, actor and organization. Same key/hash returns prior result; same key/different hash conflicts. Promotion/approval uses row lock or compare-and-swap so only one current lineage version wins. Allocation locks the source total/version. FX selection locks the projection purpose/observation pair. External imports uniquely constrain `(source_system, external_event_id)` and reject changed payload replay. Duplicate estimates are not merged solely by amount; a documented semantic source key distinguishes duplicate submission from legitimate recurrence. PostgreSQL race tests are an entry gate.

## 26. Evidence Contract

`EconomicEvidenceReference` links an observation/allocation/FX/external reference to exact `CaseDocumentFile`/artifact public identity and version, or a governed external locator. It records evidence role, actor, association time, visibility and source fingerprint. Economics does not copy binaries or infer authority from upload alone. Replacing or superseding a document creates a new association for later facts; historical facts continue pointing to the version that supported them. MDPM assessment may satisfy an evidence policy only by exact version.

## 27. Future OIP Economic Situations

| Situation | Required authoritative facts | FE first slice | Additional policy required |
|---|---|---:|---|
| `MARGIN_EROSION` | compatible baseline/current revenue and cost, FX, completeness | partial | materiality, comparison basis |
| `NEGATIVE_MARGIN` | complete compatible committed/actual revenue and cost | partial | margin denominator/basis |
| `UNAPPROVED_COST_INCREASE` | prior commitment, new cost, approval state | yes conceptually | materiality/approval hierarchy |
| `MISSING_COMMITTED_COST` | required category policy and shipment phase | partial | required-cost timing |
| `UNBILLED_COMPLETED_SHIPMENT` | completion plus authoritative invoice state | no | invoice ownership/timing |
| `UNSETTLED_SUPPLIER_OBLIGATION` | obligation and settlement state | no | payable/settlement policy |
| `FX_EXPOSURE` | currency obligations, authorized valuation rates | partial | exposure horizon/rate policy |

No OIP signal is authorized in FE-1. Each future signal must require healthy, complete projections and deterministic policy.

## 28. Abstention Contract

`INCOMPLETE`: known required facts are missing/partial (cost, revenue, allocation, actual completion, evidence). `UNKNOWN`: truth cannot currently be determined (ERP unavailable, invoice/payment state unavailable, disputed/stale FX). `NOT_APPLICABLE`: policy says the metric/dimension does not apply. A result abstains from totals/margin when mandatory revenue or cost is missing, currencies differ without authorized FX, allocation is partial for the requested scope, actual-cost completion is unknown, a required source is stale/disputed, or recognition/invoice/payment semantics are unresolved. Responses include reason codes and missing inputs. Never substitute zero or FX=1.

## 29. Architecture Decision Register

| ID | Decision | Status |
|---|---|---|
| FE-A01 | Dedicated Shipment Economics bounded context | approved by FE-D01 |
| FE-A02 | `EconomicLine` + immutable staged `EconomicObservation` | proposed for approval |
| FE-A03 | Shipment primary subject; Project aggregation/allocation; ExecutionUnit deferred | approved/proposed detail |
| FE-A04 | Decimal Money with inseparable governed currency | approved by FE-D07 |
| FE-A05 | Explicit `FXRateObservation` + `FXApplication` | approved by FE-D08; authority pending |
| FE-A06 | Append, supersede, adjust, reverse; no consequential overwrite | approved by FE-D05/D06 |
| FE-A07 | Exact-version evidence association; no binary duplication | approved by FE-D11 |
| FE-A08 | Explicit versioned allocation, residual, and locking | approved by FE-D12 |
| FE-A09 | Provenance/completeness-bearing rebuildable projections | approved by FE-D09/D10 |
| FE-A10 | ERP anti-corruption boundary; no GL | approved by FE-D02/D13 |
| FE-A11 | Economics-owned readiness separate from operational/MDPM status | proposed for approval |
| FE-A12 | Capability permissions, expected versions, idempotency and outbox/reconciliation | proposed for approval |

## 30. Business Decision Register

| ID | Human decision | Recommended default / impact |
|---|---|---|
| FE-B01 | event constituting revenue commitment and actual/recognition | acceptance may commit only with valid authority/terms; ERP recognition reference by default |
| FE-B02 | invoice/payment/settlement ownership | ERP owns; Forwarder keeps bounded references |
| FE-B03 | sale/cost/actual/adjustment approval hierarchy and separation | capability matrix; dual approval for material changes |
| FE-B04 | FX sources, authorities, rate purposes and freshness | purpose-specific contractual/manual-approved first |
| FE-B05 | tax and gross/net treatment | ERP authoritative; defer local tax |
| FE-B06 | minimum category coverage/readiness policy | version per service/transport profile |
| FE-B07 | rounding, tolerance, materiality and margin-% denominator | currency/purpose-specific policy; no global magic value |
| FE-B08 | cancellation obligation/release rules | explicit reversal/adjustment under contract policy |

These are business authority questions. Aggregate design, locking, UUID choice, and adapter mechanics are not sent to humans as business decisions.

## 31. Recommended FE Implementation Slice

After approval, implement the smallest useful vertical slice: tenant-safe `EconomicLine` and immutable `EconomicObservation`; decimal Money; `ESTIMATE` and `COMMITMENT` for customer revenue and supplier cost; explicit evidence association; supersession; accepted-quote admission adapter; shipment/project expected and committed projections with completeness; one approved FX application purpose; bounded permissioned API/UI; audit/idempotency; PostgreSQL race and cross-tenant tests. Defer `ACTUAL` if FE-B03 is unresolved. Defer invoices, payments, settlements, tax, ERP sync, ExecutionUnit economics, OIP, and AI.

## 32. FE Implementation Entry Criteria

FE-2 implementation cannot begin until humans approve: bounded context and subject scope; line/observation model; stage causes/authorities; Money serialization/rounding; FX authority/purpose/freshness; quote admission and revenue commitment semantics; category/readiness coverage; allocation/tolerance; evidence policy; correction model; ERP ownership; visibility/approval permissions; abstention reason/state behavior; and the exact initial slice/deferred list. ADRs, API draft, migration/recovery plan, security threat model, and PostgreSQL test matrix must be reviewed before code.

## 33. Framework Delta

| Project finding | Framework delta | Classification |
|---|---|---|
| fragmented quote/operational fields cannot jointly own truth | validates bounded ownership | **CONFIRMS EAAF** |
| Money/FX weakest-link abstention | candidate reusable contract | **PATTERN CANDIDATE** |
| immutable staged observations and correction | candidate temporal pattern | **PATTERN CANDIDATE** |
| exact-version MDPM evidence association | concrete reusable example | **REFERENCE EXAMPLE CANDIDATE** |
| allocation residual/version/concurrency | broader reusable economic pattern, insufficient evidence for enterprise promotion | **PATTERN CANDIDATE** |
| ERP anti-corruption and projection health | already covered boundary/derived-health principles | **NO FRAMEWORK CHANGE** |

No `29-lpaf` modification is authorized.

## 34. Human Decisions Required

Required before the recommended slice: FE-B01, FE-B03, FE-B04, FE-B06, and FE-B07, plus approval of FE-A02/A03 detail/A05/A11/A12. FE-B02 must be affirmed even if ERP integration is deferred. FE-B05 and FE-B08 may be explicitly deferred only if tax and cancellation fail closed and remain outside the slice. No further discovery is required to approve the architecture contract; targeted policy workshops are required to approve business semantics.

## 35. Recommended Next Action

Hold one architecture/product approval workshop using sections 29–32. Record accepted decisions as ADRs and versioned business policies, then authorize a separate FE-2 implementation plan for the minimal slice. Independently schedule the broader legacy customer read-boundary/capability review and production distributed rate limiting.

**PART B FINAL STATE: FE-1 CONTRACT READY FOR HUMAN APPROVAL**

Economic truth is not accounting. Price, invoice, and payment are not revenue. Estimate is not commitment; commitment is not actual. Unknown is not zero. Margin is derived, FX is explicit, and corrections preserve history and evidence lineage.

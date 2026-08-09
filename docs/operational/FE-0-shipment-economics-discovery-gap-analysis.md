# FE-0 — Shipment Economics / Financial Truth Discovery & Gap Analysis

| Field | Value |
|---|---|
| Document status | **DISCOVERY / PROPOSED — not accepted architecture** |
| Phase | FE-0 architecture discovery only |
| Repository observed | `D:\1-webapp\15-forwarder` working tree, 2026-08-08 |
| Knowledge base observed | `D:\1-webapp\29-lpaf`, 2026-08-08 |
| Implementation authority | None; this document authorizes no schema, API, UI, permission, OIP, MDPM, deployment, or production change |

Throughout this report, **Observed** means directly supported by repository evidence. **Proposed** means a recommendation requiring architecture review. **Business decision** means Codex cannot legitimately choose the policy.

## 1. Executive Summary

**Observed.** Forwarder does not yet have an authoritative Financial/Economics domain. The only persisted monetary-looking concepts are:

- `ShipmentRequest.estimated_value`, a nullable unqualified `Float` with no currency;
- `ExpertQuote.amount/currency`, a whole-request customer offer with acceptance/decline metadata;
- `Opportunity.value/currency`, a legacy CRM pipeline estimate;
- `cargo_value`, a declared cargo value without consistently modeled currency, which is not sale revenue;
- the accepted quote lineage on `OperationalShipment`, exposed in operational responses as `quote_amount` without its currency.

There are no canonical charges, supplier/carrier costs, commitments, actuals, FX rates, taxes, invoices, payments, settlements, commissions, receivables, payables, credit notes, or margin records. Existing quote data is **partially authoritative commercial intent**, not authoritative revenue recognition, invoicing, collection, or shipment economics. The current system therefore cannot truthfully calculate margin.

**Recommendation.** Add a separate **Shipment Economics** bounded context inside the modular monolith. Its central aggregate should be a versioned economic obligation/line with explicit side, party, subject allocation, Money, lifecycle observation (`ESTIMATE`, `COMMITMENT`, `ACTUAL`), effective/recorded time, source/evidence, and supersession/reversal semantics. Keep invoices, payments, and settlements as external or locally authoritative references according to future business decisions; keep the general ledger, statutory accounting, chart of accounts, tax accounting, and bank reconciliation outside Forwarder. Derive shipment/project economics and readiness as projections; OIP consumes those projections later and never supplies economic truth.

The principal FE-1 blockers are business authority for FX, “actual” and revenue-recognition meanings, invoice/payment ownership, tax scope, approval roles, and materiality—not a lack of technical design options.

## 2. Repository Evidence Reviewed

The review covered models, migrations, services, routes, API contracts, UI, tests, and operational architecture. Primary evidence includes:

- Monetary/legacy: `backend/models.py` (`ShipmentRequest`, `ExpertQuote`, `Opportunity`), quote/customer workflow services, quote routes, migrations `20250223_add_expert_quote.py`, `20260728_add_quote_customer_response.py`, and CRM migrations.
- Operational: `backend/operational_models.py`, `backend/services/operational_service.py`, `backend/routes/operations.py`, migrations `20260805_add_project_aggregate_foundation.py`, `20260729_add_operational_vertical_slice.py`, and operational tests.
- UI/contracts: `src/components/QuoteModal.tsx`, customer/expert/request/operational pages, `src/lib/api.ts`, `docs/openapi/openapi.yaml`, and frontend tests.
- Documents/MDPM: `backend/models.py` document records, `backend/mdpm_models.py`, document/MDPM services, ADR-020, ADR-030, `mdpm-1-document-readiness-slice-contract.md`, and MDPM candidate evidence.
- OIP: models/services/routes/tests, OIP-1 contract, OIP-2 contract, ADR-031/032, and OIP-2 candidate evidence.
- Architecture: FDM-001, FDD-001, operational execution matrix; ADR-001/002/003/007/010/016/017/019/020/027/029/030/031/032; time architecture material.
- Knowledge base: GOV-005/008/009/011, applicable ASTD/PAT/ADR/template indexes, bounded-context/aggregate/data/integration skeletons, retry/idempotency, outbox, anti-corruption, supersession, and ARCH-000 chapter material.

Important constraint: most `29-lpaf` standards, reference patterns, and book chapters are labeled draft skeletons. They provide headings and intent, not detailed mandatory rules. GOV-011 is the substantive adopted authoritative assurance source. No file in `29-lpaf` was modified.

## 3. Current Financial/Economic Landscape

| Concept / storage | Owner and purpose | Identity / tenant / time / mutation | Classification |
|---|---|---|---|
| `ShipmentRequest.estimated_value` | Legacy commercial request hint | request numeric ID; no amount currency; generic request timestamps/logging; normal mutable request field | **AMBIGUOUS** |
| `ExpertQuote` | Expert whole-request offer to customer | numeric ID; request FK; optional operational organization added later; integer amount + free string currency; `created_at`, validity date, response time; append new quote but response edits row | **PARTIALLY_AUTHORITATIVE** commercial offer only |
| `Opportunity.value/currency` | Legacy CRM pipeline valuation | numeric ID; customer FK; no organization boundary in model; float + 3-char default; mutable generic timestamps | **PARTIALLY_AUTHORITATIVE** CRM forecast, not shipment economics |
| request/cargo `cargo_value` | Goods declaration/context | request-owned; plain float; no attached currency in contract | **AMBIGUOUS**, explicitly not revenue |
| `OperationalShipment.accepted_quote_id` | immutable commercial lineage into execution | organization-scoped shipment; unique quote; quote locked and tenant checked during creation; shipment has optimistic version | **AUTHORITATIVE** lineage, not economic amount |
| operational `source.quote_amount` | API/UI convenience copied from accepted quote | derived at read time; currency omitted; numeric internal quote/request IDs exposed in API type | **DISPLAY_ONLY / unsafe derived** |
| customer quote response | accepted/declined response on latest quote | customer/request numeric path/body; row updated once; no explicit version/lock/idempotency key | **PARTIALLY_AUTHORITATIVE** decision evidence |
| supplier/carrier master | carrier is mostly free `carrier_reference`; CRM customer may be typed vendor | no governed economic counterparty/contract authority | **MISSING / AMBIGUOUS** |
| costs, revenue stages, charges, FX, tax, invoice, payment, settlement, commission, margin | no implemented canonical model/API/service/UI | none | **MISSING** |

No Money value object exists. No current model makes a financial amount inseparable from a governed currency.

## 4. Current Economic Lifecycle

**Observed lifecycle:**

`Customer demand (ShipmentRequest)` → `expert creates whole-request ExpertQuote` → `request becomes waiting_for_customer` → `customer accepts/declines latest quote` → `authorized user creates one OperationalShipment from accepted quote with tenant check, row lock, uniqueness and idempotency` → `operational execution`.

Observed divergences and gaps:

- Status can include `quoted`, `waiting_for_customer`, `won`, `lost`, and `closed`, but status is not an economic fact.
- Acceptance does not create a versioned contracted-revenue fact; it only changes `customer_response`.
- A quote can be created by admin or the assigned expert. There is no separate commercial approval.
- No supplier quotation/selection, expected cost, cost commitment, actual cost, invoicing, collection, payment, or settlement follows.
- Multiple quotes are retained, but “latest by `created_at`” is used; explicit supersession/current identity is absent.

Missing stages are commercial agreement formalization, expected/committed/actual revenue and cost observations, evidence association, invoice/payment/settlement references, FX normalization, corrections, and derived economics.

## 5. Current Source-of-Truth Matrix

| Concept | Current source / authority | Current problems | Recommended owner and nature | Required change | Risk |
|---|---|---|---|---|---|
| Customer sale | accepted `ExpertQuote`; customer response | whole-request, mutable response, weak tenant history, no terms/lines | Economics; authoritative commercial commitment derived from accepted version | admit/snapshot accepted quote into governed line(s) | P0 |
| Supplier/carrier cost | none; free carrier reference | no counterparty, quote, obligation, or evidence | Economics; authoritative estimate/commitment/actual | governed party reference and cost lines | P0 |
| Charge/economic line | none | no common unit of economics | Economics; authoritative append/versioned aggregate | introduce canonical line model | P0 |
| Currency | free strings/defaults; absent on estimates/cargo/operational response | no catalog, exponent, validation, inseparability | Economics/reference contract; authoritative code metadata | Money VO + governed ISO-style code policy | P0 |
| FX rate | none | normalization impossible | Economics or external market-data adapter; authoritative selected basis | rate observation/selection contract | P0 |
| Tax | none | gross/net cannot be stated | Economics only if business owns it; otherwise ERP external | tax component/reference policy | P1 |
| Invoice | vocabulary only, no implementation | invoice could be confused with revenue | ERP external or bounded invoice-reference aggregate | decide ownership and import/link contract | P1 |
| Payment | none | receivable/payable/cash unknown | ERP/payment system external or bounded reference | decide ownership; idempotent import | P1 |
| Settlement | none | obligations cannot be closed | ERP/external or bounded status reference | decide ownership and allocation | P1 |
| Commission | none | party obligation unavailable | Economics if operational commitment; accounting downstream | line/category policy | P2 |
| Margin | none | any calculation would use incomplete truth | Economics projection; **derived** | completeness-aware projection | P0 |
| Economic evidence | CaseDocument/MDPM artifacts exist | no economic association or evidence type/policy | documents remain binary owner; Economics owns typed references | exact-version association, no copy | P1 |

## 6. Revenue Model Findings

Quoted revenue exists only as `ExpertQuote.amount/currency`. Customer acceptance is evidence of commercial intent, but the repository does not establish whether it is contracted, expected, committed, recognized, invoiced, or collectible revenue. `Opportunity.value` is a CRM forecast and `cargo_value` is goods value; neither may feed margin. Revenue stages are currently collapsed or missing.

**Proposed:** preserve distinct observations for `QUOTED`, `AGREED/COMMITTED`, and `ACTUAL/RECOGNIZED` without treating invoice or collection as recognition. Maintain separate invoice and cash allocations. A later business-approved recognition policy determines “actual revenue.”

## 7. Cost Model Findings

No cost model exists. `carrier_reference` is operational text, not a supplier identity or cost. The system has no estimated, quoted-supplier, committed, accrued/actual, invoiced, or paid cost distinction and cannot state payables.

**Proposed:** represent supplier/carrier costs as economic lines using the same lifecycle observation mechanism as revenue, while separating counterparty obligation, supplier invoice, and payment allocation.

## 8. Estimate / Commitment / Actual Findings

The repository retains multiple quotes but does not model epistemic progression. It cannot explain “thought 1,000; committed 1,050; actual 1,080.”

**Proposed:** a stable economic line identity has append-oriented observations. Each observation records stage, Money, quantity/unit, effective time, recorded time, actor/authority, reason, source, evidence references, and predecessor/supersession. Promotion creates a new observation; it does not mutate the estimate. Corrections supersede or reverse the erroneous observation. Do not use one mutable status/amount row as the history.

## 9. Shipment vs Project Economics

Observed domain structure supports Project as coordination/aggregation boundary, OperationalShipment as execution aggregate, ShipmentRequest as commercial intent, and ExecutionUnit as independently managed execution. Therefore Shipment cannot be the only economic subject.

**Proposed rules:**

- A line has one primary economic subject (`PROJECT`, `SHIPMENT`, or later governed types) and zero or more explicit allocations.
- Shipment-level cost need not attach to an ExecutionUnit.
- One supplier cost or invoice may allocate across shipments/projects; the document/reference is not duplicated.
- One customer invoice may cover multiple shipments.
- Project economics is a derived aggregation of directly project-owned lines plus allocated shipment lines, with double-count prevention.
- ExecutionUnit/route-leg allocation is optional and only authoritative when explicitly recorded; never infer it.

## 10. Currency / FX Findings

Unsafe current behavior includes plain floats, default/fallback IRR, arbitrary currency strings, omission of currency from operational `quote_amount`, UI rounding, two hard-coded UI currencies, and no scale/exponent or FX basis. `unknown FX ≠ 1`.

**Proposed Money:** decimal minor/major-unit-safe amount plus governed currency code and scale rules, serialized together. Never binary float. Each normalized amount records transaction Money and selected FX observation: reporting currency, rate as decimal, direction, source, rate type, observed/effective time, selected time, selector/authority, and whether contractual/manual/settlement. Changing FX selection is versioned. FX variance is derived by comparing approved bases; it is not silently folded into cost/revenue.

## 11. Temporal Semantics

Current quotes have `created_at`, `valid_until`, and `responded_at`; operations use timezone-aware effective/occurred/recorded concepts, while legacy financial hints use naive/generic timestamps. `updated_at` is insufficient.

Required proposed distinctions are `quoted_at`, `agreed_at`, `committed_at`, `incurred_at`, `recognized_at`, `invoiced_at`, `paid_at`, plus universal `effective_at`, `recorded_at`, and `superseded_at/reversed_at`. Use UTC instants for events, local-date semantics only where contracts require a civil date, and record timezone/basis. Corrections append; current views resolve the supersession graph.

## 12. Economic Evidence

Existing CaseDocument/MDPM architecture already separates binary artifact, exact-version association, assessment, and readiness. It prohibits binary duplication and carries tenant-first, exact-version rules.

**Proposed:** Economics owns `EconomicEvidenceReference` associations to existing opaque artifact/version identities or external reference locators. Association records evidence role (customer offer, supplier quote, contract, invoice, rate evidence, payment evidence, approved adjustment), subject line/observation, actor, time, and visibility. Economics does not copy binaries and does not let document approval automatically decide economic authority. MDPM remains document readiness owner; an economic projection may consume document assessment where policy explicitly requires it.

## 13. Authority / Permission Findings

Current quote creation is admin-or-assigned-expert access, not a granular financial permission. Operational creation has explicit permission/membership checks, while the customer quote-response route has no authentication decorator and relies on numeric `customer_id` plus request ownership matching. Existing operational permissions do not cover commercial confidentiality or finance mutations.

**Authority gaps:** no distinct authority to approve sale rate, commit supplier cost, select/manual-override FX, approve actual, adjust/reverse, link invoice, record/import payment, view supplier cost versus customer sale, or export economics. FE-1 must not invent organizational roles; it should define permission capabilities and map them only after business approval.

## 14. Correction / Reversal Findings

Operational events and MDPM demonstrate append/supersession patterns. Quote response and legacy values update in place; quotes have no explicit supersedes relation, cancellation, correction, or credit-note semantics.

**Proposed:** estimates may be superseded; commitments and actuals are append-oriented and corrected by supersession, reversal, or adjustment. Reversal references the exact prior observation and negates its economic effect; adjustment records only the delta or explicitly replaces under policy. Never delete evidence-bearing facts. Current-state projections remain rebuildable from the chain.

## 15. Accounting / ERP Boundary

**Forwarder should own:** operational commercial intent; customer/supplier commitments relevant to shipment execution; shipment/project economic lines and allocations; selected FX basis; economic evidence links; completeness; and references/status/allocation for external invoice, payment, and settlement data when authorized.

**ERP/accounting should own:** general ledger, journals, chart of accounts, statutory recognition, formal tax accounting/returns, bank reconciliation, fiscal close, accounting periods, and statutory receivable/payable balances.

Use an anti-corruption adapter with external IDs, source-system identity, external version/event time, ingestion time, idempotency key, and reconciliation status. Forwarder must not manufacture accounting truth when ERP is unavailable.

## 16. Margin Model

Margin is always derived. For a selected reporting currency and explicit as-of/effective basis:

- Expected margin = eligible expected revenue − eligible expected cost.
- Committed margin = eligible committed revenue − eligible committed cost.
- Actual margin = business-defined actual revenue − approved actual cost.
- Cash position/margin = allocated collections − allocated payments; never a substitute for actual margin.

Margin percent needs an approved denominator and zero/negative-revenue policy. Every output includes reporting currency, FX basis/version, as-of time, input observation IDs, completeness state, and missing-data reasons. Unknown required revenue/cost/FX means `INCOMPLETE/NOT_COMPUTABLE`, not zero. Mixed-currency totals without approved normalization abstain.

## 17. Economic Completeness / Readiness

An economic readiness concept is useful but should be a deterministic projection owned by Economics, parallel to—not inside—MDPM. Inputs may include accepted sale terms, required charge-category coverage, supplier cost status, currency, FX basis, evidence, unresolved estimates, and approval exceptions. MDPM supplies document readiness facts only when explicitly referenced by policy. OIP may consume the result later.

Readiness should report `READY`, `NOT_READY`, or `UNKNOWN/NOT_EVALUATED` with stable blocker codes. Materiality thresholds and required categories are business policy, versioned and fail closed.

## 18. OIP Future Integration

OIP remains unchanged. Future classifications:

| Future Situation | Classification / prerequisite |
|---|---|
| margin erosion; negative margin; unapproved cost increase; missing supplier cost; unbilled completed shipment; unsettled supplier obligation; FX exposure; commercial deviation | **SUPPORTED BY FUTURE ECONOMIC TRUTH** once versioned inputs, policy, completeness, and FactReferences exist |
| overdue receivable | **STILL REQUIRES ADDITIONAL AUTHORITY/DATA**: due terms, authoritative invoice/receivable and payment allocations |
| tax exposure, statutory loss, accounting misstatement | **STILL REQUIRES ADDITIONAL AUTHORITY/DATA** from ERP/tax/accounting boundary |
| carrier profitability/reliability | **STILL REQUIRES ADDITIONAL AUTHORITY/DATA**: governed carrier identity, allocation, cohort and outcome policy |

OIP signals reference immutable/versioned economic facts, abstain on incomplete projection health, and never calculate independent finance truth.

## 19. AI Future Readiness

A trustworthy domain can later provide structured DecisionContext for margin variance, unresolved exposure, post-quote changes, and commercial attention. Context must include fact identities, stages, times, currency/FX, evidence, completeness, and missing information. AI may explain or propose review; it must not create amounts, select facts/FX, approve adjustments, resolve completeness, or execute economic commands.

## 20. Security Findings

- **P0:** customer quote response appears unauthenticated and uses enumerable numeric customer/request identifiers; ownership matching reduces but does not remove impersonation/enumeration risk.
- Legacy quote/request/CRM models have inconsistent tenant ownership. `ExpertQuote.operational_organization_id` is nullable and populated only when the creator has exactly one active membership.
- Operational shipment creation correctly checks permission, organization, quote acceptance, row lock, uniqueness, and idempotency, but read payload exposes internal IDs and omits quote currency.
- No financial field-level visibility separates supplier cost from customer sale or protects commercial margins.
- Quote APIs return numeric quote/request identities; bulk-export/report authorization for future economics is absent.
- Free text, logs, exceptions, and audit metadata need redaction rules so prices/evidence do not leak.
- Future composite FKs/queries must make cross-tenant subject, party, evidence, FX and allocation references impossible and return indistinguishable not-found behavior.

Do not broaden current access. FE-1 requires tenant-first lookup, opaque public IDs, server-side capability checks, separate view/manage/approve/export permissions, audited access to sensitive exports, and evidence visibility enforcement.

## 21. Concurrency / Idempotency Risks

Current quote creation/response lacks optimistic versioning; simultaneous quotes can race “latest,” and two responses can both pass the pre-check. Operational creation is a positive reusable pattern.

Future command boundaries must serialize or optimistic-lock: line revision, commitment from selected estimate, actual approval, reversal, allocation totals, invoice association/cancellation, FX selection, settlement, and readiness transition checks. External invoice/payment callbacks need `(source_system, external_event_id)` uniqueness, payload hash, replay result, and conflict behavior. Stable semantic uniqueness/dedup rules must prevent duplicate charges without merging legitimately repeated services.

## 22. Failure Modes

Architecture support is required for missing/invalid currency; missing/stale/disputed FX; duplicate line; wrong party/subject/allocation; late supplier invoice; post-completion cost; price change after execution; partial invoice/payment; credit note; supplier adjustment; cancelled shipment with surviving commitment; cross-shipment/project invoice; and ERP outage.

Expected behavior is explicit blocker/exception or versioned new fact—not silent default. Cancellation does not erase obligations. Partial financial documents require allocation with totals and residuals. ERP outage retains last-known external references labeled stale/unverified and queues reconciliation; it never fabricates current status.

## 23. Data Quality / Abstention Rules

Candidate invariants (**proposed**, subject to business policy where noted):

1. Every amount has one governed currency; normalized amounts retain original Money and FX basis.
2. Every line has tenant and primary economic subject; every cross-reference is tenant-safe.
3. Estimate ≠ commitment ≠ actual; invoice ≠ recognition; payment ≠ revenue; missing ≠ zero.
4. Margin is derived, provenance-bearing, and absent when required inputs/FX are unknown.
5. An actual/commitment retains authority, source, effective/recorded time, and evidence requirement state.
6. Superseded/reversed facts remain queryable and cannot silently become current.
7. Allocations cannot exceed source amount except under an explicitly approved tolerance/rounding policy.
8. External facts retain source identity/version and cannot be promoted merely because import succeeded.

## 24. Existing UI Findings

Reusable surfaces are the quote modal, customer accept/decline card, accepted-quote operational lineage, CaseDocument/MDPM evidence surfaces, and OIP provenance/health patterns.

Problems: the quote is an undifferentiated total; UI supports only IRR/USD; client parses JavaScript `Number` and rounds; terminology does not show quoted versus agreed; evidence/provenance and approval are absent; operational UI receives quote amount without currency; no cost/status/completeness; internal numeric IDs remain in types/contracts; and cargo value can be mistaken for economics. No client-side margin calculation was found—which is correct and should remain so.

## 25. Architecture Option A — Extend Quote / Shipment

Add cost and status fields directly to `ExpertQuote`/`OperationalShipment`.

- **Boundary/entities:** existing commercial/operational aggregates; amount/status columns.
- **Truth/coupling:** economics owned jointly by request and operations.
- **Complexity:** low initial migration.
- **Advantages:** fastest vertical slice.
- **Risks:** collapses stages, poor multi-party/multi-shipment support, mutable history, operational coupling, weak ERP/OIP contracts, eventual “accounting by columns.”
- **Verdict:** reject except as a temporary read adapter; it violates cohesion and information hiding.

## 26. Architecture Option B — Dedicated Economics Bounded Context (Recommended)

Add a module in the modular monolith with its own aggregate, commands, projections, audit/outbox/idempotency, and adapters to commercial/operational/document/ERP domains.

- **Core:** EconomicCase/Account per tenant/subject boundary; EconomicLine; EconomicObservation; Allocation; Money/Quantity/FXBasis; EvidenceReference; external invoice/payment/settlement references; readiness/economics projections.
- **Truth:** economics owns economic facts; source domains own their facts; projections consume stable contracts.
- **Complexity:** medium; legacy quote admission and UI migration required.
- **Advantages:** explicit stages, multi-currency, temporal/audit safety, multi-subject allocation, deterministic OIP, ERP anti-corruption.
- **Risks:** aggregate/allocation policy needs care; more rows and workflow; business policies must be decided.
- **Suitability:** strongest OIP and ERP boundary, compatible with ADR-001 modular monolith.

## 27. Architecture Option C — External ERP Owns All Economics

Forwarder stores only ERP links and displays imported totals.

- **Boundary:** ERP owns charge-to-cash/procure-to-pay; Forwarder has a read projection.
- **Complexity:** low local domain, high integration dependency.
- **Advantages:** avoids ledger duplication; statutory truth remains centralized.
- **Risks:** operational estimates/commitments may not exist early enough in ERP; outages and latency weaken execution; explanations and evidence allocation may be unavailable; OIP becomes dependent on external granularity/quality.
- **Verdict:** viable only if ERP demonstrably owns timely operational economic facts. Current repository provides no such evidence.

## 28. Recommended Architecture

Choose Option B with an explicit ERP boundary. The domain should be named provisionally **Shipment Economics** pending ubiquitous-language review; do not call it “Accounting.” Use stable interfaces and dependency inversion: Economics imports immutable subject/party/document references through adapters, never ORM-mutates source domains. Commercial acceptance can emit/admit a fact; Economics decides its own line/observation under idempotent policy. Read projections aggregate across lines and allocations.

Policy (required categories, recognition, FX authority, tolerances) is versioned configuration; mechanism (Money validation, append/supersession, locking, projection rebuild) remains domain infrastructure. The weakest-link rule applies to a derived result: one missing mandatory input/evidence/FX makes the result incomplete.

## 29. Proposed Canonical Economic Pipeline

`Commercial intent (external authoritative quote reference)` → `Economic estimate observation` → `Economic commitment observation` → `Economic actual observation` → `external invoice/payment/settlement references + allocations` → `derived shipment/project economics` → `derived economic readiness` → `future OIP Signal` → `DecisionContext`.

Authoritative objects are lines, observations, allocations, selected FX basis, evidence associations, and authorized external-reference records. Derived objects are totals, variances, margin, exposure, completeness, and OIP signals. External objects are document binaries and ERP ledger/invoice/payment truth unless business decisions assign bounded local ownership.

## 30. Proposed Domain Model

- **EconomicCase (aggregate boundary):** tenant, primary subject, reporting policy version, lifecycle/version. It coordinates lines but does not copy Project/Shipment.
- **EconomicLine:** opaque identity; side (`REVENUE|COST`); counterparty role/reference; governed service/charge category; primary subject; quantity/unit; tax treatment reference; current observation pointer resolved from history; cancellation semantics.
- **EconomicObservation:** immutable stage, Money, effective/recorded/approved times, actor/authority, source identity, predecessor/supersedes/reversal, reason, evidence requirement state.
- **EconomicAllocation:** allocates an observation or external document amount to one/many Project/Shipment subjects; versioned with rounding/residual.
- **FXObservation / FXSelection:** source rate fact separate from authorized selection/basis.
- **EconomicEvidenceReference:** exact artifact version/external evidence locator and role; no binary.
- **ExternalFinancialReference:** source-system invoice/payment/settlement/credit-note identity, status/version/times, original Money, allocations, reconciliation health.
- **EconomicProjection:** as-of expected/committed/actual/cash totals, variance/margin, input fingerprint, completeness, freshness and generation.
- **EconomicAudit, Outbox, Idempotency:** specialized actor/command history, integration events, replay safety.

Do not make category a free-text EAV. Reuse governed `ServiceType` only if semantics match; otherwise define a separate governed charge-category catalog linked to service classification.

## 31. Proposed Dependency Direction

`Reference/Master + Commercial + Operational Execution + Document/MDPM + ERP adapters` → `Shipment Economics` → `economic projections/readiness` → `OIP` → `DecisionContext/AI`.

No reverse dependencies: Economics does not query OIP for truth; Operational Execution does not depend on margin; MDPM does not decide economic completeness; OIP does not mutate Economics. Cross-domain commands use application services and stable opaque-reference contracts; async integration uses outbox/reconciliation where transactional coupling is inappropriate.

## 32. Gap Register

| ID | Priority | Gap | Why it matters |
|---|---|---|---|
| FE-G01 | P0 | No economic domain/source of truth | all economics otherwise ambiguous |
| FE-G02 | P0 | No Money/currency/FX contract | totals and margin unsafe |
| FE-G03 | P0 | No estimate/commitment/actual separation or append history | cannot explain change |
| FE-G04 | P0 | No canonical line, counterparty, subject/allocation | costs/revenues cannot compose |
| FE-G05 | P0 | No completeness/abstention contract | unknown will become zero |
| FE-G06 | P0 | Quote-response authentication/numeric-ID boundary | commercial decision security risk |
| FE-G07 | P1 | Financial permissions/authority absent | mutations/confidentiality uncontrolled |
| FE-G08 | P1 | Invoice/payment/settlement and ERP boundary undecided | payable/receivable semantics blocked |
| FE-G09 | P1 | Economic evidence association absent | facts lack proof/version binding |
| FE-G10 | P1 | Concurrency/idempotency/version rules absent | duplicate/stale financial facts |
| FE-G11 | P1 | Legacy quote tenant/identity/currency inconsistencies | unsafe admission/migration |
| FE-G12 | P2 | Tax, commission, credit-note and allocation policies absent | incomplete real-world lifecycle |
| FE-G13 | P2 | Economics UI/provenance/export absent | operations cannot safely review truth |
| FE-G14 | P2 | External reconciliation/projection health absent | stale ERP facts could look current |
| FE-G15 | P3 | Advanced forecast/scenario/AI support | later value after truth maturity |

## 33. Business Decision Register

| ID | Question / why architecture cannot decide | Options | Recommendation / consequence |
|---|---|---|---|
| FE-B01 | What event makes customer revenue “committed” and “actual/recognized”? contractual/business/accounting policy | acceptance, contract, execution milestone, invoice, ERP recognition | distinguish commitment from recognition; ERP recognition reference by default; controls actual margin meaning |
| FE-B02 | Who owns invoices, payments, receivables/payables and settlements? organizational/system authority | Forwarder, ERP, hybrid reference | ERP ownership + Forwarder references unless operational need proves otherwise |
| FE-B03 | Who may create/approve sale, cost, actual and adjustment? organization policy | role hierarchy, capability matrix, dual control | capability matrix with separation for material changes |
| FE-B04 | FX authority and bases? commercial/treasury policy | market, contractual, manual approved, settlement | store all; select by versioned purpose-specific policy |
| FE-B05 | Tax responsibility and gross/net semantics? statutory/business policy | ERP only, operational estimate, hybrid | ERP authoritative; bounded estimated tax only if required |
| FE-B06 | Required cost/revenue categories and economic readiness? commercial operating model | per service/project/type | versioned policy; unknown categories fail closed |
| FE-B07 | Materiality/tolerance/rounding and margin-% denominator? management policy | absolute/percentage/currency-specific | currency-specific versioned policy; no hard-coded defaults |
| FE-B08 | Cancellation obligation rules? contractual policy | release, retain, penalty/credit | explicit adjustment/reversal; never auto-zero |

## 34. Architecture Decision Register

| ID | Decision | Recommended default | Status |
|---|---|---|---|
| FE-A01 | bounded context | dedicated Shipment Economics module in modular monolith | Proposed |
| FE-A02 | canonical unit | EconomicLine + immutable staged EconomicObservation | Proposed |
| FE-A03 | money | decimal Money VO, governed currency, no float/default FX | Proposed |
| FE-A04 | history | append, supersede/reverse/adjust; rebuildable current view | Proposed |
| FE-A05 | subject hierarchy | project/shipment primary subject + explicit multi-subject allocations | Proposed |
| FE-A06 | evidence | exact-version association to existing artifacts; no binary copy | Proposed |
| FE-A07 | integration | opaque contracts + anti-corruption adapter + outbox/reconciliation | Proposed |
| FE-A08 | projections | versioned, provenance/completeness/freshness-bearing derived views | Proposed |
| FE-A09 | concurrency | aggregate versions, row locks at promotion/allocation, command idempotency | Proposed |
| FE-A10 | external identity | source-system + opaque external ID/version/event uniqueness | Proposed |

## 35. MDPM / OIP / EAAF Interaction

- **Operational Execution:** supplies tenant-safe subject/lineage and execution facts. Economics references them and may react to events; it never owns shipment lifecycle.
- **MDPM:** owns artifact/assessment/document readiness. Economics associates exact versions and may consume an approved assessment as evidence policy input. Economic readiness remains separate.
- **OIP:** consumes economic projections only after FE truth, completeness, policy version and projection health exist. It remains derived/advisory and cannot mutate Economics.
- **EAAF:** FE-1 candidate evidence must bind exact source/migration/API/policy identities, tenant/security/concurrency tests, recoverability, projection rebuild and evidence retrievability. Per GOV-011, one insufficient mandatory link blocks promotion; this discovery document is not an AEP or approval.

## 36. Book / Framework Delta

| Project finding | Architecture principle | Current delta | Recommendation | Classification |
|---|---|---|---|---|
| Quote/CRM/operational fields cannot own economics jointly | boundary, cohesion, state ownership | truth fragmented/ambiguous | dedicated bounded context | **CONFIRMS EAAF** |
| Amount can lose currency | explicit contract, weakest link | derived output can become false | inseparable Money + abstention | **PATTERN CANDIDATE** |
| estimate/commitment/actual need retained history | temporal semantics, auditability | mutable/latest semantics insufficient | immutable observations + supersession | **PATTERN CANDIDATE** |
| MDPM exact-version evidence can support economics without copies | information hiding, stable interfaces | no economic association | typed evidence-reference pattern | **REFERENCE EXAMPLE CANDIDATE** |
| operational idempotency/tenant locking is reusable | concurrency, idempotency, security | quote flow lacks equivalent assurance | domain-specific command boundary | **REFERENCE EXAMPLE CANDIDATE** |
| ERP must remain separate | system boundary, anti-corruption | no current integration | explicit external authority/reconciliation | **NO FRAMEWORK CHANGE** |
| projection abstains when inputs/health unknown | derived vs authoritative, weakest-link assurance | economics projection absent | completeness/freshness-bearing projection | **PATTERN CANDIDATE** |

No enterprise framework change is justified from one discovery. The detailed ASTD/PAT/ARCH documents are skeletons, so this report does not claim rules they do not contain.

## 37. Recommended FE-1 Scope

FE-1 should be architecture/contract plus one minimal vertical slice, only after decisions FE-B01–B07 needed by the slice:

1. approve ubiquitous language, boundary, authority matrix, Money/FX and temporal contracts;
2. define tenant-safe opaque subject/party/evidence reference contracts;
3. define EconomicLine and immutable `ESTIMATE`/`COMMITMENT` observations for customer revenue and supplier cost, with supersession and idempotency;
4. admit an accepted ExpertQuote through a documented adapter without treating it as recognition;
5. implement completeness-aware expected/committed shipment projection—no actual, invoice, payment, tax, settlement, or OIP signal yet;
6. add focused API/UI only for authorized entry/review/provenance;
7. validate PostgreSQL races, cross-tenant denial, currency invariants, exact-version evidence, projection rebuild, migration rollback/recovery, OpenAPI and browser behavior;
8. produce candidate-bound EAAF evidence. No ERP ledger or AI work.

## 38. Human Decisions Required Before FE-1

Architecture review must approve Option B and FE-A01–A10. Business owners must decide at least FE-B01 (commitment/actual semantics), FE-B02 (invoice/payment/settlement ownership), FE-B03 (approval authority), FE-B04 (FX authority), FE-B06 (minimum completeness for the slice), and FE-B07 (rounding/materiality). FE-B05 and FE-B08 may be explicitly deferred if FE-1 excludes tax and cancellation behavior and fails closed around them.

## 39. Recommended Next Step

Run a human architecture/business workshop using the two decision registers. Produce a **Proposed FE-1 architecture contract** and ADRs for the accepted boundary, Money/FX, staged observation/history, allocation, evidence, and ERP boundary. Before implementation, add a legacy-data admission profile for `ExpertQuote`, `ShipmentRequest.estimated_value`, `Opportunity.value`, and cargo value that explicitly classifies what is rejected, referenced, or migrated. Separately prioritize remediation of the unauthenticated numeric-ID customer quote-response boundary; do not wait for financial-domain implementation to recognize that security gap.

FE-0 DISCOVERY COMPLETE — READY FOR HUMAN ARCHITECTURE REVIEW

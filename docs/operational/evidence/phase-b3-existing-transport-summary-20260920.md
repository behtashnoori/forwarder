# Phase B — Slice 3 — Existing Transport Summary — 2026-09-20

## A. Starting State

| Item | Verified value |
| --- | --- |
| Authoritative worktree | `D:\1-webapp\15-forwarder-golden-20260921` |
| Required starting branch | `codex/phase-b2-shared-numeric-presentation` |
| Slice branch | `codex/phase-b3-existing-transport-summary` |
| Starting HEAD / B2 commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| Required parent / B1 commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| Starting cleanliness | clean |
| Golden application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` |
| Engineering base | `b48e51c8d0eda00bcc7582b68da85528b14547d2` |
| B1 commit | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` |
| B2 commit | `b523cc0b18fd48d93101de0430ec91d56a438c12` |
| Database head | `20260921_shipment_evidence_ownership` |

The Phase A Markdown/JSON freeze evidence, Phase B1 geography evidence, Phase B2 numeric evidence, and controlled integration plan were present and read before implementation. The repository had exactly one base and one Alembic head. A disposable SQLite database stamped at that head returned `current=20260921_shipment_evidence_ownership`, `heads=20260921_shipment_evidence_ownership`, and `pending=false`. The user-local default database was not used as an authority or modified. No prerequisite differed and no stop condition was triggered.

## B. Golden Transport Inventory

| Classification | Existing Golden value/seam | Current meaning and slice decision |
| --- | --- | --- |
| REQUEST_INTENT | `ShipmentRequest.shipping_type` | Selects which already-stored scoped request mode is applicable; it is context, not itself a transport mode. |
| LEGACY/UNUSED | `ShipmentRequest.transport_method` | Legacy scalar retained as a compatibility fallback. It remains byte-for-byte/read-only in projections and is never rewritten. |
| REQUEST_INTENT | `ShipmentRequest.domestic_transport_method` | Existing domestic request-level method. It is preferred only for a domestic request. |
| REQUEST_INTENT | `ShipmentRequest.international_transport_method` | Existing international request-level method. It is preferred only for an international request. |
| REQUEST_INTENT | `ShipmentRequest.transport_method_preference` | Existing request choice/suggestion metadata. It is projected unchanged but is not displayed as an actual route fact. |
| ACTUAL_ROUTE_LEG | `RouteLeg.transport_mode` | Persisted mode of one real operational route leg. It is not allowed to overwrite the request method. |
| ACTUAL_ROUTE_LEG | `RouteLeg.sequence_number` | Persisted deterministic leg ordering used for the route-mode summary; repeated modes are preserved. |
| OUT_OF_SCOPE | `OperationalShipment.shipment_request_id` | Existing source link used to read the request projection safely. No shipment transport persistence was added. |
| OUT_OF_SCOPE | `TransportMethod` catalog and `ExpertSpecialization.transport_method_id` | Intake/admin/specialization catalog. Choices, rows, identity, and expert routing were not changed. |
| OUT_OF_SCOPE | `PortProvinceMapping.transport_method` | Geography/logistics recommendation metadata, not request intent or an operational route leg. |
| OUT_OF_SCOPE | admin reporting coalesced transport values | Existing reporting aggregation was not made a new summary authority. |
| DERIVED_PRESENTATION | existing Expert list and public tracking scalar projections | Already exposed the request scalars. Consumers now use one selection and localization rule. |
| DERIVED_PRESENTATION | `project_existing_request_transport` | New read-only additive projection helper that copies the four existing request fields exactly, with no normalization or inference. |
| DERIVED_PRESENTATION | `getRequestTransportMethod` | Selects only the applicable persisted request scalar. Conflicting scoped values without shipping context resolve to missing, not a guess. |
| DERIVED_PRESENTATION | ordered route-mode summary | Stable sequence-number ordering plus canonical labels; `road → rail → road` remains three facts, not a new state. |

Before this slice, Expert list and public tracking already carried the scalar request fields, Expert detail carried only the legacy scalar, Customer workflow carried none, and the operational graph exposed route-leg modes but not its linked request's transport scalars. Public Tracking rendered the same request fact twice. Operational Shipment Detail localized individual legs but had no distinct request-versus-route transport summaries.

## C. Donor Analysis

Read-only donor inspection was limited to repository `D:\1-webapp\15-forwarder`, commit `d10f6e003a684626cdb382ba25d6f5bd329150f2` (`feat(commercial): implement accepted ADR-046 request transport intent`). Relevant inspected paths were:

- `backend/services/commercial_transport_service.py`
- `backend/services/expert_request_detail_service.py`
- `backend/services/expert_request_list_service.py`
- `backend/services/admin_shipment_request_service.py`
- `backend/services/tracking_service.py`
- `backend/tests/test_fwd03_transport_intent.py`
- `backend/tests/test_expert_assignment_referral_contract.py`
- `src/pages/ExpertConsole.tsx`
- `src/pages/PublicTracking.tsx`
- `src/pages/RequestDetail.tsx`
- `src/lib/api.ts`

Reused as requirements only: one deterministic request-summary rule, one visible Rail concept, consistent role presentation, and round-trip/non-mutation coverage.

Explicitly rejected: `backend/migrations/versions/20260916_fwd03_transport_intent.py`, the `transport_intent` model/schema, `TransportIntentInput`, ordered/combined request semantics, multimodal classification, intake redesign, mandatory cargo behavior, donor counter runtime, cumulative donor pages, and donor migration ancestry.

No donor merge, cherry-pick, file copy, or donor write occurred.

## D. Transport Presentation Contract

**Request transport** is the method already stored on `ShipmentRequest`. For domestic requests the domestic scalar is selected, for international requests the international scalar is selected, and the legacy scalar is only a compatibility fallback. Without shipping context, a legacy value or one unambiguous scoped value may be displayed; two conflicting scoped values are not guessed.

**Actual route transport** is the ordered list of `RouteLeg.transport_mode` values from the operational shipment graph. Modes are ordered by `sequence_number`, localized independently, and repeated values remain visible.

These facts are rendered with separate labels: `روش حمل درخواست` and `مسیر حمل`. Neither projection mutates storage, and route legs never replace or backfill request intent.

## E. Product Changes

| Runtime file | Bounded change |
| --- | --- |
| `backend/services/request_transport_projection.py` | Adds an exact read-only projection of the four existing request transport scalars. |
| `backend/services/customer_gamification_service.py` | Adds that safe projection to the already-authorized Customer workflow response. |
| `backend/services/expert_request_detail_service.py` | Extends the already-authorized Expert detail response from the legacy field to all existing scalars. |
| `backend/services/operational_service.py` | Adds linked-request transport under `source.request_transport`; reuses the same loaded request for `request_public_id`. |
| `src/lib/transportPresentation.ts` | Adds bounded request selection and ordered route-mode formatting without business-state derivation. |
| `src/i18n.tsx` | Extends the canonical transport-label map and normalizes lookup spelling/case only at presentation time. |
| `src/lib/api.ts` | Adds types for the additive Customer, Expert, and operational projections. |
| `src/pages/CustomerRequestDetail.tsx` | Shows the localized request-level method or an explicit missing value. |
| `src/pages/ExpertConsole.tsx` | Uses the same request selector and canonical label on Expert summary cards. |
| `src/pages/RequestDetail.tsx` | Uses the same request selector and canonical label on Expert request detail. |
| `src/pages/PublicTracking.tsx` | Shows the request fact once, localized, and removes its duplicate rendering. |
| `src/pages/OperationalShipmentDetail.tsx` | Shows request transport and ordered real route-leg modes as separate summary cards. |
| `src/components/RouteAuthoringSection.tsx` | Reuses the canonical existing label helper for current route-mode values; options and payloads are unchanged. |

## F. Customer Behavior

Customer Request Detail and Public Tracking show the applicable existing request-level transport method with the canonical Persian label. The Customer workflow projection exposes only the same non-sensitive scalars already owned by that request; it does not expose operational route legs or internal planning. Missing request transport is explicit and never defaults to Road.

## G. Expert Behavior

Expert list and detail surfaces select the same stored request fact and use the same canonical label as Customer. Expert detail receives the existing scoped scalars through an additive response extension. Assignment, tenant scope, list/detail access, SLA, and mutation behavior remain unchanged.

## H. Operational Shipment Behavior

For a shipment sourced from a request, the summary may show both:

- `روش حمل درخواست`: the linked request's stored scalar fact; and
- `مسیر حمل`: the current persisted route legs in deterministic order.

A request recorded as Sea while its route is Road → Rail → Road remains displayed as those two different facts. A direct shipment has no fabricated request card. A shipment with no route legs has no fabricated route-mode summary. No Customer projection receives route-leg planning data.

## I. Localization

The authoritative UI seam remains `useI18n().transportLabel`. Known Golden values and catalog spellings now resolve through one normalized lookup, including `road`, `rail`, `air`, `sea`, `Road Transport`, `Land Transport`, `Rail Transport`, `Air Transport`, `Air Freight`, and `Sea Freight`. Existing route-only values `multimodal_transfer` and `customs_handling` retain their established descriptive labels; this does not introduce a request business state.

Persian summary labels are `روش حمل درخواست` and `مسیر حمل`. Tests prove known raw enum/catalog values do not leak on localized summary surfaces.

## J. Missing / Duplicate Handling

- A missing request fact displays `روش حمل ثبت نشده` on request summaries.
- A direct operational shipment does not acquire a request transport fact.
- Missing route legs do not become Road or inherit request intent.
- Conflicting domestic/international values with no shipping context remain unresolved rather than choosing one.
- Public Tracking's duplicate rendering of the same request method was removed; the fact now appears once.
- Repeated real leg modes are intentionally preserved because they represent different legs.
- The historical duplicate Rail intake/catalog issue remains deferred because resolving catalog rows or intake semantics requires a later product decision. This slice changed no option list, stored value, or submitted payload.

## K. API / Persistence Integrity

Three narrow additive safe projections changed: Customer workflow, Expert request detail, and Operational Shipment graph source metadata. Each copies already-existing non-sensitive scalar fields inside an already-authorized resource. Public Tracking and Expert list already exposed these fields. No endpoint, role, tenant scope, or private operational disclosure was broadened.

```text
TRANSPORT_PERSISTENCE_CHANGED=NO
REQUEST_PAYLOAD_CHANGED=NO
TRANSPORT_ENUM_CHANGED=NO
MULTIMODAL_STATE_ADDED=NO
```

Stored request values and stored route-leg values were asserted unchanged across projection and presentation. No create/update form, normalizer, serializer for writes, model, or migration changed.

## L. Regression Status

```text
GCF-A-001 = PASS
GCF-A-002 = PASS
GCF-A-003 = PASS
GCF-A-004 = PASS
GCF-A-005 = PASS
GCF-A-011 = PASS
GCF-A-012 = PASS

PHASE_B1_GEOGRAPHY = PASS
PHASE_B2_NUMERIC = PASS
```

The focused Phase A/B1/B2 regression set passed 177 backend tests with seven accurately classified environment-dependent skips and 142 frontend tests across 18 files. The full suites passed with increased test counts. Geography runtime/data, numeric formatter behavior, dates, authorization, and route writes were not changed.

## M. Tests

| Gate | Exact result |
| --- | --- |
| Focused B3 backend (`test_phase_b3_existing_transport_summary`, request, Expert, Customer workflow, public tracking, operational vertical slice) | PASS — 68 passed, 0 failed |
| Focused B3 frontend (shared helper, localization, Public Tracking, Customer/Expert consistency, Operational Shipment Detail, route authoring) | PASS — 6 files, 55 tests |
| Relevant Phase A + B1 backend regression | PASS — 177 passed, 7 environment-dependent skipped, 0 failed |
| Relevant Phase A + B1 + B2 frontend regression | PASS — 18 files, 142 tests |
| Full backend suite | PASS — 1,052 passed, 93 environment-dependent skipped, 1 expected xfail, 0 failed |
| Full frontend suite | PASS — 61 files, 298 tests |
| TypeScript | PASS — `npx tsc --noEmit` |
| Production build | PASS — 2,538 modules transformed; output directed to and removed from a disposable directory; no tracked `dist` delta |
| ESLint | PASS — 0 errors, 13 unchanged historical warnings |
| Diff integrity | PASS — `git diff --check`; only Git line-ending notices, no whitespace errors |
| Alembic graph/current/check | PASS — one base, one expected head, disposable current equals head, `pending=false` |
| Migration delta | PASS — zero files changed under `backend/migrations` |

Phase B2 recorded 1,050 backend passes and 291 frontend tests. This slice adds two backend tests and seven frontend tests, producing 1,052 backend passes and 298 frontend tests with no reduction. The 93 PostgreSQL/environment-dependent skips and one expected xfail are unchanged and are not represented as executed PASS.

## N. Database Contract

```text
DATABASE_HEAD =
20260921_shipment_evidence_ownership

MIGRATION_ADDED =
NO

MIGRATION_MODIFIED =
NO

PENDING_MIGRATION =
NO
```

The disposable check recorded base `20240917_initial_schema`, head/current `20260921_shipment_evidence_ownership`, and `pending=false`.

## O. Scope Integrity

```text
MULTIMODAL_SEMANTICS_DEFINED=NO
TRANSPORT_INTAKE_CHANGED=NO
MANDATORY_CARGO_CHANGED=NO
EUR_ADDED=NO
DATE_TIME_BEHAVIOR_CHANGED=NO
NOTIFICATION_WORK_IMPORTED=NO
CONTROL_TOWER_IMPORTED=NO
OTHER_FWD_FEATURE_IMPORTED=NO
PRODUCT_MIGRATION_ADDED=NO
PRODUCTION_ACCESSED=NO
PRODUCTION_CHANGED=NO
SECRETS_ACCESSED=NO
DONOR_REPOSITORY_CHANGED=NO
```

## P. Remaining Risks

- Historical records can contain legacy and scoped scalar values that disagree. The presentation now follows shipping scope and does not mutate those records; resolving historical data quality remains separate governance work.
- Unknown historical method strings remain verbatim rather than being silently translated or reinterpreted. Adding a new authoritative label requires an explicit catalog/localization decision.
- The reported duplicate Rail choice can still exist in intake/catalog data. Deduplicating catalog rows or redefining choices remains deferred with the unresolved transport-intake/multimodal product decision.

## Q. Verdict

PASS — EXISTING TRANSPORT SUMMARY COMPLETE

## R. Next Goal

**Phase B — Slice 4: Canonical Request Count/List Invariant**

Reimplement the controlled plan's next independent no-schema correction so Expert request counters and visible lists use one canonical role/tenant/status scope across create, transition, reassignment, refresh, and pagination. Use only bounded FWD-03 counter/list tests as requirements, preserve Golden authorization and status taxonomy, add no migration, run the relevant Phase A/B1/B2/B3 regressions plus the full gate, and stop after one attributable `request-count-summary` commit. This goal was derived from the controlled integration plan and was not executed here.

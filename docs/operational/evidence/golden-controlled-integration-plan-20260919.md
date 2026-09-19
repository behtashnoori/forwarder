# Golden Controlled Integration Plan — 2026-09-19

Scope: analysis and integration design only. No product source, migration, database, release artifact, Production system, secret, donor branch, or donor worktree was changed. The only intended change is this evidence report in the certified Golden repository.

## A. Baseline Authority

The sole implementation baseline is:

| Authority | Exact identity |
| --- | --- |
| Repository | `D:\1-webapp\15-forwarder-golden-20260921` |
| Branch | `codex/golden-production-20260921` |
| Application provenance | `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4` |
| Certified engineering base | `b48e51c8d0eda00bcc7582b68da85528b14547d2` |
| Golden certification evidence commit | `0a6f1d368d0c266657188960e0507ff6d9039f59` |
| Database head | `20260921_shipment_evidence_ownership` |
| Certification report | `docs/operational/evidence/golden-production-recovery-certification-20260919.md` |
| Certification verdict | `PASS — EXACT EDITABLE GOLDEN BASELINE RECOVERED AND CERTIFIED` |

`0a6f1d368d0c266657188960e0507ff6d9039f59` is a documentation-only direct child of `b48e51c8d0eda00bcc7582b68da85528b14547d2`; product semantics remain fixed by `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`. The existing certification is accepted without rerunning it: generated frontend matched all 13 Production frontend files by SHA256; 309 packaged backend files matched byte-for-byte; 1,046 backend tests and 279 frontend tests passed; typecheck, build, lint, release tooling, launcher, and migration checks passed; the worktree was clean; Production was not accessed.

Two read-only donor authorities were inspected:

- FWD history: `D:\1-webapp\forwarder-dev`, rooted at normalized baseline `38431da96c4f36ceaa07c550e594bf2d08d34e38`. Its cumulative FWD stack is not descended from Golden and contains neither Golden source commit. It is semantic/test evidence, not merge ancestry.
- Control Tower: `D:\1-webapp\15-forwarder` at `d6297fdf50b27f7d69a5bf2086d11ef2eed882ed`, frozen as `S7-RC-d6297fd-ct1-frozen`. It is a bounded donor, never a baseline.

Independent verification for this plan found:

- every FWD runtime path changed by FWD-01 through FWD-07 is either absent from Golden or has a different blob from Golden; no FWD runtime file is safe to preserve byte-for-byte as a Golden replacement;
- all eight named Golden/Control-Tower shared hotspots have different blobs, confirming reconciliation/reimplementation rather than replacement;
- the Golden and Control Tower donor `backend/migrations` tree hashes are both `7f373f8dc4708124838cf9618afcb5b09f92f77b`; Control Tower adds no migration beyond Golden;
- Golden's current geography snapshot contains 2 countries and 4 international locations (`IR:3`, `TM:1`), while the FWD-02 checked-in source contains 249 country headings and 115,208 locations, including Italy, Norway, and 154 Iran locations. This is a governed data-reconciliation candidate, not proof of Persian translation completeness or service availability.

Authority rule: when donor behavior, tests, documents, or assumptions conflict with Golden, the certified Golden contract wins unless this report identifies an approved, separately tested behavior change.

## B. Golden Contract Freeze

The following contracts are forbidden to regress. “Full gate” means the certified backend/frontend/type/build/lint suites with no unexplained loss of tests, plus the focused tests named in the row. Existing certified counts are the floor/reference, not a reason to avoid adding approved tests.

| Frozen contract | Current Golden evidence | Missing characterization to add before touching the contract | Required regression gate |
| --- | --- | --- | --- |
| Application shell, router, unknown-route handling | `src/App.tsx`; `src/tests/App.routing.test.tsx`; `src/tests/components/ApplicationNavigation.test.tsx`; `src/tests/components/OperationsNav.test.tsx` | Snapshot the complete route/nav inventory by role, including every public, Expert, CRM, Admin, operations, dashboard, and not-found route | Focused routing/nav suite; assert no route/link/guard disappears; full frontend/type/build/lint |
| Authentication/session continuity | `src/tests/components/ProtectedRoute.test.tsx`; `src/lib/authContinuity.test.ts`; `src/lib/apiAuth.test.ts`; `backend/tests/test_auth.py`; `test_auth_sessions.py` | Explicit CT route authentication/error-envelope cases | Anonymous 401, malformed/expired session denial, canonical redirect, no token leakage; full gate |
| Authorization, tenant and role boundaries | `test_assigned_work_authorization.py`; `test_expert_membership_permissions.py`; `test_execution_authority_3a.py`; `test_expert_service_scope.py`; analytics/admin authorization suites | Cross-feature matrix for Platform Admin, Organization Admin, responsible Expert, unrelated Expert, inactive/revoked membership | Same-tenant allow and cross-tenant/unscoped/revoked denial for every new endpoint; negative disclosure snapshots; full backend gate |
| Customer request workflows | `test_shipment_request_contract.py`; `test_shipment_request_public_identity.py`; `test_customer_quote_response.py`; public tracking tests | Create/review/reopen transport-summary round trip and current optional cargo behavior | Legacy clients and existing valid records remain readable; approved new validations are enforced server-side; full gate |
| Expert workflows and request scope | `test_expert_assignment_referral_contract.py`; `test_expert_service_scope.py`; `test_admin_panel_read_contract.py`; Expert console routes | Counter/list invariant and responsible-Expert CT-to-detail characterization | Assignment/referral/SLA/list/detail behavior, current-scope reads, reassignment and revocation; full gate |
| Admin workflows where touched | `test_admin_panel_read_contract.py`; `test_user_management_contract.py`; frontend Admin tests | Admin quote/geography configuration only if introduced; no implied Platform Admin operational access | Existing admin totals, reports, assignment, organization-context checks; full gate |
| Operational Shipment Detail | `src/tests/pages/OperationalShipmentDetail.behavior.test.tsx`; route-authoring, operational execution, conditions, economics, documents, cargo, and history component suites; operational backend suites | Golden payload/disclosure fixture for ordinary responsible Expert before CT changes | Preserve route authoring, occurrence time, history, delays/exceptions, cargo, execution units, evidence, logistics points, economics, permissions, and responsive structure; full gate |
| Request lists and counters | Golden `backend/routes/expert_console.py` computes `new_count` from status `new`; `test_admin_panel_read_contract.py` covers admin summaries | One transaction-level test that a newly created request changes the same scoped count and visible list, followed by transition/reassignment cases | Count/list use one role/tenant/status scope; pagination cannot change totals; refresh after mutation; full gate |
| Geography/reference data | `test_governed_international_geography.py`; `test_iran_destination_point.py`; `test_v191_location_resolver.py`; `src/tests/components/LocationForm.geography.test.ts` | Italy, Norway, broad Iran, pagination/search, stable identity, inactive record, large-catalog performance, Persian-fallback labeling | Governed source only; no UI constants; create/review/reopen identity round trip; existing inactive identities preserved; full gate |
| Quote and customer response | `test_customer_quote_response.py`; quote service/routes; economics and quote presentation tests | EUR quote API/UI round trip; Expert visibility; current accepted/declined request-state/audit characterization; concurrency before adding states | Existing quotes remain readable; unsupported currency denied; accepted/declined unchanged until decision; tenant/capability negatives; full gate |
| Tracking/timeline | `test_multi_unit_tracking_api.py`; `test_multi_unit_tracking_service.py`; `test_tracking_projection.py`; `test_public_tracking_timeline.py`; `test_tracking_locations*.py`; `src/tests/components/UnifiedShipmentHistory.test.tsx` | UI must not offer retired legacy add-unit path; ordered date+time display; duplicate/conflict error and input retention; canonical create flow | Canonical authorized execution-unit/update path; occurred vs recorded time; visibility allowlist; late event ordering; customer-safe projection; full gate |
| Documents/evidence | `test_case_documents.py`; `test_case_documents_postgresql.py`; `test_case_documents_fault_injection.py`; `test_case_documents_schema_parity.py`; `src/tests/components/CaseDocumentsTab.test.tsx` | Current single-file/replace behavior, cap >1, multi-select partial failure, and ambiguous lost-response characterization before UX change | Request/shipment ownership, private storage, format/size/content validation, audit, replacement history, download and cross-tenant denial; full gate |
| Operational history/evidence | operational read/vertical-slice suites; `unified_shipment_history.py`; frontend unified-history tests | Golden response snapshot before assigned-Expert CT projection | Stable ordering and occurred/recorded semantics; no private audit/raw note disclosure; full gate |
| Logistics/private points | `test_logistics_network.py`; global logistics-point suites; `test_tracking_locations*.py`; frontend logistics-network acceptance/authority tests | End-to-end private-point selection and CT/public safe-projection test | Active same-tenant point selectable; inactive, wrong-tenant, unauthorized denied; immutable understandable snapshot; full gate |
| Date/time rendering | `test_timestamp_contracts_phase1.py`; `src/lib/localDate.test.ts`; `src/lib/localDateTime.test.ts`; Shipment Detail occurrence-time tests | Explicit per-surface calendar policy ledger and assignment-event/no-fallback UI test | Offset-bearing instants render in the application zone; Local Date never shifts; creation never impersonates assignment; two browser timezones; full gate |
| Numeric/currency rendering | shipment economics tests; cargo presentation tests; existing localized UI assertions | Shared formatter characterization for money, weight, volume, counts, zero/null, Persian digits, and excluded identifiers | Group large numbers without changing values; preserve decimals per domain; never group codes, phones, IDs, tracking or vehicle references; full gate |
| Migrations/current database head | 97-revision single graph; `test_alembic_version_table.py`; migration safety/parity/PostgreSQL suites; certified head check | A test that every new migration is a direct descendant of the then-current Golden head | One base/one head; upgrade from Golden head and fresh DB; sentinel preservation; downgrade policy exercised only on disposable DB; full backend gate |
| Canonical Windows launcher/release | `scripts/tests/test_launcher_chain_contract.ps1`; `test_launcher_chain_real_process.py`; operational release builder/pipeline tests; certification report | Update only artifact/source identities in final qualification | Preserve `cmd.exe /d /c -> PYTHONPATH/repo -> release-local Python -> approved runtime serve -> Waitress 127.0.0.1:5101`; release tests and non-Production rehearsal |

No product behavior should be changed while adding the Phase A characterization. If a characterization requires choosing one of the product decisions in Section I, record the gap and stop that assertion rather than encoding an invented answer.

## C. User-Feedback Traceability

| Requirement | Golden state | FWD donor evidence | Control Tower interaction | Final disposition |
| --- | --- | --- | --- | --- |
| A. Geography | Partial: governed architecture exists, but the checked-in international snapshot has only Iran/Turkmenistan and Iran has Tehran/IKA/Bandar Abbas | FWD-02 `4b06ed039d72c15f10d2f114fed07fc2fdef457b` supplies a governed ISO/UNECE snapshot, paginated selectors, stable IDs, Italy/Norway, and 154 Iran entries; `1714118340943f1dbbf99e4b25edc9ef41f817e6` is qualification evidence | CT consumes location/mode snapshots and must not reintroduce hard-coded subsets or broaden private disclosure | **CONTROLLED TRANSPLANT** isolated catalog/builder/selectors; reconcile Golden APIs/forms/services. No schema migration; controlled data reconciliation and performance gate. Persian source-name fallback remains explicit, not falsely “translated.” |
| B. Transport modes | Partial: duplicated Rail seed; operational routes support multimodal, request intake remains scalar | FWD-03 groups duplicate Rail choices and persists ordered JSON intent, but embodies a specific combined-mode decision | CT may label actual multi-leg routes as combined; it must not imply a customer-request model | **DEFER** ordered/combined persistence until product confirms semantics. **REIMPLEMENT** the one-Rail presentation fix without deleting catalog rows. Preserve actual-route CT multimodal display. |
| C. Cargo information | Current final-create normalization permits insufficient/blank optional data in parts of the workflow | FWD-03 requires nonblank cargo description at final creation, but that is only one possible minimum | CT is read-only and must not impose hidden validation | **DEFER** new mandatory fields/transition until product defines the minimum. Freeze existing drafts/records; later enforce the approved rule server-side and mirror it in UI. |
| D. Numeric presentation | Partial and inconsistent | FWD-04 adds a shared parser/formatter and tests; `5994253b82e31f24dd6ec68db9c601c2aec9d7f1` contains required post-implementation fixes | CT cards/list/details need the same formatter | **CONTROLLED TRANSPLANT** the pure formatter/test concepts, then reconcile every Golden consumer. IDs/codes remain unformatted. No migration. |
| E. Request summary | Multiple scalar fields/fallbacks can disagree | FWD-03 adds one Commercial projection and round-trip tests | CT has its own mode translation and cannot become a third authority | **REIMPLEMENT AGAINST GOLDEN** a canonical read projection using current stored meaning; do not require the deferred transport-intent schema. |
| F. Dates/localization | Golden has substantial Jalali/Gregorian/Persian behavior, but assignment fallback/duplicate labels remain incompletely characterized | FWD-04 proves actual assignment event, explicit Tehran rendering, Local Date safety, and two browser zones; FWD-06 adds manual-time provenance for a legacy path | Direct CT/Shipment Detail hotspot | **REIMPLEMENT AGAINST GOLDEN** actual-event and no-false-fallback fixes; preserve Golden localization. Calendar display choice stays gated by Section I. |
| G. Request counters | Existing scoped counts exist, but create/count/list invariant is not frozen | FWD-03 includes counter/list corrections and UAT | CT introduces cards/counts and can create a competing definition | **REIMPLEMENT AGAINST GOLDEN** one canonical scoped query/status taxonomy before CT cards. No migration. |
| H. Date/currency | Golden economics supports EUR; quote UI exposes IRR/USD and quote validation is not aligned | FWD-05 provides exact EUR quote handling but is coupled to a much larger response/capability design; FWD-04 supplies presentation helpers | CT V1 does not require quote writes but may display quote-derived operational state | **REIMPLEMENT AGAINST GOLDEN** bounded EUR quote validation/selector/display first; preserve IRR/USD. Calendar policy remains a decision. No schema required for EUR alone. |
| I. Quote/customer response | Accepted/declined, response time, unread/audit and Expert-visible data exist; negotiating and governed request-state transitions do not | FWD-05 implements exact quote publication, private capability, `accepted/negotiation_requested/declined`, append-only facts/receipts, security hardening, and a large migration | Accepted quotes can create operational shipments and affect CT visibility; economics and operational services are shared hotspots | **REIMPLEMENT AGAINST GOLDEN** after state-transition decision. Preserve current accepted/declined meanwhile. Reuse FWD-05 security/concurrency tests as requirements, not files wholesale. |
| J. Tracking | Golden has canonical execution units, occurred/recorded times, safe projections, and a retired legacy add-unit route still reachable from older UI | FWD-06 supplies legacy timeline/time provenance, receipts, error clarity, and UAT; `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff` fixes snapshot integrity/rollback | Direct CT sources/Shipment Detail overlap | **REIMPLEMENT AGAINST GOLDEN** canonical UI and useful timeline first. Do not revive legacy add-unit. FWD-06 migration is conditional only if legacy manual-time provenance remains required after canonical-path analysis. |
| K. Documents | Golden schema/service already support multiple immutable files per requirement and private ownership; UI selects `files[0]` and treats existing active files as replacement | FWD-07 adds multi-select/per-file results and mobile access, then discovers lost-response duplication; ADR-049 recovery is proposed, not accepted | Direct Shipment Detail ownership/security hotspot | **REIMPLEMENT AGAINST GOLDEN** mobile access and any approved multi-file UX. **DEFER** append/version/replace/retry/recovery semantics. Do not add ADR-049 schema without acceptance. |
| L. Private logistics points | Backend contract exists and is tenant/capability scoped with safe snapshots | FWD-02/FWD-06 improve selector reachability/error behavior | Direct CT input and disclosure dependency | **PRESERVE** Golden ownership/authorization; reconcile selector and CT translation only. No schema migration. |

## D. FWD-01 Through FWD-07 Inventory

The feature stack is linear and cumulative. “Required qualification commit” means its fixes/tests/evidence must inform any port; it does not authorize cherry-picking.

### FWD-01 — notification foundation

- Commits: `d7cbedf9ec7416b83aeb6313aa095462a20e441d` (implementation and qualification).
- Addresses: future customer quote notification foundation for I; indirectly supports audited channel-neutral notification delivery.
- Runtime files: `backend/models.py`; `operational_models.py`; `quarantine.py`; `notification_cli.py`; `notification_models.py`; `notification_provider.py`; `services/notification_action_service.py`; `operational_service.py`; `outbox_service.py`; `quote_notification_contract.py`; `quote_service.py`.
- Migration: `20260916_fwd01_notifications`, originally down from `20260908_governed_international_geography`; adds an outbox tenant uniqueness contract plus notification action/attempt tables and refuses destructive downgrade when history exists.
- Focused tests: `test_fwd01_notifications.py`; `test_fwd01_migration_postgresql.py`; affected authorization/outbox/release/migration suites.
- Golden relationship: all runtime files are new or differ from Golden. Golden has `OperationalOutbox` and `ExpertConsoleNotification` but no external notification intent/action/attempt model.
- CT conflict: direct on `operational_service.py`; CT must not expose notification/private-delivery data. No schema dependency for CT.
- Disposition: **REIMPLEMENT AGAINST GOLDEN**. Reuse the outbox event boundary, intent/action/attempt state ideas, tenant/idempotency/lease/UNKNOWN reconciliation tests, and fake adapter only for local qualification. Replace the fixed fake-email-first coupling with `Business event -> OperationalOutbox -> intent/action -> recipient/channel policy snapshot -> adapter -> attempt -> result/audit`. Do not activate a quote consumer or provider before policy approval.

### FWD-02 — location integrity

- Commits: `4b06ed039d72c15f10d2f114fed07fc2fdef457b` (runtime/tests); `1714118340943f1dbbf99e4b25edc9ef41f817e6` (qualification evidence only).
- Addresses: A and L.
- Runtime files: new `backend/international_geography_catalog.py`, `backend/reference_data/international-geography-v2-fwd02.json`, `src/components/InternationalLocationSelector.tsx`, `TrackingLocationSelector.tsx`; changes to `backend/routes/locations.py`, `services/logistics_network_service.py`, `multi_unit_tracking_service.py`, `src/components/LocationForm.tsx`, `src/lib/api.ts`, `src/pages/RequestDetail.tsx`.
- Migration: none. Existing reference tables are reconciled idempotently and inactive identities are not reactivated. This is a controlled data load, not Alembic DDL.
- Focused tests: `test_fwd02_geography.py`; logistics/tracking tests; selector/component tests. Dataset facts: 249 headings, 115,208 locations; Italy 5,799, Norway 1,142, Iran 154.
- Golden relationship: isolated catalog/new selector concepts are portable; every shared integration file differs.
- CT conflict: logistics and tracking selectors, API client, request detail, location translation/disclosure.
- Disposition: **CONTROLLED TRANSPLANT** new catalog/builder and selector concepts; **RECONCILE** all shared files. Carry `1714118340943f1dbbf99e4b25edc9ef41f817e6` as evidence only. Add scale/performance and Persian-label policy gates before acceptance.

### FWD-03 — request intake

- Commit: `d10f6e003a684626cdb382ba25d6f5bd329150f2`.
- Addresses: B, C, E, G.
- Runtime files: new `backend/services/commercial_transport_service.py`, `src/components/TransportIntentInput.tsx`; changes to `backend/models.py`, `backend/routes/expert_console.py`, `backend/routes/shipment_request.py`, `backend/services/admin_shipment_request_service.py`, `expert_request_detail_service.py`, `expert_request_list_service.py`, `shipment_service.py`, `tracking_service.py`, `src/components/LocationForm.tsx`, `RequestConfirmation.tsx`, `src/lib/api.ts`, `src/pages/ExpertConsole.tsx`, `PublicTracking.tsx`, and `RequestDetail.tsx`.
- Migration: `20260916_fwd03_transport_intent`, originally down from FWD-01; one nullable JSON `shipment_request.transport_intent`, no backfill, populated downgrade refusal.
- Focused tests: `test_fwd03_transport_intent.py`; `test_fwd03_migration_postgresql.py`; request/admin/expert/tracking tests and browser evidence.
- Golden relationship: no runtime file is byte-identical. Donor semantics select ordered arbitrary steps, repeated modes, combined classification, required nonblank cargo, and one canonical summary.
- CT conflict: Expert console, tracking projections, API types and request/detail surfaces; CT mode display must not pre-approve request semantics.
- Disposition: **DEFER** migration, combined-mode semantics, and cargo minimum. **REIMPLEMENT AGAINST GOLDEN** the deterministic one-Rail presentation, request-summary projection, and count/list invariant. If product later accepts ordered intent, port the service/test concepts with a fresh Golden-based migration rather than the donor commit.

### FWD-04 — presentation integrity

- Commits: `ed4026c1f07c54da1980fcea1cabcb4c1a5e289f` (implementation); `5994253b82e31f24dd6ec68db9c601c2aec9d7f1` (mandatory assignment serialization, formatter and timezone fixes plus UAT); `98a0364a6b6f97daf70152c7d3a5cefbb242cac0` (closure evidence only).
- Addresses: D and F; supports E/H/J.
- Runtime files: new `src/lib/presentation.ts`; changes to quote/timeline/tracking services, `QuoteModal`, API client, `localDate.ts`, Customer/Public/Request detail pages.
- Migration: none.
- Focused tests: `test_fwd04_quote_amount_contract.py`; timestamp/public timeline tests; `src/lib/presentation.test.ts`; two-browser-timezone UAT.
- Golden relationship: the pure helper is a useful donor, but Golden has newer/different localization and Shipment Detail contracts.
- CT conflict: shared API client, dates, amounts, cards/list/detail presentation.
- Disposition: **CONTROLLED TRANSPLANT** helper/test ideas and **RECONCILE** consumers. `5994253b82e31f24dd6ec68db9c601c2aec9d7f1` is mandatory to any reuse; `98a0364a6b6f97daf70152c7d3a5cefbb242cac0` is evidence only. Calendar choice remains product-governed.

### FWD-05 — quote response

- Commits: `92f14a08e544fb79961c2021addbf97c13ea5b1f` (runtime); `700381c42072a10bd8a7ce7a0e36db6252454ff7` (mandatory qualification/security tests); `29630f9ee255b9b0189124b4d41fb262422e53f9` (accepted documents, final security qualification, one boundary-test correction).
- Addresses: H and I; depends on FWD-01 and FWD-04 in donor history.
- Runtime files: `backend/__init__.py`, `backend/models.py`, `backend/notification_provider.py`, `backend/operational_models.py`, `backend/quarantine.py`, new `backend/quote_response_models.py`, `backend/requirements.txt`, `backend/routes/__init__.py`, `crm.py`, `customer_gamification.py`, `expert_console.py`, new `quotation_settings.py` and `quote_capability.py`, `backend/security.py`, `backend/services/assignment_service.py`, `crm_customer_create_from_request_service.py`, `crm_customer_link_service.py`, `customer_gamification_service.py`, `economics_service.py`, `expert_request_detail_service.py`, `expert_request_list_service.py`, new `governed_quote_service.py`, `quotation_settings_service.py`, `quote_capability_crypto.py`, `quote_response_authorization.py`, and `quote_response_notification.py`, changes to `notification_action_service.py`, `notification_service.py`, `operational_service.py`, `quote_notification_contract.py`, `quote_service.py`, and `tracking_service.py`, new `public/quote-capture.js` and `quote-response.html`, `src/components/QuotationSettingsTab.tsx`, changes to `QuoteModal.tsx`, `src/lib/api.ts`, `presentation.ts`, `src/pages/AdminPanel.tsx`, `CustomerRequestDetail.tsx`, `ExpertConsole.tsx`, `PublicTracking.tsx`, `RequestDetail.tsx`, new `QuoteCapabilityCustomer.tsx`, `quote-capability-customer.css`, `src/quote-capability-bootstrap.ts`, and `vite.config.ts`.
- Migration: `20260916_fwd05_quote_response`, originally down from FWD-03. It adds recipient generations, quote exact-money/publication/version fields, key policy/audit, capability grants, append-only response facts/receipts, Expert attention links, constraints and PostgreSQL triggers. It also alters quote amount nullability/response width and response check values.
- Focused tests: `test_fwd05_runtime.py`; `test_fwd05_http_boundary.py`; `test_fwd05_postgresql.py`; `test_fwd05_browser.py`; signing feasibility plus existing quote/customer/auth/economics suites.
- Golden relationship: broad shared divergence. FWD-05's security and concurrency findings are valuable, but the runtime and migration cannot be transplanted wholesale.
- CT conflict: critical on `backend/routes/__init__.py`, `operational_service.py`, `economics_service.py`, Expert console, API client, quote/status projections, and CT operational eligibility.
- Disposition: **REIMPLEMENT AGAINST GOLDEN**. Implement bounded EUR support separately without the migration. **DEFER** new response states and capability lifecycle until product decides transitions/terminology. When approved, treat `700381c42072a10bd8a7ce7a0e36db6252454ff7` and `29630f9ee255b9b0189124b4d41fb262422e53f9` security evidence as mandatory acceptance inputs.

### FWD-06 — tracking timeline

- Commits: pre-build decision evidence `b094e2f2c6f39cbb8bb227fe07f920e7334f5da5`, `19f96a8355e34676a2934632a8dba5bb7409fd4e`, and `0e14d3df7d8d2b704eb7f37138dd09850d9fc9a9`; runtime `71414b6af5a750f2f39682407f2315b540a86322`; mandatory integrity/rollback fix `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`; closure evidence `c85ebec1b1d49599b6ebfe0811367f310932b7ac`.
- Addresses: F and J; supports L.
- Runtime files: new `backend/services/tracking_receipt.py` and `backend/services/tracking_time.py`; changes to `backend/models.py`, `backend/routes/expert_console.py`, `backend/services/multi_unit_tracking_service.py`, `src/components/LocationForm.tsx`, `src/lib/api.ts`, `src/pages/PublicTracking.tsx`, and `src/pages/RequestDetail.tsx`.
- Migration: `20260916_fwd06_tracking_time`, originally down from FWD-05; five nullable occurrence-provenance columns on legacy `shipment_transport_unit_update`, checks and PostgreSQL immutability trigger; no backfill; populated downgrade refusal.
- Focused tests: `test_fwd06_m1_time.py`; `test_fwd06_m1_postgresql.py`; tracking characterization/location/projection/service tests and browser UAT.
- Golden relationship: Golden already has canonical operational event occurred/recorded times and a legacy update `occurred_at`; the donor adds manual-input provenance and receipts to the compatibility path.
- CT conflict: tracking sources/translation, Expert console, shared API, public/request detail, private-point display.
- Disposition: **REIMPLEMENT AGAINST GOLDEN** around the canonical execution-unit/event path. `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff` is mandatory if any FWD-06 logic is reused. Add the donor migration only if characterization proves a still-required legacy manual-time provenance contract that canonical events cannot satisfy.

### FWD-07 — document attachments

- Commits: `811bbbaed5d2eb48c5f713b88991ce73b80c20b8` (initial multi-file UI/service); `63f8431a0d01a2c4fdc96749a483617668c27905` (PostgreSQL/UI changes); `2f8f11d2e03860bc82d3509770684e00abe396b7` (required mobile Request Detail access); `d52c0c5696033bbbe137e47cca0a038e62b177f6` and `d61e7bcf1780765b2c91e6796150eb3aa7c630dc` (evidence normalization); `e5e9ff7edc8ea22dbb47759b2b1e28e10895e45a` (required safety/config/storage boundary and CI/test changes); `6683a7ab7f81812df1a5bf7dddc5dec9b42e1a0e` and `8f5e9a9c38100eb44571dd3c6e115f31e6a1109d` (proposed recovery/evidence); `3b92f4d004aebc2638c918e04b618418eb083b76` (owned PostgreSQL socket qualification); `385f02209382e214005d39d2583df53834bac278` (proposed ADR selector correction); `91966639f89f647ae739e400a4bef78326905427` (dependency/migration-byte reproduction); `a778bc8516e2d71b8665acd046191fbc5f0493e8` (final portability evidence).
- Addresses: K.
- Runtime/config files: `backend/services/case_document_service.py`, `backend/services/document_storage_service.py`, `backend/config.py`, `backend/__init__.py`, `src/components/CaseDocumentsTab.tsx`, `src/pages/RequestDetail.tsx`, `.github/workflows/quality-gates.yml`, `.gitattributes`, `pytest.ini`, `requirements.txt`, and `scripts/verify_credential_policy.py`; qualification launchers/boundary helpers live under `scripts/uat/`.
- Migration: none in FWD-07. Proposed ADR-049 describes a future upload-operation table and file link, but it is explicitly unaccepted and unimplemented.
- Focused tests: case-document SQLite/PostgreSQL/security/fault tests; `CaseDocumentsTab.test.tsx`; two-viewport browser UAT. The donor records the unresolved lost-response duplicate risk.
- Golden relationship: Golden already owns the one-requirement-to-many-files schema and private storage; donor code differs and predates the final shipment-evidence ownership head.
- CT conflict: direct Shipment Detail UI, document disclosure, storage and ownership.
- Disposition: **REIMPLEMENT AGAINST GOLDEN** after the document semantics decision. If used, `63f8431a0d01a2c4fdc96749a483617668c27905`, `2f8f11d2e03860bc82d3509770684e00abe396b7`, and `e5e9ff7edc8ea22dbb47759b2b1e28e10895e45a` are mandatory inputs; portability commits are qualification references, not product patches. **DEFER/REJECT FOR NOW** ADR-049 schema and any automatic retry behavior.

## E. Control Tower Inventory

The prior classification is revalidated against the certified editable Golden source.

### Clean transplant, then Golden adaptation

- `backend/routes/control_tower.py`
- `backend/services/control_tower_oip.py`
- `backend/services/control_tower_read_model.py`
- `backend/services/control_tower_scope.py`
- `backend/services/control_tower_sources.py`
- `backend/services/control_tower_translation.py` (bind labels to Golden canonical vocabulary)
- `backend/tests/test_control_tower_api.py`
- `backend/tests/test_control_tower_read_model.py`
- `backend/tests/test_control_tower_scope.py`
- `backend/tests/test_control_tower_sources.py`
- `src/pages/ControlTower.tsx` and its three donor test files, as a page concept adapted to Golden components/API/presentation

### Reconcile with smallest possible Golden edits

- `backend/routes/__init__.py`: add only blueprint import/registration; preserve route order and error handling.
- `backend/routes/operations.py`: preserve Golden detail payload and authorization; add only bounded responsible-Expert access.
- `backend/services/operational_service.py`: preserve Golden graph/detail fields and governed disclosure; add assignment-aware scope without finance/audit/private-document/raw-note leakage.
- `src/App.tsx`, `src/components/OperationsNav.tsx`: append one governed CT route/link; preserve all Golden routes, guards and labels.
- `src/lib/api.ts`: append CT types/calls; preserve Golden auth, errors, interceptors and all APIs.
- related Shipment Detail and CT tests, rebased on Golden fixtures.

### Reimplement against Golden

- `src/pages/OperationalShipmentDetail.tsx`: never replace with donor page; implement only the responsible-Expert behavior required by CT.
- donor changes in `backend/services/economics_service.py`: independently port only missing security/idempotency protections after proving they are absent from Golden. CT does not grant economics authority.

### Do not transplant

- donor `dist/**`, release manifests, frozen RC ZIP/files, generated evidence, artifact hashes and stale readiness claims;
- donor migration files as a CT delta (the entire migration tree is already identical to Golden and CT adds none);
- unrelated donor frontend/product changes;
- donor-wide shell, API client, Shipment Detail or economics replacements.

Accepted decision material such as Control Tower ADR-046 and the operational contract may be carried with corrected Golden provenance. Do not confuse the primary repository's ADR-045 economics authorization with the unrelated FWD history's ADR-045 notification decision.

## F. Three-Way Conflict Matrix

| Hotspot / behavior | Golden behavior that must survive | Desired FWD behavior | Desired Control Tower behavior | Direct transplant? | Final strategy |
| --- | --- | --- | --- | --- | --- |
| `src/App.tsx` routing | Full certified public/authenticated/CRM/Admin/operations/dashboard route inventory and role guards | FWD quote/customer shells must not replace app routing | One eligible CT route | No | Freeze route inventory; add CT route only; independent quote shell, if approved, remains isolated |
| `OperationsNav` / navigation | Golden labels, role visibility, home/back behavior | No FWD requirement justifies shell replacement | One role-governed CT link | No | Minimal Golden edit plus nav snapshot test |
| `src/lib/api.ts` | Auth headers, error semantics, all current request/operation/document APIs | Geography, summary, presentation, quote, tracking calls/types | CT calls/types | No | Append slice-specific contracts in separate commits; never copy donor file |
| `OperationalShipmentDetail.tsx` | Route authoring, history, time, cargo, units, docs, logistics, economics, permissions, responsive layout | Tracking/date/doc improvements | Responsible Expert bounded entry/detail | No | Reimplement on Golden; negative field-disclosure fixtures; CT UI last |
| `RequestDetail.tsx` / customer detail | Existing request, quote, tracking, docs and reopen behavior | FWD-02/03/04/05/06/07 all touch this surface | CT links to operational detail, not request mutation | No | Decompose into separately tested geography/summary/presentation/tracking/document changes; never apply cumulative donor page |
| `ExpertConsole.tsx` / backend Expert route | Assignment scope, list/detail/status, unread/audit | FWD-03 counters, FWD-05 response attention, FWD-06 tracking | CT responsible-Expert scope and cards | No | Establish canonical count/scope query; add each projection independently; reassignment/revocation gates |
| Quote UI/service | Integral current amount, IRR/USD UI, current accepted/declined response and audit | Shared formatting, EUR, later governed response lifecycle | Read only; accepted quote may affect shipment visibility | No | EUR/presentation first; state/capability migration only after decision; CT consumes safe projection |
| Tracking/timeline UI/service | Canonical execution units/events, occurred/recorded times, visibility allowlist, legacy path fails closed | Clear errors, useful timeline, provenance/receipt patterns, private selectors | Read/translate safe current progress | No | Use canonical Golden path; hide retired legacy action; conditionally add legacy provenance only if necessary |
| Documents UI/service | Golden ownership head, multiple file rows, private storage, audit/authorization | Multi-select/per-file result/mobile access; unresolved retry recovery | Display only permitted document summary, not private content | No | Characterize semantics, implement approved UI on Golden, keep CT projection minimal; no recovery schema yet |
| `backend/routes/__init__.py` | Existing blueprint set/order/error behavior | FWD-05 adds quote routes only if approved | Add CT blueprint | No | One minimal registration per approved feature, tests after each |
| `backend/routes/operations.py` | Golden organization/capability access and response contract | No broad FWD replacement | Responsible assigned Expert bounded read | No | Add explicit narrow authorization branch; preserve default and negative disclosure |
| `backend/services/operational_service.py` | Golden ownership census, detail graph, outbox, governed projections | FWD-01 outbox public seam; FWD-05 quote integration | CT detail/read inputs | No | Extract/reuse public outbox seam first; add CT read scope later; keep domain writes separate |
| `backend/services/economics_service.py` | ADR-045 authorization, immutable FX provenance, project/admin rules | FWD-05 security/idempotency improvements only where missing | CT must not disclose finance or broaden access | No | Contract-test Golden, then reconstruct proven missing guards; CT read model excludes economics |
| Models/outbox/notification | Existing `OperationalOutbox` and separate Expert inbox | Channel-neutral intent/attempt audit; FWD-05 attention facts later | CT excludes private notification data | No | Fresh additive Golden migration; no active producer/provider before policy; explicit projection denylist |
| Geography/logistics | Governed identities, private tenant points, safe snapshots | Worldwide catalog and reachable selectors | Translate only safe projected location | Shared modules: no; new catalog: conditional yes | Controlled catalog import, reconcile services, preserve disclosure |
| Migrations/models | Single head `20260921_shipment_evidence_ownership`; released migrations immutable | Four donor migrations have obsolete down-revisions; FWD-07 none | CT needs none | No | Fresh revisions based on then-current Golden head only; one head after each slice |

## G. Database / Migration Plan

Starting lineage is immutable:

`... -> 20260920_legal_customer_nullable_contact_names -> 20260921_shipment_evidence_ownership`

No donor migration can be copied as-is. Each references a predecessor from the independent FWD graph. New revisions must use fresh identifiers and the then-current Golden head.

| Candidate schema change | Donor origin | Donor dependency | Golden plan | Additive/destructive assessment | Rollback | CT dependency |
| --- | --- | --- | --- | --- | --- | --- |
| Notification intent/action/attempt foundation | FWD-01 `d7cbedf9ec7416b83aeb6313aa095462a20e441d`; `20260916_fwd01_notifications` | `20260908_governed_international_geography` | If Phase C is authorized, create fresh revision directly after current Golden head; model channel-neutral intent/action, policy snapshot and attempts; preserve Expert inbox separately | Additive tables/indexes plus an outbox composite uniqueness constraint; validate existing rows before constraint | Application disable/roll-forward; empty downgrade only; refuse destructive downgrade when history exists | None; CT must exclude these fields |
| Ordered request transport intent | FWD-03 `d10f6e003a684626cdb382ba25d6f5bd329150f2`; `20260916_fwd03_transport_intent` | FWD-01 revision | **Not required now.** After product decision, add nullable JSON or the approved alternative from then-current head; no inferred backfill | Additive nullable column under donor design | Retain schema/data; populated downgrade refusal | None; CT can show actual route modes without it |
| Governed quote publication/response/capability | FWD-05 `92f14a08e544fb79961c2021addbf97c13ea5b1f`; `20260916_fwd05_quote_response` | FWD-03 revision | **Not required for EUR alone; deferred for lifecycle.** If approved, redesign a fresh Golden migration after current head and split where practical into reviewable schema cohorts | Mostly additive, but quote amount nullability/type semantics and response constraint alteration are compatibility-sensitive, not “purely additive” | Disable writes/provider; retain append-only history; destructive downgrade refused | CT V1 requires no schema; only a stable safe quote/status projection |
| Legacy tracking input-time provenance | FWD-06 `71414b6af5a750f2f39682407f2315b540a86322` plus fix `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`; `20260916_fwd06_tracking_time` | FWD-05 revision | Conditional only after proving Golden canonical events cannot meet the accepted tracking-time contract; fresh revision after then-current head | Five nullable columns/checks/immutability trigger; no backfill | Old app read-only; populated downgrade refusal | None |
| Document upload operation recovery | Proposed ADR-049 only; no FWD-07 migration | Proposed after FWD-06 | **Do not create.** Requires explicit acceptance of operation identity, retention, append/replace and recovery policy | Would be additive table/link but introduces durable retention and storage reconciliation semantics | Retain receipts/history; populated downgrade refusal | None |
| Worldwide geography | FWD-02 | No migration | Existing tables receive an explicit, idempotent, non-destructive controlled reconciliation. Record dataset identity/hash/counts and performance | Data addition; no identity reuse/reactivation; potentially large operational load | Disable new snapshot/reconcile; preserve referenced rows, do not delete blindly | CT reads existing projections only |
| Control Tower V1 | CT donor | None | No migration. Verified Golden/donor migration tree hashes are identical | No schema change | Remove feature registration/code only | Native requirement |

Migration ordering is dependency-by-implemented-contract, not donor chronology. A deferred revision creates no placeholder or empty migration. Every introduced revision must leave exactly one head, pass upgrade from `20260921_shipment_evidence_ownership`, pass fresh PostgreSQL upgrade, preserve representative sentinels, and document application rollback. Released Golden migrations are never edited.

## H. Notification Architecture Boundary

Approved foundation for controlled implementation:

1. `OperationalOutbox` remains the transactional business-event boundary.
2. Domain services emit versioned facts; they do not call SMS, email, webhook, or other providers.
3. A separate notification owner creates an idempotent intent/action from an allowlisted event.
4. The persisted intent binds tenant, event, purpose, policy/template versions, recipient reference and channel-policy snapshot without storing secrets or casually persisting raw message content.
5. Provider adapters implement one send/reconcile contract outside domain models.
6. Attempts record lease/attempt identity, timestamps, redacted result, provider reference and terminal/ambiguous outcome. `UNKNOWN` requires reconciliation, never blind resend.
7. Existing `ExpertConsoleNotification` remains the in-app Expert attention contract; it is neither the external-delivery queue nor a replacement for the general architecture.
8. Fake adapters are permitted only for deterministic local tests and cannot constitute delivery evidence.

Safe FWD-01 reuse: outbox public-recording seam, action/attempt ownership, tenant constraints, idempotency, concurrent claim, late-result fencing, `UNKNOWN` reconciliation, bounded CLI/worker pattern, and focused tests.

Must be redesigned or deferred: the donor's fixed EMAIL/quote policy as the default architecture; real recipient selection; consent/preferences; channel order/fallback; provider SDKs/credentials; templates and delivery SLAs; live workers/schedulers; callbacks/webhooks; real delivery and operational rollout. No provider delivery is part of this plan.

## I. Product Decisions

Only the following decisions require product input. They do not block Phase A, the independent no-schema corrections, isolated CT backend work, or preservation testing.

| Decision | Why it matters | Dependent phase | Safe default | Can work proceed first? |
| --- | --- | --- | --- | --- |
| Multimodal request semantics | Determines whether request intent is scalar, unordered set, ordered legs, repetitions, allowed combinations and legacy mapping | Decision-dependent request-intake slice | Preserve current scalar request fields; show actual operational multi-leg routes as multimodal only | Yes: one-Rail UI, summaries of existing fields, counters, geography and CT actual-route display |
| Mandatory cargo minimum and enforcement transition | Changes which requests are valid and whether old drafts/API clients break | Request-intake/cargo slice | Preserve current records/draft compatibility; do not claim quotation readiness | Yes: characterize and display existing values |
| Quote `negotiating`/reject semantics | Determines terminology, permitted transitions/reversal, request status, concurrency and audit/outbox facts | Quote-response slice and any CT status mapping | Preserve current `accepted`/`declined`; no automatic request transition beyond Golden | Yes: EUR and formatting; CT can preserve current statuses |
| Jalali/Gregorian policy per surface and display timezone | Prevents contradictory/duplicated dates and accidental browser-zone rendering | Presentation closure, tracking UI, CT UI | Preserve Golden behavior; for instants use explicit current application zone; do not relabel creation as assignment | Yes: underlying timestamp correctness and no-fallback fixes |
| Document append/version/replace/batch/retry rules | Determines whether multi-select appends, replaces, versions, partially succeeds, or duplicates after lost responses | Document UX; any ADR-049 recovery schema | Preserve explicit current single-file operation and private ownership; no automatic retry | Yes: mobile access, characterization and CT non-disclosure |
| Notification recipient/channel/fallback policy | Determines eligibility, consent, locale, quiet hours, channel order and what failure means | Activation of notification producer/provider | Keep foundation inactive; retain durable business events and existing Expert inbox | Yes: passive foundation can be built; no real intent creation/delivery is activated |

## J. Controlled Integration Phases

### Phase A — executable Golden contract freeze

- Goal: add only missing characterization needed by Section B and a machine-readable route/role/disclosure baseline.
- Allowed scope: test files/fixtures and evidence under Golden; tiny testability-only seams only if unavoidable and behavior-neutral.
- Donor input: FWD/CT tests as scenario references, not copied expectations where they conflict.
- Forbidden: behavior changes, migrations, donor product modules, compiled assets, provider work.
- Migrations: none.
- Focused tests: all Section B tests, with new route inventory, counter/list, Shipment Detail disclosure, current quote response, current document semantics, and private-point characterization.
- Full gate: certified Golden backend/frontend/type/build/lint and migration-head checks; no unexplained count reduction or snapshot change.
- Stop: any test requires inventing a product decision, reveals ambiguous Golden authorization, or changes behavior to become green.
- Commit boundary: one `test(golden): freeze controlled integration contracts` commit plus its evidence; no product code.

### Phase B — independent no-schema feedback corrections

- Goal: complete approved, separable behavior with low overlap: governed geography, shared numeric formatting, existing transport summary, count/list invariant, EUR quote support, retired tracking-action removal, and private-point selector reachability.
- Allowed scope: FWD-02 isolated catalog/selectors and Golden reconciliation files; FWD-04 pure presentation helper and Golden consumers; narrowly scoped Golden request/quote/tracking files and tests.
- Donor input: `4b06ed039d72c15f10d2f114fed07fc2fdef457b`, `1714118340943f1dbbf99e4b25edc9ef41f817e6` evidence, `ed4026c1f07c54da1980fcea1cabcb4c1a5e289f`, mandatory `5994253b82e31f24dd6ec68db9c601c2aec9d7f1`, bounded FWD-03 counter/summary tests, bounded FWD-05 EUR tests.
- Forbidden: transport-intent schema, cargo policy, new response states/capability shell, notification provider, document retry, CT shell edits.
- Migrations: none; geography is explicit controlled data reconciliation with dataset/hash/count evidence.
- Focused tests: geography scale/identity/UI; presentation parser/formatter; counter/list transaction; EUR create/read/respond using existing states; tracking legacy action hidden; private-point authorization.
- Full gate: full Golden suites after each coherent slice; type/build/lint; two timezone/RTL browser proof for changed presentation; disposable data-reconcile rehearsal.
- Stop: large-catalog latency exceeds agreed budget, Persian fallback is mislabeled as translation, current quote records change meaning, or a shared file cannot retain Golden behavior.
- Commit boundary: separate commits per slice (`geography`, `presentation`, `request-count-summary`, `quote-eur`, `tracking-ui`) so regressions are attributable.

### Phase C — inactive channel-neutral notification foundation

- Goal: add reusable intent/action/attempt ownership without sending or activating a business policy.
- Allowed scope: new notification-owned models/services/tests/CLI, a public outbox-recording seam, minimal model/quarantine/architecture/release metadata integration.
- Donor input: FWD-01 concepts/tests only.
- Forbidden: fixed EMAIL as general default, live provider, credentials, quote consumer activation, recipient inference, CT exposure, changes to Expert inbox meaning.
- Migrations: one fresh additive revision after the current Golden head; one-head/fresh/upgrade/sentinel/populated-rollback tests.
- Focused tests: atomic event preservation, replay/idempotency, competing claim, revocation/reassignment, tenant denial, lease expiry/late result, UNKNOWN reconciliation, secret/log redaction, inactive-by-default proof.
- Full gate: backend full, frontend unaffected baseline, migration/PostgreSQL, architecture, release builder, type/build/lint.
- Stop: policy is needed to make schema meaningful but remains undecided; provider call occurs; outbox semantics change for unrelated events; downgrade can erase history.
- Commit boundary: one schema/model commit and one foundation/service/test commit; both inactive until separately authorized policy work.

### Phase D — isolated Control Tower backend

- Goal: port the feature-local CT read route, scope, sources, translation, read model and OIP without touching shared Shipment Detail/economics semantics.
- Allowed scope: the six CT backend modules and adapted CT-focused tests; blueprint registration only after tests establish import/error behavior.
- Donor input: `d6297f...` bounded modules and prior qualification scenarios.
- Forbidden: shared detail/economics replacement, frontend shell, feedback backlog, notification data, schema changes.
- Migrations: none.
- Focused tests: anonymous 401; unscoped/unauthorized 403; organization and responsible-Expert scope; cross-tenant denial; cards/list/filter/pagination/empty/failure; query budget; no finance/audit/private document/raw note/notification leakage.
- Full gate: full Golden backend, frontend baseline, type/build/lint and single-head check.
- Stop: CT requires broader authority, domain writes, schema, private fields, or changes a Golden source-of-truth query.
- Commit boundary: one isolated backend/read-model commit; blueprint registration may be a separate minimal commit.

### Phase E — decision-dependent user-feedback domain slices

- Goal: implement only product-approved remaining semantics, one domain at a time: transport/cargo, quote response, tracking provenance, document batch/recovery.
- Allowed scope: only the domain named by the accepted decision and its Golden integration/tests.
- Donor input: FWD-03, FWD-05, FWD-06 with mandatory `59931c5cbba1ffa4c6bf2430318f7b022ff6c9ff`, FWD-07 with mandatory `63f8431a0d01a2c4fdc96749a483617668c27905`/`2f8f11d2e03860bc82d3509770684e00abe396b7`/`e5e9ff7edc8ea22dbb47759b2b1e28e10895e45a` as applicable.
- Forbidden: cumulative FWD page/service replacement, unapproved state or retry behavior, unrelated CT shell work, live providers.
- Migrations: a fresh revision only when the accepted slice truly requires it; no placeholders. Quote, tracking and document migrations are independent of absent deferred migrations.
- Focused tests: the accepted decision's full API/UI/auth/concurrency/rollback matrix plus preservation tests for every shared Golden contract.
- Full gate: focused PostgreSQL and two-timezone/RTL browser UAT where relevant; full backend/frontend/type/build/lint after each slice.
- Stop: decision text is incomplete, migration is non-additive without an approved compatibility plan, lost-response behavior can duplicate effects, or Golden authorization weakens.
- Commit boundary: one feature behavior commit plus, where needed, separate migration and qualification commits; never combine transport, quote, tracking and documents.

### Phase F — Control Tower shared backend and responsible-Expert detail

- Goal: reconcile CT with the final Golden/FWD shared domain contracts.
- Allowed scope: minimal edits to `backend/routes/operations.py`, `backend/services/operational_service.py`, narrowly proven economics guards, responsibility tests and CT projections.
- Donor input: CT responsibility/security intent, not donor file bodies wholesale.
- Forbidden: broader economics access, changed default Shipment Detail response, private delivery/document fields, unrelated domain writes.
- Migrations: none.
- Focused tests: current owner/admin paths unchanged; responsible Expert allow; former/unrelated Expert deny; reassignment/revocation; field-level disclosure; ADR-045 economics/idempotency; CT-to-detail navigation contract.
- Full gate: full backend/frontend baseline, CT focused suite, type/build/lint, migration check.
- Stop: a broader authorization shortcut is required, response fields disappear/change meaning, or finance/audit/private data leaks.
- Commit boundary: one shared-backend reconciliation commit; economics hardening separate if needed.

### Phase G — Control Tower UI in the Golden shell

- Goal: add the adapted CT page, API calls, route and navigation while preserving the complete Golden frontend.
- Allowed scope: new adapted `ControlTower.tsx` and tests; append-only CT API types/calls; minimal `App.tsx` and `OperationsNav.tsx`; Golden-based Shipment Detail additions.
- Donor input: CT page/tests as behavioral/design reference.
- Forbidden: donor frontend snapshot, compiled `dist`, wholesale API/shell/detail replacement, new product semantics.
- Migrations: none.
- Focused tests: route/nav inventory, role guards, cards/list/filter/loading/empty/error, responsible-detail entry, localization/numeric/date formatting, responsive RTL and accessibility.
- Full gate: all frontend tests, TypeScript, production build, lint; full backend and CT API suite.
- Stop: any Golden route/nav/guard disappears, presentation policy diverges, bundle unexpectedly drops material behavior, or unsupported role sees CT.
- Commit boundary: CT page/API commit, shell registration commit, Shipment Detail UI commit—separate and reviewable.

### Phase H — complete qualification and RC freeze

- Goal: prove Golden preservation, approved feedback completion/preserved deferrals, CT V1, migrations and canonical launch in one traceable candidate.
- Allowed scope: evidence, release build, non-Production rehearsal and documentation-only corrections; product changes return to their owning phase.
- Donor input: qualification scenarios only; no stale artifacts/manifests.
- Forbidden: Production access/mutation, secrets, deployment, donor artifact reuse, unexplained last-minute fixes.
- Migrations: final graph exactly one head; disposable PostgreSQL from Golden head and fresh DB.
- Focused tests: every A-L row marked complete/preserved/deferred; CT scope/disclosure; migration recovery; launcher/process identity; authenticated/negative endpoint smoke.
- Full gate: backend, frontend, typecheck, build, lint, architecture/structure, release builder/tooling, PostgreSQL, browser UAT, artifact hash/provenance and launcher contract.
- Stop: any gate fails, worktree/build input is dirty, evidence is missing, a deferral is represented as complete, or launcher/process identity differs.
- Commit boundary: one qualification evidence commit followed by a separately authorized RC freeze. No deployment.

## K. Acceptance Gates

Every implementation commit must name its requirement, donor provenance, changed Golden files, migration (or none), focused tests and rollback boundary.

1. **Identity gate:** exact Golden parent, clean worktree, expected branch, no donor write, one current database head.
2. **Contract gate:** relevant Section B characterization passes before and after; intended semantic delta is enumerated; all other response/UI snapshots are unchanged.
3. **Authorization/disclosure gate:** anonymous, wrong-role, wrong-tenant, unassigned, reassigned, revoked and inactive cases; fields are checked, not only status codes.
4. **Migration gate:** fresh disposable PostgreSQL and upgrade from Golden head; one head; sentinel preservation; concurrency/constraint evidence; rollback is application-first and non-destructive.
5. **UI gate:** real backend, normal authentication, desktop/mobile RTL, accessibility, loading/empty/failure, two browser timezones for time-bearing work, no horizontal overflow.
6. **Focused feature gate:** donor tests are adapted to Golden and augmented with Golden preservation assertions; skipped environment tests are not called PASS.
7. **Full regression gate:** full backend and frontend suites, TypeScript, production build and lint after every behavior/schema slice. Certified counts are reference floors; changes require an explained test ledger.
8. **CT gate:** scope, pagination/filter, performance/query budget, responsible-detail path, ADR-045/ADR-046 boundaries, and explicit absence of finance/audit/private document/raw note/notification data.
9. **RC/launcher gate:** artifact derived only from clean Golden-based source; manifest names source, lock, head and evidence; canonical Windows launcher chain and non-Production process identity are proven.

No phase closes on a focused pass alone. A failing full gate returns the change to its owning phase; it is not repaired inside qualification by broad unrelated edits.

## L. Production Safety Contract

- Production remains untouched until a final RC is independently qualified and a separate explicit deployment authorization is issued.
- Do not access Production endpoints, environment files, database, Scheduled Tasks, IIS configuration, process list, logs, credentials, or secrets during integration.
- Do not merge or cherry-pick FWD or Control Tower branches. Port reviewed semantics into bounded Golden commits.
- Do not copy donor `dist`, manifests, ZIPs, RC metadata or evidence as new candidate proof.
- All migration/data rehearsals use owned disposable databases; all browser UAT uses synthetic identities/data and loopback services.
- Preserve the certified Windows launch chain exactly: system `cmd.exe /d /c` -> explicit release `PYTHONPATH` and working directory -> release-local Python -> approved `phase1b_production_cutover_runtime.py serve` -> explicit non-secret environment path/repo/`127.0.0.1:5101`/log options -> release-local Waitress child. Direct Scheduled Task Python/Waitress launch remains forbidden.
- Health alone is insufficient. Final rehearsal also proves valid login, invalid-login governed denial, CT 401/403 boundaries, frontend availability, intended process/release identity, database head and artifact hash without exposing secrets.

## M. Final Decision

**READY — CONTROLLED INTEGRATION MAY BEGIN FROM CERTIFIED GOLDEN**

Rationale: the exact editable Golden baseline is certified; FWD and CT donor identities and file-level conflicts are known; CT requires no migration; FWD migrations and decision-dependent semantics are isolated; unresolved product decisions do not block the contract-freeze first phase or the approved independent slices. Readiness is permission to begin the controlled sequence, not permission to merge donors, deploy, contact Production, or silently resolve Section I.

## N. Next Goal

```text
GOAL

Execute Phase A only: freeze the certified Golden application contracts with
behavior-neutral characterization tests and one evidence report/commit.

Repository:
D:\1-webapp\15-forwarder-golden-20260921

Required starting identities:
- branch: codex/golden-production-20260921
- parent evidence commit: 0a6f1d368d0c266657188960e0507ff6d9039f59
- application provenance: e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4
- engineering base: b48e51c8d0eda00bcc7582b68da85528b14547d2
- database head: 20260921_shipment_evidence_ownership

Use docs/operational/evidence/golden-controlled-integration-plan-20260919.md
as the governing plan. Add only the missing Phase A characterization for:
complete route/navigation inventory by role; request count/list invariants;
Golden Shipment Detail payload and field-disclosure boundaries; current quote
accepted/declined behavior and request-state effect; current document append/
replace/max-count/lost-response behavior; private logistics-point selection and
safe projection; assignment-event versus request-creation time; and shared
numeric/date rendering exclusions.

Tests must record current Golden behavior. Do not change product behavior to
make a characterization pass. If a test would require choosing multimodal,
cargo-minimum, quote-state, calendar, document-retry, or notification-policy
semantics, record the gap and leave that assertion pending.

Run the relevant focused tests, then the full Golden backend and frontend suites,
TypeScript check, production build, lint, migration single-head/current checks,
and the certified release/launcher contract tests. Reuse existing certification
evidence where inputs are unchanged, but execute all gates affected by added
tests or tiny testability seams. Do not rerun Production equivalence hashing
unless product/build inputs unexpectedly change.

Do not merge, cherry-pick, port FWD/Control Tower product code, create a migration,
modify either donor repository, use secrets, access Production, build an RC, push,
or deploy. Stop if characterization exposes ambiguous authorization or requires a
behavior change. Finish with a clean Golden worktree and one evidence-only/test-
only commit that lists exact tests, results, gaps, and confirms product semantics
remain unchanged. Do not begin Phase B.
```

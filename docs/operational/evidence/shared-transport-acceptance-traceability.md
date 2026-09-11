# Shared Transport acceptance traceability

| ID | TEST_NAME | BUSINESS_JOURNEY | ASSERTIONS | RESULT |
| --- | --- | --- | --- | --- |
| A | `A - legacy compatibility` | Open legacy-only and legacy-plus-canonical shipment tracking, refresh and reopen. | A1: route-less Shipment renders safely, historical transport is business-facing, and refresh/reopen preserve it without a mutation action. A2: current canonical execution is visible, the legacy allocation remains historical, and canonical precedence survives refresh/reopen. | PASS — `A - legacy compatibility` ran in a fresh disposable database with zero console, page, or unexpected network errors. |

## A diagnosis

The blank page was a `CURRENT_SLICE_PRODUCT_DEFECT`, not a harness fault: the Shipment API legitimately returns `route_leg: null` for direct shipments before planning, while the detail page dereferenced that value in its closed route-details section. The page's outer error fallback then threw outside the i18n provider, leaving a white page. The correction is safe no-route-plan rendering through an empty route-leg list. The explicit test is `A - legacy compatibility`; it passed A1 and A2 in a fresh disposable database. The fixture grants the read actor both the cargo-selector capability and `operational_execution.read`, which the existing Shipment detail integration loads. Browser evidence recorded zero console errors, page errors, or unexpected 401/403/404/409/500 responses; the runner cleaned the database, processes, temporary runtime, and credential.
| B | `B - multi-shipment same owner` | Allocate Cargo A and Cargo C in Shared Transport; inspect tracking, refresh and reopen. | B-01…B-13 business assertions passed; B-14 no Project Configuration background request; B-15 no unexpected 403; B-16 no unrelated-capability console error. Direct unauthorized Project Configuration API access remains denied. | PASS — two fresh disposable runs passed with zero unexpected console, page, or failed-request errors. |
| C | `C - multi-project multi-customer and same-name identity` | C1: allocate A/B from distinct Projects, Shipments and owners to one execution. C2: allocate X/Y whose owners have equal visible names but distinct database identities. Refresh and reopen after each combined journey. | C1 preserves A/B Project and Shipment lineage, shows Persian multi-customer groupage without the raw enum, and retains both Cargo/owner facts in canonical Tracking. C2 retains both equal visible owner labels as separate Cargo facts and remains multi-customer groupage. The runner's database audit verifies all four current writes are `ExecutionUnitCargoAllocation` rows on one execution and no C cargo has a legacy allocation. | PASS — two fresh disposable runs passed, with zero console, page, or unexpected failed-request errors. Fixture validation confirms C1 distinct identities/lineage, C2 distinct IDs with equal display names, and operator authorization for all Projects. |
| D | `D - mixed UOM` | Allocate the three cargo rows in Shared Transport, refresh and reopen. | 20.000000 PALLET, 8.000000 TON and 350.000000 CARTON remain separate in UI/API; no invented 378 aggregate. | PASS — two fresh disposable browser runs; canonical allocation audit passed and no unexpected browser errors. |
| E | `E - cargo owner lifecycle` | Edit Cargo A owner, save, refresh, reopen Shared Transport; open the historical Ownerless Cargo. | Owner persists; same-tenant owner selectable; foreign owner absent. Historical Ownerless Cargo retains `NULL` owner while its legitimate legacy transport context is visible in Tracking. | PASS — two independent clean runs passed, including the strict runtime, process, database, and credential cleanup gate. |
| F | `F - carrier lifecycle` | Select Carrier X, reopen, verify Shipment Tracking; change to Y and repeat; clear and repeat. | Carrier identity is canonical to `ExecutionUnit`, persists through refresh/reopen, Tracking projects that same truth, and foreign-tenant assignment is denied without a leak. | PASS — two fresh disposable browser runs passed with zero unexpected browser errors and complete cleanup. |
| G | `G - restricted actor` | Restricted actor completes the authorized Project A / Shipment A / Shared Transport journey, then attempts Project B reads and mutations. | Project A selector visibility, Cargo A allocation and Tracking pass; Project B is absent from project-derived UI. Direct Project B Shipment/Cargo/Tracking/execution reads and Cargo/Shipment mutations fail closed without protected-data leakage. Tenant-scoped Carrier and Owner selectors are explicitly N/A for ProjectAccess. | PASS — two fresh disposable runs passed; normal browser journeys made zero unauthorized eager requests and recorded zero unexpected console, page, or failed-request errors. |
| H | `H - cross-tenant isolation` | Tenant A opens Shared Transport and attempts foreign unit/customer access. | Independent Organization-B graph, positive A tracking, tenant-scoped selectors, foreign shipment/cargo/tracking/unit reads, allocation, and owner/carrier assignment denials; no response leakage. | PASS — two fresh disposable browser runs; all foreign probes failed closed and normal A journeys had no authorization or browser errors. |
| I | `I - canonical mutation consistency` | Fresh Cargo I: allocate to ExecutionUnit X in UI, verify Tracking/refresh/reopen, delete using the returned Allocation ID, verify absence, then allocate to ExecutionUnit Y and repeat Tracking/refresh/reopen. | Fixture begins with 0 canonical rows. UI POST returns a real Allocation ID distinct from Cargo ID; UI DELETE sends that exact ID and is not 404. Canonical states are 0 → X/1 → 0 → Y/1; no current legacy row, duplicate, orphan, or stale X truth remains. | PASS — two independent fresh disposable browser runs passed with zero unexpected browser errors and complete cleanup. |

Rows become `PASS` only after each independently named scenario has passed in two clean disposable runs.

## I acceptance evidence

`I_FIXTURE_CONTRACT=PASS; I_INITIAL_CANONICAL_ALLOCATION_COUNT=0; I_ACTOR_AUTHORIZATION=PASS.` Organization A's operator has Project I access and the required execution-unit read/update permissions. Cargo I is eligible and starts with neither a canonical nor a legacy allocation; X and Y are distinct, same-project execution units.

`I_FIRST_ALLOCATION=PASS; I_FIRST_TRACKING=PASS; I_FIRST_REFRESH_REOPEN=PASS.` The actual Shared Transport UI allocated Cargo I to X. The POST response exposed a non-empty `ExecutionUnitCargoAllocation.public_id`, distinct from the Cargo public ID; Tracking projected X as `canonical_execution` through refresh and reopening.

`I_DELETE_STATUS=PASS; I_DELETE_404=NO; I_POST_DELETE_TRACKING=PASS; I_POST_DELETE_REFRESH_REOPEN=PASS.` The UI DELETE request was intercepted and required to end in the exact created Allocation ID. It completed without 404, removed the canonical record and X membership, and X did not reappear in Tracking after refresh/reopen.

`I_REALLOCATION=PASS; I_SECOND_TRACKING=PASS; I_SECOND_REFRESH_REOPEN=PASS.` The actual UI created a new Allocation ID for Cargo I on Y; it differed from the deleted ID and the Cargo ID. Tracking then projected Y only, and retained Y through refresh/reopen.

`I_CANONICAL_STATE_TRANSITIONS=PASS; I_ALLOCATION_ID_CONTRACT=PASS; I_LEGACY_CURRENT_WRITES=0; I_LEGACY_WRITE_INVARIANT=PASS.` Browser lifecycle assertions prove 0 → X/1 → 0 → Y/1; the supplemental database audit confirms exactly one final canonical row on Y, zero legacy allocation rows for Cargo I, and no X canonical Tracking projection.

`I_DUPLICATE_CANONICAL_ALLOCATIONS=0; I_ORPHANED_ALLOCATIONS=0; I_STALE_CURRENT_TRUTH=0; I_ERROR_AUDIT=PASS.`

`I_RUN_1=PASS; I_CLEANUP_RUN_1=PASS.` Evidence directory: `shared-transport-8b292c5287404f4595c200694d0f91ca`.

`I_RUN_2=PASS; I_CLEANUP_RUN_2=PASS; I_INDEPENDENT_EXECUTION=PASS.` Evidence directory: `shared-transport-18d82c837b2f4a60877b1818d4b678a9`. Both runs used new disposable DBs, seed state, credentials, processes, runtimes and browser contexts; cleanup left zero runner runtime directories and no qualification process.

`BROWSER_I=PASS; BROWSER_A_I=PASS; E2E_CLEANUP=PASS.`

## H acceptance evidence

`H-TENANT-FIXTURE-001; CLASS = FIXTURE_DEFECT; STATUS = CLOSED.` The fixture now explicitly validates a complete Organization-B graph: its distinct organization ID owns Project B, Shipment B, Cargo B, Owner B, Carrier B, ExecutionUnit B, and the canonical B cargo allocation. Actor A is an Organization-A member only and has no Organization-B access.

`H_POSITIVE_ACCESS=PASS; H_NEGATIVE_UI=PASS; H_API_READ_DENIAL=PASS; H_CROSS_TENANT_MUTATIONS=DENIED; H_FOREIGN_STATE_UNCHANGED=PASS.` Actor A opened the legitimate A execution and tracking context. The implemented shared-transport cargo and carrier selectors excluded B identities. Direct B shipment, cargo, tracking and execution reads, B-to-A allocation, and foreign owner/carrier assignment probes returned fail-closed 403/404 responses with no protected labels or opaque IDs. Fixture state starts with the B allocation on B's unit and is fresh for every run, so rejected probes cannot persist a cross-tenant relation.

`H_OWNER_SELECTOR_ISOLATION=PASS; H_OWNER_ASSIGNMENT_ISOLATION=PASS; H_CARRIER_SELECTOR_ISOLATION=PASS; H_CARRIER_ASSIGNMENT_ISOLATION=PASS; H_TRACKING_ISOLATION=PASS; H_RESPONSE_LEAKAGE=NONE.` Owner and carrier resolution are organization-scoped; normal A tracking works while B tracking is denied. No denied body contained B cargo, owner, carrier, execution code, or supplied foreign opaque identity.

`H_UNAUTHORIZED_EAGER_REQUESTS=0; H_ERROR_AUDIT=PASS; H_TENANT_IDENTITY_ISOLATION=PASS.` Positive A navigation recorded zero console/page errors and no unexpected failed API request. Isolation derives from organization IDs in the fixture, selector queries, execution lookup, allocation service and tracking authorization—not display labels.

`H_RUN_1=PASS; H_CLEANUP_RUN_1=PASS.` Evidence: `shared-transport-9b80082b73d84fb990d2513718c8b6f9`.

`H_RUN_2=PASS; H_CLEANUP_RUN_2=PASS; H_INDEPENDENT_EXECUTION=PASS.` Evidence: `shared-transport-0e4f7b6f0c31475782e1792e74706a16`. Each run used a distinct disposable DB, seed, credential, runtime, processes and browser context; cleanup left zero runner runtimes.

`SHARED_TRANSPORT_AUTH_INVARIANTS=PASS.` G establishes ProjectAccess within Organization A; H establishes organization-ID isolation across tenants. Project-derived reads/mutations remain fail-closed, tenant-scoped owner/carrier candidates never cross organization, and normal hidden UI surfaces make no unauthorized eager request. I remains NOT RUN.

## G acceptance evidence

`G-ACCEPTANCE-COVERAGE-001; CLASS = TEST_DEFECT; STATUS = CLOSED.` The former G scenario tested only the eligible-Cargo selector and one allocation denial. It was replaced with ProjectAccess coverage without broadening the product authorization model.

`G_SCOPE_MECHANISM=ProjectAccess.` Project-scoped resources are Project, Operational Shipment, Shipment Cargo, project-derived ExecutionUnit routes, eligible Shared Transport Cargo, and Shipment Tracking. Tenant-scoped resources are Carrier and Owner selectors; they are deliberately `N/A_FOR_G_PROJECTACCESS` and no same-tenant Carrier restriction is asserted.

`G_FIXTURE_CONTRACT=PASS; G_POSITIVE_ACCESS=PASS; G_NEGATIVE_UI=PASS.` The restricted actor has exactly one ProjectAccess row for Project A, can find Project A, allocate Cargo A, open Shipment A and read its Tracking. Project B is absent from the project selector, Shared Transport eligible-Cargo selector and authenticated Project-A journey.

`G_API_READ_DENIAL=PASS; G_API_MUTATION_DENIAL=PASS; G_RESPONSE_LEAKAGE=NONE.` Direct reads of Project-B Shipment, Cargo, Tracking and project-derived execution data, plus allocation of Cargo B and protected Cargo-B/Shipment-B mutations, returned intentional fail-closed 403/404 responses. Bodies contained none of the protected labels or opaque identifiers. Canonical authorized allocation output did not contain Cargo B.

`G_UNAUTHORIZED_EAGER_REQUESTS=0; G_ERROR_AUDIT=PASS.` The positive browser journey recorded zero console errors, page errors, failed requests, or unexpected 401/403/404/409/500 responses. Intentional negative API checks ran only after that audit.

`G_RUN_1=PASS; G_CLEANUP_RUN_1=PASS.` Evidence directory: `shared-transport-797e0b44721549728bbc8919719b05d3`.

`G_RUN_2=PASS; G_CLEANUP_RUN_2=PASS; G_INDEPENDENT_EXECUTION=PASS.` Evidence directory: `shared-transport-8e01569e14304127913dfd4ebe402eb1`. Each final run used a new disposable database, migration, seed state, credential, backend/frontend process tree and browser context; each emitted `E2E_CLEANUP = PASS`.

`POWERSHELL_5_1_HARNESS=PASS.` Windows PowerShell 5.1 parsed the runner; the runner created readable UTF-8 fixture output and completed two fresh G executions without a BOM/encoding regression. `PRODUCTION_SOURCE_CHANGED=NO.`

## F acceptance evidence

`F_FIXTURE=PASS.` Organization A contains ExecutionUnit `SHARED-E2E-UNIT`, active same-tenant Carrier X and Carrier Y, and the authorized Organization Admin actor. Foreign Carrier Z is the active Customer in Organization B. The fixture starts with `ExecutionUnit.carrier_customer_id = NULL` (unassigned).

`F-01…F-07=PASS.` The actual ExecutionUnit UI lists X and Y but not the foreign Customer. X saves successfully, is displayed by the execution, and its exact ID is selected again after refresh/reopen. Cargo A is allocated only within this F journey to give the associated Shipment a canonical ExecutionUnit Tracking projection.

`F-08…F-11=PASS; F-16…F-17=PASS.` The actual Shipment Tracking UI and authenticated Tracking response identify `SHARED-E2E-UNIT` as `canonical_execution` and show Carrier X, then Carrier Y after the X→Y mutation. No legacy row becomes a competing current carrier.

`F-12…F-15=PASS.` Y saves, is displayed, and its exact ID remains the selected UI value after refresh/reopen.

`F_CLEAR_SUPPORTED=YES; F-18…F-21=PASS.` The intended UI supports selecting the explicit unassigned option. The null value saves, remains selected after refresh/reopen, and neither ExecutionUnit nor Tracking presents Y as current Carrier.

`F_EXECUTIONUNIT_CARRIER_TRUTH=PASS; F_CARGO_LEVEL_CARRIER_MUTATOR=NO.` The canonical column is `ExecutionUnit.carrier_customer_id`; the carrier command mutates only that column. Tracking resolves `unit.carrier_customer_id` for its `canonical_execution` projection. No Cargo-level Carrier assignment endpoint or write was added.

`F_CARRIER_TENANT_ISOLATION=PASS; F_CARRIER_AUTHORIZATION=PASS.` Foreign Carrier Z is absent from the selector. A direct PATCH with its ID is denied (403/404), makes no assignment, and omits the foreign label. The authorized F actor can perform the same-tenant mutations.

`F_ERROR_AUDIT=PASS; F_REFRESH_REOPEN_CONSISTENCY=PASS.` Each positive browser journey recorded zero unexpected console errors, page errors, failed requests, or HTTP 401/403/404/409/500 responses. The intentional foreign direct PATCH is excluded as an expected negative check.

`DEFECT_ID: F-CARRIER-UI-HYDRATION-001`  
`DEFECT_CLASS: CURRENT_SLICE_PRODUCT_DEFECT`  
`STATUS: CLOSED.` The execution form rendered the saved Carrier label after reopening but reset its select value to empty, obscuring the persisted identity and risking an accidental clear on a later save. The bounded correction includes `{id, label}` for the already-authorized carrier in the ExecutionUnit response and hydrates the selector from that canonical value. It does not add a new Carrier owner, endpoint, or permission.

`F_RUN_1=PASS; F_RUN_2=PASS; F_INDEPENDENT_EXECUTION=PASS.` Final evidence directories: `shared-transport-80a31a6ed58e49c38f0bf0b2857ebaea` and `shared-transport-8d4af48abfe84dc7b89993bf7689a224`. Each used a new disposable database, migration, seed, credential, backend/frontend process tree, and browser context; neither invoked A–E or G–I.

`F_CLEANUP_RUN_1=PASS; F_CLEANUP_RUN_2=PASS; E2E_CLEANUP=PASS.` After each final run the disposable database was dropped, captured processes stopped, qualification runtime directory count was zero, and the ephemeral process credential was absent.

## E acceptance evidence

`DEFECT_ID: E-NULL-TRACKING-001`
`CLASSIFICATION: FIXTURE_DEFECT`
`ROOT_CAUSE: The historical Ownerless Cargo fixture had no ShipmentTransportUnit / ShipmentCargoTransportAllocation lineage, so Tracking correctly returned an empty unit list. The product already rendered the NULL owner safely.`

`FIXTURE_CORRECTION: PASS.`  The deterministic fixture now creates the smallest tenant-owned historical legacy context for the Ownerless Cargo: `ShipmentTracking` → `SHARED-E2E-LEGACY-NULL-OWNER` → `ShipmentCargoTransportAllocation`. The allocation is historical-only; no canonical allocation, runtime legacy mutator, or synthetic Cargo Owner was introduced. `cargo_owner_customer_id` remains `NULL`.

`E_NULL_TRACKING_FIXTURE=PASS; E_NULL_OWNER_IDENTITY_PRESERVED=PASS.`  Fixture graph and post-browser database audits require the NULL owner, the legacy unit, the legacy allocation, and a Tracking projection containing that unit with the Cargo's owner value still `null`. The browser verifies the approved UI text `نامشخص / ثبت نشده`, the historical unit, and refresh/reopen stability.

`E_RUN_1=PASS; E_RUN_2=PASS.`  Each run created a fresh disposable PostgreSQL database, upgraded to `20260917_shared_transport_execution`, seeded a deterministic graph, used a new credential, and launched fresh backend, frontend, and browser processes. Playwright records: `shared-transport-4f5331d4c8e046b2a97a5aae52b93551` and `shared-transport-b5dfb59789c14625882dbaded9c56ff5`, both with `status: passed`.

`E_ERROR_AUDIT=PASS.`  Both runs recorded zero unexpected console errors, page errors, or failed HTTP 401/403/404/409/500 requests. The direct foreign-owner PATCH remains an explicitly expected negative authorization call and its body has no identifying leak.

`E_OWNER_AUTHORIZATION=PASS; E_OWNER_TENANT_ISOLATION=PASS; E_OWNER_IDENTITY_CONSISTENCY=PASS.`  Cargo A changes from Owner A to Owner B by database identity and remains Owner B after refresh, reopening Shared Transport, and Tracking. Owner B is same-tenant and selectable; the foreign Owner is absent from the selector and denied by the direct update call without leakage. The historical Cargo's `NULL` identity remains distinct from displayed fallback text.

`E_INDEPENDENT_EXECUTION=PASS.`  E was invoked twice by name only, without A–D state. Both completed runners removed their own credential, stopped child processes, dropped their disposable databases, and left no listener on the qualification ports.

`DEFECT_ID: E2E-CLEANUP-001`  
`CLASSIFICATION: HARNESS_DEFECT`  
`STATUS: CLOSED.`  Five interrupted-run directories with the exact historical `forwarder-shared-e2e-<32-hex-run-id>` naming contract and expected `fixtures.json` runtime structure were inventoried. No process referenced any candidate, so all five were confirmed runner-owned, unused, and safely removed. No unrelated temporary directory was touched.

`RUNNER_HARDENING=PASS; STALE_RECOVERY_IMPLEMENTED=PASS.`  Each new execution now creates a single runner-owned runtime directory and a non-secret `qualification-owner.json` manifest containing only purpose, run ID, creation time, and repository identity. Startup recovery accepts only an ownership-valid manifest, or the bounded legacy prefix-plus-fixture contract, and refuses cleanup if a referencing process is alive. Current-run cleanup stops only captured backend/frontend process trees, retries runtime deletion, drops the exact disposable database, restores process environment, and fails the run if any cleanup step is incomplete.

`E_CLEAN_RUN_1=PASS; E_CLEANUP_RUN_1=PASS.`  Playwright evidence `shared-transport-42f9f17609964784b87afb3401b53181` passed. Its current disposable database, captured backend/frontend process trees, runner runtime directory, and ephemeral credential were absent immediately afterward.

`E_CLEAN_RUN_2=PASS; E_CLEANUP_RUN_2=PASS.`  Independent Playwright evidence `shared-transport-d05e06f0ebe84631a95112d70b8ca3e1` passed with the same fresh lifecycle. Its database, processes, runtime directory, and credential were again absent immediately afterward.

`E2E_CLEANUP_DETERMINISM=PASS; BROWSER_E=PASS; E2E_CLEANUP=PASS.`  After both runs, the qualification runtime namespace was empty and no qualification process or process-scoped credential remained. `E-NULL-TRACKING-001=FIXTURE_DEFECT/CLOSED`; `E2E-CLEANUP-001=HARNESS_DEFECT/CLOSED`.

## C acceptance evidence

`C_RUN_1=PASS; C_RUN_2=PASS.`  Each run created a fresh disposable PostgreSQL database, upgraded to `20260917_shared_transport_execution`, seeded a deterministic graph, used a new credential, and launched new backend, frontend, and browser processes.  The C actor is authorized through explicit `ProjectAccess` rows for Projects A, B, X, and Y; it has no unrelated Project Configuration permission, and the surface does not mount or fetch it.

`C1_FIXTURE=PASS.`  Projects A/B, Shipments A/B, Cargo A/B, and Owner A/B are distinct identities in the same tenant.  `C2_FIXTURE=PASS; C2_DISTINCT_IDS=PASS; C2_EQUAL_DISPLAY_NAMES=PASS.`  Cargo X/Y are owned by separate active Customer rows with equal `company_name` labels.  The browser asserts Project/Shipment lineage for A/B, four distinct owner identities after X/Y, Persian `تجمیع بار چند مشتری`, no raw `multi_customer_groupage` enum, and refresh/reopen persistence.

`OWNER_IDENTITY_CLASSIFICATION=PASS; CLASSIFICATION_IDENTITY_SOURCE=PASS.`  `shared_transport_service` derives groupage from `ShipmentCargoItem.cargo_owner_customer_id` sets; it does not use any display or normalized name.  The browser-visible equal labels for X/Y remain separate allocations, and their different fixture identities keep the derived result multi-customer groupage.

`C_CANONICAL_WRITE=PASS; C_TRACKING_CONSISTENCY=PASS.`  The supplemental database audit found exactly four current `ExecutionUnitCargoAllocation` rows (A, B, X, Y) on one execution and zero current `ShipmentCargoTransportAllocation` rows for them.  Browser/API Tracking verified each Cargo's canonical execution and its own Cargo relationship; Tracking's canonical-first implementation excludes competing legacy rows for canonical Cargo.

`C_ERROR_AUDIT=PASS.`  Both runs recorded zero unexpected console errors, page errors, or HTTP 401/403/404/409/500 responses.  `C_INDEPENDENT_EXECUTION=PASS; E2E_CLEANUP=PASS.`  The runner removed each temporary runtime and credential, dropped each disposable database, and stopped qualification child processes.

## B-ERROR-AUDIT-001 resolution

`DEFECT_ID: B-ERROR-AUDIT-001`  
`DEFECT_CLASS: CROSS_SLICE_PRODUCT_DEFECT`  
`CLASS: CROSS_SLICE_PRODUCT_DEFECT`  
`ROOT_CAUSE: ExecutionUnits unconditionally mounted ProjectConfiguration. On the initial Services tab, its list request ran once on page open, refresh, and reopen. The B actor has Shared Transport capabilities but not project_configuration.read, so the panel's own eager GET requests were correctly denied and surfaced as browser errors.`  
`CORRECTION: ProjectConfiguration is now mounted through the existing OperationalPermission gate for project_configuration.read. An actor without that entitlement sees no Project Configuration surface and no configuration data request; Shared Transport stays available.`  
`REPRODUCTION: B_403_REQUEST_1/2/3 = GET /api/v2/projects/{projectId}/configuration/services?page=1&per_page=100, called by ProjectConfiguration > Panel.load on initial mount, refresh, and reopen; each requires project_configuration.read and each returned 403. Console origin was Chromium's failed-resource error for that endpoint. PROJECT_CONFIGURATION_VISIBLE = YES before correction, NO after correction. PROJECT_CONFIGURATION_ENTITLED = NO.`  
`SECURITY: Direct GET /api/v2/projects/{projectId}/configuration/services?page=1&per_page=100 for the B actor is intentionally asserted as 403; backend authorization is unchanged and strict.`  
`BROWSER_B: PASS. UNEXPECTED_CONSOLE_ERRORS=0; UNEXPECTED_PAGE_ERRORS=0; UNEXPECTED_FAILED_REQUESTS=0; UNEXPECTED_401/403/404/409/500=0. B_INDEPENDENT_EXECUTION=PASS. E2E_CLEANUP=PASS.`

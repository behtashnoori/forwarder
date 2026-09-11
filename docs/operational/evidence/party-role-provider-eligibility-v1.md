# Party Role / Provider Eligibility v1

`Customer` remains the tenant-scoped business-party identity. `CustomerRoleAssignment` is its additive, multi-role eligibility child. `CARGO_OWNER_CONTEXTUAL_RELATION=YES`: Cargo Owner is still `ShipmentCargoItem.cargo_owner_customer_id`; it does not require a role. `CARRIER_ELIGIBILITY_ROLE=CARRIER`.

The migration adds the child table and derives active CARRIER assignments only for distinct Customer identities already referenced by `ExecutionUnit.carrier_customer_id` in the same organization. It does not infer eligibility from Cargo Owner use, names, or activity. The current Carrier relationship remains `ExecutionUnit.carrier_customer_id`.

Candidate resolution requires active tenant Customer plus active tenant CARRIER assignment. Deactivating the role prevents future selection but deliberately does not clear existing execution facts. The authority audit rejected legacy `business_expert`: operational eligibility is governed by the canonical `ORGANIZATION_ADMIN` authority with one active tenant membership. Foreign Customer IDs return no mutable record.

Real disposable PostgreSQL qualification passed for `20260917_shared_transport_execution → 20260918_customer_carrier_role`: B received one role, C received one role despite two executions, A received none, and the foreign-tenant Carrier received one role in its own tenant. Downgrade and re-upgrade reproduced the same result and preserved all four execution carrier references. Browser qualification remains pending.

## PR02-001 diagnostic closure

The apparent failure was a `TEST_DEFECT`. The browser helper inspected the checkbox while per-customer role requests were still loading. Its transient unchecked render matched the requested OFF state, so no PUT was sent. Trace evidence showed the missing mutation followed by fresh backend truth of `carrier_eligible=true`.

The helper now waits for the known pre-mutation state, performs the PUT, and waits for the post-mutation state. A fresh disposable PostgreSQL browser run passed active → inactive → active. While inactive, the fresh carrier-options response and selector excluded Customer B, while the Execution Unit and Tracking retained B as the recorded Carrier.

`PR02_001_STATE_1 = PASS`  
`PR02_001_STATE_2 = PASS`  
`PR02_001_STATE_3 = PASS`  
`BACKEND_CARRIER_CANDIDATE_REGRESSION = PASS`  
`FRONTEND_CARRIER_SELECTOR_REGRESSION = PASS`  
`PR02_001_BROWSER_REGRESSION = PASS`  
`PR02-001 = CLOSED`

## PR02_RUN_1 complete qualification — 2026-09-09

`PR02_COVERAGE_MATRIX = COMPLETE`. A new loopback-only disposable PostgreSQL
database was migrated through `20260918_customer_carrier_role`, seeded with the
deterministic Shared Transport graph, and exercised with new credentials,
backend, frontend, Chromium context, and runner runtime. The browser asset
passed all eight assertions and the runner removed the database, processes,
runtime directory, and process-scoped credential (`E2E_CLEANUP = PASS`).

`ROLE_UI_AUTH_ALIGNMENT = PASS`; `ROLE_ASSIGN_UI = PASS`;
`ROLE_REMOVE_UI = PASS`; `ROLE_REASSIGN_UI = PASS`;
`ROLE_REFRESH_REOPEN = PASS`; `ROLE_REMOVAL_NON_DESTRUCTIVE = PASS`.

`CARRIER_SELECTOR_CONTRACT = PASS`; `DUAL_ROLE_BROWSER = PASS`;
`TRACKING_CARRIER_REALITY = PASS`; `CARGO_OWNER_REGRESSION = PASS`.

`EXPERT_ROLE_MANAGEMENT_DENIAL = PASS`;
`BUSINESS_EXPERT_ROLE_MANAGEMENT_DENIAL = N/A — NOT_A_DISTINCT_RUNTIME_ACTOR`;
`PLATFORM_ADMIN_ROLE_MANAGEMENT_DENIAL = PASS`;
`PARTY_ROLE_TENANT_ISOLATION = PASS`; `ROLE_UNAUTHORIZED_EAGER_REQUESTS = 0`.

`RAW_ROLE_ENUM_LEAKAGE = 0`; `TECHNICAL_ROLE_MODEL_LEAKAGE = 0`;
`MIXED_TECHNICAL_ERROR_TEXT = 0`; `SHIPMENT_LIST_REGRESSION = PASS`;
`WORK_QUEUE_REALITY_REGRESSION = PASS`; `CONTROL_TOWER_REALITY_REGRESSION = PASS`;
`SAVED_VIEW_REALITY_REGRESSION = PASS`; `CARRIER_LIFECYCLE_REGRESSION = PASS`;
`NORMAL_JOURNEY_ERROR_AUDIT = PASS`.

`PR02_001_NON_REGRESSION = PASS`: Carrier B was visible when active, absent
from the fresh candidate API and selector when inactive while its recorded
Execution Unit and Tracking facts remained visible, then became selectable
again after reactivation.

The first fresh attempt discovered `PR02-002`, a
`CURRENT_SLICE_PRODUCT_DEFECT`: a direct Platform Admin visit to a tenant
operational route mounted tenant-scoped reads and emitted four expected-API
403s as unexpected browser errors. A bounded route guard now prevents
Platform Admin from mounting tenant operational surfaces. The complete matrix
was restarted from a new environment and passed. No migration changed.

`PR02_RUN_1 = PASS`; `PR02_CLEANUP_RUN_1 = PASS`; `E2E_CLEANUP = PASS`.
Focused validation: backend Party Role/Carrier and selector API tests (13
passed); frontend Execution Unit/Carrier tests (5 passed); TypeScript, lint,
production build, Python compile, PowerShell runner parse, and `git diff
--check` all passed. Run #2 was not executed.

## PR02_RUN_2 independent qualification — 2026-09-09

Run #2 started only after recording the expected dirty worktree, a clean
`git diff --check`, branch `feature/shipment-summary-presentation-polish`, and
the current qualification migration head
`20260918_customer_carrier_role`.  No qualified product source or test asset
changed after the successful Run #1: `RUN_2_ASSET_UNCHANGED_FROM_RUN_1 = PASS`.

The runner created a new disposable loopback PostgreSQL database
`forwarder_integrated_cert_shared_9369600ce47a4a9a98f257ad6caaec9c`, migrated
it from empty state through `20260918_customer_carrier_role`, seeded a fresh
deterministic graph, generated a new process-scoped credential, and launched
new backend, frontend, Chromium context, and runtime.  It did not reuse a
Run #1 database, state, credential, process, browser context, or runtime:
`PR02_RUN_2_ENVIRONMENT_INDEPENDENT = PASS`.

The complete eight-test browser matrix passed with no failure artifacts:
`ROLE_UI_AUTH_ALIGNMENT = PASS`; `ROLE_ASSIGN_UI = PASS`;
`ROLE_REMOVE_UI = PASS`; `ROLE_REASSIGN_UI = PASS`;
`ROLE_REFRESH_REOPEN = PASS`; `ROLE_REMOVAL_NON_DESTRUCTIVE = PASS`;
`CARRIER_SELECTOR_CONTRACT = PASS`; `DUAL_ROLE_BROWSER = PASS`;
`TRACKING_CARRIER_REALITY = PASS`; `CARGO_OWNER_REGRESSION = PASS`;
`EXPERT_ROLE_MANAGEMENT_DENIAL = PASS`;
`BUSINESS_EXPERT_ROLE_MANAGEMENT_DENIAL = N/A — NOT_A_DISTINCT_RUNTIME_ACTOR`;
`PLATFORM_ADMIN_ROLE_MANAGEMENT_DENIAL = PASS`;
`PARTY_ROLE_TENANT_ISOLATION = PASS`; `ROLE_UNAUTHORIZED_EAGER_REQUESTS = 0`;
`RAW_ROLE_ENUM_LEAKAGE = 0`; `TECHNICAL_ROLE_MODEL_LEAKAGE = 0`;
`MIXED_TECHNICAL_ERROR_TEXT = 0`; `SHIPMENT_LIST_REGRESSION = PASS`;
`WORK_QUEUE_REALITY_REGRESSION = PASS`;
`CONTROL_TOWER_REALITY_REGRESSION = PASS`;
`SAVED_VIEW_REALITY_REGRESSION = PASS`;
`CARRIER_LIFECYCLE_REGRESSION = PASS`; `NORMAL_JOURNEY_ERROR_AUDIT = PASS`.

`PR02_001_NON_REGRESSION_RUN_2 = PASS`: Carrier B was present when eligible,
its recorded Execution Unit and Tracking fact remained after inactivation
while new candidate responses and the selector excluded it, and eligibility
returned after reactivation.  `PLATFORM_ADMIN_UI_GUARD_NON_REGRESSION = PASS`:
Platform Admin could not mount tenant operational data, made no unauthorized
eager tenant requests, received no technical leakage, and its direct
protected mutation remained denied.

The runner removed its database, processes, runtime directory, and ephemeral
credential.  Post-run runtime and local listener checks were empty:
`PR02_RUN_2 = PASS`; `PR02_CLEANUP_RUN_2 = PASS`; `E2E_CLEANUP = PASS`.
Therefore `PR02_INDEPENDENT_EXECUTION = PASS`; `PR02_BROWSER = PASS`;
`PR02 = PASS`; `PRODUCT_REALITY = PASS`.

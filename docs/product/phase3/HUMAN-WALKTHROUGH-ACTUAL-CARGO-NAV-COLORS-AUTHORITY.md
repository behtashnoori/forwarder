# Human Walkthrough — Actual Cargo save and navigation color authority

Date: 2026-10-02 (Asia/Tehran). Governing baseline: LPAF v2.7, Level B,
capability route Sol. Canonical entry is
`integration/golden-controlled@e5ff5e9dd70b6d05cb83321086d851e790b78946`,
clean and equal to origin at `0/0`. The sole migration head is
`20261017_document_type_ownership`; this mission requires no migration.

## Mission contract and Product Authority Record

| Field | Governed value |
| --- | --- |
| Outcome | Resolve `HW_ACTUAL_CARGO_SAVE_001` and normalize navigation colors through the existing design system. |
| `AUTHORIZED_PRODUCT_CHANGES` | Make the existing Cargo editor unambiguously distinguish planned and actual quantity, persist the selected fact, identify the saved fact in feedback, refresh summary/history/readiness consistently; introduce the smallest shared semantic navigation color roles and apply them to global, Shipment, Customer/Request and Admin navigation states. |
| `DELEGATED_TECHNICAL_CHOICES` | Input normalization and validation, bounded payload construction, no-op detection, feedback placement, semantic token names/classes, exact accessible HSL values, focused tests and evidence organization. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | Cargo schema/model; requested/planned/actual meanings; allocation, route, ETA rules, closure, Request/Quote, geography, Documents, RBAC, history append-only semantics, typography system, layout architecture, status/warning/success colors, dark-mode redesign, all preserved walkthrough business facts, Production, deployment and Release. |
| `DECISIONS_NEEDED` | `NONE` at entry. Stop if schema migration, new Cargo meaning, new workflow, preserved-data repair, or broader visual redesign becomes necessary. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing “FORWARDER — ACTUAL CARGO SAVE CORRECTION + NAVIGATION COLOR STANDARDIZATION”. |
| `APPROVAL_REFERENCE` | Supplied mission dated 2026-10-02, sections 1–28. |
| Definition of Done | Cases A1–A11, focused backend/frontend/PostgreSQL 18/browser checks, deterministic contrast evidence, exact candidate identity, controlled integration and same-runtime source refresh pass while protected data remains unchanged and the new ETA Shipment remains untouched. |

## Entry diagnosis and ownership

The preserved ETA Shipment is
`c71ca04e-fee6-48ed-88b0-2b20255b11cc`; Cargo
`15eed482-db3a-4cb7-9375-431314968ad9` has planned `100`, actual `NULL`,
version `1`, no pinned Route Basis, no Execution, no Allocation, no route
progress and no ETA snapshot. Runtime HTTP evidence records a successful Cargo
`PATCH` at 21:18:33, while the row remained version `1` and its only Cargo
history is the creation transition from unknown planned quantity to `100`.

The backend already owns separate `planned_quantity` and `actual_quantity`
columns, validation, audit and read projection. The observed request was a
successful no-op: the existing editor submitted the unchanged plan and a null
actual value, the service legally returned `200` when `changes` was empty, and
the UI provided no fact-specific success/no-change result. The editor rendered
the two quantities as adjacent placeholder-only numeric controls, so it did not
provide a strong visible binding between the human intention and the submitted
fact. The correction stays in the current form and existing API/SOR.

Navigation color ownership remains the existing HSL design tokens in
`src/index.css`. Raw slate, blue, primary, muted and generic button variants
currently express equivalent navigation states across global navigation,
Shipment tabs, Customer navigation and Admin tabs. A bounded semantic
navigation layer will reference the existing palette and remain independent of
status/alert colors.

## Journey and reference impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`.

- Cargo and Shipment workspace: `FWD-J04`, `FWD-J08`, `FWD-J09`,
  `FWD-IPJ-02`, `FWD-IPJ-04`.
- Customer/Request and Admin navigation: `FWD-J02`, `FWD-J03`, `FWD-J06`,
  `FWD-J08`, `FWD-IPJ-01`, `FWD-IPJ-03`.
- Required reruns: Cargo planned/actual/API/history/readiness/authorization and
  tenant isolation; representative global, Shipment, Customer/Request and Admin
  navigation at desktop and narrow width; affected integrated browser journeys.
- Human Product Walkthrough remains `IN_PROGRESS`; this mission cannot grant
  Human PASS or Release Ready.
- LPAF reference impact: `NONE`; v2.7 is applied without change.
- Project reference impact: `UPDATE_REQUIRED` for this authority record,
  finding register and exact-candidate evidence. Product Contract and Journey
  Pack semantics remain unchanged.

## PDA-07 target reconciliation

`AUTHORIZED`: fact-explicit Cargo editing/feedback/no-op handling and shared
navigation colors/states. `PRESERVED`: all Cargo meanings and backend authority,
all status/alert semantics, typography/layout, and every named out-of-scope or
preserved runtime fact. Any other observable difference is `VIOLATION` or
`UNKNOWN` and blocks integration.


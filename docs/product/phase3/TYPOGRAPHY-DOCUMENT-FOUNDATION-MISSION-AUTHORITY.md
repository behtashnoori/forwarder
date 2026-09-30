# Typography and Document Foundation Mission Authority

## Mission contract

| Field | Record |
| --- | --- |
| Outcome | Integrate the qualified Persian typography/presentation subset and the four-entry generic V1 Document Type package, then apply only that package to the preserved local walkthrough runtime. |
| Governing baseline | `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`; canonical repository governance remained v2.7 throughout this mission. The earlier v2.6 label was a reporting defect caused by a stale untracked `AGENTS.md` in an unrelated working checkout; that file was not present in that checkout's Git HEAD and no canonical governance file changed baseline. |
| Rigor and route | `Level B — Product / local preserved walkthrough`; `Sol` because extraction, candidate-bound verification, controlled integration, and preserved-runtime evidence are coupled. |
| Owner / authority | Product Owner; explicit user mission supplied on 2026-09-30. |
| Starting canonical identity | `4e1709f2dd50f350c69a202bbf71727a654fd3c9`. |
| Source candidate identity | `b49d46ca3c1c3b4e33fe5b36ed7e0a7d377b8dbe`. |
| Human walkthrough | `IN_PROGRESS`. |
| Release Ready | `NO`. |

## Product Authority Record

`AUTHORIZED_PRODUCT_CHANGES`

- Apply the qualified `@fontsource-variable/vazirmatn@5.3.0` font, typography tokens, spacing/rhythm, navigation, Shipment Workspace, form, bidi, localized UOM/status/file-input, and presentation-only localization refinements.
- Add exactly four generic operational Document Types: `generic_transport_document`, `generic_invoice`, `generic_packing_list`, and `generic_delivery_receipt` with Product Owner provenance and no statutory, customs, legal-proof, carrier, or contractual-requirement claim.
- Make those four definitions available as `OPTIONAL` in the same preserved local walkthrough organization using the existing governed package mechanism.

`DELEGATED_TECHNICAL_CHOICES`

- Font packaging/import mechanics, CSS tokens, presentation classes, component integration points, stable catalog metadata, focused-test selection, evidence layout, and controlled Git integration mechanics.

`PROTECTED_OUT_OF_SCOPE_BEHAVIOR`

- Business logic, authorization, Shipment lifecycle, Route, ETA, allocations, Delivery, document upload/completion semantics, closure semantics/state, and operational-stage semantics/model/configuration.
- The preserved Shipment `c66be7ef-ee20-4d39-a985-a3db5bd611db`: Requested `100`, Planned `100`, Actual Cargo `UNKNOWN`, Planned Allocation `100`, Actual Allocation `95`, Delivered `95`, historical destination `بندرعباس`, manual position `نزدیک مرز`, and `project_id = NULL`.
- No Route Reference, structured progress, Delivery, allocation, file upload, stage progress, closure evaluation/action, Production access, deployment, or release.

`DECISIONS_NEEDED`

- Operational stages remain Project-scoped while the preserved Shipment has no Project binding; no approximation or remediation is authorized in this mission.
- Closure policy lacks independent exact criteria for `FINAL_DELIVERY_EXISTS` and `REQUIRED_OPERATIONAL_STAGES_COMPLETE`; no approximation or remediation is authorized in this mission.

`APPROVING_OWNER_OR_AUTHORITY`: Product Owner.

`APPROVAL_REFERENCE`: user-supplied “FORWARDER — INTEGRATE QUALIFIED TYPOGRAPHY + DOCUMENT FOUNDATION ONLY” mission dated 2026-09-30.

## Facts, assumptions, and unknowns

- FACT: the source candidate is one commit ahead of `4e1709f2...` and changes 27 paths.
- FACT: no source-candidate path implements an operational-stage or closure model/evaluator/policy; its old broad v2.7 mission-authority file nevertheless describes aborted stage/closure scope and must not be integrated unchanged.
- FACT: this correction supersedes only the earlier incorrect v2.6 baseline statements; Product identity and all Product, runtime, test, and qualification results remain unchanged.
- FACT: the repository baseline contains governed Document Catalog package loading and organization document-policy services.
- ASSUMPTION: none may redefine Product behavior or the preserved runtime facts.
- UNKNOWN pending candidate-bound verification: exact affected frontend test, build, lint, bidi/browser, and preserved-runtime outcomes.

## Journey, reference, and verification contract

`JOURNEY_IMPACT = AFFECTS_EXISTING_JOURNEY`: global typography and presentation can affect all user-facing surfaces. Browser evidence is therefore required for the affected normal navigation and Shipment Workspace presentation before controlled integration.

- LPAF reference impact: `NONE`; this mission applies v2.7 and does not amend it.
- Project reference impact: `UPDATE_REQUIRED` only for this authority record and candidate-bound evidence report; business contracts remain unchanged.
- Required evidence: exact diff classification; focused document-package and affected frontend tests; full frontend tests; type-check; production build; lint; architecture/diff checks; browser presentation journey; controlled push/fetch identity; preserved-runtime before/after proof.
- Stop conditions: any lifecycle path or semantic change, Product Authority Reconciliation `VIOLATION`/`UNKNOWN`, required check failure, runtime-fact drift, missing exact package mechanism, Production access, or destructive database action.
- Definition of Done: only the authorized subset is integrated; `DOCUMENT_TYPE_COUNT=4`, `DOCUMENT_REQUIRED_COUNT=0`, `OPERATIONAL_STAGE_COUNT=0`, `CLOSURE_POLICY_ACTIVE=0`; protected Shipment facts are unchanged; canonical ahead/behind is `0/0`; Human Product Walkthrough remains `IN_PROGRESS`; Release Ready remains `NO`.

# P3-12 — command-level closed-state review

Date: 2026-09-26. Architecture accepted at
`6259830f2a5fe94798bf4183d2643bf624529c26`; implementation not started.
Fresh canonical fetch: `368cd736cbffce3d62c33336868738d9086e8306`, clean, 0/0.
Sole canonical migration head: `20261009_phase3_route_time`.
This isolated worktree started at that exact canonical and fast-forwarded only
the retained review/acceptance documentation. P3-11 runtime was not imported.
Managed worktree creation failed because this chat's older repository cannot
resolve canonical SHA (operation 869ab8dd-5dc6-45cb-89b3-94dcc2785baf). Native Git
created `codex/phase3-p3-12-closure` in the actual canonical repository instead.

## Authority and unresolved meaning

The acceptance mission §8 and ADR-068 explicitly require this review and forbid
silently choosing undefined post-closure Product behavior. Original mission §42
requires protecting the closed state, denying normal operational progression,
and preserving only correction mechanisms explicitly valid after closure.
PDA-08 in AGENTS.md stops only the affected design when that authority is missing.

Existing ADR-006/030/050/061/063/064 approve occurrence corrections, exact-version
document commands and Delivery corrections, but none defines their behavior for
the new `closed` state. Product Contract §23 defines checklist and exceptional
closure without specifying late facts, corrections or missing-evidence repair
after closure. Current runtime has no `closed` value, so current tests cannot
supply that Product decision.

The narrow unresolved families are:

- **P312-LATE-FACTS:** whether a completed, closed Shipment may receive a late
  report/Delivery, correction of an earlier occurrence/report/Delivery, or an
  audited actual-quantity/allocation correction. Preserving history is already
  required; permission to add these facts after closure is not yet specified.
- **P312-DOCUMENTS:** whether the owning Expert may append/replace/remove evidence,
  revise its context/visibility or assess required documents after closure,
  especially after an exceptional closure with missing evidence.

No allow or deny has been implemented for those rows. Their blocking effect is
limited to P3-12 closed-state integration. Versioned policy design and independent
P3-13 remain authorized. No new Product policy is inferred from security or tests.

## Matrix

YES/NO below describe the authorized target; DECISION_NEEDED means neither is
chosen. Every command still requires its existing live tenant/actor/parent
authority. Source symbols are in `backend/services/`; function inputs distinguish
normal records from corrections when the existing command handles both.

| COMMAND | ALLOWED_AFTER_CLOSED | DENIED_AFTER_CLOSED | AUTHORITY | REASON |
| --- | --- | --- | --- | --- |
| closure.normal | NO | YES | Acceptance §§5–7; ADR-068 | Only completed→closed; replay may return its retained decision, not close twice |
| closure.exceptional | NO | YES | Acceptance §6; ADR-068 | Same completed-only predecessor; reason never bypasses lifecycle |
| any Shipment reopen/status overwrite | NO | YES | Acceptance §5; original §42 | Closed is terminal; no reopen capability |
| occurrence_projection_service.project_shipment implicit status overwrite | NO | YES | ADR-068 closed-state boundary | Source projection must preserve closed rather than regenerate completed/in_progress |
| route_orchestration_service.create_plan | NO | YES | Original §42; ADR-068 | New operational planning after terminal closure |
| route_orchestration_service.add_leg | NO | YES | Original §42; ADR-068 | New operational route |
| route_orchestration_service.update_leg | NO | YES | Original §42; ADR-068 | Ordinary plan editing |
| route_orchestration_service.delete_leg | NO | YES | Original §42; ADR-068 | Ordinary plan removal |
| route_orchestration_service.add_checkpoint | NO | YES | Original §42; ADR-068 | New planned operational checkpoint |
| route_orchestration_service.update_checkpoint | NO | YES | Original §42; ADR-068 | Ordinary planned checkpoint editing |
| route_orchestration_service.add_dependency | NO | YES | Original §42; ADR-068 | New route execution dependency |
| route_orchestration_service.assign_cargo_destination | NO | YES | Original §42; ADR-068 | New planned Cargo destination |
| route_orchestration_service.activate_plan | NO | YES | Original §42; ADR-068 | Starts a new executable route |
| route_orchestration_service.replan | NO | YES | Original §42; ADR-068 | Reopens operational planning implicitly |
| operational_execution_service.initialize | NO | YES | Original §42; ADR-068 | New executable milestone materialization |
| operational_execution_service.transition | NO | YES | Original §42; ADR-068 | Ordinary execution progression after terminal state |
| operational_execution_service.reopen | NO | YES | Original §42; ADR-068 | Milestone reopening cannot silently reopen a closed Shipment |
| cargo_service.create_shipment_item | NO | YES | Original §42; ADR-068 | Adding new Cargo changes the closed operational scope |
| cargo_service.update_shipment_item planned quantity | NO | YES | Original §42; ADR-068 | Ordinary new planning |
| cargo_service.update_shipment_item actual quantity/correction | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-057 | Could repair an historical quantity or change closure evidence |
| cargo_allocation_service.set_allocation PLANNED | NO | YES | Original §42; ADR-068 | Ordinary new planning |
| cargo_allocation_service.set_allocation ACTUAL correction | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-060 | Historical correction versus new execution meaning |
| cargo_allocation_service.transfer | NO | YES | Original §42; ADR-068 | New physical reallocation/handoff |
| transport_execution_service.create | NO | YES | Original §42; ADR-068 | New execution context |
| transport_execution_service.revise | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-059 | Recorded corrections and ordinary changes share the command |
| route_orchestration_service.record_traversal | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-058 | A newly recorded traversal can describe a past operation |
| operational_service.record_event | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-006 | Late occurrence may change current operational projection |
| operational_service.verify_milestone | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; occurrence contract | Whether post-closure verification may add authority to old facts |
| operational_service.correct_milestone | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; occurrence contract | Explicit correction exists, but closed-state permission is undefined |
| route_orchestration_service.checkpoint_command | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS | Late checkpoint report versus progression |
| route_orchestration_service.verify_checkpoint_milestone | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS | Post-closure verification meaning undefined |
| route_orchestration_service.correct_checkpoint_milestone | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS | Correction can alter derived route times |
| operational_execution_service.create_event | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS | Explicit late occurrence versus new operation |
| operational_execution_service.correct_event | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS | Existing append correction lacks closed boundary |
| operational_execution_service.verify_event | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS | Existing verification lacks closed boundary |
| reported_fact_service.create new report | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-063 | Late report accepted today; new terminal state not covered |
| reported_fact_service.create correction | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-063 | Append history mandatory; post-closure authorization undefined |
| delivery_service.create new Delivery | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-064 | Late evidence versus continuing physical delivery |
| delivery_service.create correction | DECISION_NEEDED | DECISION_NEEDED | P312-LATE-FACTS; ADR-064 | Can change delivered totals after decision |
| shipment_document_service.upload append | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-050/061 | May complete a preserved missing item after exceptional closure |
| shipment_document_service.upload replacement/retry | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-050/061 | New exact version changes readiness; old evidence stays |
| shipment_document_service.remove | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-050 | Changes current evidence state |
| document_context_service.revise | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-061 | Context and visibility change after terminal state |
| delivery_service.attach_evidence | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-064 | Adds exact historical evidence through authorized document command |
| document_readiness_service.materialize | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-030 | Adds the missing governed requirement snapshot |
| document_readiness_service.associate | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-030 | Changes current exact-version evidence use |
| document_readiness_service.assess | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-030 | Appends a new assessment after the closure decision |
| document_readiness_service.resolve_applicability | DECISION_NEEDED | DECISION_NEEDED | P312-DOCUMENTS; ADR-030 | Changes current requirement applicability |
| document_readiness_service.create_override | NO | YES | Original §42; ADR-068 | No further operational transition may consume an override |
| document_readiness_service.revoke_override | YES | NO | ADR-030; independent authority | Revokes an existing authorization, without reopening/altering history |
| operational_action_service.record_follow_up | YES | NO | Acceptance §7; ADR-054/068 | WorkItem lifecycle remains independent |
| operational_action_service.resolve_action | YES | NO | Acceptance §7; ADR-054/068 | Explicit resolution of independent work; never auto-resolved by close |
| operational_service.resolve_work_item | YES | NO | Acceptance §7; ADR-068 | Same independent work boundary |
| operational_execution_service.resolve_condition | YES | NO | Acceptance §7; ADR-068 | Independent Exception resolution; no Shipment reopening |
| route_orchestration_service.resolve_route_exception | YES | NO | Acceptance §7; ADR-068 | Independent Exception resolution |
| SLA evaluation and existing reconciliation | YES | NO | Acceptance §7; ADR-054/068 | Independent SLA/Attention truth; closed state must remain protected |
| policy/version configuration | YES | NO | Acceptance §7; ADR-068 | Organization configuration; old ClosureDecision retains its pin |
| DN10 grant/revoke and account disabling | YES | NO | ADR-062/065; original protected scope | Live authorization independent of Shipment lifecycle |
| authorized read/history/download | YES | NO | ADR-050/061/064/065/068 | Current authorization still applies; history never grants access |

## Proposed resolution for review, not an accepted policy

Allow the existing audited historical corrections and evidence repair commands
with their current roles and version checks, while retaining the original
ClosureDecision/missing-item snapshot and preserving the terminal closed state.
Ordinary new planning/execution stays denied. The Product Owner must separately
say whether a newly entered past occurrence/Delivery counts as permitted evidence
repair; no backdating shortcut or arbitrary pre-close timestamp is invented here.

Before integration this inventory must be completed against all certified child
write paths (including shared ExecutionUnits), verified with command-level tests,
and reconciled with the Product answer. This working review is not a blanket
middleware rule, a completeness claim or implementation evidence.

P3-12 BUILD=NOT_STARTED; QUALIFICATION=NOT_RUN; INTEGRATED=NO.
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING; HUMAN_WALKTHROUGH=NOT_RUN;
RELEASE_READY=NO; PRODUCTION_UNTOUCHED=YES.

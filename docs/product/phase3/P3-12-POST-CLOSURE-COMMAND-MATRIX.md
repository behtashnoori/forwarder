# P3-12 — accepted post-closure command matrix

Date: 2026-09-26. Product decision: «اصلاح سوابق و ثبت دیرهنگامِ واقعیت‌های قبلی و تکمیل/اصلاح اسناد مجاز باشد؛ عملیات جدید ممنوع.»
The pending review is retained at `7f98fca1f32a2c2afd51b0889e23893180b9852e`.
P312-LATE-FACTS and P312-DOCUMENTS are RESOLVED. Existing roles and audit history
remain; `closed` and its immutable ClosureDecision remain fixed.

Architecture acceptance: `6259830f2a5fe94798bf4183d2643bf624529c26`.
Actual canonical entry: `368cd736cbffce3d62c33336868738d9086e8306`, clean 0/0;
parent migration `20261009_phase3_route_time`. No P3-11 runtime was imported.
Managed creation failed against the older chat repository (operation
869ab8dd-5dc6-45cb-89b3-94dcc2785baf); the actual canonical Git repository created
`codex/phase3-p3-12-closure` through the documented native fallback.

## Enforcement meaning

All YES entries require current tenant, actor, owner/permission and exact parent
checks. They grant no new role. A prior fact must carry an operational instant no
later than ClosureDecision.occurred_at; recorded/audit time remains now. Historical
quantity corrections without an occurred field require the existing reason.
ACTUAL allocation has its existing occurred_at plus a reason. New planned
quantities, routes, executions, allocations and physical transfers remain denied.
Shared-unit commands examine every Shipment parent, including stage and legacy
allocation parents; new work affecting any closed parent is denied.

Commands are reviewed explicitly; no blanket write middleware. Pure lists/reads
never materialize closure. All historical records keep their original meanings.

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
| cargo_service.update_shipment_item actual quantity/correction | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| cargo_allocation_service.set_allocation PLANNED | NO | YES | Original §42; ADR-068 | Ordinary new planning |
| cargo_allocation_service.set_allocation ACTUAL correction | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| cargo_allocation_service.transfer | NO | YES | Original §42; ADR-068 | New physical reallocation/handoff |
| transport_execution_service.create | NO | YES | Original §42; ADR-068 | New execution context |
| transport_execution_service.revise | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| route_orchestration_service.record_traversal | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| operational_service.record_event | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| operational_service.verify_milestone | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| operational_service.correct_milestone | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| route_orchestration_service.checkpoint_command | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| route_orchestration_service.verify_checkpoint_milestone | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| route_orchestration_service.correct_checkpoint_milestone | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| operational_execution_service.create_event | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| operational_execution_service.correct_event | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| operational_execution_service.verify_event | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| reported_fact_service.create new report | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| reported_fact_service.create correction | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| delivery_service.create new Delivery | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| delivery_service.create correction | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| shipment_document_service.upload append | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| shipment_document_service.upload replacement/retry | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| shipment_document_service.remove | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| document_context_service.revise | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| delivery_service.attach_evidence | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| document_readiness_service.materialize | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| document_readiness_service.associate | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| document_readiness_service.assess | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| document_readiness_service.resolve_applicability | YES: prior fact / correction / document repair only | YES: new operation | Product answer 2026-09-26; existing authority | Live authorization and existing history; prior occurred time for facts; original closure decision unchanged |
| document_readiness_service.create_override | NO | YES | Original §42; ADR-068 | No further operational transition may consume an override |
| document_readiness_service.revoke_override | YES | NO | ADR-030; independent authority | Revokes an existing authorization, without reopening/altering history |
| operational_action_service.create_action | NO | YES | Product answer 2026-09-26; ADR-068 | Creates new operational follow-up; no prior-occurrence contract |
| operational_action_service.record_follow_up | YES | NO | Acceptance §7; ADR-054/068 | WorkItem lifecycle remains independent |
| operational_action_service.resolve_action | YES | NO | Acceptance §7; ADR-054/068 | Explicit resolution of independent work; never auto-resolved by close |
| operational_service.resolve_work_item | YES | NO | Acceptance §7; ADR-068 | Same independent work boundary |
| operational_execution_service.resolve_condition | YES | NO | Acceptance §7; ADR-068 | Independent Exception resolution; no Shipment reopening |
| route_orchestration_service.resolve_route_exception | YES | NO | Acceptance §7; ADR-068 | Independent Exception resolution |
| SLA evaluation and existing reconciliation | YES | NO | Acceptance §7; ADR-054/068 | Independent SLA/Attention truth; closed state must remain protected |
| policy/version configuration | YES | NO | Acceptance §7; ADR-068 | Organization configuration; old ClosureDecision retains its pin |
| DN10 grant/revoke and account disabling | YES | NO | ADR-062/065; original protected scope | Live authorization independent of Shipment lifecycle |
| authorized read/history/download | YES | NO | ADR-050/061/064/065/068 | Current authorization still applies; history never grants access |
| execution_unit_service.create_unit/create_shipment_unit | NO for closed parent | YES | Product answer; ADR-068 | A new vehicle/execution is new work; unrelated Project-only units are independent |
| execution_unit_service.update_unit; legacy transport metadata | NO for closed parent | YES | Product answer; ADR-018/059 | Use audited historical stage revision for prior facts; ordinary metadata update cannot begin new execution |
| execution_unit_service.add_event; multi_unit_tracking late update | YES: prior occurrence | YES: later occurrence | Product answer; existing permissions | Check every shared Shipment cutoff; append original audit |
| shared_transport_service.allocate/release/assign_carrier | NO affecting closed parent | YES | Product answer; ADR-068 | Ordinary legacy allocation/carrier commands are new operations |
| cargo_allocation_service.set_allocation | YES: ACTUAL prior occurrence with reason | YES: PLANNED | Product answer; ADR-060 | Version/idempotency/history retained |
| route_time_service.select_basis | NO | YES | Product answer; ADR-066 | Reference selection changes future planning; configuration remains independent |
| operational_execution_service.condition_collection | YES: prior delay/exception occurrence | YES: later occurrence | Product answer; ADR-006/068 | Resolution remains independent and explicit |
| economics create_line/append_observation/correct/quote_confirm | YES: prior effective fact | YES: later effective fact | Product answer; existing FE-2 permissions | Records observations, including pre-existing commitments; no source amount, FX or accounting semantics changed |
| external_reference_service.create/transition | YES | NO | Product answer; existing reference authority | Add/correct documentary identity evidence, not operational progression; history/revision/reason retained |
| legacy tracking enable/disable visibility | YES | NO | Existing visibility authority | Changes projection availability only; cannot create execution/facts |

## Serialization and scope

The close transaction locks organization configuration and Shipment, reauthorizes
after waits, rereads sources, compares policy/Shipment/fact identity and commits
one immutable decision with the terminal state. Each criterion source write has a
PostgreSQL Shipment fence, including absent inserts and exact document versions
through direct or associated Request ownership. Fences serialize; they do not
replace the command-specific policy above. Independent work and correction stay
possible after commit. ORM plus PostgreSQL guards deny reopening and decision
rewrites; delivery projections cannot auto-close or reopen.

The [exact-source qualification report](../../operational/evidence/phase3-p3-12-closure-status-20260926.md)
records the final Product and verified gates. This authority matrix is not itself
a qualification or controlled integration receipt. Rigor C / Astra capability; no runtime model-setting assertion.
DN05_GENERAL_CLOSURE_RULE=NOT_IMPLEMENTED; DN05_STATUS=OPEN_FOR_FUTURE_SPECIFIC_POLICY.
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING; HUMAN_WALKTHROUGH=NOT_RUN;
RELEASE_READY=NO; PRODUCTION_UNTOUCHED=YES. No P3-14/P3-15.

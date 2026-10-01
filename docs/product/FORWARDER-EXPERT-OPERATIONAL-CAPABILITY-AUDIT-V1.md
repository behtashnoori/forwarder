# Forwarder Expert Operational Capability Audit V1

Audit basis: current Product services and endpoints at Alembic head
`20261015_org_shipment_stages`. `YES (policy)` means the action is already
authorized by the assigned-work/owner policy rather than a separate baseline
string.

| Action | Service / endpoint family | Required capability or policy | Current baseline before reconciliation | Expected Expert baseline | Rationale / result |
| --- | --- | --- | --- | --- | --- |
| Work assigned Requests | Request detail, messaging, status services | Current assigned-Request Expert policy | YES (policy) | YES (policy) | Existing current-assignment and tenant guard is authoritative; no new grant. |
| Create/manage Quote and negotiation | Quote communication/commercial routes | Assigned Request + Expert commercial policy | YES (policy) | YES (policy) | Customer response and accepted-outcome lifecycle remain separate. |
| Create Shipment from accepted Quote | `operational_service.create_from_accepted_quote` | `operational_shipment.create_from_quote` | YES | YES | Existing capability retained; quote, tenant, acceptance, and idempotency guards remain. |
| Create authorized direct Shipment | `operational_service.create_direct` | `operational_shipment.create_direct` | YES | YES | Existing capability retained; tenant/customer/route guards remain. |
| Read/operate owned Shipment | Operational Shipment routes/services | `operational_shipment.read` / `operational_shipment.create` + owner policy | YES | YES | Existing capabilities retained; fixed responsible Expert remains authoritative. |
| Create/read/update transport execution units | Execution unit and transport execution services | `execution_unit.create/read/update` | YES | YES | Existing operational capabilities retained. |
| Create/read/manage execution project | Operational execution service | `operational_execution.read/manage` | NO | YES | Proven normal execution workspace gap; added with owner fence on manage. |
| Create/manage route plan and legs | Route orchestration service | `route_plan.create`, `route_leg.manage` | NO | YES | Normal owned-Shipment planning; added with owner, tenant, graph, version, and lifecycle guards. |
| Activate/replan route | Route orchestration service | `route_plan.activate/replan` | NO | YES | Normal freight execution; added without correction/verification authority. |
| Read route/timeline | Route orchestration reads | `operational_shipment.read` alias | YES | YES | No duplicate `route_plan.read` grant required. |
| Record route departure/arrival occurrence | `operational_service.record_event` | `milestone_event.create` | NO | YES | Confirmed walkthrough gap; added with current-owner lock/fence and immutable event rules. |
| Report checkpoint progress | `route_orchestration_service.checkpoint_command` | `checkpoint.report` | NO | YES | Normal execution reporting; added with current-owner fence and transition chronology. |
| Verify/correct route/checkpoint facts | Verification/correction commands | `milestone.verify/correct`, `checkpoint.verify` | NO | NO | Separation-of-duty/governance; explicitly excluded. |
| Cargo item management | Cargo service | `operational_shipment.create` + owner policy | YES | YES | Existing bounded capability covers ordinary Cargo facts. |
| Cargo allocation | Cargo allocation service | `operational_shipment.create` + owner policy | YES | YES | Existing bounded capability covers stage allocation; quantity/lineage rules remain. |
| Tracking reports and structured facts | Reported fact/tracking services | `operational_shipment.create`, `execution_unit.update` + owner policy | YES | YES | Existing capabilities retained; append-only correction lineage remains. |
| Structured route progress and ETA inputs | Progress/ETA services | `execution_unit.update`, `operational_shipment.create` + owner policy | YES | YES | Existing capabilities retained; pinned-basis and chronology rules remain. |
| Shipment Documents | Shipment document service | `operational_shipment.create` + owner policy | YES | YES | Existing capability retained; exact-version, audience, and replacement rules remain. |
| Read Document readiness/history | Document readiness and unified history | `document_readiness.read` | NO | YES | Required normal operational context; read-only grant added. |
| Record operational Stage progress | Shipment stage service | `operational_shipment.create` + owning Expert policy | YES | YES | Existing capability retained; pinned configuration and sequence rules remain. |
| Record Delivery and Final Delivery | Delivery service | `operational_shipment.create` + owner policy | YES | YES | Existing capability retained; quantity, destination, evidence, and finality guards remain. |
| Evaluate/complete/close normally | Closure service | Owning Expert policy under pinned Closure Policy | YES (policy) | YES (policy) | No broad close grant added; completed-only and blocker rules remain. |
| Read/manage operational actions | Operational action service | `work_item.read/manage` | NO | YES | Normal follow-up workload; added with current-owner fence on manage. |
| Resolve normal route exception | Route orchestration exception commands | `route_exception.manage` | NO | YES | Normal owned-Shipment exception handling; added with current-owner fence. |
| Create Organization Location during work | Expert logistics point command | Any bounded Shipment/route execution create capability | YES | YES | Existing special case retained: immediately usable `PENDING_REVIEW`; no admin grant. |
| Approve/enrich/deactivate Location | Admin logistics network commands | `logistics_point.manage` + Organization Admin authority | NO | NO | Configuration/governance remains with Organization Admin. |
| Trigger unified history/audit/outbox facts | All normal operational commands | Same command capability/policy | YES | YES | No separate grant; immutable/audited side effects remain service-owned. |
| Transfer Shipment owner | Owner transfer service | Organization Admin authority and governed transfer function | NO | NO | Separate workload/governance concern; Expert baseline remains excluded. |
| Configure Stage/Closure/Document policies | Admin policy services | Organization Admin authority/configuration capabilities | NO | NO | Admin configures. |
| Users/roles/membership/capability administration | User management/admin services | Organization Admin authority | NO | NO | Expert must never administer authorization. |
| Platform reference, repair, migration, maintenance | Platform/governed tooling | Explicit Platform/System Admin authority | NO | NO | Platform governs; no tenant operational inheritance. |

## Proven baseline gaps resolved

`checkpoint.report`, `document_readiness.read`, `milestone_event.create`,
`operational_execution.manage`, `operational_execution.read`,
`route_exception.manage`, `route_leg.manage`, `route_plan.activate`,
`route_plan.create`, `route_plan.replan`, `work_item.manage`, and
`work_item.read`.

The audit also found that several capability-only services previously lacked a
same-tenant owner fence. Owner checks were therefore added to route occurrence,
route mutation/exception resolution, operational execution management, and
operational action management. This is a safety prerequisite for adding those
capabilities to every Expert; it does not change read, verification, correction,
Organization Admin, or Platform Admin authority.

# Forwarder Expert Operational Baseline V1

Status: Product-owned, canonical role/capability boundary

Baseline identity: `EXPERT_BASELINE_OPERATIONAL_PERMISSIONS` / V1

Product rule: Admin configures. Expert operates. Customer decides. Platform governs.

## Canonical Expert baseline

The following explicit capabilities belong to every active canonical `expert`
membership. They enable commands; they never replace tenant, current owner,
lifecycle, append-only, document, closure, or route guards.

| Capability | Product purpose |
| --- | --- |
| `checkpoint.report` | Report checkpoint arrival, processing, or departure. |
| `document_readiness.read` | See readiness evidence needed to operate the Shipment. |
| `execution_unit.create` | Create authorized transport execution units. |
| `execution_unit.read` | Read authorized transport execution units. |
| `execution_unit.update` | Record normal execution and tracking facts. |
| `milestone_event.create` | Record route departure, movement, and arrival occurrences. |
| `operational_execution.manage` | Manage the owned Shipment's normal execution state, conditions, and milestones. |
| `operational_execution.read` | Read the owned Shipment's execution projection and history. |
| `operational_shipment.create` | Manage ordinary facts on an authorized owned Shipment. |
| `operational_shipment.create_direct` | Create a directly authorized Shipment. |
| `operational_shipment.create_from_quote` | Create a Shipment from an accepted authorized Quote. |
| `operational_shipment.read` | Read assigned/owned Shipment work. |
| `personal_dashboard.manage` | Manage the Expert's private operational dashboard. |
| `personal_dashboard.read` | Read the Expert's private operational dashboard. |
| `route_exception.manage` | Resolve normal route exceptions on the owned Shipment. |
| `route_leg.manage` | Manage planned route legs on the owned Shipment. |
| `route_plan.activate` | Activate an authorized route plan for the owned Shipment. |
| `route_plan.create` | Create a route plan for the owned Shipment. |
| `route_plan.replan` | Replan the owned Shipment under route rules. |
| `work_item.manage` | Create/resolve normal operational actions on the owned Shipment. |
| `work_item.read` | Read normal operational actions on authorized Shipment work. |

`route_plan.read`, route timeline reads, and normal Shipment-detail route reads
are intentionally authorized through `operational_shipment.read`; a duplicate
baseline grant is not required. Request/Quote work remains governed by the
current assigned-Request policy and commercial lifecycle, so no unproven new
Request or Quote capability was added.

## Explicit exclusions

The Expert baseline does not include verification/correction separation-of-duty
capabilities (`milestone.verify`, `milestone.correct`, `checkpoint.verify`,
`operational_event.verify`, `operational_event.correct`), reason/policy
configuration, user/role/capability administration, Shipment owner transfer,
Organization Stage/Closure/Document Policy configuration, governed Location
approval/deactivation, platform reference governance, maintenance, repair,
backfill, migration, secrets, integration administration, or cross-tenant access.

`OWNER_TRANSFER_EXPERT_BASELINE=EXCLUDED`. Owner transfer remains the narrow,
qualified Organization Admin command defined by ADR-069.

## Organization Location special case

An Expert may create a tenant-owned Location while performing operational work
through the bounded Expert location command. It is immediately usable and is
created with `PENDING_REVIEW`. Organization Admin retains approval, enrichment,
duplicate review, and future deactivation. Current operational continuity does
not wait for approval. The Expert does not receive `logistics_point.manage`.

## Role/capability matrix

| Significant Product capability | Class | Expert | Organization Admin | Platform/System Admin | Customer |
| --- | --- | --- | --- | --- | --- |
| Assigned Request work and Quote negotiation | OPERATIONAL | Performs assigned work | Supervises/configures assignment | No implicit tenant work | Reviews/responds to own Quote |
| Shipment creation from accepted outcome/direct authority | OPERATIONAL | Creates when authorized | No implicit owner operation | No implicit tenant work | No |
| Owned Shipment operation | OPERATIONAL | Primary operator | Read/supervision only unless separately authorized | No implicit tenant work | No |
| Route plan, legs, activation, replan | OPERATIONAL | Owned Shipment only | Configuration/supervision boundary | No implicit tenant work | No |
| Transport execution, allocation, tracking, progress, ETA inputs | OPERATIONAL | Owned Shipment only | No implicit operational write | No implicit tenant work | No |
| Route/checkpoint occurrence reporting | OPERATIONAL | Reports owned work | Verification is separate | No | No |
| Verification and historical correction | GOVERNANCE | Excluded from baseline | Authorized separation-of-duty operation where configured | Privileged repair only through governed maintenance | No |
| Shipment documents and readiness | OPERATIONAL | Manages owned operational evidence; reads readiness | Configures document policy/catalog activation | Governs system document catalog | Reads own shared evidence only |
| Organization Location creation during work | OPERATIONAL | Creates `PENDING_REVIEW`, immediately usable | Reviews/approves/enriches/deactivates | Governs global location/reference data | No |
| Organization Location policy and review | CONFIGURATION | No | Owns | Platform governs global sources only | No |
| Operational Stage progress | OPERATIONAL | Records owned Shipment progress | Configures Stage definitions | No implicit tenant work | Reads eligible progress |
| Delivery and explicit Final Delivery | OPERATIONAL | Records under lifecycle/quantity/evidence rules | Configures policy only | No implicit tenant work | Reads own delivery facts |
| Normal completion and closure | OPERATIONAL | Assesses/completes/closes owned Shipment under pinned policy | Configures Closure Policy; exceptional authority remains separate | No implicit tenant work | No |
| Operational issue/action resolution | OPERATIONAL | Manages owned Shipment issues/actions | Configures governing reason/policy catalogs | No implicit tenant work | No |
| Owner transfer/reassignment | GOVERNANCE | Excluded | Owns narrow audited transfer | No implicit tenant transfer | No |
| Users, roles, memberships, grants | CONFIGURATION | No | Owns within tenant boundary | Owns platform-level administration | No |
| Organization policies and reference activation | CONFIGURATION | No | Owns | Governs platform reference sources | No |
| Platform maintenance, repair, migration, backfill | GOVERNANCE | No | No | Owns through explicit governed tools | No |
| Customer Quote response and customer-owned choices | CUSTOMER_ACTION | No | No | No | Owns within authenticated entitlement |

## Reconciliation contract

The existing `reconcile-expert-baseline` command is the only runtime convergence
path for this baseline. It is additive, deterministic, dry-run first, applies
only to active canonical Expert memberships, preserves explicit extra grants,
does not rewrite role/authority/organization/ownership, and is idempotent.
Direct membership JSON edits and raw SQL grants are prohibited.

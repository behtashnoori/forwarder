# Unified shipment history read contract

`GET /api/v2/operational-shipments/{public_id}/history?page=1&per_page=25` is the single shipment history endpoint. It first resolves the shipment through the existing tenant, assignment, direct-responsibility, and project scope. It then composes persisted source rows on the server. No history table or event is created by reading it.

| Source | Persisted table and shipment link | Business time / recorded time | Actor and lineage | Current domain surface |
| --- | --- | --- | --- | --- |
| Shipment | `operational_shipment`, self | — / `created_at` | `created_by_user_id`; direct or request source | Shipment Detail |
| Route revisions | `route_plan`, `operational_shipment_id` | — / `created_at` | `created_by_user_id`; `created_from_plan_id`, revision | Route plan and replan panels |
| Route activation | `operational_audit`, scoped RoutePlan entity | — / `recorded_at` | `actor_user_id`, plan revision | Route plan panel |
| Occurrence, verification, correction, execution stages | `milestone_event` through `operational_milestone.operational_shipment_id` | `occurred_at` / `recorded_at` | `actor_user_id`; `related_event_id`, `supersedes_event_id`, source milestone and route revision | Route and execution panels |
| Delay | `operational_delay`, `operational_shipment_id` | `started_at` or `resolved_at` / `created_at` or resolution audit | Create/resolve actor; governed `reason_id` | Operational Delay panel |
| Exception | `operational_exception`, `operational_shipment_id` | `occurred_at` or `resolved_at` / `created_at` or resolution audit | Create/resolve actor; governed `reason_id` | Operational Exception panel |
| Work item lifecycle | `operational_audit` scoped to `operational_work_item.operational_shipment_id` | — / `recorded_at` | `actor_user_id`; only meaningful open/reopen/resolve actions | Work queue |
| External reference lifecycle | `operational_audit` scoped to `operational_shipment_external_reference.operational_shipment_id` | — / `recorded_at` | `actor_user_id`; governed type and predecessor reference | External references |
| Document readiness | `document_readiness_audit`, `operational_shipment_id` | — / `created_at` | `actor_user_id`; requirement link where present | Document readiness panel, project/request shipments only |
| Other scoped operational actions | `operational_audit`, typed shipment/route/milestone links | — / `recorded_at` | `actor_user_id`; typed entity link | Existing domain panels |

The feed sorts descending by authoritative business occurrence time when a source has one. An audit-only action uses its recorded time. Kind, phase, and persisted ID break ties. The server applies `LIMIT` and `OFFSET` to a composed source-ID feed before hydrating items; `per_page` is restricted to 1–100. A category filter in the UI applies only to the current bounded page.

Document-readiness rows appear only for non-direct shipments when a supplied actor has `document_readiness.read` authorization on that shipment. An internal call without an actor excludes them. The endpoint never broadens the authorization of its constituent sources. History rows are read-only; corrections, verification, and resolution remain on their existing command surfaces. Unknown action codes receive a safe presentation fallback rather than a raw internal code.

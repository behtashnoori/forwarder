# Phase 1A permission matrix

| Permission | Capability |
|---|---|
| `operational_shipment.read` | list/detail |
| `operational_shipment.create` | create from accepted quote |
| `milestone_event.create` | report |
| `milestone.verify` | verify (not own report) |
| `milestone.correct` | append correction |
| `work_item.read` | queue |
| `work_item.manage` | resolve |

Backend enforcement is authoritative; UI hiding is only UX. Roles grant nothing implicitly. Membership and organization must both be active. Cross-organization IDs are hidden. UAT provisioning is explicit, confirmed, local-only, and never runs at import/startup.

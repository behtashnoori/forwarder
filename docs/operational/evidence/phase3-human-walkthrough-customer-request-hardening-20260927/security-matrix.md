# Customer Request hardening security matrix

| Boundary | Result | Proof |
| --- | --- | --- |
| Current Request assignee, not Shipment owner | PASS | service and API tests use `ShipmentRequest.assigned_to`; P313/IPJ01 preserve Shipment-owner semantics |
| Safe assignee projection only | PASS | exact `{display_name}` projection; negative checks for IDs, memberships, roles, email, phone, username, notes, rules and SLA |
| Unassigned truth | PASS | no optimistic assignment; pending copy derives from committed response/detail |
| Reassignment truth | PASS | private detail returns the new current display name |
| Customer A cannot read Customer B Request | PASS | private detail authorization regression |
| Guessed Request ID / count-list leakage | PASS | Customer and tenant negative regressions |
| Inactive/revoked Customer session | PASS | account/session regression suite |
| Authenticated Customer linkage | PASS | server session owns Customer and tenant relationship; spoofed frontend Customer ID ignored |
| Anonymous Request preserved | PASS | anonymous create remains valid and excludes assignee/workspace internals |
| Public Tracking minimized | PASS | MT3 and PostgreSQL public-tracking regressions; assignee remains absent |
| Hostname tenant isolation | PASS | Customer host-policy and cross-tenant regressions |
| Quote/history unchanged | PASS | existing and new private-detail tests plus integrated browser journeys |
| Secret/credential hygiene | PASS | current-tree scanner zero findings; per-run credentials only |

No broader internal Expert DTO is reused. No assignment history is exposed.
No Request assignee/Operational Shipment owner concepts were collapsed.

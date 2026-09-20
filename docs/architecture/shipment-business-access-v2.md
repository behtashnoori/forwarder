# Shipment Business Access v2

Target ownership is governed by [ADR-047](../operational/adr/ADR-047-fixed-operational-shipment-responsible-expert.md): each Operational Shipment has one fixed responsible Transport Expert and no Shipment reassignment workflow. This file records the implemented/read-scope compatibility state; it does not make Project access or same-organization membership Shipment ownership. Any non-owner Project-derived visibility remains a separately explicit access grant and must not mutate or replace the responsible Expert.

For a normal Expert, the Shipment read population is the union of direct or
request-root assignment and Shipments whose current `project_id` is within the
user's explicit Project access scope. Organization Admins retain tenant-wide
visibility with the existing read permission; Platform Admins receive no
implicit tenant-work visibility.

Project access is not Shipment assignment: it never modifies responsibility
fields and does not add action permissions. Project-derived visibility is
evaluated from current `ProjectAccess` and `Shipment.project_id`, so grants,
revocations, new Shipments, and Project changes take effect immediately.
Dashboard and Saved View definitions do not grant data access; they execute
inside this canonical scope.

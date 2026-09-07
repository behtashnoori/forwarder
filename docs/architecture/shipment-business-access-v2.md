# Shipment Business Access v2

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

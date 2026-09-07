# Project Access Foundation v1

Project tenancy comes from one active organization membership. Normal Experts see
only Projects with an explicit `ProjectAccess` assignment; Organization Admins
see all Projects in their organization, and Platform Admins receive no implicit
tenant-work authority. Action permissions remain separate from record scope.

Only an Organization Admin with `project_configuration.manage` may add, list, or
physically revoke assignments. The service derives tenant and actor from the
authenticated context, accepts a stable unique username for the target user, and
never accepts an organization or acting-user identifier from the client.

Project access does not grant Shipment access in v1. Shipment detail and Semantic
Analytics continue to use `assigned_shipment_scope`; Project filters only narrow
that authorized Shipment population. Permission is not Project business access,
and Project access is not Shipment access until the propagation capability.

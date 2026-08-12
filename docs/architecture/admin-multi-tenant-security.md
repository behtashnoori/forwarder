# Admin multi-tenant security

The shared application URL remains `server.logisticmarket.ir`; organization context is derived only from the authenticated user's single active membership. `PLATFORM_ADMIN` controls global website, upload, policy, and reference writes. `ORGANIZATION_ADMIN` controls tenant-owned users, requests, reports, and assignment/referral policy. `EXPERT` has no administrative surface.

Legacy `role=admin` is never platform authority. The migration promotes it to organization authority only when exactly one active membership exists; all ambiguous identities remain `EXPERT` and fail closed. Tenant IDs supplied by clients are ignored. Organization storefronts and organization-creation UI are non-goals.

# Organization Document Policy

## Ownership hierarchy

Document policy has four explicit layers:

1. `DocumentDefinition` is the platform-global document vocabulary. Only `PLATFORM_ADMIN` may create, edit, activate, or deactivate it.
2. `OrganizationDocumentRequirement` is owned directly by one `OperationalOrganization` through the repository-standard `organization_id` key (also exposed as `operational_organization_id` in the ORM). An `ORGANIZATION_ADMIN` may manage only the policy derived from their single active membership.
3. `ProjectDocumentRequirement` is an organization-owned project override. It may replace the organization requirement level and add milestone/assessment bindings.
4. `CaseDocumentRequirement` and `OperationalDocumentRequirement` are immutable tenant-owned runtime snapshots.

An organization policy never changes a global definition. Client-supplied organization identifiers are rejected; organization identity is always derived on the server.

## Requirement levels and precedence

Organization policies use `REQUIRED`, `OPTIONAL`, `CONDITIONAL`, and `DISABLED`. Project overrides retain the existing `REQUIRED`, `OPTIONAL`, and `CONDITIONAL` values.

Effective precedence is deterministic:

```text
active project override
  > active explicit organization policy
  > compatibility platform default
```

`DISABLED` and inactive organization policies exclude the definition. An active project override may explicitly re-enable a globally active definition for its own project.

## Compatibility and activation

An organization with **zero** organization-policy rows remains in `COMPATIBILITY_FALLBACK` mode. New snapshots use active global definitions and translate `DocumentDefinition.is_required` to `REQUIRED` or `OPTIONAL`, preserving pre-release behavior.

Creating the first policy row switches that organization to `EXPLICIT` mode. In explicit mode, a global definition with no organization policy is excluded. This prevents newly added platform vocabulary from silently becoming required for every tenant.

No migration fabricates organizations, policies, or document definitions, and no global data is backfilled. Existing runtime snapshots are never rewritten. Policy edits affect only later snapshot creation.

## APIs and administration

- Global vocabulary: `/api/admin/document-definitions`; mutation remains platform-only.
- Organization policy: `GET /api/admin/organization-document-policy` and `PUT /api/admin/organization-document-policy/<document-definition-public-id>`; organization-admin only and membership-derived.
- Project override: existing `/api/v2/projects/<project-id>/configuration/document-requirements` APIs and permissions.

The Admin Panel displays `مدیریت مستندات` only to platform administrators and `الزامات مستندات سازمان` only to organization administrators.

Platform administrators do not implicitly acquire an organization context. Organization-policy inspection therefore fails closed unless a future, explicit tenant-selection administration design is introduced.

## Onboarding

A new organization initially receives compatibility behavior. Onboarding should review the global vocabulary and save a complete explicit organization policy in one controlled session. From the first saved row onward, omitted definitions are intentionally disabled, so partial onboarding must be treated as partial configuration rather than an implicit platform default.

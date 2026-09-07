# Personal Saved View Foundation v1

## Boundary

`SavedView` is a private, tenant- and owner-scoped configuration artifact. It reuses the governed `SemanticQueryDefinition` vocabulary but has an independent `saved-view-definition-v1` artifact schema. It is not a Dashboard, widget, Report, SQL statement, export, or result snapshot. The legacy `Report` model is deliberately not reused because its ownership is classified `LEGACY_AMBIGUOUS` and its semantics combine report concerns outside this capability.

## First surface

The first eligible surface is `/operations/shipments`. Its operational shipment rows are directly tenant-owned, expose public identities, and already have a stable bounded list endpoint and responsive RTL presentation. The v1 adapter persists only governed filters that this surface can reproduce safely: shipment status and created-time range. Free-text customer/origin/destination and overdue inputs enter an explicit incompatible state rather than being persisted as raw database fields or silently dropped.

React Query owns Saved View server state. The operational page continues to own its transient filters and pagination. Applying a compatible view replaces those local filters and invokes the existing list path; no client KPI or population calculation is introduced.

## Persistence and concurrency

The relational `saved_view` row owns identity, organization, user, lifecycle, name, description, schema versions, and optimistic version. Validated deterministic JSON owns query and presentation configuration. `saved_view_revision` is append-only in normal service flow: creation writes revision 1 and every meaningful definition/metadata patch appends exactly one revision. Invalid, no-op, and stale patches append none. Archive and restore retain definition history.

Authorization derives organization and owner from the authenticated membership and scopes every lookup by organization, owner, and opaque public ID. The existing `operational_shipment.read` capability is reused; no parallel RBAC system is added. Missing, cross-user, and cross-tenant IDs share the same not-found response.

## Non-goals

Organization ownership, sharing, favorites, defaults, folders, tags, Saved View to widget/report conversion, scheduling, AI, SQL, formulas, charts, and a dedicated management page remain absent.

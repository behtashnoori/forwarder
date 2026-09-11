# ADR-046: Tenant-owned shared transport execution

**Status:** ACCEPTED  
**Supersedes:** the one-Project / one-OperationalShipment ownership invariant in ADR-018.  
**Date:** 2026-09-08

## Decision

`ExecutionUnit` remains the single canonical representation of a physical
transport execution.  It is owned by `OperationalOrganization`, not by a
Project or one OperationalShipment.  A Project and an OperationalShipment
participate through explicit `ExecutionUnitCargoAllocation` facts:

`ExecutionUnit <- ExecutionUnitCargoAllocation -> ShipmentCargoItem -> OperationalShipment -> Project`.

This permits a single vehicle/trip to carry cargo from multiple shipments,
projects, and customers in one tenant.  No `SharedTransport` or `Groupage`
aggregate is introduced.  Groupage is a read-model classification derived from
known cargo owners on allocations.

## Canonical and compatibility data

| Structure | Status | Meaning |
| --- | --- | --- |
| `ExecutionUnit.organization_id` | CANONICAL | tenant ownership of the physical execution |
| `ExecutionUnitCargoAllocation` | CANONICAL | cargo, shipment, project, and execution participation fact |
| `ShipmentCargoItem.cargo_owner_customer_id` | CANONICAL for new shared flows | tenant Customer owning a cargo line; historical NULL means unknown |
| `ExecutionUnit.carrier_customer_id` | CANONICAL | one optional actual carrier per execution, represented by the existing tenant-scoped CRM `Customer`/vendor master |
| `ExecutionUnit.project_id`, `operational_shipment_id` | COMPATIBILITY_ONLY | legacy one-project/one-shipment lineage; never canonical for new flows |
| `ShipmentTransportUnit`, `ShipmentCargoTransportAllocation` | DEPRECATED_BUT_RETAINED | legacy tracking/allocation history and existing API compatibility |

Each cargo retains its own quantity and UOM.  Raw quantities with differing
UOMs are never summed and no conversion is invented.

### Tracking precedence boundary

Tracking is a read projection and does not create cargo-to-vehicle facts.  If
an `ExecutionUnitCargoAllocation` exists for a cargo line, Tracking renders
that execution, its carrier, vehicle context, and allocated quantity.  A
coexisting `ShipmentCargoTransportAllocation` is hidden for that cargo line.
For historical cargo with no canonical allocation, the legacy representation
remains readable through the compatibility projection.  This boundary retains
history without allowing two representations to disagree about current shared
execution truth.

## Migration and authorization

The additive migration derives `ExecutionUnit.organization_id` only from the
existing linked Project.  It preserves legacy relationships and allocations.
It does not infer cargo ownership, leaving historical values NULL where no
explicit fact exists.

Commands must fail closed unless the actor has active, unambiguous tenant
membership and access to the execution, every cargo, shipment, project, and
cargo-owner Customer involved.  A PLATFORM_ADMIN does not gain tenant
operational access merely by that role.  Cross-tenant Customer/execution
assignments are rejected.

## Cargo-owner product contract

The existing operational Customer selector is the sole owner selector.  It is
tenant-scoped and returns active Customers only.  When a new cargo line is
created, its owner defaults to the owning Customer of the operational shipment
unless the user explicitly selects another active Customer in that tenant.
The selection is persisted and can be changed through the cargo-line edit
surface subject to the normal cargo edit permission and optimistic version
rule.  Historical NULL is deliberately rendered as **Unknown / Not specified**
and is never inferred or overwritten during read, migration, or allocation.

Qualification evidence is maintained by the focused cargo, selector, shared
transport, and UI contract tests.  A real PostgreSQL migration and authenticated
browser qualification remain required release gates; they must use a disposable
local database and deterministic fixtures, never production data.

## Accepted follow-on requirements (not implemented here)

Document control will model requirement/applicability, a document's actual
existence/status and issue date, and a separate optional file attachment.  An
uploaded file is not evidence that a document exists, and an existing document
need not have an uploaded binary.  Barfarabaran will be an external operational
reference (`BARFARABARAN_CODE`), with value plus separately modelled issued and
received dates; their business meanings must be confirmed before UI work.

After this Slice is frozen, a Product Reality acceptance audit must cover the
material actor, responsibility, authority, and scope combinations; navigation,
entitlement, route, and live-authorization consistency; Persian/English RTL
and mixed-script quality; technical-language leakage; the distinction between
zero, no-data, partial, unauthorized, and error states; and dashboard
storytelling/explainability.  It must also trace the operational cargo journey
from Catalog Item through Shipment Cargo, ExecutionUnitCargoAllocation,
ExecutionUnit, vehicle/carrier, and tracking events/milestones.  Tracking
must not establish a second vehicle or allocation source of truth.

`PROJECT_REPORT_AND_EXPORT_PRODUCT_ACCEPTANCE` is an accepted follow-on
acceptance capability, not a simple export endpoint and not implementation
authority for this Slice. Its future scope is a project cover, executive
summary, detailed narrative, operational summary, cargo/transport/party and
reference information, and a project document register (name, type, status,
issued/received date as applicable, uploader, and file/link/preview). It must
make a separate design decision about whether uploaded files are embedded in a
rendered artifact or only registered. DOCX and PDF acceptance must include
real rendered-artifact inspection for Persian RTL, mixed Persian/Latin text
and numbers, appropriate fonts and sizing, page breaks, tables, provenance,
and completeness. A generated file alone is not PASS. A later architecture
decision may generalize this gate for all document/report artifacts; generic
LPAF remains unchanged here.

## Consequences

ADR-018 remains authoritative for event history, versioning, lifecycle, and
legacy bridge principles.  Its Project ownership, single shipment ownership,
and project-local code invariants are superseded by this ADR.  Operational
events may retain a nullable legacy Project reference; execution ownership is
always tenant-scoped.

# MT-1 Tenant Data Integrity Review

**Status:** BLOCKED — no schema migration is safe without an explicit legacy
ownership mapping or quarantine/write-policy decision.

**Reviewed baseline:** `e1b5e12bbc8d9077f14da01a287a68a764b78a7c`  
**Release preserved:** `v1.9.1` at `05414d7d5b17153c3f1efcb5beff0adf7a600af6`  
**Alembic head reviewed:** `20260819_v191_acceptance_corrections`

## Decision

MT-1 cannot close from repository evidence alone. The two required ownership
roots, `ShipmentRequest` and `Customer`, both admit rows for which no
authoritative organization exists. They also admit conflicting organization
candidates. Applying `NOT NULL`, selecting a default organization, choosing one
candidate over another, or deriving ownership from user/contact text would be
speculative and is prohibited by the architecture contract.

No migration was created. This is the fail-closed outcome: the repository and
published release remain unchanged while the missing ownership adjudication is
made explicit.

## Lineage and proposed classifications

The following results use only FK-backed repository relationships. “Direct
after adjudication” means the model needs a canonical organization key, but its
existing rows are not universally backfillable.

| Entities | Proven result | Target |
|---|---|---|
| `ShipmentRequest` | Project, scoped quotes, and operational shipments are candidate sources; candidates may be absent or disagree | Direct after adjudication |
| `ExpertQuote` | Existing organization key is nullable and may disagree with its request | Direct after request remediation |
| `Customer` | Project/request/operational references may be absent or span organizations | Direct after adjudication (P0) |
| `AssignmentRule`, `ReferralRule`, `ReferralAutoAssignState`, `Report` | No authoritative organization relationship exists | Direct after manual mapping or explicit quarantine |
| `Activity`, `Task` | Business parents are nullable and may be absent or disagree | Direct after adjudication |
| `CustomerGamification` | No FK-backed ownership parent exists; text identity is not evidence | Direct only after an explicit tenant association/mapping decision |
| `DocumentAuditEvent` | Every ownership-bearing resource link is nullable; platform and tenant event semantics are mixed | Remain ambiguous until semantics are split or enveloped |
| `ReferralRuleState` | Required rule parent | Indirect after rule remediation |
| `CustomerContact`, `Opportunity` | Required customer parent | Indirect after customer remediation |
| `CustomerWorkflowStep` | Required request and gamification parents must agree | Indirect after root remediation |
| `ShipmentTracking`, `ShipmentTransportUnit`, `ShipmentTransportUnitUpdate`, `ShipmentRequestLog` | Mandatory chain terminates at request | Indirect after request remediation |
| `ExpertConsoleLog`, `ExpertConsoleMessage`, `ExpertConsoleNotification` | Required request parent; global user is not ownership evidence | Indirect after request remediation |
| `CRMCustomerLinkAudit`, `AssignmentLog`, `ReferralAssignmentLog` | Required request parent; other populated tenant parents must agree | Indirect after root remediation |
| `CaseDocumentRequirement`, `CaseDocumentFile` | Required request parent; a file's optional requirement must reference the same request | Indirect after request remediation |
| `project_party_relationship` | Project is authoritative; customer must match its organization | Indirect after customer remediation |

None of the 28 ambiguous entities is proven platform-scoped. The inventory
therefore remains at 34 direct, 14 indirect, 27 platform, 1 public capability,
and 28 legacy ambiguous entries.

## Safe migration design once the blocker is resolved

1. Add nullable canonical keys to direct ownership roots and a durable,
   queryable quarantine/adjudication record only if the architecture contract
   is amended to permit a staged nullable state. Do not use a default tenant.
2. Collect every FK-backed organization candidate. Resolve a row only when the
   candidate set has exactly one distinct organization; quarantine zero- and
   multi-candidate rows without deleting or assigning them.
3. Under the current non-null closure contract, require an approved explicit
   mapping for every quarantined row. Re-run the conflict checks and fail the
   migration if any row remains unresolved. If the contract instead adopts a
   staged quarantine, do not claim those nullable roots as direct ownership.
4. Add `NOT NULL`, organization FKs, and `(id, organization_id)` unique keys.
5. Add composite FKs enforcing the accepted-quote lineage:
   `Customer = ShipmentRequest = ExpertQuote = OperationalShipment`.
6. Add composite enforcement for Project/Customer and project-party/customer,
   plus request/project and document-file/request/requirement equivalence.
7. Reclassify mandatory descendants as indirect only after their root is
   non-null and ownership-changing reparenting is mechanically constrained.

PostgreSQL validation must cover fresh install, v1.9.1 upgrade, convergent
backfill, zero-candidate and conflicting-candidate failure/quarantine,
cross-tenant rejection, same-tenant acceptance, downgrade/re-upgrade, and
populated downgrade safety. A populated downgrade must fail before dropping
tenant keys when doing so would lose adjudicated ownership.

## Required decision/evidence to unblock

- An authoritative mapping for legacy root rows that have no FK-backed tenant.
- An adjudication for every conflicting Customer or ShipmentRequest candidate.
- A future-write rule for public intake before MT-3 supplies tenant-aware
  capability resolution (for example, explicit quarantine versus rejecting the
  write). MT-1 cannot silently attribute the current public intake.
- A decision to split platform document-definition audit events from tenant
  document events, or to give all operational audit events an explicit tenant
  envelope.
- Per-organization semantics and mappings for assignment/referral/report data.

## Dependencies and preserved defects

MT-2 remains responsible for central immutable request tenant context and
request/service scoping. MT-3 remains responsible for public tracking and
tenant-aware public intake/capability design. The existing public tracking
classification remains `PUBLIC_CAPABILITY_SCOPED + TENANT_ISOLATION_DEFECT`;
numeric/global lookup was not changed or concealed.

## Review outcome

**MT-1 MIGRATION DESIGN — BLOCK.** A migration that claims closure without the
evidence above would violate the no-speculation and fail-closed requirements.
Because implementation did not pass this gate, PostgreSQL acceptance and an
independent final PASS are not claimable.

# MT-1A Legacy Tenant Ownership Resolution and Quarantine Contract

**Status:** contract and dry-run analyzer implemented; closure remains blocked on
approved legacy decisions and a disposable PostgreSQL run. This document does
not authorize the MT-1 schema migration.

**Baseline HEAD:** `e1b5e12bbc8d9077f14da01a287a68a764b78a7c`  
**Release tag object:** `900193c325b8386b4c34ad36e626b559a999e6d5`  
**Peeled v1.9.1 commit:** `05414d7d5b17153c3f1efcb5beff0adf7a600af6`  
**Tag integrity:** PASS

## Non-negotiable ownership rules

Ownership evidence is limited to a non-null authoritative organization FK, an
immutable FK-backed authoritative parent, or an explicit reviewed mapping.
Names, company names, email domains, usernames, creator/assignee identity,
majority/first organization, current session organization, and default tenants
are never evidence. Public capability access is not ownership evidence.

There is no precedence list. Resolution is a monotone candidate-set fixpoint:

1. Seed `Project.organization_id`, `OperationalShipment.organization_id`, and
   non-null `ExpertQuote.operational_organization_id`.
2. Propagate seeds over the declared FK edges below until no candidate set grows.
   A mapping is another reviewed seed, not an override.
3. One distinct organization is `DETERMINISTIC`; more than one is `CONFLICT`;
   none is `UNRESOLVED` and requires mapping or permitted quarantine. A missing
   referenced row is `INVALID_LINEAGE`, irrespective of candidate count.
4. A mapping disagreeing with mechanical evidence is `CONFLICT`. It must never
   erase or outrank evidence.

Only after this fixpoint may descendants inherit an owner. This avoids circular
proof such as deriving a request from a customer whose only evidence came from
that same request.

## Actual root graph

The schema is not a mandatory linear Customer-to-shipment chain:

```text
OperationalOrganization
  |-- Project --------------------> Customer (primary and party edges)
  |      `------------------------> ShipmentRequest
  |-- ExpertQuote ----------------> ShipmentRequest
  `-- OperationalShipment --------> Project? / Customer? / ShipmentRequest? / accepted ExpertQuote?
```

`Project` and `OperationalShipment` are already direct and authoritative.
`ShipmentRequest` has nullable Project and Customer links. `ExpertQuote` has a
required Request but nullable organization. OperationalShipment enforces the
Project/organization pair, but not same-tenant Customer/Request/Quote links.

### Root candidate paths

| Root | Candidate organization paths | Result rule |
|---|---|---|
| Project | its non-null `organization_id` | Always direct; disagreeing customer/child is conflict |
| OperationalShipment | its non-null `organization_id` | Always direct; every linked root must agree |
| ShipmentRequest | Project; all scoped Quotes; all OperationalShipments; independently resolved Customer | cardinality rule; no preferred path |
| ExpertQuote | its nullable direct key; resolved Request; accepting OperationalShipment | cardinality rule; accepted state does not break ties |
| Customer | primary/party Projects; independently resolved Requests; direct or accepted-quote OperationalShipments | cardinality rule; textual identity is prohibited |

Customer reuse across organizations is a conflict, not a shared Customer.
CustomerGamification and CRM Customer are separate concepts and may not be
merged by email/phone. CRM relink audits, creators, experts, assignments, and
referrers are consistency/audit evidence only, never tenant authority.

## Descendant propagation

After parent ownership is proven and dangling FKs are rejected, these 12 can be
indirect through a required parent: CustomerContact, Opportunity,
ReferralRuleState, ShipmentTracking, ShipmentTransportUnit,
ShipmentTransportUnitUpdate, ShipmentRequestLog, ExpertConsoleLog,
ExpertConsoleMessage, ExpertConsoleNotification, CaseDocumentRequirement, and
CaseDocumentFile.

These eight are conditional: Activity, Task, CustomerWorkflowStep,
CRMCustomerLinkAudit, AssignmentLog, ReferralAssignmentLog,
DocumentAuditEvent, and `project_party_relationship`. Every populated
ownership-bearing path must resolve and agree. All-null owner paths remain
unresolved. Platform DocumentDefinition is not an owner.

Eight are primary roots or direct-decision entities: ShipmentRequest, ExpertQuote,
Customer, AssignmentRule, ReferralRule, Report, CustomerGamification, and
ReferralAutoAssignState. The last is a global singleton with no ownership FK;
it requires a tenant-specific redesign/split or quarantine, not a guessed map.
MT-1B permits reviewed decisions for integer-key ambiguous descendants whose
optional owner paths are all null; the composite association remains lineage-only.

## Reviewed human mapping contract

The versioned JSON format is
`docs/architecture/legacy-tenant-mapping.schema.json`. Stable integer IDs, not
names, identify both entity and Organization. Every entry includes reason,
operator, distinct reviewer, review status, stable decision ID and decision
timestamp. The analyzer additionally validates that row and Organization exist,
rejects duplicate decision IDs/versions, and rejects a decision that conflicts
with FK-backed evidence. Only the effective `ACTIVE` chain tip is applied.

Mappings are append-review inputs under normal change control. A correction
must be a new, explicitly reviewed decision and must not silently overwrite a
previous decision. The eventual migration must persist decision provenance and
the exact mapping artifact digest in its evidence output. No tool generates
mappings from weak evidence.

## Quarantine contract

Use **A: a migration staging/adjudication table** as the eventual mechanism,
not a default tenant and not an application-visible nullable fallback. It must
record entity type/ID, state (`UNRESOLVED`, `CONFLICT`, `INVALID_LINEAGE`),
sanitized evidence, first/last observed time, and reviewed resolution metadata.
The staging table is a migration artifact; MT-1A does not create it.

A quarantined row is preserved and remains unowned. It is excluded from every
tenant query, API, selector, search, count, report, export, notification, job,
cache, download, and public projection. It cannot be written through normal
business paths or assigned by session/default behavior. Only an explicit,
audited, reviewed operator resolution may transition it. Parent and descendant
must move atomically only after their candidate sets agree.

Option C—abort until complete mapping—is required for every active business
row. Staging quarantine is permitted only for explicitly approved inactive
historical records whose exclusion is mechanically enforced and tested. A
nullable organization column alone (option B) is insufficient because legacy
global queries could still expose it.

## Conflict and invalid-lineage output

Reports contain only entity type, stable numeric ID, candidate organization IDs
and symbolic evidence paths. They contain no PII. Conflict is never
auto-resolved. Dangling FK, impossible source shape, or contradictory required
parentage is invalid lineage and requires data repair plus review; mapping alone
does not legitimize a broken relationship.

## Non-mutating analyzer and fixtures

Run:

```powershell
.\.venv\Scripts\python.exe scripts\mt1a_legacy_ownership_analyzer.py `
  --database-url $env:MT1A_DISPOSABLE_DATABASE_URL `
  --mapping .\approved-legacy-tenant-mapping.json `
  --output .\mt1a-sanitized-report.json
```

The analyzer issues SELECTs, rolls back its transaction, and reports sanitized
identifiers/counts. It currently covers Customer and ShipmentRequest candidate
roots; MT-1 must extend it to quote/direct-policy roots before migration. Its
tests model: deterministic lineage, orphan customer, ownerless request,
Project/Quote conflict, cross-organization Customer, resolvable descendant
root, reviewed mapping, and unresolved historical quarantine candidate.

SQLite exercises classifier semantics only. Required PostgreSQL certification
must run the same A-H cases in a disposable PostgreSQL 16 database and verify
the transaction remains read-only at the data level. It has not run on this
workstation because neither Docker nor PostgreSQL client/server tools are
installed. Production must never be used for this certification.

## Projected ownership inventory

Current inventory is 34 direct, 14 indirect, 27 platform, 1 public capability,
28 ambiguous. Repository structure supports only conditional projections:

| State after approved mappings and consistency checks | Direct | Indirect | Platform | Public capability | Ambiguous |
|---|---:|---:|---:|---:|---:|
| Seven resolvable roots direct; all 20 descendants agree; singleton unresolved | 41 | 34 | 27 | 1 | 1 |
| Additionally redesign/split ReferralAutoAssignState with approved ownership | 42 | 34 | 27 | 1 | 0 |

These are entity-type projections, not observed row results. Any orphan,
conflict, invalid lineage, or quarantined row prevents that entity's final
reclassification. No production or legacy dataset was inspected.

Public tracking remains `PUBLIC_CAPABILITY_SCOPED + TENANT_ISOLATION_DEFECT`.
MT-1A makes no lookup or MT-3 behavior change.

## Exact MT-1 migration gate and sequence

`MT1_OWNERSHIP_RESOLUTION_READY=true` may be emitted only when all of these are
machine-proven:

- every mandatory active root is deterministic or has a valid reviewed mapping;
- zero unresolved cross-tenant conflicts and zero invalid lineage rows remain;
- all mapped rows and Organizations exist, mappings are unique and reviewed,
  and mapping/evidence disagreement fails;
- every child derives consistently from its root; permitted unresolved history
  is recorded and unreachable under the approved quarantine policy;
- no active business row is ambiguous; and PostgreSQL A-H certification passes.

Otherwise the migration aborts before mutation. The value is generated from
the evidence report; it is never an operator-supplied bypass.

When the gate passes, MT-1 must: add nullable `organization_id` to Customer,
ShipmentRequest, ExpertQuote and direct policy/report/gamification roots; load
deterministic and reviewed backfills; create adjudication/quarantine records;
validate child propagation; add organization FKs and `(id, organization_id)`
unique keys; then add composite same-tenant FKs for Request/Project,
Project/Customer and party Customer, Quote/Request, OperationalShipment with
Request/Quote/Customer, document file/requirement/request, and every conditional
parent pair. Only after validation may active roots become `NOT NULL` and
descendants be reclassified. Populated downgrade must fail before discarding
adjudicated ownership.

## Security review checklist

The design passes review only if tests prove: a mapping cannot overwrite a
different lineage candidate; missing mapping has no default/session fallback;
parent/child and Customer/Request disagreement is conflict; manual input passes
the same composite constraints as deterministic backfill; quarantine is absent
from all global and tenant surfaces; and public tracking remains an explicit
unfixed defect. Failure of any item is `MT-1A SECURITY REVIEW — BLOCK`.

**Independent result: MT-1A SECURITY REVIEW — BLOCK.** The review identified
incomplete full-graph/fixpoint and dangling-FK analysis, incomplete schema
enforcement/supersession history, absence of database-enforced read-only mode,
and no mechanical quarantine exclusion tests across product surfaces. It also
found a mapping-versus-multi-candidate bug; that specific bug is corrected and
regression-tested, but the remaining blockers prevent a PASS.

## Current decision

The ownership theory and operator/quarantine contracts are specified, but no
approved legacy mapping set exists. MT-1B has since run the classifier and
read-only mutation proof in an isolated PostgreSQL 18 cluster; application-wide
quarantine scenario J remains blocked. Therefore MT-1 must not resume its
schema migration yet.

MT-1B supersedes the incomplete certification mechanics in this document. See
`mt-1b-legacy-ownership-certification.md` for the full fixpoint analyzer,
explicit `INVALID_LINEAGE`, append-only decision format, PostgreSQL test, and
the evidence-based no-go caused by unimplemented application-wide quarantine
exclusion. MT-1A remains historical design evidence and does not grant a gate.

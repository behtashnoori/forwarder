# Admin / System Foundations Hardening Mission Authority

Local date: 2026-09-27, Asia/Tehran. Governed canonical repository:
`D:\1-webapp\15-forwarder-golden-20260921`. Isolated worktree:
`D:\1-webapp\forwarder-dev\human-walkthrough-admin-foundations-hardening`.

This record captures the Product authority supplied by the Product Owner for
the Human Walkthrough Admin / System Foundations hardening mission. It does not
authorize release, deployment, Production access, Production catalog execution,
or a Human Product Walkthrough verdict.

## Entry evidence

- Canonical branch: `integration/golden-controlled`.
- Verified local and `github/integration/golden-controlled` entry SHA:
  `4a46af61c40e0b57acc64ca8376bc70b87e8e045`, with ahead/behind `0/0` and a
  clean canonical worktree.
- The frozen pre-mission Product SHA
  `fe73dbf3c2789d9b88052be9098c28c8e2b2add7` and evidence SHA
  `eb9c20b4a6b2f0df5f2640fc8ae4303891539661` are ancestors of the entry SHA.
- Alembic has exactly one head: `20261012_phase3_cargo_eta`.
- LPAF v2.7 Architecture Framework, Agent Entry Protocol, baseline acceptance,
  governance validation, repository `AGENTS.md`, Product Contract, applicable
  accepted ADRs, Phase 3 Journey Pack, and this mission were reviewed before
  Build.
- Governance level: `B`. Capability route: `Sol`. No authority escalation was
  required at entry.

## Product Authority Record

| Field | Authority |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Separate System Admin and Organization Admin capability domains; support an explicit auditable self-hosted composition of `PLATFORM_ADMIN`/System Admin plus same-organization Organization Admin membership; prohibit implicit tenant access and impersonation; resolve DN08 for the current release; create source-controlled Forwarder Reference Catalog V1 and Standard Organization Profile V1 with explicit plan/apply; add the approved packaging, transport-means, equipment/load-unit, container, and millimetre baselines; harden Cargo Type/UOM/reference-activation UX; make organization Operational Reason codes server-generated; replace free-text SLA semantics with the governed target registry; repair Organization Admin logistics authority; harden the named Admin surfaces; requalify the complete Phase 3 candidate; and, only after controlled canonical integration, update the existing Human Walkthrough runtime while preserving its database and business records. |
| `DELEGATED_TECHNICAL_CHOICES` | Reuse of existing role name and membership permission storage, explicit capability projection, command syntax within the existing reference-data CLI, catalog/profile file organization, stable code naming for newly authorized definitions, presentation grouping, Persian copy, deterministic audit metadata, tests, and evidence structure, provided the approved Product meaning and existing history remain unchanged. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | No implicit System Admin tenant access, tenant impersonation, arbitrary Organization Admin base-taxonomy creation, EAV/generic master-data or SLA rule engine, semantic overwrite, automatic promotion, startup seeding, deletion or silent/unversioned reactivation of history, invented route/milestone SLA targets, document-policy defaults, operational-reason defaults, Product Owner walkthrough-request mutation, AI/GPS/BI redesign, schema/migration unless a separately stopped architecture gate proves necessity, Production access/mutation/migration, deployment, release, or self-passed Human Walkthrough. |
| `DECISIONS_NEEDED` | `NONE` at entry. Stop the affected design before any schema/migration or if a requested SLA target, capability, history rule, or operational behavior cannot be proven from existing governed facts. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing the explicit “Forwarder — Human Walkthrough Admin / System Foundations Hardening” mission. |
| `APPROVAL_REFERENCE` | Attached mission `Pasted text.txt`, dated 2026-09-27, Parts A–Z and the exact final-verdict/flag contract. |

## Binding Product decisions

- `SYSTEM_ADMIN` is the Product term; the compatible internal authority value
  `PLATFORM_ADMIN` may remain.
- System authority and tenant membership are separate. A self-hosted Super Admin
  is a System Admin with one explicit same-organization membership carrying the
  Organization Admin capability. System authority alone never supplies tenant
  operations.
- `DN08_STATUS=RESOLVED_FOR_CURRENT_RELEASE`:
  `ORG_ADMIN_ARBITRARY_BASE_DEFINITION=NO`,
  `SYSTEM_ADMIN_BASE_DEFINITION=YES`, and `AUTO_PROMOTION=NO`.
- Catalog/profile execution is always explicit plan then apply; normal startup
  performs no catalog writes.
- SLA policy selects a code-governed target. Only targets with deterministic
  governed start/end facts may be available. Unsupported route/milestone ideas
  remain unavailable rather than being fabricated.
- Human Product Walkthrough remains `IN_PROGRESS`; release readiness remains
  `NO` regardless of automated qualification.

## Journey and reference impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`

The required critical set remains exactly:

`FWD-J01,FWD-J02,FWD-J03,FWD-J04,FWD-J05,FWD-J06,FWD-J07,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-02,FWD-IPJ-03,FWD-IPJ-04`.

`REFERENCE_IMPACT=NONE` for the frozen LPAF baseline. Current Product
references are `UPDATE_REQUIRED` for the approved Admin semantics, DN08,
catalog/profile, Operational Reasons, SLA registry, logistics authority,
installation sequence, exact new Product/evidence SHAs, and integration receipt.
Historical evidence must not be rewritten.

The historical observations and candidate dispositions are preserved in
[Human Walkthrough Admin findings](HUMAN-WALKTHROUGH-ADMIN-FINDINGS-20260927.md).

## Data, migration, and runtime boundary

- Existing stable reference codes and used historical records take precedence.
- Existing organization, Customer Account, domestic Request, Expert assignment,
  hostname binding, and walkthrough PostgreSQL database must be preserved.
- Existing models are preferred. If they suffice,
  `MIGRATION_REQUIRED=NO` and the single Alembic head remains
  `20261012_phase3_cargo_eta`.
- Automated mutation tests use isolated databases. The walkthrough database is
  touched only after canonical integration, first by read-only identity capture,
  then catalog/profile plan and reviewed apply.
- Production remains entirely outside scope.

## Entry disposition

```text
LPAF_BASELINE=2.7
GOVERNANCE_LEVEL=B
CAPABILITY_ROUTE=SOL
PRODUCT_AUTHORITY_RECONCILIATION=PASS
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
REFERENCE_IMPACT=NONE
MIGRATION_REQUIRED=NO_EXPECTED
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
RELEASE_READY=NO
PRODUCTION_UNTOUCHED=YES
```

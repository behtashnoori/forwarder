# Human Walkthrough Shipment Owner Authorization Hardening — Mission Authority

- Date: 2026-09-28 (Asia/Tehran)
- Governing baseline: `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL`
- Mission type: governed post-final-candidate blocker diagnosis and bounded hardening
- Rigor / capability route: `Level B / Sol`
- Product Owner authority: the attached mission titled
  `Forwarder — HUMAN WALKTHROUGH BLOCKER RECOVERY — HW-SHIPMENT-AUTH-001`
- Verified canonical entry:
  `integration/golden-controlled@2a5cf7ad246ce0fd880b163bbf1742bc9689d7b1`
- Historical Product SHA before this hardening:
  `e00bd18cb1048d738fdf12570757e4491f23c3a0`
- Required schema identity: one Alembic head,
  `20261012_phase3_cargo_eta`; `MIGRATION_REQUIRED=NO`

This mission repairs the already-approved current Shipment-owner execution
contract. It grants no new actor, tenant, Admin, Carrier or Request-derived
authority and cannot grant Human Product Walkthrough PASS, Release, deployment
or Production authority.

## Entry evidence and diagnosis

### FACT

- Canonical and `github/integration/golden-controlled` were clean and aligned
  `0/0` at the exact entry SHA after a fresh fetch.
- Alembic reports exactly one source head: `20261012_phase3_cargo_eta`.
- The local walkthrough principal is the active canonical Expert user for
  `walkthrough_expert`, with exactly one active membership in the active
  walkthrough organization.
- The existing Shipment belongs to that same organization. Its persisted
  `primary_responsible_expert_id`, creator, accepted Quote issuer and current
  Request assignee all happen to resolve to the same Expert for this record.
  The equality is evidence about this record, not a rule conflating Request
  assignment with Shipment ownership.
- The Shipment summary resolves `responsible_expert.display_name` by joining
  `ExpertUser` through persisted
  `OperationalShipment.primary_responsible_expert_id`.
- Route-stage execution commands use the same persisted Shipment field through
  `authorize_document_management`; the predicate compares authenticated user
  identity to owner user identity after active single-membership and tenant
  checks. It does not compare membership id to user id.
- The standard active Expert baseline contains `execution_unit.create` and
  `execution_unit.update` but omits `execution_unit.read`.
- Both failing panel requests are reads: the stage execution list and selectable
  options. They fail at `require_permission(..., "execution_unit.read")` before
  the current-owner predicate runs. The frontend maps every HTTP 403 in this
  panel to the owner-denial sentence, so the visible message is misleading.
- The existing walkthrough Shipment owner data is correct. No owner transfer,
  raw database write, Shipment recreation or history repair is required.

### Tested hypotheses

| Hypothesis | Result |
| --- | --- |
| user id versus membership id mismatch | Rejected; authorization correctly compares owner user id to authenticated user id. |
| Request assignee reused as Shipment owner | Rejected for authorization; Shipment owner is read from its own persisted field. |
| correct label but wrong persisted owner | Rejected; label and command owner source are the same persisted identity. |
| stale or wrong browser account | Rejected by current authenticated traffic and persisted login identity. |
| inactive or duplicate membership | Rejected; exactly one active membership exists. |
| tenant mismatch | Rejected; principal membership and Shipment organization match. |
| P3-13 transfer invariant interference | Rejected; no transfer exists and ordinary owner protection is unrelated to the failing reads. |
| obsolete fixed-owner predicate | Rejected; the current owner predicate is correct and transfer-aware. |
| stale frontend/read cache | Rejected; repeat network calls reach the backend and receive fresh 403 responses. |
| different owner field for execution | Rejected; execution mutation uses the canonical Shipment owner field. |
| accepted-Quote creation assigned the wrong owner | Rejected for the existing record; owner, Quote issuer and creator match. |
| missing execution read capability | Confirmed root cause. |

## Product Authority Record

| Required field | Record |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Complete the normal active Expert operational baseline with `execution_unit.read` so an owning Expert can load the route-stage execution surface before using its already-approved create/update capabilities; add read/write owner-parity regression coverage. |
| `DELEGATED_TECHNICAL_CHOICES` | Additive baseline constant, existing idempotent governed reconciliation command, focused tests and evidence organization. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | Persisted Shipment owner SOR; Request assignment independence; Carrier non-ownership; non-owner, foreign-tenant, inactive-member, Organization Admin and Platform Admin denial; P3-13 exceptional transfer and database guard; all Shipment/Request/Quote/CRM/Cargo/route history; ETA behavior; listed UX findings; schema/migration; Production, deployment and Release. |
| `DECISIONS_NEEDED` | `NONE` at entry. Stop with `ARCHITECTURE_REVIEW_REQUIRED` if schema or new product authority becomes necessary. Stop with `EXISTING_WALKTHROUGH_RECORD_REPAIR_DECISION_NEEDED` if the persisted owner later proves wrong and no governed repair applies. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing the explicit blocker-recovery mission; LPAF v2.7 for governance. |
| `APPROVAL_REFERENCE` | Attached request `Pasted text.txt`, dated 2026-09-28, especially sections 1–33 and the exact success-flag contract. |

## SOR, authorization and preservation

`OperationalShipment.primary_responsible_expert_id` remains the single current
owner SOR. Summary projection and owner-scoped commands continue to derive from
that field. Membership remains the active tenant/capability envelope and does
not become the owner identity. The repair changes no owner, Request assignee,
Quote issuer, creator, transfer history or operational record.

The additive reconciliation path is the existing governed command
`python -m backend.operational_cli reconcile-expert-baseline --apply`. It adds
only missing baseline capabilities to active canonical Expert memberships,
preserves explicit grants, excludes inactive and non-Expert identities, and is
idempotent. If used after integration for the walkthrough runtime, it is a
capability-baseline repair, not an owner or business-history patch.

## Journey and reference impact

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
DIRECTLY_AFFECTED_JOURNEYS=FWD-J03,FWD-J04,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-02,FWD-IPJ-03,FWD-IPJ-04
REQUIRED_SLICE_RERUN=P3-04,P3-05,P3-13,shipment-owner-read-write-parity
REQUIRED_INTEGRATED_RERUN=FWD-J01..FWD-J09,FWD-IPJ-01..FWD-IPJ-04
HUMAN_WALKTHROUGH_RERUN=PRODUCT_OWNER_CONTINUES; RESULT_IN_PROGRESS
LPAF_REFERENCE_IMPACT=NONE
PROJECT_REFERENCE_IMPACT=UPDATE_REQUIRED
```

Project reference impact is satisfied by this authority record and the promoted
`AUTH-RG-EXPERT-BASELINE` regression control. No LPAF or Product Contract text
changes because the repair restores, rather than redefines, approved behavior.

## Entry disposition

```text
LPAF_BASELINE=2.7
GOVERNANCE_LEVEL=B
CAPABILITY_ROUTE=SOL
PRODUCT_AUTHORITY_RECONCILIATION=PASS_AT_ENTRY
HW_SHIPMENT_AUTH_001=OPEN
EXISTING_WALKTHROUGH_SHIPMENT_OWNER_CORRECT=YES
EXISTING_WALKTHROUGH_RECORD_REPAIR_REQUIRED=NO
MIGRATION_REQUIRED=NO
ALEMBIC_HEAD=20261012_phase3_cargo_eta
HUMAN_PRODUCT_WALKTHROUGH=IN_PROGRESS
RELEASE_READY=NO
PRODUCTION_UNTOUCHED=YES
```

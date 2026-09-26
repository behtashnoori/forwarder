# P3-14/P3-15 Mission Authority and Qualification Contract

Local date: 2026-09-26, Asia/Tehran. Governed repository:
`D:\1-webapp\15-forwarder-golden-20260921`. Isolated P3-14 worktree:
`D:\1-webapp\forwarder-dev\phase3-p3-14-final-runtime-ux`.

This record captures the Product and engineering authority supplied by the
Product Owner in the explicit mission to complete P3-14 and, only after its
controlled integration, qualify P3-15. It does not authorize release,
deployment, Production access, or a new Product capability.

## Entry evidence

- Canonical branch: `integration/golden-controlled`.
- Verified local and `github/integration/golden-controlled` entry SHA:
  `835d46f7008bbc374168d1f5eba415b444574f7f` with ahead/behind `0/0` and a
  clean canonical worktree.
- All named Phase 3 P3-01 through P3-13 branch tips are ancestors of the entry
  SHA.
- ADR-067, ADR-068, and ADR-069 are `ACCEPTED`.
- Alembic has exactly one head: `20261012_phase3_cargo_eta`.
- LPAF v2.7 Architecture Framework, Agent Entry Protocol, baseline acceptance,
  target-repository `AGENTS.md`, Product Contract, UX baseline, Journey Pack,
  and Phase 3 plan were read before Build.
- Governance level: `B`. Capability route: `Sol`. No capability or authority
  escalation was required at entry.

## Product Authority Record

| Field | Authority |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | Complete P3-14 by integrating already-approved Phase 3 operational facts and actions into a coherent Expert, Organization Admin, and Customer UX; close the known ordinary-navigation gap to existing Admin account-support behavior; preserve and expose the existing Workspace/Tower truth, freshness, and ranking contracts; improve responsive, RTL, accessible presentation. After P3-14 qualifies and is integrated, P3-15 may harden defects only where expected behavior is already authorized by the Product Contract, Journey Pack, UX baseline, or FWD-DEC-01..04. |
| `DELEGATED_TECHNICAL_CHOICES` | Component boundaries, presentation grouping, progressive disclosure, deterministic view adapters, accessible navigation treatment, non-semantic copy refinements, test structure, evidence format, and additive read-only metadata needed to prove parity, provided no Product meaning, rank, authority, schema, or lifecycle changes. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | No new attention or prioritization algorithm; no new Product capability, AI/agent, GPS tracking, public allowlist, ownership transfer side effect, lifecycle transition, schema, migration, release, deployment, Production read/write, or critical-journey expansion. No historical or resolved-candidate document becomes normative. Human walkthrough cannot be self-passed. |
| `DECISIONS_NEEDED` | `NONE` at entry. Stop and return to Product/Architecture authority if implementation would require new ranking semantics, a schema/migration, a new customer-visible action, a changed tenant/owner/time contract, or behavior not already approved. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner issuing the explicit P3-14/P3-15 mission. |
| `APPROVAL_REFERENCE` | Mission attachment dated 2026-09-26, especially FWD-DEC-01 through FWD-DEC-04, the exact critical-set declaration, P3-14/P3-15 sequence, stop rules, and final-verdict contract. |

## Binding decisions

- `FWD-DEC-01`: the critical set is exactly `FWD-J01` through `FWD-J09` plus
  `FWD-IPJ-01` through `FWD-IPJ-04`; it must not be expanded implicitly.
- `FWD-DEC-02`: closing the known Admin ordinary-navigation gap is authorized.
- `FWD-DEC-03`: the recovery Product flow must qualify through a safe test
  delivery adapter. Evidence for real external email delivery remains
  `RELEASE_UAT_EVIDENCE_REQUIRED` and does not by itself block the final Phase
  3 candidate.
- `FWD-DEC-04`: public project tracking is regression-only and is not promoted
  to the critical set.

## Journey and reference impact

`JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`

Affected and required critical journeys are exactly:

`FWD-J01,FWD-J02,FWD-J03,FWD-J04,FWD-J05,FWD-J06,FWD-J07,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-02,FWD-IPJ-03,FWD-IPJ-04`.

`REFERENCE_IMPACT` for the LPAF baseline is `NONE`. Project references are
`UPDATE_REQUIRED`: the Phase 3 plan status, runtime-surface map, qualification
status, evidence manifest, exact Product SHA, and integration receipts must be
reconciled before final disposition.

## Data, authority, and source-of-truth boundaries

- Existing domain records remain the system of record. Workspace and Control
  Tower remain read models and must not become parallel systems of record.
- Organization, customer, account, shipment, owner, and document scope is
  enforced by existing backend authority. Presentation must not infer access.
- Existing attention ordering and source priority are preserved. Shared facts
  must have provable identity/version/freshness agreement; a presentation layer
  must not manufacture a replacement rank.
- Time, dual-calendar rendering, unknown/incomplete values, plan versus actual,
  ETA, closure, ownership transfer, document context, allocation, and audit
  meaning remain governed by their accepted Phase 3 contracts.

## P3-14 completion gate

P3-14 may be integrated only when its branch is clean and tested; the full
Expert/Admin/Customer runtime hierarchy is coherent; ordinary navigation
reaches the authorized operations; Workspace/Tower parity is proven; RTL,
responsive, keyboard, semantic, and loading/error/empty states pass; focused
and full regression gates pass; references and evidence identify an immutable
Product SHA; and canonical integration is a controlled fast-forward followed by
push/fetch verification with zero divergence.

## P3-15 start and completion gate

P3-15 starts only from the clean, pushed, verified canonical SHA containing
P3-14, in a separate worktree and branch. It is qualification and authorized
defect hardening, not a capability slice. It must exercise the exact critical
set, regression-only public tracking, backend/frontend/static/migration and
PostgreSQL gates, tenant/role negatives, replay/idempotency/concurrency and
audit checks where applicable, and browser/mobile/RTL/accessibility coverage.
Every remediation must cite pre-existing authority and rerun affected gates.

The Human Product Walkthrough pack may be prepared with exact URLs, actors,
fixtures, expected results, evidence slots, and Product SHA, but its result is
`NOT_RUN` until completed by the authorized human reviewer. Consequently this
mission cannot set `RELEASE_READY=YES`.

## Stop conditions

Stop before mutation or qualification if canonical/remote identity diverges,
the worktree is not isolated and clean, a dependency/ADR is not integrated,
the Alembic head is not unique, a migration/schema change appears, existing
authority cannot resolve a behavioral defect, Workspace/Tower facts conflict
without an accepted reason, tenant/role isolation fails, required deterministic
test infrastructure cannot be established safely, or a release/deploy/
Production action would be required.

## Entry disposition

```text
LPAF_BASELINE=2.7
GOVERNANCE_LEVEL=B
CAPABILITY_ROUTE=SOL
P3_14_ENTRY_GATE=PASS
P3_15_ENTRY_GATE=NOT_STARTED
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN
RELEASE_READY=NO
PRODUCTION_UNTOUCHED=YES
```

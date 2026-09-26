# P3-11 through P3-13 — approved Product scope and architecture entry

Date: 2026-09-26. LPAF v2.7; rigor C; Astra capability need because temporal
provenance, multi-Customer privacy, terminal state and database authorization
interact. This records required capability, not a claim that model settings changed.

## Authority and outcome

The Product Owner's attached mission explicitly authorizes sequential build,
qualification and controlled canonical integration of P3-11, P3-12 and P3-13.
The exact supplied request is retained in
[the evidence source](../../operational/evidence/phase3-p3-11-13-entry-20260926/authorized-request.txt).
Its hash and repository entry evidence are in the adjacent `preflight.json`.

AUTHORIZED_PRODUCT_CHANGES:
- P3-11: deterministic, explainable, Cargo/branch-scoped next/final ETA ranges,
  occurred-time anchors, versioned references, honest missing data and retained
  estimate provenance; no invented distance.
- P3-12: explicit owning-Expert closure after mandatory requirements pass;
  versioned organization GENERAL plus applicable-mode policy; explicit same-tenant
  Organization Admin exceptional closure with reason and retained missing facts.
- P3-13: exceptional same-tenant Organization Admin owner transfer to an active,
  eligible Transport Expert; live post-transfer authority, immutable history,
  independent WorkItem/Request assignments and retained ordinary owner protection.

DELEGATED_TECHNICAL_CHOICES: bounded relational schema, source adapters, concurrency,
idempotency, existing UI composition and qualification methods within those rules.
The repository's named-ADR acceptance gate still applies before implementation.

PROTECTED_OUT_OF_SCOPE_BEHAVIOR: P3-01..10 source facts and historical evidence;
Request assignment; Customer identity/entitlement; document binaries and history;
Exception/Action/SLA independence; Attention ranking; account/login model; public
tracking; existing reference-time plan selections. No P3-14/P3-15, release,
deployment, production, AI, GPS, provider integration, arbitrary rules engine,
default policies, HS closure rule or reopening.

APPROVING_OWNER_OR_AUTHORITY: Product Owner issuing the supplied mission.
APPROVAL_REFERENCE: exact retained request, especially §§4, 28–42, 49–67, 70–78.
DECISIONS_NEEDED: named architecture acceptance of proposed ADR-067/068/069;
no reopening of the specifically approved Product decisions.

```text
DN04_STATUS=RESOLVED_FOR_P3_11
DN01_CLOSURE_STATUS=RESOLVED_FOR_P3_12
DN03_CLOSURE_POLICY=RESOLVED_WITHIN_THIS_MISSION
DN02_OWNER_TRANSFER_PORTION=RESOLVED_FOR_P3_13
DN09_STATUS=RESOLVED_FOR_P3_13
DN05_GENERAL_CLOSURE_RULE=NOT_IMPLEMENTED
DN05_STATUS=OPEN_FOR_FUTURE_SPECIFIC_POLICY
```

## Verified entry and facts

Canonical repository: `D:\1-webapp\15-forwarder-golden-20260921`.
Branch: `integration/golden-controlled`. Approved remote: `github`.
Fresh fetch found local and remote at
`368cd736cbffce3d62c33336868738d9086e8306`, ahead/behind `0/0`, clean worktree.
The sole source migration head is `20261009_phase3_route_time`; no database was
connected. P3-01..10 ancestry is checked in `preflight.json`; historical PASS
records are not new test results.

Canonical AGENTS.md and the LPAF root activation index identify 2.7 as active.
The initial chat directory's 2.6 reference is historical for this target, as
already noted in the Phase 3 plan. No framework file was changed.

FACT: RoutePlan/RouteLeg, per-Cargo terminal associations, reported facts,
reference versions, private Customer projection, delivery and document readiness
exist. The inspected route/reference models contain no governed distance field.
Shipment lifecycle permits planned/in_progress/completed/cancelled, with no closed
value. Owner changes are rejected by ORM and the database trigger.

ASSUMPTION TO VERIFY AFTER ACCEPTANCE: bounded adapters can cover the approved
scenarios without changing source meaning; lock/privilege contracts below are
implementable and qualify on owned PostgreSQL 18.
UNKNOWN: new-candidate preservation, migration, browser and concurrency evidence.
No proposed design is described as tested or implemented.

## Mandatory architecture gate

[Development Gate](../../architecture/CODEX-DEVELOPMENT-GATE.md):

> If architecture change is required, STOP BEFORE IMPLEMENTATION. Produce a
> PROPOSED ADR using `ADR-TEMPLATE.md`. Do not treat the task prompt, code edit,
> or passing tests as ADR acceptance.

[Architecture Baseline §2](../../architecture/FORWARDER-ARCHITECTURE-BASELINE.md):

> An implementation prompt is not itself ADR acceptance unless it explicitly
> accepts a named ADR decision.

The attached mission names no new accepted ADR. New ETA history, closure policy/
terminal state and controlled owner-write authority each trigger this gate.
Therefore all three Build gates are blocked independently on architecture
acceptance. This is not a missing Product policy or a missing P3-01..10 dependency.
The reviewable proposals are:

- [ADR-067 — ETA](../../operational/adr/ADR-067-explainable-cargo-eta.md)
- [ADR-068 — Closure](../../operational/adr/ADR-068-controlled-shipment-closure.md)
- [ADR-069 — Owner transfer](../../operational/adr/ADR-069-exceptional-shipment-owner-transfer.md)

Their status is PROPOSED. Only an authorized architecture owner/process can
accept them. No historical ADR is superseded by these proposals yet.

## Worktree and execution contract

The app worktree tool was tried first. It could not resolve the canonical SHA
because this chat is attached to another Git repository; operation
`796c483b-bc71-4c82-9f42-e5d82bce58a6` returned `invalid reference`.
The requested new checkout was therefore created directly from the verified
canonical repository at `D:\1-webapp\forwarder-dev\phase3-p3-11-explainable-eta`,
branch `codex/phase3-p3-11-explainable-eta`. Existing worktrees were preserved.
This checkout holds only the common entry/approval packet; no runtime was edited.

After acceptance, re-fetch and revalidate current canonical before P3-11 Build.
For each slice: build → qualification → exact Product SHA → evidence-only
descendant → reference/authority reconciliation → clean fast-forward → github
push → fetch → 0/0. Create P3-12 and P3-13 checkouts only when their turn arrives,
from the actual then-current canonical. Never branch migrations in advance.
If an independent slice blocks, preserve successful integrations and continue
only work whose own gates pass. Never roll back successful work for a later block.

## Reference and journey contract

LPAF reference: canonical external 2.7 framework; owner Product/Framework
authority; impact NONE. This mission applies it without amendment.
Project reference: `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md` and
`ADR-INDEX.md`; owner Architecture; runtime-reference impact UPDATE_REQUIRED
after acceptance and implementation. The index currently registers proposals
only. The Product Contract v1, Journey Pack v1.1 and approved UX V2.1 remain
the Product baseline; the supplied decisions resolve only the named boundaries.

JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY for each implementation slice:

| Slice | Affected journeys |
| --- | --- |
| P3-11 | FWD-J02,J04,J06,J07,J08,J09; FWD-IPJ-02,03,04 |
| P3-12 | FWD-J04,J05,J06,J08,J09; FWD-IPJ-02,03,04 |
| P3-13 | FWD-J03,J04,J06,J08,J09; FWD-IPJ-01,03,04 |

Each abbreviated J/IPJ entry carries the same FWD prefix. The current proposal
packet itself has no runtime impact. Full integrated and authorized human
acceptance stay NOT_RUN; no global Product Freeze or Release Ready claim.

DoD for each slice includes all mission cases, exact-source full backend/frontend,
PostgreSQL 18 upgrade/downgrade protection/concurrency, real Chrome target-role
normal navigation/reopen and relevant mobile/negative/stale cases, TypeScript,
ESLint/build, OpenAPI, architecture/structure/governance and diff checks. Runtime
changes after evidence require affected reruns. All synthetic runtimes must be
stopped and cleanup recorded. Qualification is not granted by architecture acceptance.

PDA-07 for this packet: authorized decision transcription and proposed architecture
are AUTHORIZED; Product/runtime/schema and canonical content are PRESERVED by
documentation-only diff. Proposed runtime behavior remains UNVERIFIED, not PASS.
Engineering Complete=NO; Product Complete=NO; Release Ready=NO; Release Complete=NO.

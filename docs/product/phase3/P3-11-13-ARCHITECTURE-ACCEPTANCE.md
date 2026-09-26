# P3-11..13 architecture acceptance and retained mission resume

Date: 2026-09-26. Governing mission: RESOLVE ARCHITECTURE GATE / ACCEPT
ADR-067, ADR-068, ADR-069 WITH EXPLICIT CLARIFICATIONS / RESUME EXISTING
P3-11 -> P3-12 -> P3-13. This is continuation of the retained mission, not a
replacement Product mission. Rigor C; Astra capability selected for coupled
history, temporal provenance, lifecycle, privacy and security boundaries.

## Authority and preserved evidence

APPROVING_OWNER_OR_AUTHORITY: Product Owner's explicit named ADR acceptance.
APPROVAL_REFERENCE: [exact supplied acceptance request](../../operational/evidence/phase3-p3-11-13-acceptance-20260926/authorized-request.txt),
SHA-256 `52b94b3ef0795d5bb722e1e02531cd51f3a529e00afb10851e7a67f89e668e50`.
Original Product authority remains [P3-11..13 mission](P3-11-13-MISSION-AUTHORITY.md).
The proposal commit `081f73a3d84c6aa6136e7f1fd4268f57bac497cf`, original request,
entry/preflight/qualification records, and status-history entries are preserved.
Only current references and ADR decisions are reconciled by this acceptance.

AUTHORIZED_PRODUCT_CHANGES: retained P3-11 ETA, P3-12 closure, P3-13 owner-transfer
scope, with the explicit new P3-12 predecessor: both normal and exceptional
closure permit completed -> closed only. No planned/in_progress/cancelled closure.
DELEGATED_TECHNICAL_CHOICES: retained bounded implementation choices; explicit
idempotent ENSURE_CURRENT_ETA or REFRESH_CURRENT_ETA service semantics and narrow
SECURITY DEFINER structural fence, subject to proof.
PROTECTED_OUT_OF_SCOPE_BEHAVIOR: source Route/Event SORs, completed meaning,
Request/WorkItem assignments, independent Exception/Action/SLA lifecycles,
Customer DN10 grants and private branch isolation, exact document/history
contracts, P3-01..10, all other retained mission exclusions.
DECISIONS_NEEDED: none for these three named architecture decisions. Any genuinely
undefined post-closure command remains a narrow Product decision before its
implementation; database privilege failure blocks P3-13, never permits bypass.

## Accepted bounded decisions

- [ADR-067](../../operational/adr/ADR-067-explainable-cargo-eta.md): immutable,
  Cargo-specific ETA snapshots with provenance and reference pins. Pure historical
  lookup is distinct from explicitly documented idempotent ensure/recalculation.
  An ordinary Product read experience is permitted; unrelated list/count queries
  never materialize. No additional Product capability or mandatory user step.
- [ADR-068](../../operational/adr/ADR-068-controlled-shipment-closure.md): versioned
  checklist and explicit closed terminal state. Both normal Expert and exceptional
  Admin commands require completed. Exception bypasses mandatory checklist failure
  only. Preserve missing/unknown facts and independent operational lifecycles.
  Before integration produce COMMAND / ALLOWED_AFTER_CLOSED / DENIED_AFTER_CLOSED /
  AUTHORITY / REASON matrix; undefined meanings are DECISION_NEEDED.
- [ADR-069](../../operational/adr/ADR-069-exceptional-shipment-owner-transfer.md):
  application authentication binds the human; application authorization proves
  that authenticated Admin may transfer. DB independently checks supplied actor
  and target eligibility, tenant, owner/version, chain, replay, history and
  atomicity. The app credential is trusted; a compromised credential plus valid
  Admin ID does not establish independently authenticated human identity.
  Separate evidence A ordinary UPDATE, B history integrity, C invalid structural
  calls/privileges, D application actor binding. All NOLOGIN/search_path/qualified
  names/no dynamic SQL/revoked PUBLIC/minimum EXECUTE/no SET ROLE/no bypass
  constraints remain mandatory. No new DB identity mechanism is authorized.

```text
ADR_067=ACCEPTED
ADR_068=ACCEPTED
ADR_069=ACCEPTED
ARCHITECTURE_GATE_P3_11_13=PASS
DN04_STATUS=RESOLVED_FOR_P3_11
DN01_CLOSURE_STATUS=RESOLVED_FOR_P3_12
DN02_OWNER_TRANSFER_PORTION=RESOLVED_FOR_P3_13
DN09_STATUS=RESOLVED_FOR_P3_13
DN05_GENERAL_CLOSURE_RULE=NOT_IMPLEMENTED
DN05_STATUS=OPEN_FOR_FUTURE_SPECIFIC_POLICY
```

## Fresh entry evidence and baseline reconciliation

[Fresh preflight](../../operational/evidence/phase3-p3-11-13-acceptance-20260926/preflight.json)
proves fetched canonical local/remote `368cd736cbffce3d62c33336868738d9086e8306`,
0/0, clean canonical and retained review checkout, all P3-01..10 ancestry, sole
source Alembic head `20261009_phase3_route_time`, and unchanged normative hashes.
No database was connected. Build for all three remains NOT_STARTED at acceptance.

The starting chat directory's v2.6 instruction was inspected. The actual target
repository AGENTS.md, retained mission and later explicit acceptance request use
v2.7. The canonical external root activation index and acceptance record prove
v2.7 was activated on 2026-09-24; v2.6 compatibility copies are historical.
This records existing activation and follows the later task-specific instruction;
it neither changes framework files nor silently activates a new baseline.
Global framework/Product validation remains EVIDENCE_PENDING.

## References and verification boundary

| Reference | Owner / location | Impact and reconciliation |
| --- | --- | --- |
| LPAF v2.7 | Framework authority; D:/1-webapp/29-lpaf/29-lpaf (1)/29-lpaf/lpaf/current/LPAF-v2.7-Architecture-Framework-FA.md | NONE; existing baseline applied unchanged |
| Forwarder architecture | Architecture owner; docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md, ADR-INDEX.md, CODEX-DEVELOPMENT-GATE.md | UPDATE_REQUIRED fulfilled by this documentation-only acceptance; no remaining reference delta |
| Current mission/review/decision/Phase 3 indexes | Product/Architecture; linked current documents | Named acceptances and bounded supersession recorded; original evidence retained |

REFERENCE_RECONCILIATION=PASS. REFERENCE_IMPACT=NONE means no outstanding
reference action after reconciliation; it does not deny that project references
were updated. PDA-07=AUTHORIZED for the specific owner decisions; PRESERVED for
runtime/schema by documentation-only diff. JOURNEY_IMPACT=NONE for acceptance
alone; implementation retains each slice's AFFECTS_EXISTING_JOURNEY classification.
Tests/browser/migration/concurrency/security qualification are NOT_RUN here.
Engineering Complete=NO; Product Complete=NO; Release Ready=NO; Release Complete=NO.

## Resume contract

Commit this documentation-only acceptance first and record exact
ARCHITECTURE_ACCEPTANCE_HEAD in its subsequent receipt (a commit cannot include
its own SHA). Require diff check, docs-only paths, no migration and clean worktree.
Then resume the retained worktree for P3-11; qualify exact Product, create evidence
only descendant, reconcile, fast-forward canonical, push github, fetch and require
0/0. Later slices start from actual canonical sequentially; independent blocked
slices do not invalidate previous integrations. No early migration branches.
All retained required qualification gates remain mandatory. Do not start P3-14,
P3-15, global integrated qualification, Human Walkthrough, release or deployment.
No production access, data, credentials, databases or migrations.

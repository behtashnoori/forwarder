# FWD-03 entry, discovery and architectural decision gate

Date: 2026-09-16. MISSION_RESULT: BLOCKED_PENDING_ADR_046_ACCEPTANCE.
This is an interim gate record, not implementation or product completion.

## Identity and authority

Root: `D:/1-webapp/forwarder-dev`. Start branch:
`feature/fwd-02-location-integrity`; start HEAD:
`1714118340943f1dbbf99e4b25edc9ef41f817e6`. Worktree was clean; upstream
`origin/feature/fwd-02-location-integrity`, ahead/behind 0/0. Remote:
`https://github.com/behtashnoori/forwarder.git`. Live ls-remote confirmed the
same FWD-02 head and no FWD-03 branch. Created `feature/fwd-03-request-intake`
at that exact head. FWD-01 `d7cbedf9ec7416b83aeb6313aa095462a20e441d` ancestry
check exited 0. No other worktree changed; no reset/clean/rebase used.
No applicable AGENTS.md was found in root/parents or repository search.

Owner/authority: mission issuer, no personal identity inferred. One agent, rigor B.
Scope: Commercial intake -> store -> customer summary -> expert view -> reopen;
Geography and Notification are consumed through their existing boundaries.
Out: operational route engine, global analytics, new AI/provider, Production,
main merge, deployment, historical migration edits or destructive catalog seed.

## Governance and reference impact

Global LPAF v2.2 remains ACTIVE; FWD-03 explicitly uses limited v2.4 pilot rules.
Actual framework root: `D:/1-webapp/29-lpaf/29-lpaf (1)/29-lpaf/lpaf`.
Current v2.4 hash independently verified:
`217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397`.
Re-attestation binds it to the original approval by link-only repairs, not fresh
global activation. Applicable: v2.2 mission/chain/SOR, authorization, evidence,
ADR, regression and release separation; v2.4 MOD-01/03, READ-02, AI-02 boundary,
QUAL-01–05, ADOPT-01/02 and count/rowset reconciliation principle. No new AI,
workflow, attention or analytics platform is required. No normative conflict found.

| Reference / owner | Actual path | Impact |
| --- | --- | --- |
| Mother / Architecture-Business Owner | framework root above, `LPAF-v2.2-Architecture-Framework-FA.md`, `candidates/v2.4/LPAF-v2.4-Modular-Operational-Intelligence-Governance-FA.md` | NONE; product-specific contract, mother untouched |
| Project / Forwarder Architecture Owner | `docs/architecture/FORWARDER-ARCHITECTURE-BASELINE.md` | UPDATE_REQUIRED after acceptance/implementation; proposed ADR is not silently installed as baseline |

Primary owner: Commercial / ShipmentRequest. Shared geography: Country and
InternationalCity. Transaction data: cargo and intent; historical values retained.
Operational route owner: OperationalShipment/RoutePlan/RouteLeg; not reusable for
intake wishes. Notification remains ADR-045's owner. No temporal change proposed.

## Focused discovery (interim)

| Customer issue | Current behavior / root cause | Owner | Reuse/extend/new | Acceptance |
| --- | --- | --- | --- | --- |
| Two rails | Seed source has two identical Rail Transport entries and selector returns every row; actual installed dataset UNKNOWN, runtime reproduction still pending | Commercial/catalog | EXTEND selector, preserve records | synthetic duplicate selection + historical reads |
| Combined transport | Scalars cannot encode arbitrary order; normalization discards transport_sequence | Commercial | NEW ordered value, ADR-046 gate | road/sea/road round-trip, no operational leg |
| Blank cargo | Direct normalization accepts whitespace as None | Commercial | EXTEND validation | final API/UI rejection, state retained |
| Summary | Expert list exposes legacy scalar fields; no ordered field exists | Commercial read projections | EXTEND after acceptance | same meaning customer/expert/reopen |
| New counter | Expert endpoint uses status=new; list uses current assigned_request_scope then status filter; no mismatch asserted without reproduction | Commercial query | REUSE/verify | same authorized population, distinct requests, refresh |

Existing intake is public; hostname resolution derives tenant or INTAKE. Do not
invent mandatory customer login from mission wording. Expert visibility uses
persisted authority/membership/assignment, not username inequality. More detailed
customer capability and summary discovery remains required after gate acceptance.

## Validation table before implementation

| Field | Required when | Validation | Message / disposition |
| --- | --- | --- | --- |
| cargo_description | new final submission | string, non-whitespace | «شرح کالا را وارد کنید.» |
| cargo_weight | optional existing field, kg | numeric contract currently permissive; reject malformed/nonfinite proposals require final review of callers | field-specific numeric error; no new requiredness |
| cargo_volume | optional existing field, m³ | same numeric review | field-specific numeric error; no new requiredness |
| cargo_value | optional existing field, toman | same numeric review | field-specific numeric error; no invented currency conversion |
| quantity/packaging | no corresponding intake field observed | no invented requirement | NOT_APPLICABLE until actual product contract found |
| transport intent | customer chooses on new path | ordered supported modes; owner-defined classification | ADR-046 proposed field errors |

No persisted Draft state was observed in the inspected request path; full caller
review remains pending. No draft state will be invented. Old incomplete reads must
remain valid. Direct command validation, not UI stars, is the acceptance boundary.

## Reproducible observations and checks

Executed direct `normalize_shipment_payload` with domestic province IDs 1/2,
synthetic phone, whitespace cargo and transport_sequence=[road,sea,road]. Result:
`blank_cargo_accepted=True`, `sequence_discarded=True`. This was an in-process
normalizer check, not a persisted API/browser test, and used no database.
Alembic ScriptDirectory graph inspection returned sole head
`20260916_fwd01_notifications`; no database connected or migrated.
Read FWD-01/FWD-02 evidence, ADR index, baseline, development gate, legacy map,
ADR-002/004/007 and affected implementation. Further full affected ADR review is
still required before implementation. No unexecuted scenario is labeled PASS or
NOT_REPRODUCED_ON_THIS_BASELINE.

## Gate and continuation

`CODEX-DEVELOPMENT-GATE.md`: "If architecture change is required, STOP BEFORE
IMPLEMENTATION. Produce a PROPOSED ADR". Baseline section 2 covers the changed
canonical request contract. ADR-046 proposes the precise additive value and legacy
precedence; the mission expressly does not accept an unwritten ADR automatically.
Approval requested only for ADR-046, not routine file/class choices. No product
code/schema was changed while awaiting this decision. Ordinary cargo, selector
and counter work remains authorized, but integrated implementation is not claimed.

After acceptance: finish caller/summary discovery, implement owner command/query
and UI, disposable DB tests including PostgreSQL migration, FWD-01/FWD-02 and full
mandatory regressions, RTL real-role UAT, architecture update, secret/diff review,
scoped commit, non-force push, fetch and verify remote equality. Preserve FWD-02's
901 passed / 136 skipped / 1 xfailed baseline as comparison, not a waiver for new
failures. No product test suite or Browser UAT has run in FWD-03 yet.

Engineering Complete: NO. Product Complete: NO. Release Ready: NO.
Release Complete: NOT_APPLICABLE (no deployment authorized).
FORWARDER-HISTORICAL-REPLAY-001 = BLOCKED_MISSING_EXTERNAL_EVIDENCE.
PRODUCTION_IDENTITY = UNKNOWN. Broader pilot evidence remains EVIDENCE_PENDING.
COMMITS: NONE. LOCAL_HEAD: start HEAD. REMOTE_HEAD (FWD-03): ABSENT.
LOCAL_REMOTE_SYNC (FWD-03): NOT_APPLICABLE_YET. READY_FOR_NEXT_SLICE: NO.
REAL_MESSAGES_SENT: NO. LLM_APIS_CALLED: NO. PRODUCTION_CHANGED: NO.

Documentation checks: `git diff --check` PASS for tracked diff;
`python scripts/check_architecture_governance.py` PASS. Only this evidence,
ADR-046 and its index entry are changed. No commit/push before implementation
qualification gates; these documentation checks do not satisfy product gates.

## Required delivery fields (interim, not final delivery)

ROOT_CAUSES: missing ordered intent storage; blank cargo accepted by normalizer.
TRANSPORT_SINGLE_AND_COMBINED: existing scalar support; ordered extension BLOCKED.
LEGACY_TRANSPORT_COMPATIBILITY: preserved; proposed precedence in ADR-046.
CARGO_VALIDATION_CONTRACT: table above; enforcement NOT_IMPLEMENTED.
REQUEST_SUMMARY: existing scalar projection; new sequence NOT_IMPLEMENTED.
NEW_REQUEST_COUNTER: status=new found; parity tests NOT_RUN.
MODULE_AND_AGENT_BOUNDARIES: Commercial command/query; Geography and Notification
retain ownership; future client readiness NOT_QUALIFIED.
SCHEMA_MIGRATION: no change; sole head inspected; nullable value PROPOSED.
AUTHORIZATION: current hostname/assigned-work boundaries inspected; tests NOT_RUN.
BROWSER_UAT: NOT_RUN. FWD01_FWD02_REGRESSION: NOT_RUN in this mission.
QUALIFICATION: documentation checks only; product gates pending.
KNOWN_GAPS: named historical replay, Production identity, ADR-046 approval.
EVIDENCE_PATH: docs/operational/evidence/fwd-03-request-intake/README.md.

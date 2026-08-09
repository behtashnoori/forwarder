# PR-4B Integrated Certification Report

## 1. Executive Summary

The authorized PR-D03 bootstrap was implemented and proved on a fresh,
loopback PostgreSQL 18 database. The same-tenant service-level Golden Path
completed through Commercial, Operational Shipment, MDPM, OIP, and Shipment
Economics. Authenticated browser certification then found a new P0 product
defect: the shipment detail page reads `shipment.data.id`, although the opaque
shipment detail response intentionally contains `public_id` and no numeric
`id`. It consequently requests three `/undefined/...` child resources and
renders a 404. Mandatory browser, recovery, documentation, AEP, and RC gates
cannot pass under the Weakest Mandatory Link Rule.

## 2. Bootstrap Contract

PASS. The contract is
[`integrated-certification-bootstrap.md`](../integrated-certification-bootstrap.md).
It distinguishes reference/master data, disposable identities, business
transactions, and derived state. Project fixture creation is the documented
narrow exception because the current product exposes no Project creation
workflow. Credentials remained process-only and do not appear in evidence.

## 3. Candidate Identity

- Source product repair: `12fd8b56b29b7c35c5a46fbe6ca426fca1767c1`
- Source evidence commit: `1dab153a5ff661c80e3e2b54bc3bab561e363c1f`
- Derived certification candidate: `b66989aa68abde76bcb5b67250aca4dbae0eccfb`
- Tree: `9819cc88332ab1dd6158d166fc5ac1d7969f50bf`
- Migration head: `20260818_immutable_fx_provenance`
- OpenAPI SHA-256: `2537daa975cd42c44147e961c577b60f24c2b985b95e67ae1aa042252b639bb3`

## 4. Disposable Environment

- PostgreSQL: 18.0, loopback only
- Database logical identity: `forwarder_integrated_cert_final_20260809`
- Primary organization count: exactly 1
- Primary organization public identity: `f7a9c259-4d37-4949-95f1-73d6cdda1b1a`
- Synthetic data: explicit
- Production accessed: NO

## 5. Personas / Permissions

Six disposable same-tenant personas were created: Admin, Commercial,
Operations, Document Reviewer, Control Tower/OIP, and Economics. Permissions
are capability-scoped in the bootstrap; the Admin persona is the consolidated
full-matrix identity.

## 6. Reference Data

Minimum certification-prefixed Province locations, ServiceType, MilestoneType,
DocumentDefinition, Project configuration, and governed OIP threshold policy
were created. No production business dataset was loaded.

## 7. Golden Path Result

Service/application boundary Golden Path: PASS. Authenticated normative browser
Golden Path: FAIL (P0). Overall mandatory Golden Path: FAIL.

## 8. Golden Path Trace

All browser-facing identities below are opaque.

| Node | Public identity |
|---|---|
| Commercial Request | `SR-V9KF37` |
| Quote | `accepted-quote-6b86b273ff34fce1` (redacted derived label) |
| Project | `d59ca036-762d-4eee-8f9f-99c300dfa729` |
| OperationalShipment | `e75ecf1d-42d6-4427-adaa-4aa0dd818f6f` |
| Document Artifact | `a0e7fb93-a8e0-400f-907e-7bd3c64d982a` |
| MDPM Requirement | `ea973148-3937-4b5a-b536-40559fecff43` |
| Milestone | `9a6903e9-2694-404c-a434-65dd5b52ee80` |
| OIP Situation | `3a4cb5a7-c6d9-4315-bf32-b3730429047d` |
| Economic Line | `4ae53173-05ce-4369-a179-864287378e52` |
| Economic Observation | `be4919f5-6d00-41c5-93ea-ac57bee5da4c` |
| FX binding | Not applicable to the same-currency authoritative facts |

MDPM readiness was `allowed=true`; the OIP lifecycle reached
`ACKNOWLEDGED`; the Commitment economic projection was `COMPLETE`.

## 9. Browser / Network Certification

- Disposable Admin authentication: PASS
- Persian shell: `html[lang=fa][dir=rtl]` PASS
- Error-level console entries captured: 0
- Shipment detail request with opaque UUID: HTTP 200
- Follow-on requests: `/api/operational-shipments/undefined/route-plans`,
  `/undefined/timeline`, and `/undefined/route-exceptions`: HTTP 404
- Visible result: FAIL, server 404 alert
- English LTR and remaining browser matrix: NOT EXECUTED after P0 stop

Root cause is at `src/pages/OperationalShipmentDetail.tsx`: `load()` assigns
`const internalShipmentId = shipment.data.id`, while the opaque response and
`OperationalShipmentSummary` contract use `public_id`. The unit fixture carries
a legacy numeric `id`, masking the integrated failure.

## 10. FE Browser Certification

NOT CERTIFIED. Service-level economics materialization and projection passed,
but the required shipment UI is unreachable due to the P0 detail-page defect.

## 11. Security Certification

Prior candidate-valid static/regression evidence remains available, and this
run authenticated successfully with an opaque shipment request. The integrated
browser security matrix is incomplete because the normative page fails before
its child resources load. No claim of consolidated PASS is made.

## 12. PostgreSQL / Regression Binding

Prior 18/18 PostgreSQL and 10/10 historical DMS evidence remains source-lineage
evidence. Focused derived-candidate verification passed 16 tests covering the
new bootstrap contract, economics, and Phase 1B fixture behavior; Python compile
and `git diff --check` passed. Full candidate regression reuse/sealing is
prohibited by the new P0.

## 13. Backup Evidence

NOT CREATED. The mandatory ordering permits representative backup only after a
passing Golden Path.

## 14. Restore Evidence

NOT EXECUTED because no authorized representative backup exists.

## 15. Performance Smoke

NOT EXECUTED after the P0 stop condition.

## 16. Documentation Certification

NOT CERTIFIED. Product documentation must describe a technically passing
candidate; this prerequisite is false.

## 17. Integrated AEP

NOT SEALED under the EAAF Weakest Mandatory Link Rule.

## 18. Final RC Identity

NOT CREATED / NOT FROZEN.

## 19. Git State

The derived candidate commit contains only the bootstrap contract, guarded
operator scripts, and focused test. Pre-existing untracked user/release material
was preserved. No push, deployment, or Production access occurred.

## 20. Commits Created

- `b66989aa68abde76bcb5b67250aca4dbae0eccfb` —
  `test: add integrated certification bootstrap`
- Evidence report commit: the commit containing this document

## 21. Remaining P0

`PR4B-P0-001`: shipment detail uses an absent numeric `shipment.data.id` for
normative child API calls. Acceptance criterion: use the opaque route identity,
add a response-shape regression without numeric `id`, and rerun all downstream
integrated gates on a newly derived candidate.

## 22. Remaining P1

None newly classified; P1 assessment resumes only after P0 closure.

## 23. Production-only Evidence Gaps

All Production controls remain `PRODUCTION_EVIDENCE_REQUIRED`. Production was
not accessed.

## 24. Human Decision Required

None. This is an implementation defect with an unambiguous existing opaque
identity contract, not an architecture or business decision.

## 25. Production Preflight Handoff

NOT PREPARED because RC freeze did not occur.

## 26. Final Decision

PRODUCTIZATION BLOCKED

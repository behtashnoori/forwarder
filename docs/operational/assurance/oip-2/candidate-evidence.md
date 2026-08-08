# OIP-2 candidate evidence — CAND-FWD-OIP-2-001

## Candidate identity

- Base: `08b4784`
- Branch: `codex/oip-2-situation-attention`
- Migration: `20260814_oip_situations`, parent `20260813_mdpm_readiness`
- Migration SHA-256: `EECA7653FFADD1F803D21CDD9B54E30FE81B7683F178FCE07080E25AD219204C`
- Policy catalog: SIG-OIP-001 through SIG-OIP-007 as recorded in the slice contract
- Projection: `oip-attention-v1`

## Validation evidence (2026-08-08)

- Single Alembic head: passed (`20260814_oip_situations`).
- Focused backend + operational + MDPM + migration regression: 51 passed after updating the asserted single head; focused OIP/migration rerun: 18 passed.
- Runtime migration safety: 22 passed.
- Full frontend suite: 111 passed. Production build and lint passed; lint retains 12 pre-existing warnings and the build retains its bundle-size warning.
- OIP tests prove: exact catalog, threshold abstention, configured detection, deduplication, explanation, evidence trace, DecisionContext, advisory-only recommendation, clear/reopen/history, version conflicts, reason/snooze rules, tenant isolation, and impossible-intelligence guards.

## Security and impossible-intelligence registry

Tenant lookup begins with membership and includes organization in every Situation query. Cross-tenant opaque lookup returns not found. Mutation permissions and expected versions are mandatory. Evidence is a bounded locator, not a copied payload. UI/API expose no OIP numeric IDs. Tests reject an eighth/predictive type and verify that financial exposure, carrier reliability, compliance score, predictive risk, and customer criticality are absent.

## Explicit limitations

- NEXT_MILESTONE_OVERDUE is inactive pending approved overdue tolerance and effective-time precedence.
- EXECUTION_UNIT_STALE is inactive pending approved freshness duration and clock rule.
- Live reconciliation currently adapts existing OperationalWorkItems and active Delay/Exception aggregates. MDPM, direct dependency, and execution-unit adapters need expanded fixture/integration coverage before promotion.
- Real PostgreSQL OIP race/rebuild suite, disposable upgrade/downgrade execution, authenticated browser UAT, RTL/LTR capture, OpenAPI parity, and full repository regression are not yet completed.
- Automatic snooze-expiry eligibility is implemented at queue read time; a scheduled projection refresh is not included.
- Claim is supported. Assign/reassign return an explicit ACTION GAP until an opaque operational-member identity contract exists; no numeric user identifier is accepted by the OIP API.

## Framework delta

PROJECT RESULT: the modular-monolith derived-intelligence pattern is viable and preserves operational authority.

FRAMEWORK DELTA: **PATTERN CANDIDATE**; this implementation confirms EAAF boundaries but supplies insufficient cross-project and PostgreSQL/browser evidence for framework promotion. No files in `D:\1-webapp\29-lpaf` were changed.

## Current decision

**OIP-2 IMPLEMENTED WITH EXPLICIT LIMITATIONS**

---

# Final promotion closure — CAND-FWD-OIP-2-PROMOTION-001

## OIP-D20 evidence (2026-08-08)

- Bound implementation commit: `414bae0269905ae61a1dcf82e7bd8101c9a5d7c5`.
- Bound implementation tree: `60431ab880d53338755df1ccd53883d7e95b5a51`.
- Architecture: [OIP-D20](../../adr/ADR-032-oip-projection-health-lifecycle.md), contract `oip-projection-health-v1`.
- Migration head: `20260816_oip_projection_health`, parent `20260815_oip_threshold_policy`.
- Migration SHA-256: `3EE88CD1E7A24B6CFC60C0C4BB20F113498B335F6AF520C2B2C8F5C2864B7EC5`.
- Threshold migration SHA-256: `B5DA78135E348B3604A0720B2B8EAF85E27820F31312FAE9A7DE6CAD6C855C1B`.
- OpenAPI SHA-256 before candidate commit: `C48D256525CE7F7AF27EFCA1FB06EE6F2FDD11901028C09BF07B3DA3D94046E3`.
- Projection/policy: `oip-attention-v1` / `oip-health-watermark-v1`.
- PostgreSQL: fresh disposable `oip2_gate_health_20260808`; full migration to head passed; 13-race plus rebuild/recovery suite passed (`14 passed`).
- Browser: authenticated disposable environment proved STALE, FRESH, active REBUILDING, DEGRADED (`REBUILD_FAILED`, sanitized), and recovery to FRESH. Queue/detail retained readable intelligence and operational controls. Clean matrix tabs had zero error-level console entries. Persian RTL and English LTR passed.
- Regression: OIP targeted `16 passed, 1 skipped`; full backend `582 passed, 47 skipped`; full frontend `111 passed`; production build passed; lint passed with 12 pre-existing warnings and zero errors.
- EAAF weakest mandatory link: all OIP-D20 mandatory implementation and local-validation links passed. No deployment, production access, or push occurred.

## Remaining accepted limitations

Opaque assign/reassign identity remains deferred; UNASSIGNED + Claim is supported. AI, Action Engine, financial, compliance, carrier, and predictive intelligence remain excluded. The active REBUILDING browser observation used a test-only pause after the real start commit; no timer or fake UI state exists in runtime/API.

## Framework delta

PROJECT RESULT: OIP-D20 closes trustworthy machine-health disclosure without crossing into operational truth.

FRAMEWORK DELTA: **REFERENCE EXAMPLE CANDIDATE**. Evidence supports an implementation reference, not an automatic EAAF philosophy change or reusable framework promotion.

## Promotion decision

**OIP-2 PROMOTION CANDIDATE READY**

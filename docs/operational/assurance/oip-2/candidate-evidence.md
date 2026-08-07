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

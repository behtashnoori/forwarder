# Test results

Date: 2026-10-01

Product candidate: `c22bbb0aeec434481b3e3fca21b6b75c74502318`

## Automated checks

- `python -m pytest backend/tests/test_execution_authority_3a.py backend/tests/test_guided_operational_projection.py backend/tests/test_organization_shipment_stages.py backend/tests/test_phase3_closure.py -q`: `63 passed`.
- `npm run test:frontend -- src/tests/components/ShipmentClosure.test.tsx src/tests/components/OperationalGuidance.test.tsx`: `2 files / 11 tests passed`.
- `npx tsc --noEmit`: passed.
- `npm run build`: passed; `2594` modules transformed.
- `npm run lint -- --no-cache`: passed with `0 errors`; `16` existing advisory warnings outside the changed behavior.
- `git diff --check`: passed.

## Owned browser/database qualification

- Runtime: owned disposable PostgreSQL 18 cluster and newly created database.
- Schema head: `20261015_org_shipment_stages`.
- Source: exact clean candidate; `dirty_source=false`.
- Browser: Chrome / Playwright, one end-to-end journey, `1 passed (21.6s)`.
- Proof: Closure, Summary, Task List, Attention, Next Action, explicit route occurrences, projected completion, explicit close, Unified History, tenant isolation, desktop, and 390px mobile.
- Cleanup: the runner stopped the owned PostgreSQL cluster (`postgres-stop.log`: `server stopped`) and removed its owned temporary runtime directory.
- Production access: false.

Candidate evidence is under `owned-postgresql-browser-candidate/`. An earlier iterative run is retained under `owned-postgresql-browser-preintegration/` and is not the publication basis.

## Preserved database verification

- Access method: read-only PostgreSQL 18 inspection and normalized data-only dump.
- Pre hash: `88D053B79E4B192004A6D6BC3A44F826A365446DCFB38760E7CB2AEB50021933`.
- Post hash: `88D053B79E4B192004A6D6BC3A44F826A365446DCFB38760E7CB2AEB50021933`.
- Business commands executed: `0`.

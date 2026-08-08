# FE-2 Candidate Evidence

Candidate: `FE2-SHIPMENT-ECONOMICS-CORE-20260808`  
Decision: ADR-033  
Migration: `20260817_shipment_economics_core` after `20260816_oip_projection_health`  
Contract: `fe-2-shipment-economics-slice-contract.md`

Evidence bindings:

- Money/stages/correction/FX/abstention/security/idempotency: `backend/tests/test_shipment_economics.py`.
- API runtime: `backend/routes/economics.py`; contract: `docs/openapi/openapi.yaml`.
- UI: `ShipmentEconomicsSection.tsx` embedded in opaque OperationalShipment detail.
- Migration: additive tables only, no data update/backfill; downgrade raises a fail-closed error.
- Quote-response regression: `backend/tests/test_customer_quote_response.py`.
- MDPM/OIP regression: existing suites; no economics import in MDPM/OIP modules and no financial OIP policy/situation added.

Validation recorded on 2026-08-08:

- Focused Economics plus quote-response/MDPM/OIP regression: 33 passed.
- Disposable local PostgreSQL: full lineage upgraded to FE-2 head; five economics tables verified; downgrade failed closed; database removed.
- Frontend production build passed; ESLint passed with zero errors (12 pre-existing warnings).
- In-app browser connection was available, but the local web server was not running (`connection refused`), so interactive RTL/LTR UAT was not claimed.

Known limitations: allocation and ERP references deferred; FX supports only contractual/manual-approved facts and does not fetch rates; no per-counterparty master is invented; the broader PostgreSQL financial race matrix and interactive browser UAT remain promotion gates.

Framework delta: confirms EAAF bounded ownership and weakest-link abstention; immutable economic observation and explicit-FX provenance remain pattern candidates. No framework repository modification.

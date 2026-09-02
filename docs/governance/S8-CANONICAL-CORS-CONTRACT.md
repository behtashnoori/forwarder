# S8 — Canonical CORS configuration contract

## Decision and root cause

Canonical production origin: `https://samand.forwarderet.ir`.

Governed P0 evidence supplied for this mission showed that Production currently
allows only `https://server.logisticmarket.ir` and rejects the canonical origin.
Production was not accessed or modified by S8.

Repository root cause: `get_configured_cors_origins()` previously selected
`CORS_ORIGINS or CORS_ORIGIN` without requiring the canonical origin or detecting
conflicting values.  A legacy-only environment therefore remained valid and
silently became the active CORS contract.

## Repair

- Production now requires the canonical origin and rejects the legacy origin.
- `CORS_ORIGINS` is the multi-origin form; `CORS_ORIGIN` is an equivalent
  compatibility alias only when it agrees. Conflicting non-empty values fail at
  startup.
- Wildcard/allow-all remains rejected in production; credentials remain enabled
  only for explicitly allowed origins.
- Startup output records environment, total origins, canonical-origin presence,
  and allow-all state without secrets.
- The production template makes the canonical origin explicit.

## Evidence

- Focused CORS/configuration tests: `16 passed`.
- Full backend: `850 passed`, `92 skipped`, `1 xfailed`, `0 failed`, `0 errors`,
  exit 0, `323.59s`.
- Frontend suite: `33` files and `156` tests passed.
- Frontend production build: passed.
- Secret scan and tenant/RBAC behavior remain unaffected.

## Release impact

`S7-RC-11ae2d2` is immutable historical evidence and does not contain this fix.
S8 changes runtime configuration validation and therefore requires a new source
candidate, full release-gate binding, artifact, manifest, and hash before any
separately authorized deployment.

Residual risk: legacy binding retirement and live canonical CORS verification are
separate infrastructure/pre-deployment work. S8 neither accessed nor changed
Production, IIS, DNS, certificates, environment files, or data.

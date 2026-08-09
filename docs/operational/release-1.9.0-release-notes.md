# Forwarder 1.9.0 — Integrated Operations Release

- Change type: MINOR
- Previous published version: 1.8.0
- Deployment type: backend-frontend-migration
- Production baseline: application 1.6.1 / `20260809_cargo_catalog_items`
- Final migration head: `20260818_immutable_fx_provenance`
- Status: Publication Preparation — Not Tagged — Not Published — Not Deployed
- Reference Data/Seed: administrator-managed; Production Seed executed: false
- Production: unchanged

The original 1.9 scope introduced bounded Operational Execution. The final
integrated publication boundary also contains separately governed MDPM document
readiness, deterministic OIP situations and projection health, Shipment
Economics with immutable FX provenance, opaque Shipment identity closure,
integrated browser/security certification repairs, and the declared PostgreSQL
runtime-driver dependency.

The complete Production upgrade range is
`20260809_cargo_catalog_items` through
`20260818_immutable_fx_provenance`. A restored clone of the actual Production
database completed that path and returned ready at head while preserving sampled
Production-derived counts. Production itself was not migrated or modified.

Existing shipments receive no automatic Operational Execution, MDPM, OIP, or
Economics rows. Reference Data and OIP policies/thresholds require separately
authorized administrator initialization. ACTUAL economics remains incomplete
when authoritative facts are unavailable. Allocation, ERP, external FX,
financial OIP, AI/predictive capability, and automatic workflow remain excluded.

The superseded pre-dependency candidate at `9bef5ee` remains historical evidence.
The dependency-closure commit `db29d4c` is also not the final tag target because
publication metadata/tooling changes follow it. The publication-preparation
commit containing this record is the candidate for later annotated tag
`v1.9.0`, subject to final review and authorization.

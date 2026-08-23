# China→Iran Global Logistics Point Catalog V1 — baseline owner decision

Decision date: 2026-08-23

Architecture authority: ADR-041 — Platform Global Logistics Point Catalog and Organization Adoption

## Decision

Launch China→Iran Global Logistics Point Catalog V1 with the nine currently ready points only. This is an intentionally minimal governed baseline, not approval of the broader 39-row candidate inventory and not authorization to seed Production.

- Approved package: `backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json`
- Approved checksum: `sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c`
- Approved row count: 9

Production seed authorized: **NO**

## Rationale

- Preserve strict global-point identity quality.
- Avoid forcing ambiguous city or hub records into facility identities.
- Avoid delaying the project for unresolved external verification.
- Allow incremental, controlled catalog growth from real operational feedback.
- Use Platform Admin governance for every later addition.

The other 30 candidates are **not rejected permanently**. They remain in the original candidate inventory for future governed review: 20 are `NEEDS_OWNER_DECISION`, and 10 are `NEEDS_EXTERNAL_VERIFICATION`. Their baseline disposition is `DEFERRED_FROM_INITIAL_BASELINE`; this decision-layer disposition does not rewrite their package review status or proposed runtime lifecycle.

## Approved baseline

| Immutable code | English name | Country | Type | Modes |
|---|---|---|---|---|
| GLP-CN-ALASHANKOU | Alashankou | CN | BORDER_CROSSING | ROAD, RAIL |
| GLP-CN-NINGBO-ZHOUSHAN | Ningbo-Zhoushan | CN | PORT | SEA |
| GLP-KZ-ALTYNKOL | Altynkol | KZ | RAIL_TERMINAL | RAIL |
| GLP-KZ-DOSTYK | Dostyk | KZ | BORDER_CROSSING | ROAD, RAIL |
| GLP-KG-IRKESHTAM | Irkeshtam Border Crossing — Kyrgyzstan Side | KG | BORDER_CROSSING | ROAD |
| GLP-TM-FARAP | Farap | TM | BORDER_CROSSING | ROAD, RAIL |
| GLP-TM-SERAKHS | Serakhs | TM | BORDER_CROSSING | ROAD, RAIL |
| GLP-IR-SARAKHS | Sarakhs | IR | BORDER_CROSSING | ROAD, RAIL |
| GLP-IR-INCHEH-BORUN | Incheh Borun | IR | BORDER_CROSSING | ROAD, RAIL |

## Baseline semantics

The baseline is production-candidate data, but is not a complete China→Iran network or an exhaustive corridor model. It exists to validate the full Platform→Organization→Expert workflow and can be extended without architecture changes.

Future additions must follow:

`candidate → evidence → owner review → Platform Admin governance → activation → organization adoption → materialization → operational use`

No legacy mapping row is created by this decision. No legacy ID or historical tracking data changes. Existing candidate relationships to `TrackingLocationReference` remain informational only.

## Future Production seed contract — prepared, not authorized

A future controlled apply must require all of the following:

- Exact package path: `backend/reference_data/global-logistics-points-china-iran-v1.0.0-approved-baseline.json`.
- Exact checksum: `sha256:08a7ca1fb17ae79964930cd47c019261b6952aa9542b2fc48ee09c7564690c7c`.
- Exact approved row count: 9.
- Authenticated Platform Admin identity.
- Explicit approval reference to this decision record.
- Separate plan and apply operations.
- Refusal on identity, code, checksum, or state conflicts.
- Persisted seed-run evidence and exact created/unchanged/conflict counts.
- Post-apply convergence, adoption, materialization, duplicate, and activation-gate checks.
- An approved rollback procedure and rollback approver.

Unless the accepted governed importer explicitly implements pre-reviewed governed activation, initial imported rows must be created as `DRAFT` / `UNVERIFIED`. Platform Admin governance must then move them through `REVIEWED` / `VERIFIED` / `ACTIVE`. Phase 2 governance must not be bypassed.

Production access, migration, seed, activation, deployment, and push remain unauthorized by this decision.

# S7 — Release Gate and candidate assurance

## Candidate identity and audit trail

The frozen deployable source is `11ae2d2d4f115d5fab2314e79b242fc0879dbec6` on `release-gate/s7-forwarder-candidate`. It is the S7-R1 report-ID repair commit, parented by S6 `921505a0275a8d601c5e9b3d0ddd41c4b6681a3d`. The earlier S7 regression stopped at 843 passed / 1 failed; it was not reused. S7-R1 proved the timestamp-only evidence-ID defect, added a collision-resistant suffix and exclusive writes, then passed 846 backend tests. The earlier incorrectly transcribed SHA `11ae2d2c1daea32b3dce2f54c4553c33dfebaa8c` does not exist.

## Gates

- Production-to-candidate delta includes bounded backend/frontend stabilization, tests, governance and the S7-R1 UAT tooling/test change; S7-R1 is not deployed application runtime.
- Candidate migration head and governed Production reference are both `20260907_direct_shipment_responsibility`: **NO_MIGRATION_REQUIRED**.
- Secret scan, safe backend import/route registration, migration metadata, full backend regression (846/0/0/92/1), frontend suite (33 files/156 tests), and production build all passed.
- S7-R1 does not touch Golden Business Journey runtime paths; S6 evidence remains valid and GBJ rerun is not required.
- Artifact: `Forwarder-S7-RC-11ae2d2.zip`, `1305636` bytes, SHA-256 `e6f81ada5ec7ba6664a5c849b52cce1b30dc992295c89e328eda9d08452184d8`.

## Risks and release decision

Accepted pre-release risks: browser E2E is unavailable; geographic catalog completeness is intentionally fail-safe (unusable countries are excluded); legacy/wildcard ingress and live CORS need redacted pre-deployment verification. Repository configuration supports explicit origins, but no live infrastructure claim is made. These do not evidence a tenant/security/migration/artifact defect.

The candidate is **READY_WITH_ACCEPTED_RISK** for a separately authorized deployment mission only. Use the exact artifact; do not silently rebuild. The evidence-pack contracts define rollback/roll-forward and production verification; failed deployment followed by rollback is **FAILED / RECOVERED**, never PASS.

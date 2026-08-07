# EVD-FWD-VAL-003 — Release 1.9 browser/security validation

| Field | Value |
| --- | --- |
| Candidate | `CAND-FWD-1.9.0-NEXT-RC-001` / `fa2871e0717a6062e5cb362eaaf4f751893d2c5a` |
| Produced UTC | 2026-08-07T16:44:00Z |
| Producer | Codex stabilization executor |
| Environment | Local Vite frontend and loopback-only disposable PostgreSQL UAT target |
| Evidence level / lifecycle | VERIFIED / ACTIVE |
| Downstream gate | Release 1.9 RC defect closure and S3 disposable rehearsal |
| Expiration | Candidate/frontend/API/fixture change, loss of authentication policy applicability, or evidence supersession |

## Verified results

- Admin authenticated using a synthetic account on `forwarder_phase1b_uat_eaaf_s3_20260807`.
- The operational list rendered customer, route, status, dates, milestone, and work count without visible shipment, quote, or request database IDs.
- The detail rendered route, timeline, checkpoints, exceptions, work, recent events, and audit areas without visible database IDs; checkpoint sequence and version remain business presentation values.
- The preview API result remained available despite independent auxiliary reads.
- With one active project milestone definition, the UI rendered `1 expected milestones` and enabled `Confirm initialization`.
- Confirmation on the disposable target created exactly one project-defined milestone and rendered `0% complete · 1 milestones`.
- The browser console contained zero errors after the corrected preview and initialization flow.

No screenshot, credential, token, cookie, or personal data was retained. The disposable write does not imply production readiness.


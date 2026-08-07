# MDPM-1 authenticated browser UAT — 2026-08-07

- Environment: disposable PostgreSQL cluster `instance/mdpm_validation_20260807_2215/pgdata`, loopback port `55449`, database `forwarder_phase1b_uat_mdpm_20260807_2215`.
- Seed lineage: `phase1b_uat + mdpm_validation_seed:v1`; manifest retained at `instance/mdpm_validation_20260807_2215/seed-lineage.json`.
- Authentication: synthetic `phase1b_uat_admin`; the local synthetic password was rotated only in this disposable database before the run and is not retained in evidence.
- Frontend/backend: local Vite and Flask development servers on loopback only.

## Results

| Contract | Result | Evidence |
|---|---|---|
| Missing required document | PASS | Server returned `DOC_ARTIFACT_MISSING` in the retained authenticated API sequence. |
| Associated but unapproved | PASS | Browser replacement produced `ASSOCIATED` and `DOC_APPROVAL_REQUIRED`. |
| Approved artifact | PASS | Browser approval changed readiness to `Ready for READY`. |
| Verification required | PASS | Retained authenticated sequence showed approval insufficient; verified artifact rendered `VERIFIED`. |
| Replacement reset | PASS | Browser replacement of an approved artifact rendered `ASSOCIATED` and blocked readiness. |
| Rejection | PASS | Browser rejection rendered `REJECTED` and `DOC_ARTIFACT_REJECTED`. |
| Controlled override | PASS | Browser granted the exact shipment/requirement/milestone/READY override; READY transition succeeded and advanced milestone version once. |
| Unauthorized override | PASS | Synthetic no-permission authenticated request returned 403; retained in `instance/mdpm_validation_20260807_2215/unauthorized-override-evidence.json`. |
| Conditional states | PASS | Retained sequence covers `UNRESOLVED`, `APPLICABLE`, and `NOT_APPLICABLE`; browser final state rendered `NOT_APPLICABLE`. |
| Stale version | PASS | An out-of-band requirement version increment followed by browser approval surfaced `Requirement was changed by another operation.` |
| Direction/language | PASS | Runtime DOM state was `fa`/`rtl`; language switch produced `en`/`ltr`. |
| Console | PASS | Zero browser console errors after authenticated MDPM flows. |
| Opaque MDPM identities | PASS | Artifact, requirement, milestone, and override controls use UUID public identities. |
| Containing route identity | PASS — CLOSED | Shipment list and work-queue navigation use `OperationalShipment.public_id`; authenticated list navigation produced `/operations/shipments/668da312-87de-4933-afd9-c23a2aeef993`, and direct load plus refresh retained that canonical opaque URL. |

## Opaque route remediation closeout

- Root cause: list, create, and work-queue navigation selected the internal `OperationalShipment.id`, while the legacy detail client accepted only a numeric identifier.
- Remediation: navigation now selects the existing `public_id`; the detail client uses the tenant-scoped `by-public-id/<uuid>` lookup. The aggregate identity and numeric persistence primary key were not changed.
- Security: authorized opaque deep link returned the shipment; the same public ID under the other synthetic organization returned the normal `RESOURCE_NOT_FOUND` 404 envelope.
- Browser proof: authenticated list navigation, direct deep link, and refresh all retained the UUID URL. Operational execution, Document Readiness, `Ready for IN_PROGRESS`, override-derived readiness, timeline, blocker, and document state loaded without a visible numeric shipment identity.
- Runtime proof: Persian `rtl` remained active; the earlier English `ltr` proof remains valid. A clean post-remediation proof tab recorded zero console errors.
- Legacy numeric browser route classification: **CLOSED**. Numeric persistence IDs remain implementation details for bounded legacy commands and are not canonical browser navigation identities.

The final authenticated screenshot is `final-authenticated-state.png` (SHA-256 `D87B2FE8A4FC8BAF3F2E6B368883A141C2E7C69F4D063CC9DADBD134549A986D`). Earlier request/response evidence remains under the disposable instance directory.

# FWD-05 amendment matrix

ADR final local SHA256: `76B91A53260AABB2DEE6A15AFF714050ABCD6806A428CD1DEDAAAB0CB0036F69`.
PDR final local SHA256: `6B7F4409294B8D025FE9BF4131686F951F497AF2634E84014AE58E06B4BBB330`.

All rows are reconciled decision text; runtime implementation is pending.

| Area | Original | Amended disposition |
| --- | --- | --- |
| Acceptance | PROPOSED, no authority | Named Owner ACCEPT_AS_EXPLICITLY_AMENDED; original bytes/source preserved |
| D01 authority | tracking writer; scoped grant proposed | bounded quote possession accepted; old writer retirement required, unimplemented |
| D02/D03 replacement | later publication/created_at supersession | explicit predecessor/effective chain; accepted replacement denied; declined replacement and negotiation finalization accepted |
| D03 display | unread/inbox proposed | independent quote response display/counters/query; no operational status effects |
| D04 money | integral BIGINT only | quote-major.v1 EUR/USD <=2 decimals; IRR integer rial; NUMERIC(21,2), exact strings, strict scale/range and explicit N-1 unsupported |
| D04 legacy | codes preserved | original values/codes unchanged; legacy-unspecified unit; no conversion/rounding/backfill |
| D05 admin | narrow zone proposal | usable audited organization admin IANA setting; missing-zone Persian reason; immutable zone/policy/deadline snapshot |
| Recipient | certified link/BLOCKED proposed | truthful ready/queued/simulated/failed/unknown/BLOCKED current-assignee follow-up; no fake remediation; onboarding dependency OPEN |
| D06 grant | 30 days/reissue proposed | max(publication,expiry)+30 days; reissue revokes without extending; superseded reads only own receipt |
| Reference 28 | mapping needed before Build | NOT_PROVEN; pilot-only access deferral; recovery/review at slice end or before real release |
| Modularity | owner contracts and event separation | Commercial/Authorization/Notification/Adapter ownership retained; Agent never customer writer/approver |
| Qualification | Security and full product gates pending | 18 primitive probes +14 baseline tests PASS; Security review, full runtime/PG/browser/migration/regression unqualified |

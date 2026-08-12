# MT-1 real parent-link cohort reduction

## 1. Parent-link package integrity

All three authoritative hashes match: CSV `57265f19...12bce6`, JSON
`7b400ff3...cf5df3`, summary `50f9613c...b6fef`. The package declares read-only
extraction, no completion DB access, no PII, assignment, inference, or
quarantine change.

## 2. Graph construction methodology

Nodes are only `(entity_type, entity_id)` stable pairs from the original review.
Edges come only from the 289 CSV records. Canonical observed dependency fields
are followed transitively; duplicate identical FK evidence is collapsed, while
conflicting edges, cycles, absent canonical parents, external breaks, and null
canonical parents fail closed. Repository guesses never create edges.

## 3. 135-row graph coverage

Exactly 135 unique original rows are represented, with no missing or injected
child. There are 20 ordinary roots, one platform singleton, 82 mandatory proven
descendants, 31 conditional proven descendants, and one unproven descendant.

## 4. Internal vs external vs null parent edges

Of 289 records, 229 are present-parent observations, 39 are null-parent
observations, and 21 are root/singleton markers. Of the 229 present observations,
126 point to Census rows and 103 to external structural rows. Duplicate identical
`ShipmentRequestLog` observations are retained as evidence records but represent
one mechanical edge per row.

## 5. Root components

There are 21 proven root components: 13 ShipmentRequest components, Customer:1,
six CustomerGamification roots, and ReferralAutoAssignState:1. The broken
DocumentAuditEvent:1 is separately reviewed and is not assigned a fabricated
root.

## 6. Proven descendant paths

All 82 mandatory descendants have unique complete paths. Thirty-one conditional
rows have a present request path: 29 ExpertConsoleNotification rows and
DocumentAuditEvent:2 and :3. Proof paths are enumerated per member in the v2
plan and re-derived by the validator.

## 7. Broken/unproven paths

DocumentAuditEvent:1 has a null ShipmentRequest parent. Its other external actor
and definition references cannot substitute for the canonical disposition root,
so it remains `DESCENDANT_UNPROVEN` and individual.

## 8. Per-entity structural result

ShipmentRequest (13), Customer (1), and CustomerGamification (6) are
`ROOT_DECISION`. CaseDocumentRequirement (2), ExpertConsoleLog (29), ExpertQuote
(3), ReferralAssignmentLog (12), ShipmentRequestLog (13), ShipmentTracking (6),
ShipmentTransportUnit (6), and ShipmentTransportUnitUpdate (11) are
`DERIVED_DESCENDANT_PROVEN`. ExpertConsoleNotification (29) and
DocumentAuditEvent:2-3 are `CONDITIONAL_DESCENDANT_PROVEN`;
DocumentAuditEvent:1 is `DESCENDANT_UNPROVEN`. ReferralAutoAssignState:1 is
`PLATFORM_OR_SINGLETON_REDESIGN`.

## 9. Safe multi-member cohorts

The 13 ShipmentRequest root components are safe multi-member disposition
cohorts. Exact members and complete paths are stable and enumerable. The eight
other proven roots and the one broken row remain singleton cohorts: nine total.

## 10. Unsafe cohort examples

Type-only grouping, assignee grouping, external-user grouping, substituting an
external actor for a request root, merging different ShipmentRequests, or
tenantizing ReferralAutoAssignState are prohibited.

## 11. Original vs reduced human decision count

The original 135 events reduce to a minimum of 22 disposition events: 13
ShipmentRequest component decisions plus nine singleton decisions. Expansion
must still emit 135 explicit row decisions.

## 12. Organization inheritance prohibition

Organization assignment inheritance is `NO` for every structural class. Parent
links prove dependency only, never ownership.

## 13. Remaining human work

Humans must review all 22 events with two-person approval. Customer:1 is not
auto-retired. DocumentAuditEvent:1 needs individual evidence. No review fields
are prefilled.

## 14. MT-1 readiness

`MT1_OWNERSHIP_RESOLUTION_READY=false`

`AUTO_BACKFILL_ALLOWED=NO`

`QUARANTINE_MUST_REMAIN=YES`

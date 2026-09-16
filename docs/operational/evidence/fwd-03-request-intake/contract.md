# FWD-03 implementation contract (2026-09-16, before validation code)

Commercial owns normalization, validation and display projection. New public
`POST /api/v2/shipment-request` invokes the same command with the server-selected
v2 contract; a body flag cannot select weaker validation. Legacy
`POST /api/shipment-request` remains scalar-compatible. Supplying intent on either
path invokes the new intent rules. Both paths require nonblank cargo on final
creation. No persisted Draft or cargo/transport update command exists: focused
route/service searches found only creation and status/assignment/CRM/tracking
mutations. This slice adds no transport edit endpoint or new edit permissions.

| Input case | Normalization | Validation | Persisted value | Read projection | Error / compatibility |
| --- | --- | --- | --- | --- | --- |
| v2 customer_choice, omitted/null/empty intent | no inferred choice | explicit nonempty steps required | none on failure | none | TRANSPORT_INTENT_REQUIRED / INVALID_TRANSPORT_INTENT |
| v2 forwarder_suggestion, omitted/null | null | valid preference | SQL NULL | no ordered choice; historical scopes if any | accepted |
| road/sea/road or road/road | exact order/repetitions | version 1, exact keys, supported active catalog modes | identical JSON | ordered labels, combined / single-mode | accepted |
| combined selection with one distinct mode | no deduplication | at least two distinct modes | none | none | TRANSPORT_CLASSIFICATION_MISMATCH field error |
| single-mode selection with multiple distinct modes | no deduplication | exactly one distinct mode | none | none | TRANSPORT_CLASSIFICATION_MISMATCH |
| bad shape/version/mode | no coercion of shape/version | reject unknown fields, booleans, unsupported modes | none | none | stable reason + field |
| transport_sequence | no alias (only prior probe evidence) | reject explicitly | none | none | UNSUPPORTED_TRANSPORT_FIELD |
| legacy scalar only | trim; existing generic lowercase preserved | known code/name alias or active exact custom catalog name | original scoped scalars; intent NULL | generic / international / domestic labels separately | no fabricated order |
| intent plus generic scalar | resolve documented alias | generic scalar must describe the whole single-mode intent | both if compatible | intent primary | combined or different mode is TRANSPORT_INPUT_CONFLICT |
| intent plus domestic/international scalar | resolve known mode | each scope value must occur in intent; neither implies step position | both if compatible | intent primary; historical scopes retained | absent/unknown mode is TRANSPORT_INPUT_CONFLICT |
| unknown historical code / blank old cargo | no write | no new-write validation on reads | unchanged | original text in original scope | readable; no guessed meaning |
| old client status/assignment mutation omits intent | existing narrow command | existing state/authority/concurrency rules | intent untouched | same ordered projection | no transport update supported |
| client sends transport fields to a non-transport mutation | no implicit transport update | explicitly reject field attempts at existing status command | unchanged | unchanged | TRANSPORT_UPDATE_NOT_SUPPORTED; null is not omission |
| PUT/PATCH request transport | no route added | unsupported method/path | unchanged | unchanged | 404/405; no lost update through a new editor |
| blank/whitespace/nonstring cargo on final create | trim valid string only | required on both API paths | none on failure | old records still readable | CARGO_DESCRIPTION_REQUIRED |

Catalog mapping evidence: `backend/seed_transport_methods.py` describes Land
Transport explicitly as road; Road Transport as road; Rail Transport as railway;
Air Freight/Air Transport as air; Sea Freight as sea. Canonical legacy codes
road/rail/air/sea also occur in `backend/models.py` and referral contracts. These
exact case-insensitive aliases are supported. No translation-based/fuzzy mapping.
The two seeded Rail Transport rows have identical name, Persian name and
description. The new mode selector aggregates known aliases into one mode option
with all active catalog IDs, preserving every catalog row. Unknown custom names
remain in legacy catalogs/reads but are not offered as a guessed v1 intent mode.
New intent writes recheck an active mapped catalog row for every selected mode.

Legacy response scalar fields retain scope and are never synthesized from intent.
An additive `transport_summary` includes ordered steps/labels, classification,
legacy scopes, and explicit `legacy_display_limited` for combined intent.
Unchanged clients may ignore that field and cannot be claimed to display intent.
Controlled customer/expert screens use the same Commercial projection. Preparation
validates using the owner service, without storing a Draft or granting submission;
submission repeats validation and trusted-host tenant resolution.

No temporal columns added. Existing timestamps/dates keep their contracts.
Migration predecessor rechecked: sole head `20260916_fwd01_notifications`.
One nullable JSON column; no backfill. Downgrade locks PostgreSQL request table,
checks for any non-null intent before DDL, then drops only when empty of intent.
Application rollback retains column/data. All qualification DBs disposable/local.

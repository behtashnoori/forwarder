# ADR-048 Amendment M1 — durable manual time entry for FWD-06

- Status: PROPOSED; acceptance NOT_RECEIVED.
- Date: 2026-09-16 (Asia/Tehran).
- Owners: Architecture / Operations / Product / Security / Data roles; no person invented.
- Scope: FWD-06 compatibility tracking manual entry and minimum associated persistence only.

## Context and verified identity

Root D:/1-webapp/forwarder-dev; existing branch feature/fwd-06-tracking-timeline; HEAD 0e14d3df7d8d2b704eb7f37138dd09850d9fc9a9; upstream origin/feature/fwd-06-tracking-timeline; origin https://github.com/behtashnoori/forwarder.git; one worktree, initially clean. Existing continuation reports and acceptance were read and preserved.

ADR-048 remains ACCEPTED_FOR_BOUNDED_FWD06 with SHA256 3A0934566E785C71DD244C403212757E9A2272C01D7960ABE74D0917DB65A7A1. This amendment does not reopen that acceptance. LPAF v2.2 remains GLOBAL_ACTIVE. The mother index, active main/entry and v2.4 identity re-attestation were read; v2.4 current hash verified as 217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397, OWNER_APPROVED / PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE. Existing focused pilot discovery is reused. Mother reference impact NONE; project reference impact UPDATE_REQUIRED after named acceptance. Reference28 mapping remains NOT_PROVEN under the existing bounded deferral; no time/security waiver.

The Owner continuation explicitly confirms the product direction Asia/Tehran for manual input, regardless of browser or event location. It explicitly does not accept an unknown technical ADR. The Accepted business register and ADR-016 were read in full. The roadmap is not migration authority.

## Exact current clauses and proposed amendments

Current TIME-BIZ-007 (Accepted, time-business-decision-register.md):

> Use the actual event Location's IANA timezone. If Location is unknown, require explicit timezone. Browser timezone is not authoritative. Override requires permission, reason and audit; preserve occurrence, recording time, source and provenance. External timestamps require an offset.

Current TIME-BIZ-011 (Accepted):

> Without a known Location, explicit timezone selection is mandatory; no browser/server-zone guess is allowed.

Proposed additional exception to BOTH clauses (their general rules remain unchanged):

> For FWD-06 authorized manual entry only, the input wall clock is interpreted in Asia/Tehran under immutable tracking.manual-iran.v1 policy, explicitly displayed as «زمان ورود به وقت ایران — تهران». This is an Owner-approved manual-input policy, not a claim about the event Location timezone and not a per-event Location override. The declared policy is sufficient when Location or Location timezone is unavailable. Persist the declared wall clock, input basis, source and policy with the resulting UTC Instant in the owning event transaction. This exception grants no permission to select another input timezone. API/import/Agent input remains explicitly offset-bearing and must not inherit the manual default. Display timezone selection never changes input authority or stored meaning.

Current ADR-048 decision 8 affected exact text:

> نیاز اثبات‌شده به تصحیح، schema تازه یا تغییر lifecycle با تصمیم نام‌دار جدا متوقف شود.

Current ADR-048 migration consequence affected exact text:

> schema change در طراحی فعلی پیش‌بینی نمی‌شود؛ sole head واقعی `20260916_fwd05_quote_response` است.

Proposed narrowly replacing the no-new-schema effect for M1 only:

> For FWD-06 only, permit one explicit additive migration after 20260916_fwd05_quote_response adding five nullable fields to shipment_transport_unit_update: occurred_at_utc (DateTime(timezone=True)), time_input_wall (String(29)), time_input_basis (String(64)), time_input_source (String(32)), time_input_policy (String(64)). All five are absent for historical rows, without defaults or backfill. New manual writes require all five; new offset-bearing machine writes require the first four and leave the manual policy null. Preserve existing occurred_at as a UTC-naive compatibility mirror for new validated writes only and created_at as system recording time. No new owner, correction command, lifecycle, historical conversion or Production migration is authorized.

The other eight-point invariants remain in force. In particular ADR-048's proven-legacy-UTC authorization remains limited to update.created_at; it is not expanded to historical occurred_at or other fields. Historical occurrence values without independent proof stay explicitly unknown in new presentation; existing raw history is preserved.

## Requirement → source → direction → implementation → gap → action

| Requirement | Accepted source | New direction | Existing implementation / gap | Required action |
| --- | --- | --- | --- | --- |
| Manual input basis | TIME-BIZ-007/011; ADR-016 | Explicit server Tehran default | RequestDetail initializes browser-local now; localDateTimeInputToUtc uses browser zone; conflicts with Location priority | Accept exception above; owner policy query and server wall-clock resolution; blank occurrence input |
| Durable provenance | TIME-BIZ-007; roadmap phase 3 | Preserve actual input meaning | Update has occurrence, recording, actor and location snapshots, no input basis/source/policy | Accept minimum additive migration; persist on event itself |
| Foreign report | TIME-BIZ-007 permission/reason/audit | Only accepted override authority | No tracking timezone override authority found in targeted backend search; unrelated operational overrides are insufficient | Do not implement foreign-zone manual override; show precise unavailability; offset-bearing machine source remains distinct |
| Calendar / display | ADR-016; FWD-04 shared presentation | Persian/Gregorian, selected display zone | Existing presentation.ts dual calendar formatter; no second input date SOR | Extend shared presentation/input seam; one Gregorian local date value; reuse established calendar tooling; server conversion is authority |
| Recording / occurrence | ADR-048 clause 5 | System recording, required real occurrence | Existing update.created_at system UTC-naive; no provenance field | Keep created_at alias; aware new canonical occurrence; reject missing/naive machine input |
| Replay / historical read | ADR-048 clauses 5–7 | No reinterpretation after policy change | Existing receipt model can hold result identity, not event provenance SOR | Reauthorize before replay, fingerprint fixed input/policy, return stored result; leave old provenance unknown |

## Decision: ownership, API and storage

Tracking owns policy resolution, event persistence, eligibility, summaries and receipts. Geography continues to own location resolution/snapshots. Shared presentation owns calendar/display conversion; UI and future Agent consume commands/queries. No new policy table, Evidence engine, notification policy or model API is introduced.

Authorized manual command supplies Gregorian-normalized local wall time and exact policy identifier, not browser-derived UTC. Server obtains trusted tenant/actor/assignment context and resolves wall time with IANA rules exactly once. Missing policy, invalid calendar/time, nonexistent or ambiguous local time fail explicitly; no now fallback. Manual client must not spoof machine input to obtain foreign-zone authority. Offset-bearing machine command is a distinct source contract, retains its submitted wall clock and numeric offset basis, and does not infer an IANA location zone. If both explicit Instant and wall/basis are supplied, inconsistency fails closed. Policy changes never alter stored snapshots or replay results.

The five event columns are the minimum proposed typed snapshot: canonical Instant avoids extending legacy occurrence provenance; wall + basis preserve original interpretation; source separates manual and machine; policy identifies this exact Owner direction. No speculative override fields are added because override is unavailable. Constraints enforce either all-null legacy envelope, complete manual envelope, or complete offset-source envelope (policy null). Source/basis lengths and allowed shapes are validated by Tracking. Compatibility occurred_at is a derived mirror, not a second editable truth.

Event columns share event identity, tenant envelope, append-only write, transaction and existing event retention. No receipt, internal_note, temporary audit log or browser state serves as provenance SOR. Existing actor reference remains governed by its retention/SET NULL contract; no human identity is reconstructed. No independent provenance deletion or retention job is added. Receipt and operational effect remain atomic and retain ADR-048's no-expiry rule.

Internal query may expose authorized time basis/source/policy; public query exposes only allowlisted occurrence/recording display values, never actor, tenant, internal note, private catalog, receipt internals or policy audit. Counts/last_recorded_at/pagination derive solely from their authorized visible scope. No sensitive public identity is added for future document/map joins.

## Alternatives and consequences

No schema plus formatter fails durable provenance. Receipt JSON/internal_note/log storage violates event ownership and retention. A provenance platform or canonical cutover exceeds this mission. Five additive event fields preserve the required minimum without migrating history. Cost: explicit migration and dual compatibility/canonical occurrence writes for new events; atomicity and mirror consistency require tests.

## Compatibility, operational impact and rollback

Migration is executed only against an identified disposable test database after acceptance. No startup migration, historical backfill or Production access. Backend reads retain historical unknown envelopes; old offset-bearing clients without key preserve append semantics, gain no replay guarantee, and their new input receives offset-source snapshots. Old naive machine input is rejected as already required by ADR-048. Application rollback retains schema, event snapshots and receipts. Database downgrade refuses before DDL whenever any new snapshot exists; an empty disposable fixture can downgrade. No destructive rollback or historical timestamp conversion.

## Validation after acceptance

Qualify actual disposable DB, synthetic ordinary actors, upstream legal commercial transition, backend and browser timezone override before claiming any runtime evidence. API under test is real, no Production or real dispatch. PostgreSQL migration upgrade/empty downgrade/populated refusal and existing-row byte preservation; policy/Location changes must not reinterpret stored or replayed events. Native receipt races, payload conflict, rollback and authority revocation. Browser UTC/America_New_York with identical Tehran input; Persian/Gregorian round-trip and calendar switch; Tehran/other display of same Instant without mutation; missing/invalid/ambiguous/nonexistent time and offset mismatch negatives. Reopen/login/logout, late/tied/private history, global visible last-recorded time, query failure versus empty, subject duplicate input preservation, four optional physical-reference types, public leakage and tenant negatives. Relevant FWD01–05 regression and architecture/secret/diff checks; only then mission commits, push and fetched remote verification. Separate security reviewer only if the actual gate requires one.

## Supersession and requested decision

Supersedes only the TIME-BIZ-007/011 manual-input application and ADR-048 no-new-schema restriction described above, and only upon acceptance. All other Accepted rules and gaps remain unchanged. Status history: 2026-09-16 PROPOSED in response to explicit Owner continuation. Runtime implementation, migration, UAT and PostgreSQL qualification NOT_RUN. NOT_PASS_CONTROLLED_LOCAL_FWD06.

Requested exact decision: «ADR-048 Amendment M1 — durable manual time entry for FWD-06 را با همین متن و Hash ارائه‌شده، فقط برای توسعه و آزمون محلی FWD-06 می‌پذیرم.»

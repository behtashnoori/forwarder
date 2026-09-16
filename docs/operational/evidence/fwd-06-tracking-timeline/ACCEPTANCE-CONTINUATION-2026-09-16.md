# FWD-06 bounded acceptance continuation — 2026-09-16 (Asia/Tehran)

This is a separate continuation of the existing checkpoint. README.md and FINAL-REPORT.md retain the prior BLOCKED_OWNER_ADR_DECISION record unchanged. No runtime implementation, schema, historical data or mother-framework change was made in this continuation.

## Identity and accepted decision

Root D:/1-webapp/forwarder-dev; branch feature/fwd-06-tracking-timeline; starting HEAD 19f96a8355e34676a2934632a8dba5bb7409fd4e; upstream origin/feature/fwd-06-tracking-timeline; origin https://github.com/behtashnoori/forwarder.git. One existing worktree; initially clean. FWD05 ancestor 29630f9ee255b9b0189124b4d41fb262422e53f9 verified with merge-base --is-ancestor exit0. No new branch, reset, clean, forced stash/checkout, amend or history rewrite.

The actual ADR proposal bytes matched A3FFFEAA2C364B5073410B67ACD1943DC22139CB1895809F9E2F4A5956875FD3 before modification. Exact bytes are preserved as ADR-048-PROPOSED.md. Owner explicitly accepted the unchanged eight-point decision as ACCEPTED_FOR_BOUNDED_FWD06. No supplied human identity; none invented. Current ADR SHA256: 3A0934566E785C71DD244C403212757E9A2272C01D7960ABE74D0917DB65A7A1.

Mother impact NONE. LPAF v2.2 remains GLOBAL_ACTIVE; v2.4 OWNER_APPROVED / PILOT_ADOPTION_ALLOWED / NOT_GLOBAL_ACTIVE; current v2.4 hash 217BDB9DFF2B4FE42A127B4F15831DB17439A703CA4D4702D299B804CD7C0397 verified. Existing focused discovery is reused rather than rereading archives. Active v2.2 main/entry were read, with rigor B for material local product qualification and applicable Mission/Understand/Domain/Solution/Verify controls. Project impact UPDATE_REQUIRED: ADR lifecycle, current ADR index and append-only baseline/decision-index acceptance records updated. Reference28 mapping remains NOT_PROVEN under the already authorized bounded deferral.

## Narrow stop: unresolved accepted time-policy application

FACT: ADR-016 is Accepted and explicitly says business-policy implementation remains phased; it links the Accepted Time Business Decision Register and implementation roadmap. This is important: the roadmap is not authorization to activate every phase immediately.

FACT: TIME-BIZ-007 says: "Use the actual event Location's IANA timezone. If Location is unknown, require explicit timezone." It also requires permission, reason and audit for an override and preserved occurrence, recording time, source and provenance. TIME-BIZ-011 rejects browser/server-zone inference without known Location.

FACT: roadmap phase 3 (Tracking Time Provenance) lists Canonical Location timezone/external contract prerequisites and additive source, zone and audit migration. ADR-048 prohibits schema, new lifecycle/correction and out-of-scope authority changes. The mission explicitly requires reporting a disagreement if an executable criterion changes another active contract; it forbids inventing the missing decision.

FACT: LogisticsPoint has no local timezone column. Its optional global_point relationship can reach GlobalLogisticsPoint.timezone_name, but that field is nullable and privately authored/manual points need not have a global parent. The tracking selector does not expose a timezone resolution contract. Country/city, product display timezone and host timezone cannot prove an actual event zone.

FACT: ShipmentTransportUnitUpdate has occurred_at, created_at, actor ID and location snapshots, but no event timezone/source-zone or override reason/authorization snapshot. Existing append API accepts occurred_at only; UI initializes it with host-local now and localDateTimeInputToUtc uses the browser zone. These are existing gaps, not new defects introduced here.

UNKNOWN / DECISION NEEDED: whether phased TIME-BIZ-007 zone/provenance storage and override handling are intentionally deferred for this bounded legacy UI while explicit, valid IANA input resolution is implemented, and whether a known private point with unavailable timezone may use explicit selection without constituting an override. ADR-048's accepted text does not expressly reconcile those policy details. No technical impossibility of a timezone picker is asserted. An explicit timezone picker can resolve an Instant; that alone does not prove compliance with the complete existing Location/override/provenance policy.

A schema migration is NOT proven necessary for the bounded picker alone. It would be necessary for dedicated missing zone/override snapshots if phase-3 preservation is mandatory here; no such migration is authorized. No data was placed into internal_note, an unrelated log or receipt payload to evade this boundary. No blanket policy waiver or new architecture decision was created.

STOP_CONDITION: ambiguous timestamp / changed active-contract meaning under CODEX-DEVELOPMENT-GATE Failure behavior and mission sections 2,5,9. Runtime Build stopped before changing the timestamp contract. Clarification must reconcile the phased accepted time policy with the bounded no-schema implementation; acceptance of ADR-048 itself does not need repeating.

## Receipt feasibility and retained scope

OperationalIdempotency already supports organization + operation + resource_type + command_resource_id + key uniqueness, request_hash, result_resource_id and response_json; result identity has no tracking-specific FK. Existing advisory transaction locking is scoped. No receipt schema blocker was discovered. No public receipt contract or tracking coordination has yet been implemented or qualified. Its existing consumers and retention behavior remain unchanged.

Current compatibility owner remains multi_unit_tracking_service on ShipmentRequest/ShipmentTracking/ShipmentTransportUnit/ShipmentTransportUnitUpdate. Allowed bounded contracts are assigned-expert create/append/read, internal history, public customer-visible snapshot allowlist plus recorded times and limited receipt reuse. Canonical OperationalShipment/RouteLeg/ExecutionUnit ownership and ADR040 cohort/lineage gates remain unchanged. No cutover, dual write, correction, historical migration, real provider, GPS/map, product Agent/LLM or Production authority.

## End-of-attempt legacy exception review

Actual use in this continuation: proposal identity verification, acceptance/lifecycle recording, contract/model/authorization/receipt feasibility inspection only. Legacy runtime extension NOT_IMPLEMENTED. This is a blocked attempt review, not a claim that the complete FWD-06 end-of-mission gate passed. Remaining debt: canonical mapping/cohort migration, phased event-zone/provenance policy, all required implementation/qualification. Review still due at completed FWD-06 end or before actual release; no later mission automatically authorized. Ending development authority does not delete data or automatically disable existing tracking. Reference28 deferral is retained for this mission; not extended to another.

Historical replay BLOCKED_MISSING_EXTERNAL_EVIDENCE; Production identity UNKNOWN; Reference28 mapping NOT_PROVEN; onboarding OPEN; real customer delivery NOT_READY. No gap closed by acceptance.

## Qualification and reproducibility

Product tests, PostgreSQL races/rollback/reauthorization, timezone runner, Browser UAT and FWD01–05 runtime regression: NOT_RUN for this continuation; required scope not waived. Prior 36PASS/native prerequisite evidence remains solely baseline characterization. No correction capability claimed. Documentation checks below cannot establish product PASS.

Run from D:/1-webapp/forwarder-dev:

```powershell
python -B scripts/check_architecture_governance.py
python -B scripts/scan_repository_secrets.py current
git diff --check
Get-FileHash docs/operational/adr/ADR-048-bounded-legacy-tracking-timeline.md
Get-FileHash docs/operational/evidence/fwd-06-tracking-timeline/ADR-048-PROPOSED.md
```

Check outcomes and actual commit/fetched Git identities are recorded in CONTINUATION-GIT-VERIFICATION.md and the final response. Logs remain outside Git in an owned temporary evidence directory. No production DB, session, raw capability, secret or bulky log is committed.

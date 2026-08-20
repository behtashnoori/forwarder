# Codex Development Gate

This gate is mandatory for every future Codex implementation task in Forwarder.

## Before implementation

Codex must report and complete:

- [ ] Read `FORWARDER-ARCHITECTURE-BASELINE.md`.
- [ ] Read `ADR-INDEX.md` and each affected ADR in full.
- [ ] Identify affected domains and ADRs.
- [ ] Identify canonical models and owners.
- [ ] Identify legacy models and compatibility paths.
- [ ] Identify tenant authority and authorization source.
- [ ] Classify all changed temporal values as Instant, Local Date, Business Local DateTime, Duration, or Recurrence.
- [ ] State whether schema/data migration is required.
- [ ] State whether the request changes architecture.

If architecture change is required, STOP BEFORE IMPLEMENTATION. Produce a PROPOSED ADR using `ADR-TEMPLATE.md`. Do not treat the task prompt, code edit, or passing tests as ADR acceptance.

## Architecture-change triggers

Stop for new/changed aggregate ownership, canonical model, tenant boundary, timestamp contract, document ownership, cargo ownership, master-data authority, API authority semantics, legacy-to-canonical movement, destructive history, or new cross-domain writes.

## During implementation

- Keep writes inside the authorized aggregate/application service.
- Derive tenant identity from trusted context/parent ownership.
- Preserve compatibility and immutable history.
- Prefer opaque public identity and stable error contracts.
- Use explicit idempotency/version controls where relevant.
- Add migration, rollback, audit, and tenant-negative tests proportionate to risk.
- Do not broaden scope to repair unrelated drift.

## After implementation report

Every completion report must include:

- architecture rules checked;
- ADRs followed;
- canonical models used;
- legacy models touched and why;
- tenant isolation and cross-tenant tests;
- timezone/storage/serialization checks;
- migration compatibility, head state, and rollback behavior;
- tests and static checks executed;
- architecture deviations: `NONE` or an explicit accepted list;
- Production access/deployment/push status.

## Failure behavior

A missing decision, uncertain tenant owner, ambiguous timestamp, disputed canonical model, or Proposed-only ADR is a governance blocker—not permission to choose a convenient implementation.

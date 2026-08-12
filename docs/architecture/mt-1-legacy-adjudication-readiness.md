# MT-1 legacy adjudication readiness

## Real census observed

- 135 UNRESOLVED and 135 QUARANTINED rows.
- Zero Organization candidates, no authoritative lineage, no mapping, and no
  invalid-lineage reason in the transferred census package.
- All 13 ShipmentRequest roots lack project, customer, and request-user lineage.
- The assignee membership path yields zero Organizations: there are no active
  operational memberships and no legacy memberships for assignee users
  20–23. Assignee identity is therefore not ownership evidence.
- Customer 1 is an orphaned root and the Customer table has no organization ID.
- Automatic ownership assignment is prohibited.

`MT1_OWNERSHIP_RESOLUTION_READY=false`

`HUMAN_DECISIONS_REQUIRED=YES`

`AUTO_BACKFILL_ALLOWED=NO`

`QUARANTINE_MUST_REMAIN=YES`

MT-1 may resume only after reviewed human decisions, valid Organization IDs for
assignments, two-person approval, mapping/schema validation, zero unresolved
active rows if full active-row resolution is required, analyzer rerun with the
approved mapping package, PostgreSQL certification, and independent security
review. Only then may a separate migration/backfill design be considered.

## Mapping schema compatibility

The current `legacy-tenant-mapping.schema.json` faithfully represents an
approved organization assignment and append-only predecessor history, but it
cannot represent decision classes that intentionally have no target
Organization (`KEEP_QUARANTINED`, `RETIRE_INACTIVE_LEGACY_ROW`,
`REDESIGN_REQUIRED`, `NEEDS_MORE_EVIDENCE`). It also requires a target even for
`PENDING_REVIEW`.

A future backward-compatible v3 should retain every v2 assignment field and add
an explicit `decision_class` union: the assignment branch requires
`target_organization_id`; non-assignment branches prohibit it and preserve
quarantine/disposition. Historical v2 meaning must remain unchanged. No schema
change is made now because there are no approved decisions to translate, and
premature evolution could be mistaken for mapping authorization.

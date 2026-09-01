# S2 Document Policy and Snapshot Propagation

## Decision

The UAT observation is **DOMAIN_BEHAVIOR_CORRECT with a UX semantic risk** in
the reviewed path. Current organization policy controls future resolution;
case and operational-shipment requirements are historical runtime evidence.
A policy edit does not rewrite existing runtime requirements.

## Terms and source of truth

| Term | Proven meaning |
| --- | --- |
| Active definition | Platform vocabulary eligible for resolution. |
| Policy | Tenant row with `REQUIRED`, `OPTIONAL`, `CONDITIONAL`, or `DISABLED`. |
| Disabled | Excluded from future effective policy; not optional. |
| Optional | Effective, potentially non-blocking runtime requirement. |
| Snapshot | Immutable case/operational requirement for one record. |
| Incomplete | Runtime readiness/artifact/assessment status, not current policy. |
| Effective requirement | Project override, then active explicit organization policy, then compatibility fallback. |

`DocumentDefinition` is platform vocabulary. `OrganizationDocumentRequirement`
is tenant policy. `ProjectDocumentRequirement` is a tenant-project override.
Case and operational requirements, files, associations, assessments, and
readiness projections are record-specific evidence.

## Flow, timing, and decision table

Admin UI → policy API → membership-derived tenant policy →
`effective_definitions` → case initialization or shipment materialization →
expert readiness API/UI. A successful policy write is effective at the next
resolution/materialization; no cache or effective-date model was found.

| Current policy | Timing | Snapshot | Runtime visibility/readiness |
| --- | --- | --- | --- |
| REQUIRED/OPTIONAL | after resolution | created | snapshot level drives readiness |
| DISABLED | before resolution | none | no new requirement or readiness contribution |
| DISABLED after snapshot | existing record | preserved | original snapshot level/status remains |
| Project override | project resolution | created after resolution | override wins and is snapshotted |

## Invariants and evidence

1. Disabled policy creates no fresh effective requirement.
2. Existing snapshots are not silently rewritten; they preserve auditability,
   document association, and traceability.
3. Optional and disabled are distinct.
4. Readiness derives from runtime requirements, not a later policy edit.
5. Organization policy and project override are tenant-fenced.

The S2 regression performs the admin API change and consumes it through case
requirement initialization: REQUIRED creates a historical snapshot; DISABLED
removes it from fresh effective resolution; a fresh case has no row; the old
row remains unchanged. Existing tests cover tenant isolation, compatibility
fallback, optional policy, and project precedence.

## Remediation and residual risk

No runtime/API/data/migration change is justified: the current implementation
satisfies the proven invariant. The residual UX risk is that expert readiness
shows a runtime snapshot without an explicit "historical snapshot/current
policy independent" label. Address presentation only in a separately approved
frontend UX slice with its test tooling available.

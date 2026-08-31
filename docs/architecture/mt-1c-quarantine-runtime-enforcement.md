# MT-1C quarantine runtime enforcement

**Status:** BLOCKED — tenant data integrity no-go.

## Implemented foundation

`backend/quarantine.py` introduces a persistent ownership-certification scope and decision registry, kept separate from tenant assignment. It supplies centralized SQLAlchemy read criteria, legacy Query count/aggregate and bulk-DML hooks, explicit object assertions, mapped parent-reference checks, and a decision-aware analytics cache token. Current public tracking returns the existing non-disclosing 404 for a denied ShipmentRequest, and case-document routes check request/file metadata before storage resolution. The migration adds no tenant key and does not implement MT-2 or redesign MT-3.

Once an entity census is activated, missing metadata fails closed for the entire entity type, including rows created after the recorded watermark. With no activated census, legacy v1.9.1 behavior remains unchanged because MT-1C has not loaded or invented real ownership decisions.

## Validation completed

- Focused SQLite adversarial tests exercise explicit deterministic, quarantined, invalid-lineage, conflict and missing states; public numeric/code containment; bulk mutation filtering; new-child rejection; and census cache versioning.
- A loopback-only disposable PostgreSQL 18.0 integration verified root filtering, missing covered metadata, public numeric/code containment, normal deterministic data and transaction rollback. The test dropped its schema and the cluster was stopped; sandbox policy prevented removal of the stopped temporary data directory at `C:\Users\pc\AppData\Local\Temp\forwarder_mt1c_pg_d94fd05cf63743c5bea773fee12e78c1`.
- Backend regression: 681 passed, 66 skipped, 1 expected failure. The expected failure remains the MT-3 tracking characterization.
- Python compile, touched-file Ruff, `git diff --check`, architecture tests and Alembic sole-head checks passed. The sole head is `20260820_mt1c_quarantine_runtime`.
- The release tag remains `v1.9.1` at peeled commit `05414d7d5b17153c3f1efcb5beff0adf7a600af6`; no Production access, deployment, or push occurred.

## Independent security-review blockers

The initial focused test labels did not constitute proof of all real surfaces. Independent review found these remaining blockers:

1. `project_party_relationship` uses a composite analyzer identity but the runtime registry currently accepts only a numeric `entity_id`; analyzer/runtime coverage is therefore incomplete.
2. Analyzer `UNRESOLVED + quarantine_status=QUARANTINED` cannot be imported faithfully by the current runtime classification schema, and no atomic analyzer-result loader exists.
3. Existing descendants are filtered by their own decisions. A clear notification/document/quote can survive a later quarantine decision on its root unless all descendant decisions are atomically republished; that atomic mechanism is not implemented.
4. Held identity-map instances can bypass a subsequent read decision, and `before_flush` does not yet reject mutation of the quarantined root itself.
5. Updating a decision in place can leave `(max decision_epoch, decision_count)` unchanged, allowing a warm analytics cache result to survive. Decisions need immutable/versioned publication or enforced epoch advancement.
6. Real endpoint/job/report/export/storage/CLI tests and broader PostgreSQL transition/concurrency coverage remain incomplete.

Therefore every mandatory matrix row remains `pass:false`. `QUARANTINE_RUNTIME_CERTIFIED=false` and `MT1_OWNERSHIP_RESOLUTION_READY=false`. No completion commit is permitted.

## Remaining work

Use analyzer-compatible string/composite resource identities and separate classification from quarantine status; implement one atomic, versioned census publisher; make descendant predicates follow the actual root graph at read time; guard held-instance reads and root mutations; make cache invalidation transactionally mandatory; then execute the real 15-surface adversarial suite on PostgreSQL before requesting another independent review. Complete approved legacy mappings/conflict adjudication and active/inactive policy are still required after MT-1C and must not be inferred.

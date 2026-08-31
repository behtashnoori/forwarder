# MT-1B Legacy Ownership Certification

**Status:** BLOCKED — MT-1 resume is a no-go  
**Scope:** certification tooling and quarantine contract only; no MT-1 schema migration or MT-2/MT-3 behavior

## Ownership fixpoint

The SELECT-only analyzer requires every declared table and lineage column for all 28 `LEGACY_AMBIGUOUS` inventory entries; a partial schema is a coverage error rather than a successful empty result. `Project.organization_id`, `OperationalShipment.organization_id`, non-null `ExpertQuote.operational_organization_id`, reviewed mappings, and the direct organization keys on `ArtifactAssociation` and `EconomicEvidenceAssociation` are authoritative seeds. The two association paths allow document conflicts to be discovered rather than hidden. Mechanical lineage reaches a fixpoint before mapping is considered, so a mapping cannot manufacture its own candidate set. Evidence paths are symbolic and contain stable IDs only; no PII is selected or emitted.

A seedless cycle remains `UNRESOLVED`; a cycle may transmit an existing authoritative seed but cannot invent one. Classification happens after convergence: structural failure is `INVALID_LINEAGE`, zero candidates is `UNRESOLVED`, one is `DETERMINISTIC`, and more than one is `CONFLICT`. There is no precedence or default tenant.

`INVALID_LINEAGE` includes a missing required parent value, a populated relationship whose row is missing even when the FK is nullable, a missing/dangling required direct owner, and a populated parent whose required lineage is invalid. Structural invalidity converges before candidate propagation; an invalid parent cannot lend apparently safe ownership to a descendant. It is never downgraded to unresolved and blocks readiness.

## Mapping and decision history

Mapping format v2 records stable entity/type IDs, target Organization, reason, distinct operator/reviewer identities, timestamp, version, immutable decision ID, optional superseded-decision reference, and `ACTIVE`, `SUPERSEDED`, `REJECTED`, or `PENDING_REVIEW`. Draft 2020-12 JSON Schema validation runs before semantic validation. Semantic validation rejects missing entities/Organizations (including all conflict candidates), duplicate IDs/versions, non-contiguous or cross-entity history, non-monotonic instants, invalid states, and same-person review. The effective state is the immutable chain tip; an older ACTIVE decision is superseded by linkage and is not rewritten in place.

Ordinary mapping does not override competing candidates or disagreeing lineage. Explicit conflict adjudication must include the complete competing candidate set, an evidence reference, and policy version. Historical entries remain in the artifact; correction is a new version and never an in-place rewrite. Artifact signing and authorization-directory validation remain future operational controls and cannot be claimed by this slice.

## Quarantine contract

Every non-deterministic row has `quarantine_status=QUARANTINED`. `ReferralAutoAssignState` is **QUARANTINE_UNTIL_REDESIGN** because its global singleton has no authoritative organization relationship. The machine-readable matrix is `mt-1b-quarantine-exclusion-matrix.json`.

The current application does not have a central quarantine predicate or staging table. Consequently list/detail/search/selectors/reports/exports/jobs/notifications/documents/public tracking/admin/cache/join paths are not mechanically proven to exclude quarantine. All matrix entries remain false. This is an intentional fail-closed result, not a request to implement MT-2 or MT-3. Public tracking remains `PUBLIC_CAPABILITY_SCOPED + TENANT_ISOLATION_DEFECT`.

## PostgreSQL certification

An isolated PostgreSQL 18.0 cluster was initialized under the OS temporary directory, bound only to `127.0.0.1:55439`, with database `forwarder_mt1b_cert_20260811`. The installed service on port 5432 was not connected to or modified. The full declared analyzer schema was created only in the disposable cluster. A separate analyzer transaction used `SET TRANSACTION READ ONLY`, proved `transaction_read_only=on`, and rejected mutation with SQLSTATE `25006`. Scenarios A-I and K-M passed. Scenario J is BLOCKED because no application-surface quarantine guard exists, so overall PostgreSQL certification remains false. Evidence: `mt-1b-postgresql-evidence.json`.

## Evidence-generated readiness

`evaluate_readiness()` is the only flag generator. It no longer accepts caller-supplied PASS booleans: it validates the exact quarantine-surface set, PostgreSQL A-M evidence and read-only proof, and an independent structured security-review classification. Missing, partial, extra, or non-PASS evidence fails closed. The CLI always emits this evaluated readiness object and has no ready override.

Current evidence evaluates to `MT1_OWNERSHIP_RESOLUTION_READY=false`: the quarantine matrix is not implemented across application surfaces, active-row policy remains undefined per legacy model, and complete approved mapping/data evidence is absent. Therefore MT-1 must not resume.

The independent post-change review is recorded in
`mt-1b-security-review-evidence.json` and returns
`MT-1B SECURITY REVIEW — BLOCK`. It confirms that coverage, mapping-candidate
contamination, alternate witnesses, and raw boolean readiness inputs were
hardened, but does not accept the remaining self-asserted evidence provenance
or string-only reviewer/policy authority as certification.

## Remaining blockers

- Implement and characterize a reusable quarantine exclusion control on every matrix surface without an admin, join, cache, worker, document, or public-tracking bypass.
- Define versioned per-entity active/inactive predicates; only approved inactive history may remain quarantined.
- Produce approved mapping history and repair every active invalid lineage/conflict.
- Run and retain isolated PostgreSQL A–M evidence.
- Obtain an independent post-implementation security PASS.
- Anchor evidence to its generator/test artifacts and approved reviewer/policy
  authorities; hand-authored PASS-shaped JSON must not be sufficient.

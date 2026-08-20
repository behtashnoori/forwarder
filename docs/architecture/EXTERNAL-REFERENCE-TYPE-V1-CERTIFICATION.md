# External Reference Type V1 Non-Production Certification

- Status: CERTIFIED — production apply is not authorized
- Date: 2026-08-20
- Repository baseline: `8277e293b4fff70c071b5a0e702f3e730105b6cb`
- Authority: ADR-039, ADR-021, and ADR-028
- Scope: governed type catalog only; no operational values or public exposure

## Reviewed package

The reviewed package is
`backend/reference_data/external_references/external-reference-types-v1.0.0.json`.
It uses schema version `1`, catalog version `1.0.0`, contains exactly three
definitions, and has canonical checksum
`sha256:462a61225b8ecce9050aa5c7e257dc4e789e47cfafb9f2f6f5175b9024b9fc43`.
Two independent checksum calculations matched.

| Code | Owners | Normalization | Search | Uniqueness | Lifecycle |
| --- | --- | --- | --- | --- | --- |
| `BILL_OF_LADING_NUMBER` | OperationalShipment | `TRIM_UPPERCASE_V1` | `PREFIX` | `OWNER` | `ACTIVE` |
| `AIR_WAYBILL_NUMBER` | OperationalShipment | `TRIM_UPPERCASE_V1` | `EXACT` | `TENANT` | `ACTIVE` |
| `CMR_NUMBER` | OperationalShipment, ExecutionUnit | `TRIM_UPPERCASE_V1` | `PREFIX` | `NONE` | `ACTIVE` |

The package records reviewed UN/CEFACT or UNECE provenance. It excludes
`COTAGE_NUMBER`, `WAREHOUSE_RECEIPT_ID`, `REGISTRATION_ORDER_NUMBER`,
`BARFARABARAN_REFERENCE`, and every other future type.

## Harness repair

The first certification attempt stopped after a successful non-production
apply because an ad hoc verification harness used a wildcard import and then
called `_expected_row`. Python wildcard imports omit underscore-prefixed names
unless the module explicitly exports them through `__all__`, so the helper was
not bound and verification raised `NameError`.

The repaired read-only harness explicitly imports `_expected_row`; the package
engine and reviewed package semantics were not changed for this repair. A
focused regression test proves database-equivalence verification executes
without wildcard-import dependence.

## PostgreSQL certification

Certification used disposable loopback PostgreSQL 18.0 database
`forwarder_extref_cert_resume_20260820_02` on `127.0.0.1:5432`. The server was
not in recovery and the database was migrated from empty state to sole Alembic
head `20260903_external_operational_references`.

The fresh read-only plan produced:

- CREATE: 3
- NO_CHANGE: 0
- UPDATE_COMPATIBLE: 0
- CONFLICT: 0
- database fingerprint:
  `sha256:e68aba8d250d7d7f9553a70c66e9ede1131db6704145c46a5862684c8ad42ec1`

All catalog, apply-run, shipment reference, execution-unit reference, shipment,
unit, request, document-policy, file, and association counts were unchanged by
PLAN.

One explicitly confirmed testing-environment apply used a new idempotency key,
named operator, test approval reference, reviewed checksum, and fresh plan
fingerprint. Run `cdb581d0-3be8-4a31-8855-766e32634e4a` succeeded with three
creates and zero conflicts.

## Equivalence and side effects

All three persisted rows exactly matched the normalized package projection for
code, bilingual names, lifecycle, normalization, search, uniqueness, masking,
owner applicability, and persisted provenance/source fields. Every row had
revision 1. There were zero unexpected type rows, shipment reference values,
or execution-unit reference values.

The before/after protected-table matrix showed zero package-induced changes to:

- ShipmentRequest
- OperationalShipment
- ExecutionUnit
- OrganizationDocumentRequirement
- ProjectDocumentRequirement
- CaseDocumentRequirement
- OperationalDocumentRequirement
- CaseDocumentFile
- ArtifactAssociation

## Idempotency and negative controls

The exact same key and request replayed the original successful run without a
new semantic mutation. A fresh plan returned NO_CHANGE=3. Applying the unchanged
package with a new key succeeded harmlessly with zero creates; type count stayed
three and all revisions stayed 1.

Each of these controls was rejected with zero semantic database delta:

1. wrong expected checksum;
2. modified package with old checksum;
3. stale plan fingerprint;
4. reused idempotency key with different request;
5. missing confirmation;
6. missing operator;
7. missing approval reference;
8. unsupported fourth type;
9. invalid owner applicability;
10. invalid uniqueness policy;
11. invalid search policy; and
12. duplicate type code.

## Transaction rollback and convergence

A separate disposable database received a controlled failure after transactional
catalog work began. No type or protected row survived. The intentionally
preserved apply-run record was `failed` with a sanitized error summary. The
rollback database was dropped after verification.

The final main-database plan produced CREATE=0, NO_CHANGE=3,
UPDATE_COMPATIBLE=0, and CONFLICT=0 with fingerprint
`sha256:bdde051da1dce7f4c94fdecd487aa4a120674f96c0465481c1f92c8a2ed03cc7`.

## Regression and operational boundary

Focused package, harness, operational-reference, tenant/search, and architecture
tests passed. The full backend suite passed with 794 tests passed, 82 skipped,
and one expected failure. Python compilation, changed-scope Ruff, diff checking,
sole-head verification, architecture governance, and repository secret scanning
were required before the certification commit.

Both disposable databases were deleted. No PostgreSQL server or cluster was
created for this work. Production apply, production access, production database
access, deployment, release, tag, push, and public/customer exposure did not
occur and are not authorized by this certification.

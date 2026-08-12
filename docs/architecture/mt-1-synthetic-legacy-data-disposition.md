# MT-1 synthetic legacy data disposition

## Authoritative provenance record

This record applies only to the 135 rows identified by the hashes in
`legacy-adjudication/legacy-synthetic-disposition-manifest.json`. On 2026-08-12,
the human repository owner explicitly classified every one of those rows as
test/synthetic data, not customer or tenant business data.

```text
DATASET_CLASSIFICATION=SYNTHETIC_ONLY
LEGACY_REAL_CUSTOMER_DATA_PRESENT=NO
HUMAN_OWNERSHIP_ADJUDICATION_REQUIRED_FOR_THIS_DATASET=NO
AUTO_TENANT_ASSIGNMENT_ALLOWED=NO
SYNTHETIC_DATA_MAY_BE_DISPOSED_ONLY_BY_EXPLICIT_POLICY=YES
REAL_DATA_CENSUS_REQUIRED_IF_REAL_LEGACY_DATA_IS_EVER_INTRODUCED=YES
LEGACY_SYNTHETIC_ADJUDICATION_STATUS=NOT_APPLICABLE
```

This classification is dataset-bound. It is not an inference from row shape,
empty lineage, environment name, or lack of Organization candidates. It cannot
be copied to another census: analyzer acceptance requires the independently
observed census hashes and row count to match this manifest. Unknown provenance
fails closed. An approved real
non-Production clone remains subject to the complete census, ownership mapping,
quarantine, validation, PostgreSQL certification, and security-review path.
Production ownership and tenant fences are unchanged.

## Historical adjudication evidence

The earlier census, parent-link analysis, and 22-event cohort projection were
technically valid while provenance was unknown. The later human assertion makes
that workflow not applicable to this dataset; it does not make the earlier work
incorrect. Existing review packages remain immutable historical evidence and
must not be populated with Organization IDs or represented as pending customer
ownership work.

`MT1_OWNERSHIP_RESOLUTION_READY=false` retains its original meaning: the rows
have not acquired real tenant ownership. It must not be changed to true for a
synthetic exemption.

## Allowed disposition policy

| Disposition | Bound | Assessment |
| --- | --- | --- |
| `KEEP_QUARANTINED_SYNTHETIC` | Preserve all rows and current fences | Safest default; selected now |
| `RETIRE_SYNTHETIC_DATA` | Separate approved local/test retirement workflow | No deletion is authorized here |
| `RESET_SYNTHETIC_ENVIRONMENT` | Recreate only an explicitly identified non-Production environment | Requires separate approval and verification |
| `ARCHIVE_SYNTHETIC_FIXTURE` | Sanitized, access-controlled fixture with hashes | Must not become ownership evidence |
| `REGENERATE_FROM_CANONICAL_TEST_FIXTURES` | Replace only through a reviewed, reproducible fixture contract | New census/hash binding required |

The selected default is `KEEP_QUARANTINED_SYNTHETIC`. It performs no destructive
action. Any later retirement, reset, archive, replacement, or quarantine change
requires an explicit policy decision scoped to a verified non-Production target.
This document emits no cleanup SQL and grants no Production or server-database authority.

## Gate semantics

```text
LEGACY_DATA_PROVENANCE_CLASSIFIED=true
LEGACY_DATASET_CLASSIFICATION=SYNTHETIC_ONLY
REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED=false
SYNTHETIC_LEGACY_DISPOSITION_READY=true
MT1_REAL_DATA_GATE_APPLICABLE=false
MT1_OWNERSHIP_RESOLUTION_READY=false (not applicable; not redefined)
QUARANTINE_RUNTIME_CERTIFIED=true
MT1C_FULL_SURFACE_CERTIFIED=true
```

`SYNTHETIC_LEGACY_DISPOSITION_READY=true` means the safe non-destructive default
has been selected. It does not approve cleanup. MT-1 may continue past the
dataset-specific real-ownership branch while quarantine remains. Discovery or
introduction of any real row invalidates this manifest and reactivates the full gate.

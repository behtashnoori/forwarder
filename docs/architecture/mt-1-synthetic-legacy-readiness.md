# MT-1 synthetic legacy readiness

## Plain-language decision

**What did we find?** 135 legacy rows: 135 unresolved, 135 quarantined, and zero
Organization candidates.

**Are they real customer data?** No. The human repository owner authoritatively
classified all 135 as synthetic/test data.

**Do they need Organization ownership mapping?** No. **Should Organization IDs
be invented?** No.

**Should quarantine protections be weakened?** No. The safe default is
`KEEP_QUARANTINED_SYNTHETIC`.

**Do the prior 22 human adjudication events still need completion?** No, not for
this dataset. They are historical evidence produced under unknown provenance.

**What must happen before destructive cleanup?** Separate explicit synthetic
cleanup approval, bound to a verified non-Production target.

**What if real legacy data is later discovered?** The synthetic exemption ends;
a fresh real-data census and full ownership-resolution path become mandatory.

**Can MT-1 continue?** Yes, past the real-data ownership-adjudication branch for
this exact hash-bound dataset. This is not a claim that ownership was resolved.
Quarantine and certified tenant fences remain required; no cleanup is approved.

```text
LEGACY_DATA_PROVENANCE_CLASSIFIED=true
LEGACY_DATASET_CLASSIFICATION=SYNTHETIC_ONLY
LEGACY_SYNTHETIC_ADJUDICATION_STATUS=NOT_APPLICABLE
REAL_LEGACY_OWNERSHIP_ADJUDICATION_REQUIRED=false
SYNTHETIC_LEGACY_DISPOSITION_READY=true
MT1_REAL_DATA_GATE_APPLICABLE=false
MT1_OWNERSHIP_RESOLUTION_READY=false (semantic status: NOT APPLICABLE)
QUARANTINE_RUNTIME_CERTIFIED=true
MT1C_FULL_SURFACE_CERTIFIED=true
```

The separate provenance gate fails closed: UNKNOWN provenance, malformed
assertions, Organization candidates, or active mappings reject the exemption.
A real non-Production clone remains on the real ownership path.

## Independent security review

Adversarial review confirmed that the exemption is explicit and dataset-bound;
UNKNOWN is not synthetic; candidates and active mappings invalidate synthetic
acceptance; classification cannot mutate rows, clear quarantine, or trigger
cleanup; Production authority is absent; real-data readiness and tenant fences
are unchanged; and prior evidence remains present.

`MT-1 SYNTHETIC LEGACY DATA SECURITY REVIEW — PASS`

`MT-1 SYNTHETIC LEGACY DATA CLASSIFIED — REAL OWNERSHIP ADJUDICATION NOT APPLICABLE`

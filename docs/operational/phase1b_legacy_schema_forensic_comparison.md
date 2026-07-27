# Phase 1B legacy schema forensic comparison

## Final forensic conclusion — 2026-07-27

The completed comparison establishes that Main remains at legacy revision `54ea21ea0d9f` and no active candidate is canonically equivalent to it. Consequently stamp and legacy-marker approaches are rejected, and fresh active-head creation plus controlled data transfer is required. Phase 1B implementation/UAT is complete; database cutover and automated mapping are deferred. No persistent database, Main, or server change occurred.

`PHASE_1B_IMPLEMENTATION_COMPLETE / PHASE_1B_DATABASE_CUTOVER_DEFERRED / FRESH_TRANSFER_REQUIRED / AUTOMATED_MAPPING_DEFERRED / MAIN_DATABASE_UNCHANGED / SERVER_UNCHANGED`

## Candidate evidence gate — 2026-07-27

The verified main fingerprint is available, but all five candidate fingerprint
outputs and their SHA-256 files are absent. Exact per-category deltas for
tables, columns, keys, constraints, indexes, and sequences therefore remain
unknown. No equivalence claim or nearest-revision ranking is authorized.

See `phase1b_candidate_materialization_comparison.md` for the evidence inventory
and isolation record.

`PHASE_1B_BRIDGE_TOPOLOGY_DECISION_BLOCKED`

# Phase 1B legacy reconciliation strategy

## Final selected strategy — 2026-07-27

Phase 1B product implementation and UAT are complete. No active candidate is canonically equivalent to the unchanged Main database at `54ea21ea0d9f`; stamp and legacy marker are rejected. The selected future strategy is a fresh database migrated to active head `20260801_route_exception` followed by controlled data transfer in a separate gate.

The operational assessment proved source read-only/rollback, target migration, inventory hash, explained migration/system baseline, and cleanup with `disposable_remaining=false`. Mapping failed at the native analysis child with exit `1` (`NATIVE_FAIL:ANALYSIS:1`) and is deferred. No transfer, persistent migration, seed, stamp, deploy, Main write, or server change occurred.

`PHASE_1B_IMPLEMENTATION_COMPLETE / PHASE_1B_DATABASE_CUTOVER_DEFERRED / FRESH_TRANSFER_REQUIRED / AUTOMATED_MAPPING_DEFERRED / MAIN_DATABASE_UNCHANGED / SERVER_UNCHANGED`

## Candidate evidence gate — 2026-07-27

No reconciliation strategy has been selected. Missing candidate fingerprints
prevent proof that the main schema is equivalent to, or deterministically
reconcilable with, any of the five active revisions. A no-op marker, controlled
reconciliation plus stamp, and fresh-database transfer remain alternatives for
a later gate; none is authorized here.

The next gate requires complete run-token-bound outputs, matching SHA-256 files,
per-candidate final-revision evidence, and cleanup evidence. It must then derive
exact sanitized deltas and semantic risk before selecting a topology.

`PHASE_1B_BRIDGE_TOPOLOGY_DECISION_BLOCKED`

# S7-R1 — Phase 1B UAT report-ID collision repair

## Trigger and scope

S7's full backend regression failed at
`test_validate_only_and_dry_run_never_execute`: a validate-only report was
silently overwritten by the immediately following dry-run report.  This repair
is limited to Phase 1B evidence-report identity and its tests.  No application
workflow, frontend, migration, business data, production system, or release
artifact was changed.

## Reproduction and root cause

The runner path was:

`main` → UTC timestamp token → `P1B-UAT-<token>` → `<run_id>.json` / `<run_id>.md`
→ `Path.write_text`.

The timestamp was formatted to microseconds, but it was the only identity
component.  Back-to-back calls can receive the same observable wall-clock value;
this was reproduced by running the full Phase 1B runner test file, where the
test failed intermittently, and by the original full S7 regression.  A repeated
file run could also pass, confirming that the symptom was nondeterministic rather
than a valid uniqueness guarantee.

Root-cause classification: **TIME_PRECISION_DEFECT**.  The persistence path used
overwrite-capable writes, so a collision caused silent evidence loss.  This is an
evidence-integrity defect, not an assertion issue.

## Invariant and repair

Each evidence-producing invocation must have a distinct, stable run identity and
must never silently replace an existing report.  Safe modes remain non-executing.

- The readable UTC timestamp is retained.
- A `secrets.token_hex(8)` per-execution suffix makes the run ID collision
  resistant even when the clock value is fixed or repeated.
- Report files are created exclusively (`"x"` mode).  Any pre-existing JSON or
  Markdown path raises `HarnessError` rather than being overwritten.

The filename shape remains `P1B-UAT-<timestamp>-<suffix>.json` / `.md`; consumers
continue to receive the paths emitted by the runner and report contents retain
their `run_id` and mode.

## Proof

| Check | Command / method | Result |
| --- | --- | --- |
| Back-to-back safe modes | Fixed-clock test runs validate-only then dry-run | Two distinct IDs, two retained reports, correct modes, neither executes actions. PASS |
| Existing identity | Call `write_reports` twice with the same ID | Second call raises; original evidence remains validate-only. PASS |
| File order | Phase 1B runner test file, repeated | `14 passed` on each post-fix file run. PASS |
| Neighbor sequence | Runner file plus Phase 1B seed tests | `22 passed`. PASS |
| Full backend regression | `D:\\Projects\\webapp\\15-forwarder\\.venv\\Scripts\\python.exe -m pytest -q` | `846 passed`, `92 skipped`, `1 xfailed`, `0 failed`, `0 errors`, exit 0, `385.75s`. PASS |

## Compatibility and residual risk

No schema, data, frontend, package, or production configuration contract changed.
The suffix intentionally makes report names unique rather than relying on
timestamp-only names; emitted report paths remain the authoritative consumer
contract.  Cryptographic-token collision is negligibly probable and exclusive
creation still prevents silent replacement if one occurs.

S7 remains separately stopped: this repair restores the regression gate but does
not package a release candidate or alter the previous S7 result.

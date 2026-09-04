# D2 r4 operator contract

This package carries the frozen application ZIP and the separately immutable `Forwarder-Windows-Runtime-S7-RC-a257669-r4.zip`. Verify both package manifests and hashes before any use. `deploy_a257669_r4.ps1` requires explicit `-Execute -ConfirmDeployment`, approved read-only preflight and backup evidence, and host paths supplied at invocation; it never uses an undocumented production path.

The candidate extracts its runtime only to `release-S7-RC-a257669-rg1-frozen\runtime\python.exe`. Migration and Scheduled Task activation use that exact path. A failure after migration restores the captured task and IIS release/runtime, proves the previous listener, and never downgrades the database.

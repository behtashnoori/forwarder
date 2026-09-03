# REQ-4A — IIS provider forensic qualification

## Scope and decision

This is Development-only release-tooling work under LPAF v2.1. Production was
not accessed, connected to, changed, or deployed. IIS, Windows features,
Scheduled Tasks, profiles, and machine-wide PowerShell configuration were not
installed or changed on NARGES. The frozen S7 application candidate remains
immutable.

The exact-byte R6-final3 Production run (1,281,884 bytes, SHA-256
`ca165077f68cd9cf1efba68dc177cc0142c5efc94ee8599fa9cfe73aebcd2a3a`)
proved the REQ-3 database and Alembic corrections, passed through PRECHECK 103,
then failed with `Cannot find drive. A drive with the name 'IIS' does not
exist.` It remained `ABORTED_BEFORE_MUTATION` and `NO_GO`. This authoritative
Production evidence replaces a local exact reproduction requirement.

Exact local reproduction is impossible without changing the Development
topology: NARGES is not the governed host, the session is not elevated, IIS and
WebAdministration are absent, and the Production filesystem and Scheduled Task
do not exist. Installing or fabricating that topology was rejected. A controlled
harness proves the tooling contract; only R8 read-only Production ValidateOnly
can prove real IIS integration.

## Root cause and REQ-3 escape

R6 `Get-IisReference` dereferenced
`IIS:\Sites\forwarder` without discovering or importing WebAdministration and
without verifying its provider or drive. A fresh child `powershell.exe` process
does not inherit a parent's imported modules or PSDrives, so the raw provider
exception escaped the intended gate.

REQ-3's “64/64” was not a fixed path manifest. `Env-Map` issued one numbered
`Require` for every configuration line. The small fixture contained fewer
lines than Production, so Production ordinals exceeded 100. In addition,
SimulationRoot and QualificationRoot substituted `iis.txt`, bypassing the real
IIS branch. The tests therefore qualified the DB parser but neither clean-shell
IIS initialization nor the complete Production dependency path.

R8 removes per-line ordinal inflation for duplicate-key detection and emits the
expected, executed, and passed totals at the successful end of ValidateOnly.
The expected total is independently selected from a fixed branch registry:
normal operator mode 49, SimulationRoot 39, and controlled QualificationRoot
59, plus the explicitly classified optional singular-CORS gate. The qualified
harness therefore requires exactly 60/60/60. GO is emitted only when expected,
executed, and passed are equal and the final manifest marker is present.

## Clean-process and IIS contract

The package wrapper always starts a new Windows PowerShell 5.1 child with
`-NoProfile`. Normal mode performs the following sequence before any IIS path
access:

1. discover WebAdministration;
2. explicitly import it with terminating errors;
3. discover the WebAdministration provider;
4. discover the IIS drive;
5. verify the governed site;
6. read physical path, site state, and bindings with governed error handling.

Missing module, import failure, provider, drive, site, path, or bindings becomes
`PRECHECK_FAILED`, `ABORTED_BEFORE_MUTATION`, and `NO_GO`. ValidateOnly contains
no IIS setter invocation before its mutation boundary.

## Controlled harness and bypass isolation

The operator wrapper exposes no `QualificationRoot` parameter. The internal
entrypoint accepts the test seam only when both a dedicated qualification root
and the process-scoped `FORWARDER_REQ4A_HARNESS=REQ-4A-CONTROLLED-HARNESS`
authorization are present. Its versioned `iis-contract.json` models each
prerequisite transition independently; it does not reduce the sequence to one
Boolean. Normal package execution cannot accidentally activate it and still
retains host and Administrator admission.

The harness proves `HARNESS_IIS_CONTRACT_PATH=PASS`; it does not claim a real
provider ran. `REAL_IIS_PROVIDER_TEST=NOT_AVAILABLE_ON_NARGES` remains an open
integration item for Production ValidateOnly.

## External dependency map

| Path | Dependency | Classification |
|---|---|---|
| Wrapper | package manifest, SHA-256, SystemRoot PS5.1 | explicitly validated; governed failure |
| ValidateOnly | filesystem C: paths and frozen artifacts | explicitly validated; governed failure |
| ValidateOnly | production.env and URL parsing | explicitly validated; governed failure |
| ValidateOnly | psql executable, exit code, tagged scalars | explicitly validated; governed failure |
| ValidateOnly | ScheduledTasks module and governed task | explicitly initialized/validated; governed failure |
| ValidateOnly | WebAdministration/provider/IIS drive/site | explicitly initialized/validated; governed failure |
| ValidateOnly | site path/state/bindings | read-only, explicitly validated; governed failure |
| ValidateOnly | TCP listener, HTTP health, disk | explicitly validated; governed failure |
| Execute | Expand-Archive, env/task/IIS setters | after explicit mutation boundary |
| Verification | release files, health and CORS | explicitly validated; governed failure |
| Rollback | env backup, task XML, IIS path, target directory | exact-restore checks; recovery state reported |
| All paths | registry provider | not used |

Execute and rollback retain intentional IIS and Scheduled Task mutation only
after `MUTATION_BOUNDARY_REACHED`; they are exercised locally solely through
isolated filesystem simulation.

## Qualification evidence

Source qualification covers the eight IIS state failures, positive contract
path, clean child processes, normal-mode fail-closed behavior on NARGES,
database/Alembic regression, external dependency failures, ValidateOnly zero
mutation, simulated deployment, post-deployment verification, and exact
rollback. R7 was built during qualification, rejected because its expected gate
count was not independent of runtime execution, and marked `.DISCARDED` without
being overwritten or authorized. The corrected R8 package was then built once.

- Windows PowerShell: `5.1.26100.9278`
- real IIS provider: not available on NARGES
- Production access/change/deployment: none
- source tests: 55/55 PASS
- exact frozen-package tests: 45/45 PASS
- governed failure injection: 42/42
- fresh Windows PowerShell processes: 10/10
- expected/executed/passed prechecks: 60/60/60
- unhandled tooling exceptions: 0
- ValidateOnly active mutation count: 0
- simulated deployment/post-verification/rollback: PASS/PASS/PASS
- package: `D2-VALIDATION-S7-RC-f11f2ab-r8-final`
- package size: 1,282,910 bytes
- package SHA-256: `b0e95e22179f1e262f23b0834f57a8394c97770c247c5d14700f0c2cf5608a50`
- package manifest SHA-256: `b1f59cea252a5cecdd0165de61e0f839930adfbf8512277421c5e8fec5fc8657`
- release-tooling provenance: `2d062671c089bec27e2af25f6df61b50a12dafd4`
- package rebuilt after qualification: no

## Residual risk and release state

The controlled harness proves release-tooling sequencing and failure handling,
not real IIS integration. The only authorized next Production operation is
exact-byte verification, staging extraction, and read-only R8 ValidateOnly.
Deployment remains forbidden until that run returns `VALIDATION_RESULT=GO`.

`FINAL_RELEASE_STATE=READY_FOR_PRODUCTION_VALIDATEONLY_ONLY`

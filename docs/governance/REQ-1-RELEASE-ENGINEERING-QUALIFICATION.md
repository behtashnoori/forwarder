# REQ-1 — Release Engineering Qualification

## Scope and frozen identity

Development-only qualification began on branch `release-gate/s7-forwarder-candidate`
at `89008c161e53180acfbc9d93ccaaf4a16dac1eb2`. No Production connection,
transfer, mutation, merge, push, or deployment occurred. The frozen application
remained `S7-RC-f11f2ab` / source `f11f2abfbff396f66f261f11c7f4bdb80b2d2007`.
Its artifact SHA-256 remained
`a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d` and
sidecar SHA-256 remained
`4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f`.

## Failure history and systemic root cause

The three Production attempts correctly failed closed: generic PostgreSQL URL
handling rejected a SQLAlchemy URL, the repaired parser did not model quoted
and padded CRLF env values, and a PowerShell method expression was passed to a
typed Boolean command parameter without parentheses. The systemic cause was a
qualification design that tested individual source routines with low-fidelity
fixtures, preferred PowerShell 7 when available, terminated at early gates, and
executed the packaged operator path only once with a small failure set.

Root-cause tree:

```text
Tooling defects escaped Development
├── Runtime mismatch
│   ├── pwsh preferred over powershell.exe
│   └── parser checks substituted for PS5.1 execution
├── Fixture mismatch
│   ├── LF/unquoted DATABASE_URL
│   ├── no BOM/whitespace/percent-encoding/duplicate coverage
│   └── incomplete task/IIS/listener/disk/CORS model
├── Path mismatch
│   ├── source script used more often than copied package script
│   └── no repeated immutable-package run
└── Coverage weakness
    ├── early failures hid later gates
    ├── no enumerated failure matrix
    └── no before/after protected-resource fingerprint per case
```

The immediate Boolean defect was `Require $map.Contains('DATABASE_URL') ...`.
PowerShell command argument parsing supplied a string-shaped argument to
`[bool]$Condition`. It is now `Require ($map.Contains('DATABASE_URL')) ...`.
The packaged wrapper's assignment to automatic variable `$args` was renamed to
`$childArguments`. A PS5.1 parser/runtime test and automatic-variable scan now
guard both files. Typed `[bool]`, `[int]`, `[string]`, `[array]`, `[hashtable]`,
`[datetime]`, and switch/custom contracts were reviewed; no unsafe string-to-bool
cast is present.

## Complete call graph and mutation boundary

```text
validate_forwarder_s7_rc_f11f2ab.ps1
├── package manifest identity → file length/hash validation
└── powershell.exe → deploy_s7_rc_f11f2ab.ps1 -ValidateOnly
    ├── mode/host/admin → artifact/sidecar/inner identity
    ├── current release/env/runtime wrapper
    ├── Env-Map → Get-GovernedPostgreSqlUrl → DB/Alembic read-only gate
    ├── target-config scratch copy → Write-Governed-Env → Validate-Env
    ├── Scheduled Task → IIS → listener/health/disk → CORS transition/target
    ├── ValidateOnly → STAGED_VERIFIED → ABORTED_BEFORE_MUTATION
    └── Execute → MUTATION_BOUNDARY_REACHED
        ├── rollback capture → Expand-Archive → Verify-Release
        ├── env/task/IIS transition → activation → runtime Verify-Release
        └── failure → Rollback → exact env/task/IIS/active-release restore
```

All 21 release functions and 72 explicit `Require` call sites were statically
reviewed. Critical identity, env, DB, Alembic, path, task, IIS, disk, listener,
health, CORS, extraction, transition, verification, and rollback paths were
executed under PS5.1. Package-integrity failures execute in the wrapper; all
other prechecks execute through the packaged deployment entrypoint. Mutation,
post-deployment verification, and rollback execute through the same packaged
deployment script in an isolated filesystem fixture.

## Production-like fixture and runtime evidence

The fixture models host `SRV8756807400`, task `Forwarder Backend Production`,
port `5101`, the governed release/runtime paths, database
`forwarder_prod_20260728_161711`, Alembic head
`20260907_direct_shipment_responsibility`, legacy-current/canonical-target CORS,
and fake `postgresql+psycopg2` credentials. Env coverage includes CRLF, UTF-8
BOM, quotes, surrounding whitespace, percent-encoded credentials, empty values,
duplicates, and malformed forms.

The exact packaged command was:

`PowerShell.exe -ExecutionPolicy Bypass -File .\validate_forwarder_s7_rc_f11f2ab.ps1`

The immutable final package ran five consecutive clean-reset simulations. Each
returned `VALIDATION_RESULT=GO`, all ordered `PRECHECK_01=PASS` through
`PRECHECK_58=PASS`, identical `STAGED_VERIFIED` then
`ABORTED_BEFORE_MUTATION` transitions, and `MUTATION_COUNT=0`.
`CONSECUTIVE_GO_RUNS=5/5`.

## Failure injection and safety

All 26 required cases returned deterministic nonzero/NO_GO before mutation:
missing/tampered artifact, sidecar hash, missing env, empty/malformed/unsupported
DB URL and driver, DB access/identity/Alembic, disk, expected release path, task
identity/metadata, IIS, canonical/allow-all/conflicting/unknown-origin CORS,
listener, health, missing/stale deployment script, malformed package JSON, and
access denial. Before/after fingerprints covered env, task, IIS, DB fixture,
target release, and activation state. All were unchanged; secrets were absent
from output. Expected failures are governed; wrapper internal errors emit
`REASON=TOOLING_DEFECT`. `UNHANDLED_OPERATOR_EXCEPTIONS=0`.

The database command is `BEGIN TRANSACTION READ ONLY`; static checks reject
migration, DDL, and DML paths. Correct DB/Alembic identities pass and incorrect
ones fail. CORS separately proves `CURRENT_STATE_CAN_TRANSITION=YES` and
`TARGET_CONFIGURATION_VALID=YES`.

The real local mutation orchestration reached `DEPLOYED_AND_VERIFIED`, including
release/source identity, task/IIS switch, health, canonical GET/preflight,
legacy and unknown-origin rejection, DB, and Alembic checks.
`SIMULATED_DEPLOYMENT_RESULT=PASS`. A forced post-boundary verification failure
restored exact env bytes, task reference, IIS path, and prior active release:
`ROLLBACK_EXACT_RESTORE=PASS`.

## Quality gates, package, and residual risk

Windows PowerShell 5.1 parser and runtime, release integration, packaged path,
Python tests, diff/whitespace checks, typed-parameter scan, and automatic-variable
scan passed. Full suite: `850 passed, 92 skipped, 1 xfailed`. The 9,127 warnings
are pre-existing frozen-application Python/SQLAlchemy deprecation and ORM
warnings; changing them is outside this tooling-only mission. Targeted secret
scan found zero credential/private-key patterns. The release scripts contain no
database mutation or IIS binding mutation command.

Package: `D2-VALIDATION-S7-RC-f11f2ab-r4-final`. The pre-qualification
`r3-final` build is superseded and must not be transferred; `r4-final` is the
first build containing the required ordered precheck evidence.

- Folder: `D:\Projects\webapp\15-forwarder\release-candidates\D2-VALIDATION-S7-RC-f11f2ab-r4-final`
- ZIP: `D:\Projects\webapp\15-forwarder\release-candidates\D2-VALIDATION-S7-RC-f11f2ab-r4-final.zip`
- ZIP size: `1280716` bytes
- ZIP SHA-256: `3c72d25aea24cb03549f9a051bec3e404a0549127fd03ec91fb53fc44adb71db`
- package-manifest SHA-256: `69388b2441082cc6547cd8229fd14a2940069b9f282b757de96ac376fd46671f`

The builder copies current source scripts, hashes every packaged file, embeds
those hashes in the package manifest, and the wrapper verifies them before
execution. Frozen application hashes are rechecked before building.

Residual risk: local files faithfully exercise orchestration and PowerShell
binding, but cannot reproduce every external Windows service/provider failure
or network timing characteristic. The next action is one governed Production
ValidateOnly run only; deployment remains a separate decision.

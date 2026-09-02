# D2 — Production Validation Package

## Objective and immutable inputs

D2 creates a self-contained, transfer-ready **ValidateOnly** package around the
frozen `S7-RC-f11f2ab` application artifact. It does not rebuild or alter the
application RC. Its ZIP SHA-256 is
`a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d`; the
sidecar SHA-256 is
`4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f`.

It packages the D1 entrypoint, a wrapper that can only invoke D1 with
`-ValidateOnly`, the frozen ZIP/sidecar, a non-secret expected-baseline JSON,
README, checksums, manifest, and an outer ZIP. The package manifest validates
every payload file; the outer ZIP hash governs the package manifest itself.

## Operator workflow

1. Copy the complete frozen D2 folder to the approved staging location.
2. Open PowerShell as Administrator.
3. Run `PowerShell.exe -ExecutionPolicy Bypass -File .\validate_forwarder_s7_rc_f11f2ab.ps1`.
4. Copy back the generated non-secret `D2-validation-report-*.json`.
5. Stop. A `NO_GO` requires a return to Development; no Production repair is allowed.

The wrapper verifies package payload hashes before invoking D1. It reports only
`GO` or `NO_GO`, plus explicit `PRODUCTION_MUTATION=NO` and
`DEPLOYMENT_PERFORMED=NO`.

## Baseline and CORS treatment

The non-secret baseline encodes supplied P0-R3 facts: `SRV8756807400`, current
ADR-043 release and IIS path, runtime wrapper, task, port 5101, canonical host,
database, and matching Alembic head. D1 performs read-only filesystem, IIS,
Task Scheduler, HTTP, and database checks. The DB query is a read-only
transaction; migration and data/schema mutation are prohibited.

Legacy CORS is classified as `LEGACY_TRANSITION_EXPECTED` during validation.
It is not a ValidateOnly failure by itself. D1 proves that the existing config
can be transformed without inventing secrets and that the future contract is
canonical origin only, allow-all `0`, and legacy origin absent. Live canonical
CORS verification remains strictly post-activation in a separately authorized
future deployment.

## Local evidence and limits

The actual built package is tested in local fixture directories: manifest and
payload hashes, frozen RC hashes, wrapper-only ValidateOnly invocation, `GO`,
tampered artifact `NO_GO`, zero active-release mutation, and no fixture secrets
in output. PowerShell scripts are parser-checked for Windows PowerShell 5.1.

Residual risk: a future operator must run the package afresh against the then
current Production state. This package is a validation gate, not deployment
authorization.

`PRODUCTION_ACCESS=NO`

`PRODUCTION_CHANGE=NO`

`ARTIFACT_TRANSFER=NO`

`DEPLOYMENT_PERFORMED=NO`

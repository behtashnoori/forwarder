# D1 — Controlled Deployment Design

## Discovery and objective

The deployment entrypoint is [deploy_s7_rc_f11f2ab.ps1](../../scripts/deploy/deploy_s7_rc_f11f2ab.ps1). It reuses the release ZIP/sidecar identity model from `scripts/verify_release_artifact.py`, the immutable release construction from `scripts/build_release_package.py`, and the established ADR-043 Windows Scheduled Task/IIS topology. It does not create a second service architecture.

The governed candidate is `S7-RC-f11f2ab`, source `f11f2abfbff396f66f261f11c7f4bdb80b2d2007`, artifact SHA-256 `a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d`, and sidecar SHA-256 `4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f`.

## Supplied Production baseline

P0-R3 evidence, used without reconnecting, identifies `SRV8756807400`, the
`forwarder` IIS site, `Forwarder Backend Production`, listener `127.0.0.1:5101`,
release `C:\1-webapp\forwarder-production\release-adcc5da-adr043`, runtime root
`C:\1-webapp\forwarder-runtime`, database
`forwarder_prod_20260728_161711`, and Alembic head
`20260907_direct_shipment_responsibility`. The existing canonical HTTP and HTTPS
bindings are evidence-only prerequisites; this package has no binding operation.

## State and mutation model

The explicit states are `PRECHECK`, `PRECHECK_FAILED`, `STAGED`,
`STAGED_VERIFIED`, `STAGING_FAILED`, `ROLLBACK_STATE_CAPTURED`,
`CONFIG_PREPARED`, `SWITCHING`, `SWITCH_FAILED`, `STARTING`, `START_FAILED`,
`VERIFYING`, `VERIFY_FAILED`, `ROLLBACK_RUNNING`, and exactly one terminal
outcome: `DEPLOYED_AND_VERIFIED`, `FAILED_AND_RECOVERED`,
`FAILED_AND_NOT_RECOVERED`, or `ABORTED_BEFORE_MUTATION`.

`MUTATION_BOUNDARY_REACHED` is emitted immediately before copying the original environment file. All prior checks are read-only. `-ValidateOnly` is the default and cannot extract, edit configuration, change the task/IIS path, restart the backend, or make database changes.

## Controlled transition and recovery

Prechecks prove host/admin identity, exact bytes, source/head, existing release,
runtime wrapper, task/IIS references, site state, canonical bindings, current
health, disk capacity, read-only database identity/head, configuration existence,
and target-directory nonexistence. The target is the new
`release-f11f2ab-s7` directory; the previous release is never deleted or
overwritten. Artifact and sidecar hashes fail closed before extraction; extracted
`release-manifest.json` must independently prove source and Alembic identities.

The environment is copied byte-for-byte before any transition. Only the governed effective CORS values change: canonical plural origin, disabled allow-all, and matching singular alias when present. Required secret-bearing configuration keys are checked for presence but never logged. Rollback restores the captured bytes/hash, previous task reference, and prior IIS physical path.

Database identity is read only: it uses `psql` with `BEGIN TRANSACTION READ ONLY`
to compare database and Alembic head, never emits the URL/password, and contains
no migration, DDL, DML, data migration, or schema-repair command. Matching
Alembic head `20260907_direct_shipment_responsibility` is a hard gate. No
binding, TLS, certificate, DNS, ARR, or cleanup operation exists in the package.

## Verification and operator use

Production execution needs separate written authorization. The future operator first runs:

```powershell
.\scripts\deploy\deploy_s7_rc_f11f2ab.ps1 -ValidateOnly -ArtifactPath '<staged ZIP>' -ManifestPath '<staged sidecar>'
```

Only after a fresh valid result may an explicitly authorized administrator run
`-Execute -ConfirmDeployment` with those exact paths. The exact original task
XML and configuration bytes are captured before switch; rollback restores that
XML, prior IIS path, and prior configuration hash. Runtime verification occurs
only after activation: listener, local/canonical health, canonical frontend/API,
canonical GET and OPTIONS CORS, unknown/legacy-origin denial, task/IIS target
identity, database/head continuity, and staged release structure. Authentication,
tenant resolution, reporting authorization, and forged-host checks are read-only
post-deployment smoke checks; any mutating journey is
`OPTIONAL_SEPARATELY_AUTHORIZED_MUTATING_SMOKE_TEST`.

Critical verification failure invokes rollback. A successful rollback is `FAILED_AND_RECOVERED`, never deployment success. Evidence output contains state, candidate/source, hashes, and outcome without secrets.

## Local assurance and limits

The orchestration is exercised against isolated local fixture directories through
`-SimulationRoot`. It covers validate-only zero mutation, bad artifact/manifest,
wrong host, wrong database, wrong Alembic head, missing release/task/IIS,
invalid target configuration, successful transaction, staging failure, and forced
verification failure with exact rollback. The fixture proves database checks are
mocked/read-only and checks evidence output contains no fixture secret. It has no
Production connection capability in that mode.

Residual risk: current Production facts are supplied P0-R3 evidence and must be freshly validated by the authorized operator; this design neither rediscovers nor changes them.

`PRODUCTION_ACCESS = NO`

`PRODUCTION_CHANGE = NO`

`DEPLOYMENT_PERFORMED = NO`

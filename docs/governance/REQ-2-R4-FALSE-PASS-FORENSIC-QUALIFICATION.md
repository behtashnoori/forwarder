# REQ-2 — R4 False-Pass Forensic Qualification

## Scope and safety

This was a Development-only investigation on branch
`release-gate/s7-forwarder-candidate`, starting at
`36737f221bc8942852db1280c27e8baa67f81889`. No Production connection,
change, artifact transfer, deployment, push, or merge occurred. The frozen
application remains `S7-RC-f11f2ab` at source commit
`f11f2abfbff396f66f261f11c7f4bdb80b2d2007`.

## R4 identity and contents

The exact local R4 ZIP was verified before extraction:

- path: `D:\Projects\webapp\15-forwarder\release-candidates\D2-VALIDATION-S7-RC-f11f2ab-r4-final.zip`
- bytes: `1280716`
- SHA-256: `3c72d25aea24cb03549f9a051bec3e404a0549127fd03ec91fb53fc44adb71db`
- forensic extraction: `D:\Projects\webapp\15-forwarder\forensics\REQ-2-r4-20260903-073643`

| File | R4 bytes | R4 SHA-256 | Qualified source SHA-256 | Identity |
|---|---:|---|---|---|
| `deploy_s7_rc_f11f2ab.ps1` | 20173 | `23a7ee61b9e3c0c91cb6b0db854300538729503950de9367a8be2b1a6d85a626` | `23a7ee61b9e3c0c91cb6b0db854300538729503950de9367a8be2b1a6d85a626` | equal |
| `validate_forwarder_s7_rc_f11f2ab.ps1` | 3512 | `de7b6d0fe5df552cd1fbc687ef336d53615ffc5ab93efc30a2245f7ecb1c407f` | `5b85391d2d575e226dfbb22a5ac08378bf0afea1dcd7aadc90d9864468c9bf54` | different |
| `README-OPERATOR.txt` | 422 | `920cd16819f20ac898504771090202ff554335875fc852bdb947570d6fa99d04` | generated | recorded |
| `expected-production-baseline.json` | 739 | `190a229a555c5f87bbee6ab326fb8cf7d2fe9ddcbc01a0ea29dc18d2d36cc67f` | generated | recorded |
| `D2-package-manifest.json` | 1542 | `69388b2441082cc6547cd8229fd14a2940069b9f282b757de96ac376fd46671f` | generated | recorded |
| `SHA256SUMS.txt` | 588 | `61f2da977ffb942aa0d850eb4b914c9a2b7243972663bcea73588d666b31eef2` | generated | recorded |

`PACKAGED_SCRIPT_EQUALS_QUALIFIED_SOURCE=NO`. The builder copied the source
wrapper and then rewrote its default package ID from `r3-final` to `r4-final`.
REQ-1's test helper, however, invoked the builder without the third package-ID
argument and therefore built and ran `r3-final`. The R4 deployment script was
byte-identical to source, but the statement that the exact handed-off R4 wrapper
had been executed was false.

## Exact R4 reproduction and failing call

The forensic harness parsed the extracted R4 deployment script, loaded the
exact `Require`, `Fail`, `Env-Map`, `Get-GovernedPostgreSqlUrl`, and
`Assert-DatabaseIdentity` function extents, and invoked the non-simulation
database branch with a PostgreSQL/psycopg2 URL. It ran under:

`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`

Version: `5.1.26100.9278`.

Observed result:

```text
DATABASE_URL_PRESENT=YES
DATABASE_ENGINE=POSTGRESQL
DATABASE_DRIVER=psycopg2
System.Management.Automation.ParameterBindingArgumentTransformationException
Cannot convert value "System.String" to type "System.Boolean".
R4_FAILURE_REPRODUCED=YES
```

The exact R4 failing call is packaged line 110:

```powershell
$userInfo=$uri.UserInfo.Split(':',2); Require ($userInfo[0]) 'database user is absent'
```

`$userInfo[0]` is `System.String`. Parentheses delimit the expression but do not
turn the string into a Boolean. Binding it to `Require([bool]$Condition, ...)`
caused the ordinary parameter-binding exception.

The Production trace fixes the R4 numbering without inspecting Production. R4
has 14 fixed gates before parsing the env file. The observed last pass before
the database evidence was 42, so the env map contained 23 parsed keys:

| Production R4 precheck | Gate |
|---|---|
| 01 | mutually exclusive execution mode, script line 163 |
| 02 | expected host, line 167 |
| 03 | Administrator role, line 167 |
| 04–11 | artifact exists/name/hash, sidecar exists/hash, source, Alembic, and size/hash identity, lines 79–87 |
| 12 | current release exists, line 170 |
| 13 | `production.env` exists, line 171 |
| 14 | runtime wrapper exists, line 172 |
| 15–37 | 23 unique env keys, `Env-Map` line 54 |
| 38 | `DATABASE_URL` key exists, line 100 |
| 39 | URL is non-empty, line 90 |
| 40 | PostgreSQL/psycopg2 URL match succeeds, line 92 |
| 41 | URL host is non-empty, line 95 |
| 42 | URL database path is non-empty, line 96 |
| next attempted gate (43) | database user is non-empty, line 110; parameter binding failed before `PRECHECK_43` could print |

Therefore `R4_PRECHECK_42_NEXT_GATE=database user is non-empty` and
`NEXT_BOOLEAN_PARAMETER_CALL=Require ($userInfo[0])`.

## Proven false-pass root cause

`FALSE_PASS_ROOT_CAUSE=REQ-1 always supplied SimulationRoot, causing
Assert-DatabaseIdentity to return at lines 103–107 before the non-simulation
database-user gate at line 110; its package test also built r3 rather than the
handed-off r4 wrapper.`

The five reported GO runs genuinely observed the simulation path, not the known
Production path. The fixture printed the same database evidence but then took
the simulation-only identity checks and returned. No test invoked the
`$uri.UserInfo` branch. The static assertion only checked the previously fixed
`$map.Contains('DATABASE_URL')` expression. It neither enumerated every Boolean
consumer nor asserted runtime types. Consequently 5/5 GO, 58/58 prechecks, and
zero unhandled exceptions were true only for the bypassing fixture. The build
test's default `r3-final` identity independently invalidated the exact-package
claim.

No evidence indicated module/function shadowing, dot-source replacement, a
cached child script, or a rebuild after R4 creation. Those alternatives were
excluded by R4/source hashes, the manifest, the wrapper source, and direct
execution of the extracted function text.

## Systemic correction and Boolean/typed-parameter audit

The Boolean gate now accepts an object, measures its exact runtime type, and
fails with a governed `TOOLING_DEFECT` unless it is precisely
`System.Boolean`. This prevents PowerShell's parameter binder from emitting an
operator-facing conversion exception. It does not coerce strings. Every passed
gate emits both its deterministic call site and runtime type.

The failing database-user producer is now:

```powershell
Require (-not [string]::IsNullOrWhiteSpace($userInfo[0])) 'database user is absent'
```

The regex match and confirmation switch boundaries are also explicit Boolean
expressions. The wrapper resolves and invokes the absolute System32 Windows
PowerShell path, verifies version 5.1, resolves the deployment entrypoint, and
rejects a child path outside the extracted package.

PowerShell AST enumeration found 74 `Require` call sites in the final deployment
script. They are at lines 59; 67–71; 84–92; 95, 97, 100–101; 105, 110–111,
115, 120; 127; 131–136; 139–143; 146–152; 161–163; 169, 171–178; 181–194;
198–202; and 215. Each argument is an explicit comparison, predicate, test
command, or negation with static/runtime result `System.Boolean`; all are safe.
The complete production-like ValidateOnly path executed 58 of them per run and
recorded `System.Boolean` 58/58 in each of 10 runs. The remaining call sites are
Execute/runtime/rollback branches and were exercised by simulated deployment
and rollback where reachable.

Function parameter audit found no `[bool]` parameter remaining. Typed contracts
are strings for paths/messages/references, and the `Verify-Release` runtime flag
is a native `[switch]`. Automatic-variable collision scanning found none.

## Deterministic PRECHECK 01–58 map

This map is the exact frozen-R5 production-like fixture trace. All entries
reported runtime type `System.Boolean`.

| No. | Function:line | Branch condition |
|---:|---|---|
| 01 | script:169 | only one execution mode |
| 02 | script:172 | simulation root exists |
| 03–10 | Require-Artifact:84–92 | artifact and sidecar byte identity |
| 11–12 | script:175 | expected host and Administrator fixture |
| 13–15 | script:176–178 | current release, env, runtime wrapper exist |
| 16–21 | Env-Map:59 | six source env keys are unique |
| 22 | Assert-DatabaseIdentity:105 | `DATABASE_URL` key exists |
| 23–26 | Get-GovernedPostgreSqlUrl:95–101 | non-empty, supported engine/driver, host, database path |
| 27–28 | Assert-DatabaseIdentity:110–111 | database and Alembic identities |
| 29–34 | Env-Map:59 | target-config preparation keys unique |
| 35–40 | Env-Map:59 | prepared target keys unique |
| 41–42 | Validate-Env:67 | database URL and JWT secret present |
| 43–46 | Validate-Env:68–71 | allow-all off, canonical plural, legacy absent, singular/plural agreement |
| 47–49 | script:181–183 | task reference, IIS path, unused target release |
| 50–54 | script:185–189 | task metadata, IIS state/bindings, listener, health |
| 55 | script:191 | at least 5 GB free |
| 56–58 | script:192–194 | transitionable current CORS, canonical target, unknown origin rejected |

The output then records `CURRENT_STATE_CAN_TRANSITION=YES`,
`TARGET_CONFIGURATION_VALID=YES`, `STATE=STAGED_VERIFIED`, and
`STATE=ABORTED_BEFORE_MUTATION`.

## Frozen R5 package qualification

The package was built once, hashed, frozen, extracted, and only that extraction
was executed. It was not rebuilt afterward.

- package ID: `D2-VALIDATION-S7-RC-f11f2ab-r5-final`
- folder: `D:\Projects\webapp\15-forwarder\release-candidates\D2-VALIDATION-S7-RC-f11f2ab-r5-final`
- ZIP: `D:\Projects\webapp\15-forwarder\release-candidates\D2-VALIDATION-S7-RC-f11f2ab-r5-final.zip`
- ZIP bytes: `1281110`
- ZIP SHA-256: `e6c0a43e792268bf6856387debee04c8278a5bcfba74ecd3ba8b82b45bc2ce3c`
- package manifest SHA-256: `ce0e98271fc56b6f7180c45939f873911f36d7b0de56a6b7c537c73115dd63ad`
- deployment script SHA-256: `0726d50504ec31f6191e96f77968c2a13e6fb5c0ba4caabff3049964b04c6faf`
- validation wrapper SHA-256: `3c0580c0d5c036b855782cc24d99ab920ad63de7d89cac28d38458d61e0fcb88`
- baseline SHA-256: `190a229a555c5f87bbee6ab326fb8cf7d2fe9ddcbc01a0ea29dc18d2d36cc67f`
- application ZIP SHA-256: `a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d`
- application manifest SHA-256: `4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f`

The extracted wrapper and deployment script are byte-identical to their final
source inputs. Ten consecutive exact-package runs reached `PRECHECK_58=PASS`
and `VALIDATION_RESULT=GO`; before/after protected-resource fingerprints were
identical. `VALIDATEONLY_MUTATION_COUNT=0`.

The 35 requested failure-injection cases were covered. Cases 1–26 are the prior
matrix. Cases 27–30 injected string `True`, string `False`, empty string, and
null into the Boolean consumer; each produced a governed tooling defect, never
a parameter-binding exception. Cases 31–35 detected source/package divergence,
changed ZIP bytes after qualification, wrong wrapper child resolution, missing
required PS5.1 runtime, and unexpected child-path policy. The complete test file
reported `38 passed`; there were zero unhandled tooling exceptions.

Simulated Execute crossed the mutation boundary and reached
`DEPLOYED_AND_VERIFIED`. A forced post-boundary verification failure reached
`FAILED_AND_RECOVERED`. Rollback restored exact env bytes, task reference, IIS
path, and absence of the target release.

## Residual risks and decision

The isolated fixture cannot reproduce every Windows service/provider outage or
network race. Also, precheck ordinal positions depend on the number of parsed
env keys; call-site evidence is now emitted alongside each ordinal so this can
no longer hide branch differences. The immutable ZIP hash is the external trust
anchor for the manifest and wrapper; operators must verify that published hash
before use.

All REQ-2 pass criteria are satisfied in Development. The recommended next step
is controlled transfer of exactly the published R5 ZIP under a separate
authorization, followed by one governed Production ValidateOnly run. Deployment
remains a separate decision.

## Release provenance closure

- `QUALIFIED_APPLICATION_SOURCE_COMMIT=f11f2abfbff396f66f261f11c7f4bdb80b2d2007`
- `RELEASE_TOOLING_PROVENANCE_COMMIT=the Git commit containing this record and the four REQ-2 tooling/test files named in the release-closure report`
- `QUALIFIED_PACKAGE=D2-VALIDATION-S7-RC-f11f2ab-r5-final`
- `QUALIFIED_PACKAGE_SHA256=e6c0a43e792268bf6856387debee04c8278a5bcfba74ecd3ba8b82b45bc2ce3c`

The exact tooling-provenance commit SHA is necessarily assigned by Git only
after this record becomes part of that commit. It is recorded in the external
release-closure report. The package SHA-256 above remains the immutable,
exact-byte release trust anchor; the package was not rebuilt or changed during
Git closure.

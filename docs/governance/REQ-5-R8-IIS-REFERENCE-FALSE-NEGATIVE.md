# REQ-5 — R8 IIS reference false-negative forensic

## Safety and authoritative evidence

This mission changed release tooling in Development only. There was no
Production access, connection, mutation, transfer, deployment, push, or merge.
The frozen S7-RC-f11f2ab application was not rebuilt or modified.

The exact R8 Production ValidateOnly passed database, Alembic, ScheduledTasks,
WebAdministration, provider, drive, and site gates, then failed PRECHECK 43 and
aborted before mutation. An immediate independent read-only inspection proved
that site `forwarder` resolves to the governed previous release `dist` after
Windows path normalization. Production IIS is therefore accepted as correct;
R8 is historical and invalid for deployment.

## Exact R8 implementation

R8 produced its expected value with:

```powershell
Join-Path $script:PreviousRelease 'dist'
```

Its actual producer and comparison were:

```powershell
function Get-IisReference {
    Require $script:IisInspectionReady 'IIS inspection prerequisites were not initialized'
    return (Get-ItemProperty -LiteralPath 'IIS:\Sites\forwarder' -Name physicalPath -ErrorAction Stop).physicalPath
}
Require ((Get-IisReference) -eq (Join-Path $script:PreviousRelease 'dist')) `
    'IIS does not reference governed previous release dist'
```

The visible authoritative values, when instantiated as scalar `System.String`
values under Windows PowerShell 5.1, are each 60 characters, one pipeline
record, and R8's raw `-eq` returns True. `Require` uses `Write-Host`, which does
not contaminate the success pipeline; an exact function reproduction returned
one `System.String` record. Pipeline contamination is disproven for the scalar
case.

The Production evidence did not record the raw provider value's type, length,
character codes, or record count before independent normalization. It therefore
cannot distinguish a trailing separator, expandable environment expression, or
other representation difference that renders to the same displayed path. The
false-negative class is nevertheless reproduced: the same governed directory
with a trailing separator or environment-variable representation makes R8's
raw comparison False while canonical Windows directory identity is True.

The proven tooling defect is that R8 compared an unvalidated, uncanonicalized
provider property directly with a constructed path. It had no scalar cardinality,
runtime-type, expansion, full-path, separator, or diagnostic contract. This is
sufficient to convert equivalent Windows directory representations into a
false negative; it does not imply a Production configuration defect.

## R9 scalar and path contract

`Get-GovernedIisPhysicalPath` captures provider output into an array, requires
exactly one record, requires that record to be a non-null `System.String`, and
rejects empty strings, leading/trailing whitespace, provider objects, arrays,
multiple records, relative paths, malformed paths, and read failures.

`ConvertTo-GovernedWindowsPath` expands environment variables, normalizes `/`
to `\`, requires an absolute path, uses `GetFullPath`, and removes trailing
separators except for a drive root. Equality uses
`String.Equals(..., OrdinalIgnoreCase)` against a separately canonicalized
expected path. It performs exact directory identity—not substring or prefix
matching.

Before the gate, R9 emits safe diagnostics:

- `EXPECTED_IIS_DIST_VALUE/TYPE/LENGTH`
- `ACTUAL_IIS_DIST_VALUE/TYPE/LENGTH`
- `IIS_DIST_EQUALS_RESULT`

Diagnostics use `Write-Host` and cannot join the returned scalar pipeline.

## Regression and failure qualification

REQ-4A module discovery/import, provider, drive, and site gates remain before
provider access. REQ-3 tagged database/Alembic scalars, exit-code checking,
cardinality checks, and ordinal identity comparisons remain unchanged. The
fixed precheck registry remains independent of runtime execution.

Qualification includes exact, case-varied, trailing-separator, slash-varied,
and environment-expanded equivalent paths; null, empty, arrays, multiple
records, provider objects, whitespace, relative paths, wrong release/dist,
malformed values, and read failure; the complete earlier dependency matrix; ten
fresh PS5.1 processes; zero-mutation ValidateOnly; and simulated deployment,
verification, and exact rollback.

Final evidence:

- source qualification: 68/68 PASS;
- exact frozen-package qualification: 51/51 PASS;
- governed failure injection: 48/48, with zero unhandled tooling exceptions;
- fresh PS5.1 process and IIS-reference contract runs: 10/10;
- final gate reached: 10/10;
- expected/executed/passed prechecks: 60/60/60;
- ValidateOnly active/env/IIS/task/database mutations: 0;
- simulated deployment/post-verification/rollback: PASS/PASS/PASS;
- package ID: `D2-VALIDATION-S7-RC-f11f2ab-r9-final`;
- package size: 1,283,379 bytes;
- package SHA-256: `f8744db803d360abcacc0c422cd44da286fd433cc1a2efe46fc5eb345d050064`;
- package-manifest SHA-256: `6f16f28dd743aca52b33953a976cad3178fb059cc7013cb27654d7204989e171`;
- tooling provenance: `4aa08141e482f4287fba18248cf7397a1baf33cc`;
- Windows PowerShell: `5.1.26100.9278`;
- package built once and not rebuilt after qualification.

## Residual integration requirement

Development proves the extraction/comparison contract but cannot inspect the
real WebAdministration object on NARGES. The only authorized next Production
action is exact-byte verification, staging extraction, and read-only R9
ValidateOnly. Its new type/length/value diagnostics will close the remaining
raw-shape evidence gap. Deployment remains forbidden until Production returns
`VALIDATION_RESULT=GO`.

`FINAL_RELEASE_STATE=READY_FOR_PRODUCTION_VALIDATEONLY_ONLY`

# REQ-6 — R9 IIS provider scalar extraction / R10

## Safety and frozen application

This mission changes release tooling in Development only. It performs no
Production access, connection, mutation, transfer, deployment, push, or merge.
The frozen `S7-RC-f11f2ab` application remains unchanged at source commit
`f11f2abfbff396f66f261f11c7f4bdb80b2d2007`, application SHA-256
`a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d`,
and application-manifest SHA-256
`4bff7378c3fbd0ef36dee33ea0bc40bd3e9661c618092c12a5fc1e6d0e12665f`.

R9 is historical, must not be overwritten, and must not be deployed. Its frozen
identity is `D2-VALIDATION-S7-RC-f11f2ab-r9-final`, 1,283,379 bytes, SHA-256
`f8744db803d360abcacc0c422cd44da286fd433cc1a2efe46fc5eb345d050064`,
with package-manifest SHA-256
`6f16f28dd743aca52b33953a976cad3178fb059cc7013cb27654d7204989e171`.

## Authoritative Production failure and provider forensic

R9 Production ValidateOnly ended in governed `NO_GO` with
`STATE=PRECHECK_FAILED`, `STATE=ABORTED_BEFORE_MUTATION`, and
`DEPLOYMENT_GATE: IIS physical path must be one scalar string`. It caused no
Production mutation and performed no deployment. An independent read-only
identity check proved that IIS site `forwarder` already referenced the exact
governed directory:

```text
C:\1-webapp\forwarder-production\release-adcc5da-adr043\dist
```

The dedicated read-only provider forensic subsequently proved one returned
record of runtime type `System.String`, with no `physicalPath` property. Direct
`.physicalPath` access returned null. Production IIS configuration is therefore
correct; the R9 provider-return assumption is false.

## Exact R9 null-generation mechanism

R9 used:

```powershell
$records = @(
    (Get-ItemProperty `
        -LiteralPath 'IIS:\Sites\forwarder' `
        -Name physicalPath `
        -ErrorAction Stop).physicalPath
)
```

On the actual host, `Get-ItemProperty -Name physicalPath` returned the property
value itself as a `System.String`. Applying `.physicalPath` to that scalar
produced `$null`; the subsequent strict string gate then emitted the observed
error. Thus the exact root cause is
`GET_ITEMPROPERTY_NAME_RETURNS_SCALAR_STRING_BUT_TOOLING_ATTEMPTED_DOT_PROPERTY_EXTRACTION`.
Canonicalization was not the primary failure.

## Corrected R10 contract

R10 captures the provider call before any property access:

```powershell
$records = @(
    Get-ItemProperty `
        -LiteralPath 'IIS:\Sites\forwarder' `
        -Name physicalPath `
        -ErrorAction Stop
)
```

It requires exactly one non-null record whose runtime type is precisely
`System.String`; arbitrary provider objects, arrays, integers, Booleans, null,
empty output, and multiple records fail closed. It then rejects empty or
whitespace-contaminated values, expands environment variables, normalizes
slashes, requires a rooted Windows path, obtains the full path, removes only a
non-root trailing separator, and compares exact directory identity with
`OrdinalIgnoreCase`. No substring, prefix, parent-release, or object-to-string
coercion is accepted.

Before the equality gate, R10 emits `RAW_IIS_PROVIDER_RECORD_COUNT`,
`RAW_IIS_PROVIDER_RECORD_TYPE`, expected and actual value/type/length, and
`IIS_DIST_EQUALS_RESULT`. These diagnostics use `Write-Host`; the helper returns
exactly one intended pipeline record on success.

## Qualification and regression coverage

The controlled harness preserves the exact extraction, cardinality, type,
canonicalization, and equality logic and bypasses only environmental admission.
Its real-shape fixture models one direct `System.String` with the authoritative
Production value. A contrast test proves the same scalar has no
`physicalPath` property, reproduces R9's null, and proves R10 returns the scalar
as one pipeline record.

Targeted cases cover exact/case/trailing/slash/environment representations;
null and zero records; two strings; a string array; `PSCustomObject` and provider
objects; integer and Boolean; empty, leading/trailing whitespace, relative and
malformed paths; wrong release, parent release, wrong dist; provider failure;
and missing IIS drive/site. The full prior failure matrix, IIS prerequisites,
database and Alembic identity, Scheduled Task identity, canonical S8 CORS,
deterministic precheck accounting, zero-mutation ValidateOnly, simulated
deployment verification, and exact rollback remain mandatory regressions.

## Immutable package and Production gate

The new immutable identity is `D2-VALIDATION-S7-RC-f11f2ab-r10-final`. Exact
package size, hashes, and release-tooling provenance are recorded in the final
REQ-6 qualification report produced after the one-time build. R10 remains only
`READY_FOR_PRODUCTION_VALIDATEONLY_ONLY`.

A local GO is not deployment authorization. The next permitted Production step
is exact-byte verification followed by read-only R10 ValidateOnly. Only a future
result containing `VALIDATION_RESULT=GO`, `PRODUCTION_MUTATION=NO`, and
`DEPLOYMENT_PERFORMED=NO` may open a separate deployment-authorization decision.

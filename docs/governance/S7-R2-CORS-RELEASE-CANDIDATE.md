# S7-R2 CORS Release Candidate

## Candidate identity

- Candidate: `S7-RC-f11f2ab`
- Authorized source commit: `f11f2abfbff396f66f261f11c7f4bdb80b2d2007`
- Source subject: `fix(config): establish canonical production cors contract`
- Artifact: `Forwarder-S7-RC-f11f2ab.zip`
- SHA-256: `a7bfac4e250e54e4aca2338783eb4667680781499ad1da2262b949ae9379544d`
- Size: `1305889` bytes
- Alembic head: `20260907_direct_shipment_responsibility`

This candidate supersedes the release decision for the older S7 artifact because it
contains the S8 canonical CORS contract. The older immutable artifact remains
unchanged at `release-candidates/S7-RC-11ae2d2/` outside this repository.

## Evidence gates

- Focused CORS tests: `16 passed`.
- Full backend regression: `850 passed, 92 skipped, 1 xfailed, 0 failed, 0 errors`.
- Frontend tests: `33 files passed, 156 tests passed`.
- Frontend production build: passed.
- Repository secret scan: `0` findings.
- Release packaging completed from a fresh detached source checkout and produced the
  artifact and sidecar manifest recorded above.

## CORS deployment contract

Before deployment, the authorized environment configuration must set:

```text
CORS_ORIGINS=https://samand.forwarderet.ir
CORS_ALLOW_ALL_ORIGINS=0
```

`CORS_ORIGIN`, if retained for compatibility, must be absent or resolve to the same
canonical origin. The legacy `https://server.logisticmarket.ir` origin must not be
present. The application intentionally fails closed when the production CORS
configuration is missing, wildcarded, placeholder/local, internally inconsistent,
or excludes the canonical origin.

No Production system, credential, database, IIS setting, DNS record, or TLS
configuration was accessed or changed while preparing this candidate.

## Deployment and rollback controls

Deploy the exact ZIP whose SHA-256 is recorded above. Any rebuilt ZIP is a distinct
candidate and requires a new manifest and release decision. Verify the configured
environment contract before starting the new application process and retain the
previous approved artifact and configuration values for rollback. Rollback is a
controlled deployment action and is not performed by this release-gate evidence.

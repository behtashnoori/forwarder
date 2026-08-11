# Forwarder v1.9.1 Slice 8 publication readiness

## Slice 7 commit closure

- Initial baseline: `5b144f7f5032a44ef60fde1065bb1a3b24e8bfa6`.
- `7e85adfdb8df2385cf52ea0578b2d0f72801ba03` — release readiness remediation.
- `509fe09d564e20ad69d11f47efc938386df5f156` — release rehearsal coverage.
- `d9b383b8b2186c92a9eec0356f3ea73aa72e17c3` — runbooks, release notes, and sanitized Slice 7 evidence.
- Slice 8 baseline: `d9b383b8b2186c92a9eec0356f3ea73aa72e17c3`.
- Unrelated pre-existing untracked material was preserved and excluded.

## Release identity and source validation

- Application version: `1.9.1`.
- Proposed annotated tag: `v1.9.1`.
- Proposed tag message: `Forwarder v1.9.1`.
- Alembic sole head: `20260819_v191_acceptance_corrections`.
- Production baseline revision: `20260818_immutable_fx_provenance`.
- Version consistency and release-builder source validation: PASS.
- Release notes and active deployment/migration/rollback/smoke documents: PASS.
- `git diff --check`: PASS.
- Current-tree secret scan: PASS, zero findings, redaction enabled.

## Test results

- Backend: PASS, 642 passed and 65 PostgreSQL-dependent skips; 6,384 accepted legacy/deprecation warnings.
- Focused release/backend contracts: PASS, 39 passed in the pre-commit focused run and 18 passed after package-source correction.
- Frontend: PASS, 24 files and 125 tests.
- TypeScript: PASS.
- ESLint: PASS with zero errors and 12 accepted warnings.
- Production frontend build: PASS, 1,886 modules; stale Browserslist data and large-chunk advisories remain Category 3.
- Disposable PostgreSQL v1.9.0-to-v1.9.1 migration, row preservation, direct/accepted-quote persistence, backup, and restore: PASS.
- Disposable rehearsal observed no blocking lock; strong locks confirm the write-quiescence requirement.
- Committed-source browser smoke: PASS for Persian/English rendering, language switching, staff-login navigation, and zero console errors.
- Full synthetic Chromium acceptance from Slice 7 remains PASS for direct/accepted-quote operations, canonical locations, source-aware list/detail, lifecycle, MDPM, economics/FX, OIP, idempotency, and release-identity states.

## Publication and package gate

Human authorization to create or publish the annotated tag was not provided.
No tag was created and no branch or tag was pushed. The immutable package was
not built because the release builder requires the exact annotated tag at HEAD.
Consequently package filename, byte size, SHA-256, extracted-package validation,
and remote-ref verification are pending human publication authorization, not
failed gates.

The intended release package will be built from the exact authorized tagged
commit and will contain the production frontend build, tracked backend runtime,
migration chain through `20260819_v191_acceptance_corrections`, release manifest,
requirements, container/startup files, and deployment, migration, rollback,
smoke, package, server, and secret-verification runbooks. It will exclude local
environment files, credentials, dumps, uploaded documents, logs, dependencies,
virtual environments, browser profiles, caches, test databases, and unrelated
untracked material.

## Cleanup and safety

Disposable rehearsal databases were removed after verification. The temporary
backend and PostgreSQL resources used by the accepted Slice 7 browser gate were
already stopped. The temporary Slice 8 browser/Vite smoke resources are stopped
during final cleanup. Production was not accessed, modified, migrated, deployed,
or restarted.

Final checkpoint: `SLICE 8 READY FOR HUMAN PUBLICATION AUTHORIZATION`.

## Authorized publication attempt

Human authorization for tag creation, immutable packaging, package
verification, and exact branch/tag publication was received. Final preflight
confirmed release commit `17108c7f11ea3615e21fec817ff84cd11349cef9`, version
`1.9.1`, sole Alembic head `20260819_v191_acceptance_corrections`, a clean
tracked tree, zero current-tree secret findings, and no pre-existing local or
remote `v1.9.1` tag. The baseline-to-release delta contained only this Slice 8
publication evidence.

Annotated tag `v1.9.1` was created locally with message `Forwarder v1.9.1`.
Tag object `86db037419871900f06cca8093cfd69d398fe643` resolves exactly to the
authorized release commit. It was not pushed.

The approved builder produced `release-v1.9.1-20260811`, and the standalone
archive `Forwarder-v1.9.1-17108c7.zip` was created with byte size `908877` and
SHA-256 `6d19b0d5010cdd12d17945bb60464e9e7fff99e19fb7bd96419c0f4143ac19f7`.
Its manifest records build timestamp `2026-08-10T21:16:30Z`, release commit
`17108c7f11ea3615e21fec817ff84cd11349cef9`, tag `v1.9.1`, and package-content
hash `076fdf34244fcd96334a37936ad7539996c11184f1e1875a43055bb265f51e90`.

Actual-package verification from a separate extracted directory was BLOCKED by
the fail-closed package secret policy. The package contains the governed
historical credential migration, but the verifier only accepts it when the
manifest declares the older v1.9.0 upgrade chain from
`20260809_cargo_catalog_items` through `security_credential_remediation`. The
v1.9.1 manifest correctly declares the Production baseline
`20260818_immutable_fx_provenance` and only
`20260819_v191_acceptance_corrections`, so the historical exception cannot be
established and verification fails closed. No secret value is recorded here.

Per the publication authorization, package verification failure stopped all
remote publication. Neither the branch nor tag was pushed. No Production
system was accessed or changed. Final classification for this attempt:
`RELEASE PUBLICATION BLOCKED — PRODUCTION CUTOVER NO-GO`.

## Authorized retag and corrected-package attempt

Human authorization was received to replace the local-only annotated tag,
rebuild from corrected release-source commit
`aebd4d6163a3eefd454871fd03406486c83ade21`, verify a disposable extraction,
and publish only after every mandatory gate passed. Corrected policy, release,
version, credential, compilation, Ruff, diff, and sole-head checks passed. The
authorized commit contained only `verify_package_secrets.py`,
`scripts/build_release_package.py`, and
`backend/tests/test_package_secret_policy.py`.

The old local tag targeting `17108c7f11ea3615e21fec817ff84cd11349cef9`
was replaced as authorized. The new annotated tag object is
`eb4471219a390ff34b5389a67509b3946d0245f7`, with message
`Forwarder v1.9.1`, and resolves exactly to the corrected commit. Both the
remote release branch and remote tag remained absent.

The old archive `Forwarder-v1.9.1-17108c7.zip` remains
`SUPERSEDED — DO NOT PUBLISH`. A new candidate archive,
`Forwarder-v1.9.1-aebd4d6.zip`, was built with byte size `890959` and SHA-256
`b80bb08dd80bf2e1313e5cf242d81e77b287f41e699a74f1748e5ad5754859de`.
Its manifest content hash is
`b8dfaac68154863696e269849bb47cae768a18b7c38496eb036d9fa5add9000d`.

Mandatory verification of a fresh extraction failed closed. The exact
historical declaration and migration ancestry validated, and the exact legacy
file fingerprint validated, but the packaged remediation migration byte hash
did not equal the pinned fingerprint. The clean linked-worktree checkout had
materialized different line endings before the builder copied the migration,
making this security fingerprint checkout-dependent. No credential value was
printed or recorded. The new candidate is therefore also
`BLOCKED — DO NOT PUBLISH`.

Package runtime and Chromium smoke were not run because VERIFY-PACKAGE did not
pass. Neither branch nor tag was pushed. Production was not accessed, changed,
migrated, deployed, or restarted. This post-tag evidence remains an
uncommitted operational record so the tag is not moved merely to include it.

## Package hash canonicalization remediation

Preflight reconfirmed branch `codex/pr-4a-dms-gate-repair` at tagged commit
`aebd4d6163a3eefd454871fd03406486c83ade21`. Annotated tag `v1.9.1`
remained local-only, tag object `eb4471219a390ff34b5389a67509b3946d0245f7`,
and both the remote branch and remote tag remained absent. Production was not
accessed. Unrelated tracked and untracked user material was preserved.

The mismatching file was
`backend/migrations/versions/security_credential_remediation.py`. Git stores
the canonical blob as 1,203 bytes with 43 LF endings, no CRLF pairs, and no
lone carriage returns; its SHA-256 is the already-pinned remediation
fingerprint. Windows `core.autocrlf=true` can materialize that exact content as
1,246 bytes with 43 CRLF pairs. Replacing CRLF pairs with LF in that simulated
Windows representation reproduces the Git blob byte-for-byte. The prior
candidate's sanitized verification record established that the package
mismatch occurred at this remediation hash after Windows materialization. The
blocked candidate archive and its disposable extraction were no longer present
for independent re-reading during this mission; the older superseded archive
and its extracted directory remained untouched.

The verifier now hashes the remediation migration using a binary, narrow
canonical representation: replace each exact `CR LF` byte pair with `LF`, then
SHA-256 the result. It performs no text decoding, trimming, generic whitespace
normalization, case conversion, or lone-CR conversion. The legacy migration
continues to use its exact raw-byte fingerprint. Declaration equality,
migration identity and ancestry, the historical credential fingerprint, and
the package-wide secret scan remain fail-closed.

Deterministic tests cover LF and simulated CRLF acceptance with the same
fingerprint; non-newline byte mutation; non-newline whitespace mutation; lone
carriage return; declaration tamper; invalid ancestry; the v1.9.0 legacy
contract; unrelated future migration isolation; and current/package secret
rejection. Focused tests passed (17), and the broader release/migration suite
passed (62). Python compilation, Ruff, builder source/version validation,
credential policy, `git diff --check`, and the independent Alembic sole-head
check passed. The current-tree secret scan reported two redacted findings in
the pre-existing untracked `.codex/slice8-tracked-source.tar`; that user-owned
archive was preserved. The older `scripts/verify_release_security.py` helper
also failed because it still pins the prior `20260818_immutable_fx_provenance`
head, while Alembic and the v1.9.1 builder correctly require and report sole
head `20260819_v191_acceptance_corrections`; changing that unrelated stale
helper was outside this hashing-only mission.

Because the verifier is tracked release source, this remediation requires a
new local commit and makes the current local `v1.9.1` tag stale. Neither old
archive is publishable: `Forwarder-v1.9.1-17108c7.zip` remains superseded, and
`Forwarder-v1.9.1-aebd4d6.zip` remains blocked even though the latter archive is
no longer present locally. No package was rebuilt, no tag moved, no ref pushed,
and no deployment or Production operation occurred. Human retag authorization
is required before any new candidate may be built or published.
Final classification: `RELEASE PUBLICATION BLOCKED — PRODUCTION CUTOVER NO-GO`.

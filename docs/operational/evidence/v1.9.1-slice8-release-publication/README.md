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

## Final retag authorization and controlled publication attempt

Human authorization was received to replace the local-only tag, build and
verify a new package, run disposable package smoke, and publish only if every
gate passed. Final preflight confirmed release commit
`8ebd85591586010b7b12db340bb7d21d15787ad9`, a clean tracked tree, version
`1.9.1`, sole Alembic head `20260819_v191_acceptance_corrections`, and absent
remote release branch/tag. The authorized commit delta remained limited to the
canonicalized package verifier, its tests, and sanitized evidence.

`.codex/slice8-tracked-source.tar` was confirmed untracked. The builder copies
an explicit root allowlist, built frontend files, and tracked `backend` runtime
files only, so `.codex` and unrelated diagnostic archives cannot enter the
package. Classification: `UNRELATED PRESERVED LOCAL MATERIAL — EXCLUDED FROM
RELEASE PACKAGE`. `scripts/verify_release_security.py` was confirmed legacy,
non-authoritative diagnostic tooling: it is not referenced by the builder,
package verifier, active release runbooks, or release workflows. The
authoritative path is `VERIFY-PACKAGE.ps1` plus the packaged
`verify_package_secrets.py`.

The local annotated tag was replaced as authorized. New tag object
`fe65b344adce3b598b668d0b2c5088f5515f2ec0` has message
`Forwarder v1.9.1` and targets exactly
`8ebd85591586010b7b12db340bb7d21d15787ad9`. The prior extracted package was
preserved as `release-v1.9.1-20260811-17108c7-superseded` before the approved
builder invocation `python scripts/build_release_package.py`.

New candidate `Forwarder-v1.9.1-8ebd855.zip` is 890,143 bytes with SHA-256
`c69e265f5c27283807fd3f024ae3deba9d22abc720b615ff1fbaf5a83a16df0a`.
Its manifest content hash is
`eff8da9e4df0b93452c8d0bc660097399b369ce507639b3fa49c91f5d0f5062d`,
build timestamp `2026-08-11T15:30:22Z`, release commit
`8ebd85591586010b7b12db340bb7d21d15787ad9`, and tag object
`fe65b344adce3b598b668d0b2c5088f5515f2ec0`.

`VERIFY-PACKAGE.ps1` passed from a fresh extraction: 242 files, 3,073,787
bytes, manifest hash matched, package secret policy passed, and no `.codex` or
forbidden diagnostic content was present. Direct packaged-byte checks passed
for LF/CRLF canonical equivalence, non-newline tamper rejection, lone-CR
rejection, commit identity, and tag-object identity.

Disposable PostgreSQL initialization, packaged explicit migration through the
package migration CLI, exact head observation, synthetic seed, packaged backend
startup, readiness, packaged frontend serving, login, and same-origin API
gateway checks passed. Chromium publication smoke did not pass. After the
synthetic direct-operation persona authenticated and the packaged API returned
its expected `operational_shipment.create_direct` permission through both the
backend and same-origin gateway, the packaged UI failed the first mandatory
permission assertion because the Direct operation source was not rendered.
The run stopped immediately; accepted-quote, bilingual, console, and remaining
browser checks therefore have no passing result.

No branch or tag was pushed. Both remote refs remain absent. Disposable
backend, frontend gateway, Chromium, and private PostgreSQL processes were
stopped and test ports closed. The safety layer blocked recursive deletion, so
the disposable extraction remains at
`C:/Users/pc/AppData/Local/Temp/forwarder-v191-final-420f7687de5348cb8473d9fac341c5e2`.
Production was not accessed or changed. Publication and Production cutover
remain blocked.
Final classification: `RELEASE PUBLICATION BLOCKED — PRODUCTION CUTOVER NO-GO`.

## Packaged Chromium blocker closure investigation

Preflight reconfirmed branch `codex/pr-4a-dms-gate-repair`, release-source
commit `8ebd85591586010b7b12db340bb7d21d15787ad9`, local annotated tag object
`fe65b344adce3b598b668d0b2c5088f5515f2ec0` targeting that commit, version
`1.9.1`, sole Alembic head `20260819_v191_acceptance_corrections`, and absent
remote release branch/tag. Existing user-owned untracked material was preserved.

Read-only package investigation proved the ZIP, extracted release, and retained
runtime contain the same frontend bundle. The ZIP SHA-256 remains
`c69e265f5c27283807fd3f024ae3deba9d22abc720b615ff1fbaf5a83a16df0a`;
its canonical manifest content hash remains
`eff8da9e4df0b93452c8d0bc660097399b369ce507639b3fa49c91f5d0f5062d`.
The package bundle SHA-256 is
`1c3dfa0fdda7e13f623ea6b1f554e8263b56b2219346480442c580e24fe85e2a`
and contains the Direct implementation, its exact
`operational_shipment.create_direct` predicate, and English/Persian labels.
Stale or missing Direct code was rejected.

The preserved fresh-extraction Chromium result reproduced the blocker: all six
synthetic personas authenticated, but the first mandatory
`direct_only-direct-source` assertion failed. Direct backend and same-origin
gateway probes returned the expected permission. The component initializes
permissions to an empty array and renders Direct only when the operational
context request succeeds and the exact permission is present.

The source/package A/B comparison classified both fresh production output and
the immutable package as affected. Both were byte-identical because the plain
Vite build consumed the same ignored `.env.production`. Static bundle evidence
showed `VITE_API_URL=http://server.logisticmarket.ir` compiled into the asset,
contradicting manifest `api_base=same-origin` and diverting UI API calls away
from the disposable gateway. Development acceptance used the relative Vite
proxy and was not equivalent. Fixture/session, locale, feature flag, permission
normalization, frontend render logic, stale artifact, and harness-defect
hypotheses were rejected.

`ROOT_CAUSE=The release builder accepted an ignored local VITE_API_URL and
compiled an external API origin into an artifact declared and served as
same-origin, so New Operation never populated its permission state from the
packaged gateway.`

`DEFECT_CLASS=BUILD`

`AFFECTED_FILES=scripts/build_release_package.py, src/lib/env.ts,
src/lib/api.ts, backend/tests/test_release_publication_contract.py`

`TAG_IMPACT=STALE_IF_FIXED`

The minimum remediation pins the package build to the explicit
`__FORWARDER_SAME_ORIGIN__` build sentinel, resolves that sentinel to a relative
API base, removes the contradictory production-empty request failure, and
reuses the canonical API base for logo upload. Permission predicates and
backend authorization are unchanged. Regression coverage proves the builder
overrides contaminating local environment input and that the frontend retains
the same-origin contract.

Validation passed: focused New Operation tests (10), full frontend tests (125),
release/version pytest (13), TypeScript, ESLint (zero errors; 12 pre-existing
warnings), production build, Python compile, Ruff, source metadata, version,
sole Alembic head, and `git diff --check`. A builder-driven build contained no
`server.logisticmarket.ir` API origin, retained the Direct permission literal,
and produced `assets/index-DDHITCwo.js` with SHA-256
`b2b77b7032f6b59e3b4793709f690b03bd236c1fb397a3529064f47f34200df6`.

Independent gatekeeper result: `IMPLEMENTATION REVIEW — PASS`. The reviewer
confirmed the root cause, minimum fix, unchanged permission/security gates,
mandatory new release-source commit, stale-tag consequence, and mandatory
post-retag package/runtime/Chromium rerun. No package was rebuilt for
publication, no tag was moved, and no ref was pushed. The current
`Forwarder-v1.9.1-8ebd855.zip` remains blocked and must not be published.
`VERIFY-PACKAGE`, disposable runtime, packaged Chromium, and
`PACKAGED_DIRECT_SOURCE_RENDERING` remain not rerun because the tag is stale.
All run-owned disposable services were stopped; Production was not accessed or
changed.

Final classification: `RELEASE SOURCE CHANGE REQUIRED — HUMAN RETAG AUTHORIZATION NEEDED`.

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

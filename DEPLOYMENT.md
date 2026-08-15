# Forwarder 1.9.4 deployment preparation

Release baseline is immutable `v1.9.3.1` at `20260825_admin_multitenant`; target is `v1.9.4` at `20260826_org_document_policy`. Deployment requires separate Production authorization.

1. Verify the archive SHA-256, manifest, annotated tag, commit, and package contents with `VERIFY-PACKAGE.ps1`.
2. Expand the archive into a new immutable release directory; never overwrite the v1.9.3.1 directory.
3. Confirm `index.html` references hashed `/assets/` entries and never `/src/main.tsx`.
4. Preserve the existing secret-managed environment configuration.
5. Require current `20260825_admin_multitenant`, run the canonical check, and upgrade only in the approved change window.
6. Require target `20260826_org_document_policy`, activate the immutable v1.9.4 directory, and perform `SMOKE-TEST.md`.

Do not seed, backfill, or fabricate organization ownership. Follow `ROLLBACK.md` if acceptance fails.

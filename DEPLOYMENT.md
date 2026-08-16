# Forwarder 1.9.5 deployment preparation

Release baseline is immutable `v1.9.4` at `20260826_org_document_policy`; target is `v1.9.5` at `20260827_org_hostname`. Deployment requires separate Production authorization.

1. Verify the archive SHA-256, manifest, annotated tag, commit, and package contents with `VERIFY-PACKAGE.ps1`.
2. Capture current server state, verify the active v1.9.4 release, and complete database and document-storage backup checks.
3. Expand the archive into a new immutable release directory; never overwrite v1.9.4.
4. Confirm `index.html` references hashed `/assets/` entries and never `/src/main.tsx`.
5. Preserve secret-managed environment configuration and prepare the release runtime.
6. Stop Production safely, require current `20260826_org_document_policy`, and upgrade exactly to `20260827_org_hostname`.
7. Validate WSGI, switch the backend/IIS release, and perform `SMOKE-TEST.md`.
8. Only under server-phase authorization, create the Samand hostname mapping and configure DNS, IIS binding, and TLS.

Do not seed, backfill, or fabricate organization ownership. Follow `ROLLBACK.md` if acceptance fails.

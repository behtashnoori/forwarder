# Forwarder 1.9.5.1 hotfix deployment preparation

Release baseline is immutable `v1.9.5` at `20260827_org_hostname`; target is `v1.9.5.1` at `20260828_referral_state_compat`. Deployment requires separate Production authorization.

1. Verify the archive SHA-256, manifest, annotated tag, commit, and package contents with `VERIFY-PACKAGE.ps1`.
2. Capture current server state, verify active v1.9.5, and complete database and document-storage backup checks.
3. Expand into a new immutable release directory; never overwrite v1.9.5.
4. Confirm production `index.html` references hashed `/assets/` files and never `/src/main.tsx`.
5. Preserve secret-managed environment configuration and prepare the release runtime.
6. Stop Production safely, require `20260827_org_hostname`, and upgrade exactly to `20260828_referral_state_compat`.
7. Validate WSGI, switch the backend/IIS release, and perform `SMOKE-TEST.md`.

The migration preserves all referral state rows and only advances the PostgreSQL sequence when required. Do not edit or delete the nullable legacy state row.

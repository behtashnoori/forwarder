# Security Track completion — credential remediation and Alembic head

- **Date:** 2026-08-04
- **Status:** Complete in repository; Not Deployed
- **Accepted Alembic head:** `security_credential_remediation`
- **Parent:** `20260811_project_configuration`
- **Production:** Unchanged

## Historical migration decision

`20240926_add_password_to_expert_user` remains immutable and replayable. It originally added a nullable password column, assigned one fixed bcrypt value so existing rows could satisfy the new invariant, and then made the column non-null. Rewriting it would change established migration history and risk divergent databases.

The additive `security_credential_remediation` child revision disables only accounts whose hash is still exactly that historical shared value. It preserves every user row, ID, foreign key, relationship, hash, and audit/history record. It does not reset passwords. Downgrade intentionally does not reactivate a known shared credential.

## Executable credential and onboarding policy

Forwarder has no executable default credential. The legacy `backend/seed_experts.py` path is a compatibility refusal and creates no data. Obsolete credential creation, mutation, direct-password diagnostic, and shared-login helper scripts were removed. `scripts/setup-users.sh` and `scripts/setup-users.bat` now delegate only to the interactive `python manage.py create-admin` command.

The supported first-account path accepts an operator-supplied password through a non-echoing prompt, hashes it through the existing service, refuses duplicates, and writes one account atomically. Further users are created individually through the authorized administration surface. No setup, startup, migration, release, or deployment step invokes user Seed.

## Release and migration sequencing

The repository credential-policy verifier rejects shared plaintext defaults, executable password assignments, or the historical reusable bcrypt outside the immutable historical migration and its exact disabling remediation. The release security verifier combines that policy with an Alembic single-head assertion.

`security_credential_remediation` is the exact accepted parent for the first Release 1.9.0 migration. `20260812` remains unassigned and no Operational Execution migration exists. Release 1.9.0 is waiting only for its authorized bounded implementation, not Security Track remediation.

## Rollback and deployment boundary

Application rollback does not reactivate remediated accounts. Database downgrade of this security revision is a schema no-op because reactivation would restore the vulnerability. An authorized administrator may onboard or replace individual accounts through normal policy. This closure performs no deployment, Seed, data population, Production access, package, publication, tag, or push.

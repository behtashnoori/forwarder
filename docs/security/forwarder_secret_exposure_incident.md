# Forwarder secret exposure incident

- Discovery date: 2026-07-22
- Secret type: PostgreSQL connection URL
- Exposed locations: the former setup script template and environment setup documentation
- Secret value: redacted; never reproduce it in tickets, logs, patches, or documentation
- Rotation status: `CONFIRMED` by the authorized owner at `2026-07-22T21:15:01+03:30`
- Credential validity: the owner confirmed that the former credential was revoked
- Server action: `CONFIRMED` — the owner confirmed that the protected server environment was updated and application connectivity was validated without sharing the credential with Codex
- Current-tree remediation: credential-bearing examples and unsafe administrative defaults removed; install-time environment mutation removed
- Current-tree scan: `PASS`, including tracked and non-ignored untracked files, with zero unreviewed findings. Reviewed non-production fingerprints correspond only to legacy development defaults or documented fake fixtures; none matches the incident credential.
- History status: `HISTORY_CONTAINS_ROTATED_SECRET`
- History scope: 62 reachable refs (local branches, remote-tracking branches, and one tag) and 2,407 unique path-bearing objects reviewed; the redacted scan found 22 unique fingerprints across 75 historical blob occurrences. The incident credential remains reachable from remote refs and one tag.
- Potential impact: anyone with repository access could have recovered the former credential
- Owner action: completed; the owner confirmed revocation, external secret storage, and application connectivity
- Codex handling: Codex did not receive or test the replacement credential and did not connect to Production
- Incident status: `CLOSED_ROTATION_COMPLETE_HISTORY_RISK_ACCEPTED`
- Rotation closure: `CLOSED` — the exposed credential is confirmed rotated and revoked
- History disposition: `RISK_ACCEPTED` — the rotated credential remains in Git history under formal management acceptance
- History decision: `FORMAL_RISK_ACCEPTANCE_AFTER_ROTATION`
- Risk acceptance review date: `2026-10-22`
- Risk acceptance record: `docs/security/forwarder_historical_secret_risk_acceptance.md`

Codex performed no production connection, credential validation, deployment, restart, migration, seed, or server change as part of this remediation.

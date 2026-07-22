# Forwarder secret exposure incident

- Discovery date: 2026-07-22
- Secret type: PostgreSQL connection URL
- Exposed locations: the former setup script template and environment setup documentation
- Secret value: redacted; never reproduce it in tickets, logs, patches, or documentation
- Rotation status: `UNCONFIRMED`
- Credential validity: the former credential may still be active until the authorized server-side rotation mission proves revocation
- Server action: `PENDING` — rotate or revoke the PostgreSQL credential, update the protected server environment, and validate connectivity in the separate authorized server mission
- Current-tree remediation: credential-bearing examples and unsafe administrative defaults removed; install-time environment mutation removed
- Current-tree scan: `PASS`, including tracked and non-ignored untracked files, with zero unreviewed findings. Reviewed non-production fingerprints correspond only to legacy development defaults or documented fake fixtures; none matches the incident credential.
- History status: `HISTORY_CONTAINS_ACTIVE_OR_UNCONFIRMED_SECRET`
- History scope: 62 reachable refs (local branches, remote-tracking branches, and one tag) and 2,407 unique path-bearing objects reviewed; the redacted scan found 22 unique fingerprints across 75 historical blob occurrences. The incident credential remains reachable from remote refs and one tag.
- Potential impact: anyone with repository access could have recovered the former credential
- Owner action: the authorized database owner must revoke or rotate the former credential and confirm invalidation
- Incident status: `LOCAL_REMEDIATION_PUSHED_SERVER_ROTATION_PENDING`
- History decision: `PENDING_MANAGEMENT_DECISION`

No production connection, credential validation, deployment, or server change is part of this remediation.

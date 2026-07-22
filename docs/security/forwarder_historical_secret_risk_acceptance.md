# Formal risk acceptance — historical secret exposure

- Decision: `FORMAL_RISK_ACCEPTANCE_AFTER_ROTATION`
- Decision date: `2026-07-22`
- Review date: `2026-10-22`
- Decision owner: authorized repository management, recorded through the management decision in the current controlled Codex session
- Credential status: `ROTATED_AND_REVOKED`
- Current tree status: `CLEAN`
- History status: `HISTORY_CONTAINS_ROTATED_SECRET`
- History rewrite: deferred

## Scope

This acceptance covers the known historical exposure of the revoked PostgreSQL application credential in reachable Git history, including local branches, remote-tracking branches, and the existing tag inventory reviewed during Phase 0.1S. It does not authorize reuse of the former credential, exposure of the replacement credential, weaker repository access controls, or acceptance of any newly discovered secret.

## Rationale

The affected credential has been rotated and revoked, the replacement credential is stored outside the repository, application connectivity was confirmed by the authorized owner, and the current repository tree is clean. An immediate coordinated history rewrite would require a repository freeze, force-updating shared references, invalidating existing clones, and coordinated recovery by every consumer. Management therefore accepts the residual historical disclosure risk until the review date instead of performing that disruptive operation in this mission.

## Compensating controls

- The exposed credential is revoked and must never be restored or reused.
- The replacement credential remains outside Git and is supplied only through protected environment configuration or an approved secret manager.
- Redacted repository secret scanning runs for pushes and pull requests with read-only workflow permissions and immutable action pins.
- Local controls scan tracked files, non-ignored untracked files, and reachable history without printing secret values.
- Repository access and unexpected authentication activity must remain subject to operational review.
- Any new credential exposure, evidence that the former credential remains usable, or failure of repository scanning reopens the incident and invalidates this acceptance.

## Residual risk

The revoked value remains recoverable from existing Git history, remote references, tags, forks, caches, and previously created clones. Revocation prevents that historical value from authenticating to the intended database, but it does not erase the disclosure or eliminate risks caused by unknown copies, credential reuse outside the declared scope, or future control failure.

## Review and expiration

Management must review this acceptance no later than `2026-10-22`. The review must confirm continued revocation, repository scanning coverage, access controls, absence of credential reuse, and whether coordinated history rewriting has become proportionate. This acceptance does not start Phase 0.2 and does not authorize history rewrite, force push, tag deletion, or ref deletion.

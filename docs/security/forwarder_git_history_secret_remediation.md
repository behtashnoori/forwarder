# Git history secret remediation decision

Status: `FORMAL_RISK_ACCEPTANCE_AFTER_ROTATION`

Review date: `2026-10-22`

The redacted scan covered 62 reachable refs (local branches, remote-tracking branches, and one tag) and 2,407 unique path-bearing objects. It found 22 unique fingerprints across 75 historical blob occurrences. The result is `HISTORY_CONTAINS_ROTATED_SECRET`; the authorized owner confirmed credential revocation, external storage of the replacement credential, and application connectivity at `2026-07-22T21:15:01+03:30`. Codex did not receive or test the replacement credential. The repeated exposure was first observed in short commits `1b9aaa3d9d92`, `c4a13989413b`, and `74cf6b069e31`, depending on path, and remained present in later reachable history. It is reachable from remote refs and one tag. No secret value is recorded here.

The provider-specific scanners available to the team were not installed locally. A controlled redacted scanner confirmed the known exposure and candidate history, but does not justify a claim that every possible provider-specific or entropy-based secret class is absent.

## Option A: coordinated history rewrite

Use `git filter-repo` or BFG only after management approval, a temporary push freeze, secure backup, complete branch/tag inventory, and confirmed credential rotation. Coordinate force-pushes, require every user to re-clone, invalidate old clones, and rescan all refs. This mission does not perform a rewrite.

## Selected decision: no rewrite after rotation

Management formally accepted the residual historical exposure risk after confirmed rotation and revocation. Repository secret scanning remains enabled and the current tree remains clean. The governing record is `docs/security/forwarder_historical_secret_risk_acceptance.md`.

History rewriting is deferred. History rewriting, tag deletion, ref deletion, and force-pushing remain prohibited in this mission. Phase 0.2 is not started by this decision.

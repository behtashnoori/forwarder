# Git history secret remediation decision

Status: `PENDING_MANAGEMENT_DECISION`

The redacted scan covered 62 reachable refs (local branches, remote-tracking branches, and one tag) and 2,407 unique path-bearing objects. It found 22 unique fingerprints across 75 historical blob occurrences. The result is `HISTORY_CONTAINS_ROTATED_SECRET`; the authorized owner confirmed credential revocation, external storage of the replacement credential, and application connectivity at `2026-07-22T21:15:01+03:30`. Codex did not receive or test the replacement credential. The repeated exposure was first observed in short commits `1b9aaa3d9d92`, `c4a13989413b`, and `74cf6b069e31`, depending on path, and remained present in later reachable history. It is reachable from remote refs and one tag. No secret value is recorded here.

The provider-specific scanners available to the team were not installed locally. A controlled redacted scanner confirmed the known exposure and candidate history, but does not justify a claim that every possible provider-specific or entropy-based secret class is absent.

## Option A: coordinated history rewrite

Use `git filter-repo` or BFG only after management approval, a temporary push freeze, secure backup, complete branch/tag inventory, and confirmed credential rotation. Coordinate force-pushes, require every user to re-clone, invalidate old clones, and rescan all refs. This mission does not perform a rewrite.

## Option B: no rewrite after rotation

Accept residual history risk only when the old credential is conclusively revoked, repository access has been reviewed, future secret scanning is enforced, and management records explicit risk acceptance.

No option is selected automatically. History rewriting, tag deletion, and force-pushing are prohibited in this mission.

# Git / GitHub synchronization checkpoint through D1

Checkpoint date: 2026-09-20 (Asia/Tehran)
Evidence captured: 2026-09-20T16:08:22+03:30

## A. Checkpoint identities

```text
D1_PRODUCT_COMMIT = d0f2c57602d5d00320bb550935f9b9930d71f172
SYNC_EVIDENCE_COMMIT = SELF (the unique commit with subject
chore(git): record D1 synchronization checkpoint)
```

The evidence commit's exact immutable SHA is reported in the final handoff and is
also the final tip of `integration/golden-controlled`. A commit cannot contain its
own SHA because changing the file would change that SHA.

- Repository: `https://github.com/behtashnoori/forwarder.git`
- Authoritative worktree: `D:\1-webapp\15-forwarder-golden-20260921`
- Completed source branch: `codex/phase-d1-control-tower-backend`
- Canonical branch: `integration/golden-controlled`
- Upstream: `github/integration/golden-controlled`
- Starting canonical baseline: `b52741d8ff4b58071000c5416213d8d0b872e77b`
- C2 product commit: `2bbc369effb70ca428b1dfb23b987bd16b8634bf`

## B. Preconditions and lineage

Before synchronization:

- the D1 source branch HEAD was exactly the required D1 product commit;
- the worktree was clean;
- the canonical local and remote refs were both exactly the required baseline;
- the baseline was an ancestor of D1;
- the C2 product commit was an ancestor of D1;
- D1 added no migration;
- Alembic reported exactly one head: `20260923_notification_lifecycle`.

No squash, rebase, merge commit, history rewrite, or force push was used.

## C. Secret and artifact safety

The pre-push safety checks established:

- no staged, modified, or untracked files were pending;
- the baseline-to-D1 range introduced no environment file, production environment
  file, credential or key file, local database, PostgreSQL storage, runtime binary,
  build output, `node_modules`, virtual environment, or disposable temporary
  certification artifact;
- the D1 operational evidence report is the only evidence artifact in the product
  range and is intentional, durable repository documentation;
- a high-confidence scan of D1 additions found no private-key marker, AWS access
  key, GitHub token, OpenAI-style token, or JWT signature;
- a credential-assignment scan of D1 additions found no password, secret, API-key,
  or access-token assignment;
- the repository package-secret policy test suite passed: `13 passed`;
- `git diff --check` passed for the baseline-to-D1 range.

Historical archives, build output, and dependency directories already present at
the canonical baseline were not added or changed by D1.

## D. Canonical fast-forward and initial push

The checked-out canonical branch was advanced by `--ff-only` from:

```text
b52741d8ff4b58071000c5416213d8d0b872e77b
```

to the exact D1 product commit:

```text
d0f2c57602d5d00320bb550935f9b9930d71f172
```

The canonical branch was pushed explicitly to `github`; no temporary Codex branch
was pushed. Immediate verification after fetching from GitHub showed:

```text
local canonical SHA = d0f2c57602d5d00320bb550935f9b9930d71f172
remote canonical SHA = d0f2c57602d5d00320bb550935f9b9930d71f172
ahead/behind = 0/0
```

## E. Milestone tag

After confirming there was no conflicting local or remote tag, the following
annotated tag was created and pushed:

```text
tag = golden-controlled-d1-20260920
target = d0f2c57602d5d00320bb550935f9b9930d71f172
annotation = Golden controlled integration checkpoint through isolated Control Tower backend
```

The tag was not overwritten. Its dereferenced local and remote targets were
verified as the exact D1 product commit.

## F. Evidence-only commit

This report is the only file added after the D1 product commit. The evidence commit
contains no product, runtime, frontend, backend, test, or migration change. After it
is committed, the final canonical tip is pushed and local/remote equality,
ahead/behind, repository cleanliness, the unchanged Alembic head, and the unchanged
D1 product tree are verified again.

## G. Safety boundary

This checkpoint did not deploy, access Production, access secrets, modify a
database, change product code, change a migration, push a temporary Codex branch,
or begin D2. Shipment Detail and Notification behavior remain untouched.

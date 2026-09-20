# Git / GitHub synchronization checkpoint through C1

Checkpoint date: 2026-09-20 (Asia/Tehran)  
Evidence captured: 2026-09-20T13:47:17+03:30

## A. Local authoritative state

- Authoritative worktree: `D:\1-webapp\15-forwarder-golden-20260921`
- Required source branch before synchronization: `codex/phase-c1-notification-foundation`
- C1 product commit: `2d36f35d37a24d817a21c4e263ee59b6f19d0966`
- Canonical branch after synchronization: `integration/golden-controlled`
- Canonical branch starting point: exact C1 product commit above
- Alembic heads result: exactly one head, `20260922_notification_foundation`
- Worktree before branch, remote, tag, report, and push operations: clean
- Pending or untracked product artifacts before synchronization: none

No product file or migration was changed for this checkpoint.

## B. Remote identity

The pre-existing `origin` was retained unchanged as a forensic recovery source:

```text
D:\1-webapp\golden-forwarder-recovery-20260919\forwarder-golden-history.bundle
```

It is a local bundle, not GitHub, and was not used as the push target. A separate,
explicit remote named `github` was added after independent verification:

```text
https://github.com/behtashnoori/forwarder.git
```

GitHub reported the repository identity as `behtashnoori/forwarder`, default branch
`main`, public visibility. Authentication was active for the matching
`behtashnoori` account. Repository rulesets were empty, `main` was not protected,
and neither the proposed canonical branch nor milestone tag existed remotely before
publication.

## C. Commit lineage

Commit ancestry, rather than branch names, was used as the source of truth. Every
adjacent ancestry check below returned success, and every listed milestone is an
ancestor of C1:

| Stage | Commit | Subject |
|---|---|---|
| Golden planning | `2b95c35acc12e1ba28c390a125eb51f46af7dd4b` | `docs(governance): freeze controlled golden integration plan` |
| Phase A | `953a67ff5820864c08bc8727f34f49ed66237527` | `test(golden): freeze production regression contracts` |
| B1 | `a503d7b6473b90b01ff9a11c6e751375ff9f2121` | `feat(geography): reconcile governed location catalog` |
| B2 | `b523cc0b18fd48d93101de0430ec91d56a438c12` | `feat(presentation): unify business numeric formatting` |
| B3 | `d1dd6b60abc27846d563816c34b9aa4de190161a` | `feat(presentation): show existing transport summary` |
| B4 | `02acad646e2349296653bf0cf0bc5fe38519fb98` | `fix(requests): unify expert count and list scope` |
| B5 | `49e2ceecee6b6ddbead7ae735fe15ecb63ed4869` | `feat(quotes): add EUR currency support` |
| B6 | `b623f7fa7135caac69798def574556140f78191f` | `fix(tracking): remove retired add-unit action` |
| B7 | `b783052beead6fb5fb69fc34f796991208737b15` | `feat(locations): expose authorized private logistics points` |
| C1 | `2d36f35d37a24d817a21c4e263ee59b6f19d0966` | `feat(notifications): add inactive channel-neutral foundation` |

The resulting product lineage is linear:

```text
Golden planning -> Phase A -> B1 -> B2 -> B3 -> B4 -> B5 -> B6 -> B7 -> C1
```

No squash, rebase, merge, or history rewrite was performed.

## D. Secret and artifact safety result

The pre-push checks covered tracked files and the complete pending/untracked set.

- Pending/untracked files: none.
- Environment-named tracked files: `.env.example` only; no production environment
  file was tracked.
- Private-key markers: none.
- AWS access-key, GitHub token, OpenAI token, and JWT signatures: none.
- Credential-bearing database URLs were found only in test fixtures.
- Project package-secret policy: `13 passed`.
- No disposable PostgreSQL storage, local SQLite database, `node_modules`, Python
  virtual environment, certification temporary directory, or temporary build output
  was pending for publication.

Five historical ZIP artifacts are present in the inherited lineage:

```text
forwarder-production-20250928.zip
forwarder-production-20250929.zip
release-candidates/D2-VALIDATION-S7-RC-a257669-rg1-frozen-r4/D2-VALIDATION-S7-RC-a257669-rg1-frozen-r4.zip
release-candidates/D2-VALIDATION-S7-RC-a257669-rg1-frozen-r5/D2-VALIDATION-S7-RC-a257669-rg1-frozen-r5.zip
release-candidates/Forwarder-Windows-Runtime-S7-RC-a257669-r4.zip
```

The runtime archive contains expected Windows/Python runtime binaries. Archive-entry
name inspection found no environment, credential, private-key, SQLite database, or
PostgreSQL storage paths. The release archives were introduced by historical release
engineering commits already resolvable in the same GitHub repository before this
checkpoint. Current ignore rules prevent new release runtime ZIPs from being added.
They are therefore recorded as inherited legacy artifacts, not newly introduced C1
content or a newly disclosed secret.

## E. Canonical integration branch

`integration/golden-controlled` was created locally at the exact C1 product commit,
without squashing or rebasing. Its upstream is:

```text
github/integration/golden-controlled
```

The initial canonical-branch publication was verified at:

```text
2d36f35d37a24d817a21c4e263ee59b6f19d0966
```

The evidence-only commit containing this report advances the canonical branch but
does not alter the C1 product tree except for this report. Its immutable SHA is the
commit with subject `chore(git): record controlled integration sync checkpoint` and
is resolved directly from branch/commit metadata after creation.

## F. Branches intentionally not pushed

The following temporary milestone branches remain local forensic/work-history
references and were not pushed by this checkpoint:

```text
codex/golden-production-20260921
codex/golden-contract-freeze-phase-a
codex/phase-b1-governed-geography
codex/phase-b2-shared-numeric-presentation
codex/phase-b3-existing-transport-summary
codex/phase-b4-request-count-list-invariant
codex/phase-b5-eur-quote-support
codex/phase-b6-retired-tracking-action-removal
codex/phase-b7-private-point-selector-reachability
codex/phase-c1-notification-foundation
```

## G. Push result

The dry run reported a new remote branch with no overwrite. The canonical branch was
then published explicitly to the verified `github` remote and its upstream was set.
No `--force` or `--force-with-lease` option was used. No temporary Codex branch was
pushed.

The annotated milestone tag `golden-controlled-c1-20260920` was also published after
confirming repository tag usage and absence of a conflicting local or remote tag.

## H. Remote SHA verification

Immediately after the initial branch push:

```text
local C1 SHA:  2d36f35d37a24d817a21c4e263ee59b6f19d0966
remote SHA:    2d36f35d37a24d817a21c4e263ee59b6f19d0966
tag target:    2d36f35d37a24d817a21c4e263ee59b6f19d0966
```

The final canonical-branch tip is the evidence-only commit containing this report.
Its local and remote SHA equality is verified after the final push and reported in
the checkpoint handoff; the self-containing commit cannot embed its own SHA without
changing that SHA.

## I. Tag result

- Tag: `golden-controlled-c1-20260920`
- Type: annotated
- Annotation: `Golden controlled integration checkpoint through Phase C1 notification foundation`
- Local target: `2d36f35d37a24d817a21c4e263ee59b6f19d0966`
- Remote dereferenced target: `2d36f35d37a24d817a21c4e263ee59b6f19d0966`
- Existing tag overwritten: no

## J. Repository cleanliness

The repository was clean before synchronization. The only file created for the
checkpoint is this evidence report. No commit was created merely to move refs, and
no product or migration file changed. Final cleanliness is verified after committing
and publishing this report.

## K. Production safety statement

This checkpoint did not deploy, access Production, access Production secrets, modify
Production data, clean donor/recovery repositories, push donor/recovery repositories,
merge Control Tower, or begin C2.

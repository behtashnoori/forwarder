# Forwarder v1.10.0 writer/listener containment defect closure

Date: 2026-09-22  
Scope: deployment tooling only  
Deployment-tooling revision: `r5`  
Production access by Codex: **NO**

## Mission and authority

The mission closes only the asynchronous writer/listener teardown defect observed during the second Production Execute attempt. Human authority remains reserved for Production collection, backup, protected transfer, isolated restore proof, GO/NO-GO review, maintenance-window approval, recovery decisions, validate-only, and Execute. No Product behavior, Product package, migration, database schema, or business contract is changed.

Facts:

- Deployment tooling `r4` disabled and stopped the exact governed Scheduled Task, revalidated the captured Waitress PID and executable, force-stopped that PID, and immediately performed one `Get-NetTCPConnection` check.
- The observed Waitress listener outlived its task/wrapper parent and remained visible briefly after `Stop-Process` returned.
- The second attempt stopped before deployment-window backup and before migration, then Checkpoint A restored the previous application.
- Collector `r5` subsequently established healthy restored Production state, but Codex did not access or recollect Production during this closure.

Unknowns retained for the next human-operated gate:

- whether the existing pre-Execute backup/restore proof is still within the eight-hour freshness limit;
- the next collector `r5` result and its aggregate release-gate decision;
- the third, completely absent target timestamp;
- separate human GO and Execute authority.

## Root cause

`Stop-Process` completion and TCP listener disappearance were treated as synchronous. On Windows Server, process/socket state can remain observable for a short interval after the exact termination request succeeds. The single immediate port check therefore produced a false containment failure even though the scoped stop was correct. The defect was a missing bounded teardown wait, not insufficient kill scope.

The same immediate-stop/immediate-socket-check assumption existed in `Invoke-ForwarderV110RollbackContainment.ps1`; it is part of the same containment behavior and was corrected with the same bounded contract. No other matching teardown assumption was found in the v1.10.0 deployment tooling. Startup `Wait-Listener` is a separate activation wait and was not changed.

## r5 containment contract

The deployer and rollback containment tool now:

1. disable the exact governed Scheduled Task;
2. prove that the task is disabled;
3. stop the exact task;
4. re-read the captured listener PID and revalidate its exact executable plus Waitress command identity;
5. terminate only that proven PID;
6. poll every `250 ms` for at most `15,000 ms`;
7. require a continuous `2,000 ms` quiet period before PASS;
8. prove on every poll that the task remains disabled;
9. require the original PID to be gone or to no longer own the governed port;
10. require `127.0.0.1:$BackendPort` to have no listener; and
11. fail immediately if any different PID appears on the governed port, recording `replacement_not_terminated=YES`.

The only production-path termination primitive is `Stop-Process -Id <captured listener PID> -Force` after exact identity revalidation. There is no process-name lookup, Python-wide termination, taskkill, killall, replacement-PID termination, force bypass, or containment bypass.

Containment returns PASS only with all four durable evidence fields true:

- `writer_containment_task_disabled`
- `writer_containment_original_listener_terminated`
- `writer_containment_governed_port_free`
- `writer_containment_no_replacement_listener`

The baseline also records process-gone/port-released detail, poll count, timeout, polling interval, quiet period, and confirmation time.

## Ordering and recovery proof

The executable sequence remains:

```text
stage
→ writer containment
→ deployment-window backup
→ migration
→ post-migration assertions
→ Scheduled Task/runtime cutover
→ IIS cutover
→ health/readiness
→ post-deploy verification
```

`Inject 'BACKUP'` and all deployment-window backup code remain after the successful `Invoke-WriterContainment` return and four PASS outputs. `Inject 'MIGRATION'` remains after verified backup evidence. A containment timeout or replacement listener throws before either gate. Because `$migrationComplete` remains false, the existing catch path re-registers, enables, and starts the prior task and emits `ROLLBACK_CHECKPOINT=A` plus `PRIOR_APPLICATION_RESTORED=YES`.

## Regression qualification

Windows PowerShell version: `5.1.26100.9168`.

The release-tooling suite result was `35 passed`. The five production-migration PostgreSQL rehearsals were also collected and reported as `5 skipped` because no owned disposable `FORWARDER_V110_PRODUCTION_TOOLING_POSTGRES_URL` was supplied; this closure changes no migration or database behavior. Ruff and `git diff --check` passed.

Coverage:

| Required case | Evidence |
|---|---|
| A. Delayed listener teardown | Actual containment loop observes the original PID for multiple polls, then requires the quiet period and passes. |
| B. Teardown timeout | Bounded fixture remains owned by the original PID; containment fails after the test timeout, backup/migration do not run, and Checkpoint A restores state. |
| C. Replacement listener | Original PID disappears and PID 84 binds the port; containment fails immediately with `replacement_not_terminated=YES`; stopped PID inventory contains only the original PID. |
| D. Orphan listener | A real loopback Python listener is started by a launcher that exits; PowerShell 5.1 proves the parent absent, revalidates the exact PID/executable/Waitress-shaped command, terminates it, and proves socket teardown. |
| E. Task state | Poll-time task-state checks and baseline evidence prove the governed task remained disabled through successful containment. |
| F. Ordering | Dynamic failure assertions and source-order assertions prove no deployment-window backup or migration before containment PASS. |
| G. Checkpoint A | Timeout and replacement failures both preserve pre-migration state and exercise Checkpoint A restoration. |
| H. PowerShell 5.1 | All scripts parse under Windows PowerShell 5.1; the native containment self-test and fixture execution run under 5.1. |

Native self-test outputs:

```text
NATIVE_ORPHAN_LISTENER_PARENT_ABSENT=PASS
NATIVE_EXACT_PID_SOCKET_TEARDOWN=PASS
PRODUCTION_MUTATION_PERFORMED=NO
```

Frozen package verification outputs:

```text
PRODUCTION_PACKAGE_VERIFICATION=PASS
PRODUCTION_PACKAGE_SHA256=2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf
PRODUCT_VERSION=1.10.0
APPLICATION_COMMIT=e36ee7cee157657c97dc42a539eaf1909f510a33
DATABASE_REVISION=20260926_fixed_shipment_responsible_expert
```

## Artifact identity and determinism

Primary build and independent qualification rebuild are byte-identical:

```text
dc836c66abf5eaa3c2cd2fab16d31fcc27c3eadf9a0caeddebc9251824701ade  primary ZIP
dc836c66abf5eaa3c2cd2fab16d31fcc27c3eadf9a0caeddebc9251824701ade  independent rebuild ZIP
```

Final paths:

- expanded bundle: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r5\`
- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r5.zip`
- independent rebuild: `D:\1-webapp\forwarder-production-qualification-r5-20260922\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r5.zip`

Hashes:

```text
dc836c66abf5eaa3c2cd2fab16d31fcc27c3eadf9a0caeddebc9251824701ade  Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r5.zip
0c2b02935ab19c1207bb189a6ce695c73006e1f89b3773f863713a302073c4bf  BUNDLE-INVENTORY.json
d49984ee9fe8853c87d491b32ebc5327ba1d671df23f6f637a3856f358a1196a  SHA256SUMS.txt
2e6d2e169732786be56ac803d67a6c4dc33d005d395120a526d0124b7245c219  Deploy-ForwarderV110Production.ps1
b71670c877eb70b441602dffec83ededb39b9105854ab73ad3985fe870ca829e  Invoke-ForwarderV110RollbackContainment.ps1
718dfb14c00ab6009481dbaec472d6eb753cc095cc39c91de57d2b313c82d3b4  BUNDLE-MANIFEST.json
2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf  Forwarder-Production-v1.10.0-e36ee7cee157.zip
```

All `SHA256SUMS.txt` entries reverified successfully. The frozen Product ZIP was copied byte-for-byte and was not rebuilt.

## Preservation and governance reconciliation

- Product code and package: unchanged.
- Database migrations/schema: unchanged; no `backend/migrations` diff exists.
- Collector `r5`: unchanged. Source and already-qualified r5 bundle hashes both equal `2d00de1d52f02a0fb970cc462bf31f4f598353252a05a8680f9b3bb619b49bcd`.
- Failed target `release-20260922060617-20260926_fixed_shipment_responsible_expert`: preserve, do not reuse, do not manually delete.
- Failed target `release-20260922081228-20260926_fixed_shipment_responsible_expert`: preserve, do not reuse, do not manually delete.
- Next target: must be a third, completely absent timestamped path.

LPAF v2.2 remains the active normative baseline and its Agent Entry Protocol was applied at Level B Product/Production rigor. Authority and release ownership remain human-reserved. The frozen Product package owns application bytes; tooling `r5` owns only deployment/rollback control behavior. Production remains the System of Record for state, data, and history. Module/public contracts, domain behavior, migration compatibility, predecessor/target heads, data ownership, and history ownership are unchanged. Failure and denial paths fail closed; replacement listeners are not killed; Checkpoint A and post-migration containment semantics remain intact. Exact-byte release evidence binds the revision, manifest, inventory, checksums, source identity, database heads, and frozen package.

Reviewed v2.3 Product Integration guidance yields `REFERENCE_IMPACT = NONE`: this is a non-user-facing deployment-control correction with no capability, navigation, RBAC reachability, public API, domain, data, or product-surface change. The evidence link is this closure record plus the r5 manifest. No Folder 29 update is required. No unresolved governance conflict remains.

## Next operator step

Rerun the unchanged read-only collector `r5`. Check the exact eight-hour backup/restore freshness gate. If stale, repeat the full fresh governed backup, protected transfer, isolated PostgreSQL 18 restore/migration proof, restore-evidence return, and collector `r5`. Obtain `READY_FOR_SEPARATE_GO_REVIEW`, then perform final validate-only with the corrected r5 deployment tooling and a third completely absent target. Stop for a separate human GO after validate-only. No Execute command is authorized or provided by this closure.

WRITER_CONTAINMENT_TOOLING_CLOSURE=PASS

NEXT HUMAN STEP — PREPARE THIRD RELEASE ATTEMPT

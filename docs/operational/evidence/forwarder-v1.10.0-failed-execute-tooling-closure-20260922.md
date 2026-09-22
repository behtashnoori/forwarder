# Forwarder v1.10.0 Failed-Execute Tooling Closure — 2026-09-22

## Governance and bounded authority

The active governing baseline is LPAF v2.2 and its mandatory Agent Entry Protocol. This is a Level B Production-release tooling mission covering M0/M1, M6, M7, and M9. The reviewed v2.3 Product Integration and `REFERENCE_IMPACT` guidance is applied as a strong default. Product code, Product package bytes, migrations, business behavior, database schema, the qualified `r5` collector, and Production access or deployment are outside this closure.

**FACT:** the first Execute attempt entered writer-containment startup and failed before containment completed or migration began with `Cannot overwrite variable PID because it is read-only or constant`. Windows PowerShell variable names are case-insensitive, so local `$pid` resolves to built-in constant `$PID`.

**FACT:** Checkpoint A reported `PRIOR_APPLICATION_RESTORED=YES`. The operator-supplied post-failure `r5` result proved the prior release, task, listener, IIS path, health/readiness, and baseline database revision remained active and consistent; no migration ran.

**FACT:** a Windows PowerShell 5.1 AST scan across every v1.10.0 Production PowerShell tool found only this one automatic/read-only definition conflict. `$PSScriptRoot`, `$Matches`, and other automatic variables are read only in their intended roles.

**FACT:** the abandoned target exists and therefore fails the deployer's mandatory target-absence gate. The Checkpoint A contract says to abandon the candidate, and no governed cleanup action is defined.

**ASSUMPTION:** the failed target remains unchanged on Production as reported by the human operator. Codex did not inspect Production.

**UNKNOWN:** future fresh backup identity, restore-proof identity, final `r5` result, new absent target timestamp, GO decision, and maintenance-window authority do not yet exist.

**DECISION NEEDED:** after new evidence produces `READY_FOR_SEPARATE_GO_REVIEW`, the release authority must separately decide whether final zero-mutation validate-only may run. A later Execute remains a separate human decision.

## Root cause and bounded correction

Deployment tooling `r3` used `$pid` for the listener owner in the non-fixture containment branch. Windows PowerShell 5.1 treats it as `$PID`, a constant automatic variable, and rejected the assignment after staging had begun. Revision `r4` renames the binding to `$listenerPid`, places all writer-containment behavior in one exercised function, and emits `WRITER_CONTAINMENT=PASS` only after containment completes. Task disable/stop, exact listener ownership validation, scoped process stop, zero-listener gate, backup ordering, migration ordering, and rollback semantics are unchanged.

Permanent regression protection now:

- parses all Production PowerShell tools with Windows PowerShell 5.1;
- derives read-only/constant variables from that runtime and adds the relevant automatic-variable set;
- rejects case-insensitive assignment, parameter, or foreach definitions that collide with the protected set;
- executes the shared writer-containment function under Windows PowerShell 5.1;
- injects failure at the next `BACKUP` boundary and proves containment passed the former failure site;
- proves the database remains at the starting revision, no deployment-window backup or migration occurred, Checkpoint A restored the prior application, and the staged target remains as abandoned evidence.

## Qualification

- Production tooling tests: `31 passed`.
- Disposable PostgreSQL 18 integration tests: `5 passed`.
- Explicit Windows PowerShell version: `5.1.26100.9168`.
- Windows PowerShell 5.1 parse: PASS.
- Automatic/read-only variable AST gate: PASS.
- Backup URL support and secret-safe `PGSSLMODE`: PASS.
- Exact pre-Execute evidence gate: PASS.
- Post-containment deployment-window backup gate: PASS.
- Migration ordering and Checkpoint A/B/C behavior: PASS.
- Post-deploy fixture verification: PASS.
- Python compile and Ruff: PASS.
- Independent deterministic `r4` rebuild: byte-identical ZIP and SHA256 PASS.
- Production access/mutation/deployment by Codex: NO / NO / NO.

## Final r4 artifact identity

- Expanded bundle: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r4\`
- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Production-Deployment-Bundle-e36ee7cee157-r4.zip`
- ZIP bytes: `23017072`
- ZIP SHA256: `70fca5cf896408b1710fc5676b15cf826bb8aacc24251477413475d1da5cb337`
- Expanded file count: `12` including inventory and checksum records.

Expanded checksums:

```text
d18ca29d91553e088799c3a78ff838f3c884de48e0593d0710a7111593a47a6e  BUNDLE-INVENTORY.json
2791c6db08bfc569ee6bbc6a45ceb241fe53c1faece90922450b0dc26dcf6364  BUNDLE-MANIFEST.json
f5fd1d30df12e267baecdf4ad448da5dd74585031e16f33cd96653159a166490  Deploy-ForwarderV110Production.ps1
2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf  Forwarder-Production-v1.10.0-e36ee7cee157.zip
06cbe84c394a321aa0a30cba56b9633bb28c0947a52be9a368ec56e4f22d09ca  Forwarder-Production-v1.10.0-e36ee7cee157.zip.sha256
a04fb2694314dc1e1d1e0c76e4245179fbc0d2f376f5d19c6b3651a3b4d8739e  Invoke-ForwarderV110RollbackContainment.ps1
7311903106823571921777b02634f19795b3e2d29251f33cadbf16a0f31791a9  New-ForwarderV110PreDeploymentBackup.ps1
b56f6a41032f26f81c73fe0d3d2b8b85567e569f0605c83043b683cc8c1f6db5  README-FIRST.md
dba81a11eb3c620cd92c546648a92ccfe0a0c100e76785e28fad8e04232bf5ea  SHA256SUMS.txt
09f39e80054a064547778ae894a566c8a04602468509ab001da7c24f4851d626  sql/post-migration-assertions-readonly.sql
650a49409039618b0d222f5143b24791ee88d977f19777a5ce19d683ef5801df  Verify-ForwarderV110PostDeploy.ps1
a4269df362a2ba352ef78a4d243c96f2ccee35e96d88a6d1586359e37ab1367d  Verify-ForwarderV110ProductionPackage.ps1
```

The frozen Product package SHA256 remains `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`. No Product or migration file changed. Collector `r5` remains byte-identical to its qualified bundle at SHA256 `2d00de1d52f02a0fb970cc462bf31f4f598353252a05a8680f9b3bb619b49bcd`.

## Failed target and next-attempt evidence

The failed target `C:\1-webapp\forwarder-production\release-20260922060617-20260926_fixed_shipment_responsible_expert` is preserved as failed-attempt evidence. It is not active, not reusable, and not manually deletable under the current contract. A new timestamped absent target must be generated for the final future validate-only.

The earlier pre-Execute backup was already approximately 6.99 hours old against an 8-hour maximum at the post-failure observation. It must not be reused for a second attempt. The required sequence is:

1. fresh governed Production backup;
2. protected transfer of exact dump and sidecars;
3. isolated PostgreSQL 18 restore;
4. exact five-migration rehearsal and read-only assertions;
5. return the restore-evidence sidecar to the protected backup root;
6. run collector `r5` and obtain `READY_FOR_SEPARATE_GO_REVIEW`;
7. separate human review;
8. final validate-only using deployment tooling `r4` and a new absent target;
9. separate human GO before any future Execute.

No Production Execute command is supplied by this closure.

## LPAF and reference impact

Authority remains human-reserved for Production backup execution, evidence transfer, GO, maintenance window, database recovery, and Execute. The frozen Product package owns application bytes; `r4` owns only the corrected operator entrypoint. Production retains state/data/history ownership. Migration compatibility and target heads are unchanged. Negative paths, Checkpoint A recovery, post-migration containment, no blind downgrade, no automatic Production restore, exact artifact identity, evidence completeness, and the Product/tooling release boundary are all preserved.

`REFERENCE_IMPACT_FINAL=NONE` because this closure changes only Forwarder-specific release tooling, tests, bundle metadata, and operational evidence. It does not change Product capability, product surface, domain/data/SOR/reference truth, architecture boundary, runtime business behavior, migrations, or Folder 29. No unresolved LPAF conflict remains.

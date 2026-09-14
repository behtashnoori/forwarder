# Canonical release state lifecycle audit

Application: `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`.
The previous canonical ZIP and its SHA are invalidated by the reported server failure.
No product source, production system, or Docker execution is involved in this repair.

## Reproduced escape

On Windows PowerShell 5.1, run the old extracted `QUALIFY-REAL-EXECUTE.ps1`,
then invoke `deploy_windows_iis_waitress.ps1 -PackageRoot $root -ValidateOnly`
in the same process. The first command returns all its old PASS markers. Its
finally block removes `ForwarderExecuteState`, but its `function global:`
definitions survive. The next deployment resolves `Get-Website` to the leaked
mock and throws exactly:

`The variable '$global:ForwarderExecuteState' cannot be retrieved because it has not been set.`

The old deployment source itself contains no reference to that global. The old
harness ran ValidateOnly before Execute, never tested the operator's next
invocation, never checked mock-function lifetime, and accepted PASS strings that
the deployment printed itself. A fresh deployment process would not contain
these leaked mocks, so the reproduced failing process is specifically the
post-qualification dirty shell. The new suite covers both paths explicitly.

## Active PowerShell surface

Every root PowerShell file shipped by the builder is parsed by
`AUDIT-STATE-LIFECYCLE.ps1`: deployment, package verifier, certification driver,
real ValidateOnly test, real Execute test, and the auditor itself. It records
every variable's declaration/reference, initializers, first read, writers,
readers, and enclosing function/conditional/try/catch contexts. `-ReportPath`
writes the full per-variable JSON. The audit rejects global/script variable
references and exported global/script functions anywhere in the AST, including
unexecuted branches. The deployment also cannot use variable cmdlets to inspect
ambient test state. Environment variables and PowerShell automatic variables
are distinguished from mutable deployment state by their native lifetimes.

| State | Declaration and initialization | First read / readers / writers | Cleanup and path safety |
|---|---|---|---|
| PackageRoot, modes, confirmation, fixture path, environment/release paths, FailAt | Bound script parameters before any function call | Mode/root checks and explicit helper calls; resolved PackageRoot written before discovery | Invocation scope; both modes reject incompatible arguments before discovery |
| RequiredBefore, RequiredTarget, Timeouts | Unconditional assignments before helper definitions | Discovery, migration, target construction, waits, rollback | Invocation scope; available on every reached path |
| state | Assigned from exactly one fixture or real-discovery branch | Baseline and DB gate; Execute updates DB/fixture fields; Save and Rollback receive it explicitly | No reads before discovery returns; failed discovery never enters rollback; ValidateOnly returns before mutation |
| before, oldPython | Assigned after successful discovery/package verification | Baseline gate, target XML, rollback | Passed to Rollback; all initialization precedes the mutation try/catch |
| migrationNeeded | Both DB-gate branches assign boolean | Execute migration branch only | Unknown lineage throws first; ValidateOnly returns before use |
| target, targetPython, oldRoot | Derived after ValidateOnly return and before mutation try | Materialization, task switch, ownership checks, rollback | Execute only; rollback receives targetPython explicitly |
| mutationStarted | False before try; true immediately before task cutover | Catch decides whether rollback is legal | No catch can read it before assignment; pre-cutover failures do not roll back running services |
| primary | Catch assigns the error before rollback | Final throw and compound rollback-failure message | Catch scope; preserves primary and secondary failures independently |
| site/task/xml/rows/owners/runtime/process/revision/healthResponse | Function-local assignments; runtime explicitly null before optional listener branch | Discovery validates counts before indexing, process identity before consuming it, migration output before substring | Discovery scope; no cleanup reads on a failed discovery |
| migration process/info/stdout/stderr/result/limit | Process allocated before try; streams/limit assigned after successful start | Bounded wait, exit check, output parsing | Finally disposes only the already-allocated process; output tasks read only after initialization |
| listener/health deadlines, response, rows/owners/process | Each helper initializes per call/per iteration | Bounded loops; counts guard owner indexing | No retained state across invocations; error path exits or retries without reading an unset response |
| path/XML/regex temporaries | Function parameters or assignments before use | Match/count checks guard captures and array access | Function scope; no cross-mode state |
| fixture stateFile/temp/reset state/result/rejected | Certification driver initializes before test calls; rejected reset per case | Fixture matrix checks both revisions, unknown revision and every failure stage | Own temporary directory removed in finally; fixture objects never reach real discovery |
| simulation | Local object initialized before adapter functions are invoked | Read-only adapters observe it; mutating adapters update object fields; matrix asserts real Execute/rollback results | Child process and script scope; no global mocks, no dangling readers |
| mutations | Local hashtable allocated before ValidateOnly adapters | Every write-capable adapter increments Count and throws; count checked after exact invocation | Object avoids scalar child-scope increment shadowing; DB SHA independently detects writes |
| previous environment/location values | Captured before disposable setup/invocation | Finally restores DATABASE_URL, APP_ENV, FW_TEST_DATABASE and working directory | No inherited production database is used; no production environment file is read by tests |
| ForwarderExecuteState sentinel | Deliberately planted only by test Set-Variable after an unset-state validation | Repeated/Execute/rollback validation must ignore it; value equality checked | Removed in isolated child; production has zero references to it |
| verifier metadata/manifest/checksum maps | Loaded/allocated before comparisons/iteration | File layout/hash/lineage checks | Read-only invocation scope; malformed/missing inputs throw before dependent reads |
| auditor AST/results and child-process output | Explicit initialization before parse/launch | Error count, marker and exit-code checks | Local scope; no inherited qualification variables |

There is no trap handler in the active surface. Rollback only receives state
after its initialization boundary. Finally blocks reference resources created
before their try blocks. Active production code has zero global/script mutable
references rather than blanket null initialization or fake Production state.

## Wider repository inspection

`-RepositoryInventory -ReportPath ...` inventories all tracked PowerShell files,
including historical deployment copies, not merely files matched by a current
filename convention. At the initial scan there were 42 files. Archived packages
are not edited, rebuilt, or executed as part of this canonical release.

The only other scoped-state families are:

* ADR-043 read-only preflight: collection counters are initialized in script
  scope before their function readers; scheduled/frontend release and proxy
  values have explicit initial values before conditional discovery. A sibling
  local-state defect was repaired: database identity output is now guarded by
  the same DATABASE_URL condition that initializes its fields, and absence is
  reported as a collection error rather than reading unset variables.
* Historical UAT/S7 deploy scripts and their archived copies: State, Mutated,
  counters, Evidence, startup/ownership flags are initialized before try/catch.
  Root/path values are assigned in the real/simulation branches before helpers;
  backup paths/hash precede Mutated=true; recovery reads them only after that
  flag. Startup evidence is guarded by initialized StartupAttempt and startup
  state. These scripts are excluded from the canonical package.
* Local database cutover: PlainPassword=null, PasswordBstr=Zero and State are
  explicitly initialized before try; finally clears the password and only
  frees a nonzero BSTR. No unset cleanup reads were found.

All other tracked scripts have no global/script/local-qualified mutable state;
their local parameter/assignment/conditional/handler references are retained in
the repository inventory. Historical revisions do not become newly certified
production entry points by being inventoried.

## Qualification requirements

Fresh validation runs in `powershell.exe -NoProfile -NonInteractive`, requires
5.1 and StrictMode, proves no Forwarder globals exist (including the explicit
Get-Variable absence probe), changes to an arbitrary temp directory and invokes
the exact packaged deployment command without FixtureStatePath. Only OS boundary
commands are local adapters; package verification and migration CLI code run
unchanged against a disposable SQLite database. Six mutation categories are
asserted, including a database checksum. No Production connection is made.

The dirty-child matrix covers unset/stale globals, repeated ValidateOnly,
post-Execute and post-failure/rollback ValidateOnly; all 16 fixture failure stages
and 15 real-code failure stages (the migration branch is exercised by the
fixture migration matrix) plus rollback-failure reporting. Certification checks
that no old-style global reader function leaked, then runs fresh validation
again. Negative AST tests seed global/script reads into normal, conditional,
function and finally paths and require rejection.
Failure-injection catches also require the exact requested stage error; an
unrelated exception cannot count as a successful injection. Two executable
mutation tests replace the injection with an unset ForwarderExecuteState read
or an unrelated exception and prove the matrix stops without a PASS marker.
The stricter catches exposed an additional harness defect: long temporary
directory names caused PowerShell 5.1 Copy-Item path-length errors before the
requested cutover stage. Disposable roots and per-case subdirectories now have
short names. This changes only test paths; deployment code and its real copy
operation are exercised unchanged. The rollback-failure assertion preserves
the actual unexpected exception when reporting a failed test.

All checks are required by both preview and post-freeze clean-ZIP-extraction
certification. A new ZIP is built only after preview passes and the single
tooling-only commit is frozen. The exact ZIP's metadata, migration inventory,
checksums and corruption rejection matrix are then certified.

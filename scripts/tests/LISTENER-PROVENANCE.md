# Scheduled Task launcher ownership

Application stays frozen at `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`.
The previous canonical ZIP SHA256
`81388fcff81b2471137a18cd3fde99c5dc0aa09734adb5f01f7a8378febe82ad`
is invalidated. Its task parser required direct backend module arguments and
its qualification repeated that false assumption in the task action.

The authoritative chain is:

`Scheduled Task -> C:\Windows\System32\cmd.exe /d /c -> <release>\runtime\python.exe -> C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py serve --repo <release> -> spawned <release>\runtime\python.exe -m waitress --listen=127.0.0.1:5101 backend.wsgi:app`.

The task parser verifies the approved system command and runtime launcher,
`serve`, exactly one `--repo`, the release-local runtime and matching working
directory. It parses quoted tokens and cmd's outer quote pair separately,
supports namespaced task XML and paths with spaces, and refuses ambiguous
actions, shell programs, duplicate options and mismatched endpoint options.
The external environment and optional log remain launcher options. The task
does not need backend module arguments. Those belong to the listener process.

Task replacement changes only the parsed runtime token, `--repo` value, and
working directory. It retains the approved external launcher, environment,
log, task settings and registration metadata. The original XML is retained
verbatim for rollback. Path comparison remains case-insensitive on Windows.

The Scheduled Task is a launcher: a successful invocation can finish and leave
its Waitress child listening. `Ready` and `Running` both support an official
backend. Task State and LastTaskResult are diagnostic observations only.

Read-only discovery requires the unique Production task, an explicit true
Settings.Enabled value, one supported Execute/Arguments/WorkingDirectory action
consistent with the exported rollback XML, and the release-local runtime
identified by that action. The IIS physicalPath must be that release's `dist`.
The loopback listener must have exactly one unique PID, a readable
Win32_Process.ExecutablePath matching the configured runtime, a Waitress backend
command line, and internal HTTP 200. The expected child command is the exact
five-token command produced by the approved launcher's `serve` implementation.
Duplicate rows for one PID are accepted.
An unreadable or inconsistent identity stops without changing the server.

| Captured condition | Result |
| --- | --- |
| Enabled Ready task, LastTaskResult 0, matching listener, HTTP 200 | Official backend |
| Enabled Running task, matching listener, HTTP 200 | Official backend |
| Ready task, listener from another release | Orphan/mismatched runtime |
| Disabled Ready task with listener | Explicit stale/orphan refusal |
| Missing task with listener | Orphan refusal |
| Valid task without listener | Backend unavailable |
| Multiple unique listener PIDs | Refuse ambiguous ownership |
| Matching listener with bad health or failed request | Unhealthy; provenance still matches |

Qualification runs the exact packaged non-fixture ValidateOnly entry point in
a fresh Windows PowerShell 5.1 process from an unrelated directory. Only Windows
server boundaries are simulated. Package verification and the packaged runtime's
read-only migration CLI run unchanged against a disposable SQLite database.
Production is never contacted. The captured topology uses the supplied release
`C:\1-webapp\forwarder-production\release-forwarder-systemic-workflow-b4294fc-20260913222754`,
listener PID 93244, Ready state, LastTaskResult 0, matching action and executable,
the approved external runtime launcher with `serve --repo`, aligned IIS and
HTTP 200. It contains no direct backend module invocation in the task action.
Every topology case asserts exact outcome, zero server
mutation calls, unchanged observed topology and unchanged database SHA256.

A separate local OS test runs real system cmd.exe, a disposable copy of the
unchanged packaged runtime, the captured helper's `serve`/`os.execv` mechanism,
and a minimal WSGI health app. It verifies the parent chain, successful cmd
return while the child remains alive, one real loopback PID, Win32_Process
executable/command, and HTTP 200. Paths are rebased to a temporary release using
Production's no-space naming pattern. The externally managed helper's Windows
`os.execv` mechanism does not quote space-containing argv paths; no external
helper or product source is changed here. Task XML quoting/normalization is
tested separately. The OS test does not register a task or contact IIS.

Execute qualification also models a launcher remaining Ready while its child
survives Stop-ScheduledTask. It must stop the verified exact child PID before
task replacement, then rediscover a matching Ready launcher after Execute and
each rollback. Listener verification during Execute and rollback uses the same
executable and child-command checks as baseline capture. Listener stop paths
recheck both before terminating the unique PID. Recovery also rechecks the
enabled task and parsed launcher runtime, then internal health.
`QUALIFY-LAUNCHER-CHAIN.ps1` loads the exact shipped function definitions to
exercise those paths, validates XML field preservation, and rejects direct
backend assertions in every task ownership helper. The fixture migration
branch, all 16 fixture failure stages,
15 non-fixture failure stages, rollback failures, state lifecycle checks and
one-pass operator sequence remain mandatory. The real migration command's
upgrade branch is not run against Production; migration simulation is local.

Package checksum verification now precedes discovery, so the packaged database
runtime cannot execute before its bytes are checked. A negative regression
rejects a deliberately invalid package before any server discovery. Fresh child
harnesses explicitly load the PowerShell utility module before installing server
adapters, and retain the complete native child error output before reporting a
failure. Neither adjustment weakens failure or zero-mutation assertions.

Both pre-commit preview and extracted final-ZIP certification require every
ownership, baseline, non-fixture validation, zero mutation, Execute, failure,
rollback, operator and package integrity marker. No final certificate is issued
when any required marker is missing or any command exits unsuccessfully.

Sibling audit: the canonical baseline, scheduled-task parser, Execute,
listener wait, pre-stop recheck, rollback and final validation now share this
model. The older full-app/certified/S7 builders and tests, and the untracked
baseline alignment utility, were inspected as historical tools. They are not
inputs to this builder or shipped entry points. Their runtime/command checks
do not require the task action to contain a direct backend invocation. The
ADR-043 inventory reports task state diagnostically; it has no ownership gate
requiring Running. Old ZIPs and old extracts remain historical evidence and
are not rewritten or recertified. The zero direct-task-assumption marker
applies to the active canonical operational tooling and shipped package.

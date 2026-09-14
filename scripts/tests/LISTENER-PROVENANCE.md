# Scheduled Task launcher ownership

Application stays frozen at `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`.
The previous canonical ZIP SHA256
`cbfb13da4bd71c15b592751f47fdb26043efa558870580476f2f637d53640153`
is invalidated. Its discovery logic rejects the captured Production topology
with `orphan Waitress listener: scheduled task is not running`.

The Scheduled Task is a launcher: a successful invocation can finish and leave
its Waitress child listening. `Ready` and `Running` both support an official
backend. Task State and LastTaskResult are diagnostic observations only.

Read-only discovery requires the unique Production task, an explicit true
Settings.Enabled value, one supported Execute/Arguments/WorkingDirectory action
consistent with the exported rollback XML, and the release-local runtime
identified by that action. The IIS physicalPath must be that release's `dist`.
The loopback listener must have exactly one unique PID, a readable
Win32_Process.ExecutablePath matching the configured runtime, a Waitress backend
command line, and internal HTTP 200. Duplicate rows for one PID are accepted.
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
aligned IIS and HTTP 200. Every topology case asserts exact outcome, zero server
mutation calls, unchanged observed topology and unchanged database SHA256.

Execute qualification also models a launcher remaining Ready while its child
survives Stop-ScheduledTask. It must stop the verified exact child PID before
task replacement, then rediscover a matching Ready launcher after Execute and
each rollback. The fixture migration branch, all 16 fixture failure stages,
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

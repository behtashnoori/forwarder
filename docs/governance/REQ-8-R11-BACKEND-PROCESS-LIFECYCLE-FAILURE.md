# REQ-8 — R11 backend process lifecycle failure

## Safety and release history

REQ-8 is Development-only. It performs no Production access, connection,
change, deployment, push, or merge. R10 and R11 are historical and must never
be redeployed. The frozen `S7-RC-f11f2ab` application remains unchanged.

R10 failed its canonical CORS gate and recovered because its task rewrite did
not replace the listener-owning previous process. R11 added an explicit
`Stop-ScheduledTask` and listener-drain gate. Its authorized Production run
reached `SWITCHING`, but failed with `previous backend listener did not stop`.
Rollback restored the exact environment, Scheduled Task, and IIS identity,
removed its owned target release, and ended `FAILED_AND_RECOVERED`.

## Authoritative Production process evidence

After the R11 failure, one listener remained on `127.0.0.1:5101`. Its process
was base-installation `python.exe`; its command line identified the previous
release virtualenv, `-m waitress`, and `backend.wsgi:app`. Its Python parent was
also alive, while that parent's upstream PID no longer existed. At the same
time Task Scheduler reported `Forwarder Backend Production` as `Ready` with
last result 1. Task state was therefore proven non-authoritative for backend
lifecycle.

The pinned external wrapper (10,716 bytes, SHA-256
`f99238f35468a3bec7d387b62493e5b1af3efa721801f93bbd90a21d5f8ecbc7`)
loads `production.env` with `dotenv_values`, updates `os.environ`, changes to
the release repository, and calls `os.execv` for `python -m waitress`.

## Development reproduction and exact mechanism

A real Windows reproduction used:

```text
cmd.exe
→ virtualenv python.exe
→ wrapper environment load
→ os.execv(virtualenv python.exe, python -m waitress ...)
→ base-installation python.exe listener
```

The task-like `cmd.exe` controller exited normally while the base-Python
Waitress process continued listening. The listener executable and command-line
identity changed across the virtualenv launcher boundary. This reproduces the
Production contradiction and proves the mechanism: on this Windows launcher/
`os.execv` topology, the listener can escape the controller lifetime that Task
Scheduler observes. `Stop-ScheduledTask` cannot be treated as proof that the
escaped listener terminated.

## Lifecycle ownership model and corrective action

R12 retains the current Scheduled Task architecture for the narrow repair but
does not trust its state for stop/start proof. It discovers the exact loopback
listener, requires singular cardinality, obtains its CIM process, and requires
all of these Production-observed identity signals:

- local address `127.0.0.1` and governed port 5101;
- exactly one listener;
- executable leaf `python.exe`;
- command line contains the expected release-local virtualenv Python path;
- command line contains `-m waitress`;
- command line contains `backend.wsgi:app`.

Missing, multiple, unreadable, or mismatched identity fails closed. The tool
never terminates by image name. Only the PID of the singular verified listener
may be force-terminated. It then waits at most 30 seconds for listener count
zero. Real Windows tests prove that terminating that verified listener releases
the port; an unrelated HTTP listener is rejected and remains alive; ambiguous
identity and timeout remain fail-closed.

Startup waits for exactly one listener and then re-runs the same governed
identity contract against the intended target release before health and CORS
verification. Thus a listener belonging to the previous or unrelated release
cannot satisfy activation.

## Rollback contract

After a partial or complete target start, rollback uses the target release
identity to stop only a verified target listener and proves zero listeners. It
then restores the exact environment, Scheduled Task XML, and IIS path; starts
the previous task; requires exactly one listener whose command line identifies
the previous release; and retains the existing health and identity gates.
Target deletion remains conditional on the current run's explicit ownership
flag. A pre-existing target path is rejected before mutation and is never
automatically removed.

## Architecture decisions

Replacing Task Scheduler, introducing a Windows service, or redesigning the
wrapper around job objects would expand infrastructure risk and is not required
for the immediate repair. The chosen PID-specific fallback is narrow and backed
by multiple identity signals plus real-process tests. A Windows service or a
version-controlled launcher with explicit PID/job ownership remains the
preferred later architecture.

The Production wrapper remains outside source control. R12 continues to pin its
exact hash as a pre-mutation prerequisite. Its complete source should become a
separately versioned runtime artifact later; reconstructing or replacing the
unavailable full wrapper during this repair would not be evidence-preserving.

## Release assurance and candidate impact

The regression suite includes real Windows `cmd.exe`, virtualenv launcher,
`os.execv`, Waitress, candidate WSGI, listener/PID/PPID inspection, real HTTP,
controller exit with surviving listener, verified PID stop, unrelated-listener
rejection, ambiguity, timeout, candidate start, canonical GET/OPTIONS,
legacy/unknown rejection, rollback, owned cleanup, and zero-mutation
ValidateOnly. Synthetic process-state files alone are not accepted as lifecycle
evidence.

The application candidate remains `S7-RC-f11f2ab`; no application artifact or
manifest is rebuilt. After qualification, the next immutable tooling identity
is `D2-VALIDATION-S7-RC-f11f2ab-r12-final`. Its maximum state is
`READY_FOR_NEW_PRODUCTION_VALIDATEONLY_ONLY`.

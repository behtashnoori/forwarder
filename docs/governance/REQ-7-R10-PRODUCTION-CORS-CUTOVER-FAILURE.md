# REQ-7 — R10 Production CORS cutover failure

## Safety and incident classification

REQ-7 is a Development-only repair. No Production access, connection, change,
deployment, push, or merge was performed. The operator-authorized R10 deployment
crossed the mutation boundary, reached `VERIFYING`, and passed release identity,
listener, local health, and canonical public health gates. It failed
`PRECHECK_72` (`canonical CORS GET failed`) and automatically restored the
configuration, Scheduled Task, and IIS path. The correct classification is
`DEPLOYMENT_RESULT=FAIL`, `RECOVERY_RESULT=PASS`, and
`STATE=FAILED_AND_RECOVERED`; recovery is not deployment success.

The post-rollback legacy CORS behavior is evidence of exact recovery only. It is
not evidence of the failed candidate process's environment.

## Evidence gap closure

The first REQ-7 investigation stopped because the Production-only runtime
wrapper and Scheduled Task action were absent from the repository, application
artifact, and package. Read-only operator evidence subsequently established the
wrapper identity as 10,716 bytes with SHA-256
`f99238f35468a3bec7d387b62493e5b1af3efa721801f93bbd90a21d5f8ecbc7`.

Its serve chain is:

```text
production.env
→ dotenv_values(path)
→ os.environ.update(values)
→ os.chdir(candidate repository)
→ python -m waitress
→ backend.wsgi:app
```

The wrapper does not implement CORS. Its own env writer uses quoted dotenv
values, `CORS_ALLOW_ALL_ORIGINS=false`, and matching singular/plural origins.
The actual Scheduled Task invokes that wrapper with `serve --env production.env
--repo <release> --host 127.0.0.1 --port 5101`; its action contains the release
identity in `PYTHONPATH`, current directory, Python executable, `--repo`, and
WorkingDirectory.

## Proven root cause

R10 changed the persisted Scheduled Task action and IIS reference, but never
stopped the already-running previous backend before calling
`Start-ScheduledTask`. Changing task XML and `production.env` cannot alter the
environment or imported modules of the process that already owns
`127.0.0.1:5101`. Starting a task that already has a running instance does not
provide a governed process replacement.

Consequently, the listener and health checks could pass against the previous
backend while its restored-at-process-start legacy CORS policy rejected the
canonical Origin. This exactly matches the observed sequence: listener PASS,
local and public health PASS, then canonical ACAO absent. The CORS gate was
correct; it exposed a Scheduled Task/backend handoff defect.

Local runtime evidence separately proves all three candidate configurations—`0`,
`false`, and quoted `"false"`, with canonical singular/plural origins—pass real
Waitress HTTP GET and OPTIONS checks. `dotenv_values` overrides contaminated
parent CORS values before application import. Canonical ACAO and credentials are
present; legacy and unknown origins are rejected. The frozen application is not
the defect and remains unchanged.

## Corrective action

R11 enforces an explicit backend handoff:

1. stop the governed previous Scheduled Task;
2. wait until the loopback listener count is zero;
3. replace every governed previous-release task reference and IIS reference;
4. prove the task no longer retains the previous release;
5. start the governed task;
6. wait for exactly one new loopback listener;
7. perform the existing health and strict CORS verification.

Rollback now stops any failed target process, waits for listener release,
restores the exact environment/task/IIS state, starts the restored previous task,
and waits for its listener. Target directory deletion is permitted only when the
current run set an explicit target-ownership flag immediately before extraction;
unknown pre-existing Production paths remain fail-closed and are never cleaned
automatically.

The real Production wrapper remains external, but R11 converts its supplied
identity into a release prerequisite by pinning and validating its SHA-256 before
mutation. This closes exact-byte admission for the current release without
inventing unavailable source. A future infrastructure change should place the
complete wrapper source under version control and distribute it as a separately
versioned runtime artifact.

## Release-assurance gap and regression

R10's `cors.txt`/`preflight.txt` simulation proved orchestration assertions, not
the runtime chain, process replacement, or HTTP behavior. That was a release-
assurance gap.

REQ-7 adds a production-realistic regression using the candidate Python
environment, actual `python-dotenv` parsing, `os.environ.update`, application
import, Waitress, and real loopback HTTP requests. It checks health, canonical
GET ACAO, canonical OPTIONS ACAO, credentials, legacy rejection, unknown-origin
rejection, all three required env syntaxes, parent-environment replacement, and
the fact that a running process retains its old CORS configuration until an
explicit restart. Static and orchestration regressions enforce stop/drain/
rewrite/start/acquire ordering, rollback restart, zero-mutation ValidateOnly,
and governed target ownership.

## Candidate and package consequence

`S7-RC-f11f2ab` and its application artifact remain immutable. R10 is historical
and must not be redeployed. After source and exact-package qualification, the
next permitted package identity is `D2-VALIDATION-S7-RC-f11f2ab-r11-final`.
Its maximum state is `READY_FOR_NEW_PRODUCTION_VALIDATEONLY_ONLY`; a successful
new Production ValidateOnly is required before any separate deployment decision.

# Forwarder final release closure audit

## Domain reference matrix

Repository-wide searches covered `backend`, `frontend`, environment templates,
deployment/runtime scripts, tests, deployment documentation, release manifests,
and generated frontend inputs. Historical evidence files are records, not current
instructions. IIS bindings are deliberately outside the application CORS gate.

| Reference | File(s) | Purpose | Status | Runtime effect | Action |
|---|---|---|---|---|---|
| `https://samand.forwarderet.ir` | `backend/config.py`, `backend/env.production.example`, S7 manifest, release scripts/tests | Canonical application origin | CURRENT | Production CORS and release verification | Retain as sole canonical origin |
| `CORS_ALLOW_ALL_ORIGINS` | `backend/config.py`, `backend/cors_config.py`, deployment scripts/tests | Explicit allow-all prohibition | CURRENT | Production startup fails when truthy | Retain false/`0` gate |
| `CORS_ORIGINS` / `CORS_ORIGIN` | backend config, env templates, deployment scripts/tests | Governed plural setting and S8 compatibility alias | CURRENT | Conflict fails startup; plural or unambiguous alias supplies origins | Retain contract and regression tests |
| `https://server.logisticmarket.ir` | backend legacy rejection constant, manifests, deployment fixtures/tests | Known legacy origin and negative-test input | LEGACY | Explicitly rejected by Production config and HTTP tests | Retain only as rejection evidence |
| `server.logisticmarket.ir` | historical operational evidence; `VERIFY-SERVER.ps1` old default | Historical public endpoint | LEGACY | The old verifier default could direct a manual check to legacy infrastructure | Default changed to canonical; historical records retained |
| `samand.logisticmarket.ir`, `*.forwarderet.ir`, `server.forwarderet.ir` | historical IIS discovery/evidence and hostname-routing tests | Historical bindings/tenant-routing fixtures | LEGACY | No Production application CORS allow-list effect | Retain as history/negative fixtures; binding retirement is post-release |
| `server.logisticmarket.ir` | `vite.config.ts` | Vite development-server host allow-list | LEGACY | Development server only; absent from the frozen production `dist` runtime | No frozen-candidate change; track as non-Production cleanup |
| `forwarderet.ir` / `logisticmarket.ir` substrings | documentation, historical evidence, tenant hostname tests | Search-family coverage | MIXED | None unless one of the governed runtime keys above is used | No action for immutable history or isolated test data |

Conclusion: no hardcoded legacy origin overrides Production application CORS.
The only current release-input default that incorrectly preferred the old public
host (`VERIFY-SERVER.ps1`) was corrected. Historical IIS bindings are neither
accepted by application CORS nor a release prerequisite.

## Final canonical-domain contract

- Canonical origin: `https://samand.forwarderet.ir`.
- `CORS_ALLOW_ALL_ORIGINS` must parse false; deployment writes `0`.
- `CORS_ORIGINS` is the primary setting. `CORS_ORIGIN` is an S8 compatibility
  alias only when absent or set-equivalent; disagreement raises at startup.
- Wildcard, localhost placeholders, the known legacy origin, unknown
  `*.forwarderet.ir` origins, and historical domains are rejected in Production.
- IIS binding inventory is independent of application CORS policy.

## R12 startup-chain audit

R12 proved shutdown of the governed previous listener and then timed out before
the new listener appeared. It did not preserve candidate-scoped startup output,
so the exact R12 exit cause remains unproven.

| Stage | Expected input | Tooling contract | Exit-before-listener failure mode | Coverage |
|---|---|---|---|---|
| Scheduled Task | Governed task and target-release reference | Enable and start must succeed | disabled/missing task, registration/action/identity failure | simulated orchestration and controlled contract |
| `cmd.exe` | task action containing target path | launches release-local interpreter chain | quoting, working-directory, access, or action failure | real Windows cmd topology test |
| venv Python | `<release>\.venv\Scripts\python.exe` | exact release path in governed identity | missing/broken venv or launcher escape | real Windows venv/`execv` test |
| runtime wrapper | pinned wrapper SHA-256 | wrapper loads environment then replaces itself with Waitress | wrapper mismatch/import/argument/logging failure | hash precheck and real wrapper topology; Production wrapper not executed on this host |
| environment | runtime `production.env` | process environment supplies required values | unreadable file, malformed/duplicate key, missing DB/secrets, unsafe CORS | PowerShell env gates plus backend config tests |
| cwd / `PYTHONPATH` | extracted target repo | `backend` must import from target | wrong cwd/path or missing package | wrapper topology and extracted structure gates |
| `backend.wsgi` | importable module | exposes `app` via runtime factory | dependency/import/module initialization exception | backend startup tests and real Waitress HTTP test |
| `create_runtime_app` | valid production configuration | app factory and readiness path initialize | secret, database, extension, or app factory error | backend runtime/config tests |
| migration readiness | expected DB and Alembic scalar | read-only identity equals frozen manifest | DB unavailable/auth/TLS/schema/head mismatch | read-only PostgreSQL parsing/scalar regressions; no live DB here |
| CORS config | canonical explicit origin, allow-all false | conflict and unsafe values fail closed | missing/conflicting/legacy/wildcard config | config unit tests and real Waitress GET/OPTIONS tests |
| Waitress | `--listen=127.0.0.1:5101 backend.wsgi:app` | one listener owned by exact target process | bind denial/port collision/import exit/process escape | real Windows lifecycle and ownership tests |
| listener gate | one loopback listener | observed within bounded timeout and identity certified | zero, multiple, unrelated, or unverifiable owner | R7/R8 lifecycle tests and orchestration rollback tests |

## Diagnostic repair

Each candidate start now creates `forwarder-startup-attempt-v1` evidence before
starting the task. It records candidate/release/time, task-start result, bounded
listener observations, target-release process observations, the starting byte of
`backend-production.log`, at most 64 KiB appended after that boundary, and the
failure reason. URI credentials and secret assignment lines are redacted. On a
start or runtime verification failure, the evidence JSON is written beside the
deployment script before rollback begins. ValidateOnly creates no attempt file.

The repair establishes evidence for the next failure; it does not retroactively
prove an R12 root cause.

## REQ-12 governed runtime closure

The Development-qualified relocatable CPython 3.12.6 AMD64 runtime is frozen as
`Forwarder-Windows-Runtime-REQ12.zip`. Its manifest inventories every file and
binds the archive size and SHA-256. Deployment verifies both identities before
the mutation boundary, expands the runtime into `<target>\runtime`, executes an
application dependency probe before stopping the existing service, and rewrites
the Scheduled Task interpreter from `<previous>\.venv\Scripts\python.exe` to
`<target>\runtime\python.exe`. Listener ownership uses that same immutable
interpreter identity.

Development qualification includes the 26 fail-closed cases, cumulative release
tooling tests, real packaged-runtime Waitress GET/OPTIONS/CORS checks, a real
ephemeral Windows Scheduled Task lifecycle, ten consecutive full deployment
rehearsals, and ten consecutive rollback rehearsals. Production was neither
accessed nor modified.

## ValidateOnly current-listener ownership repair

The Production ValidateOnly evidence proved a single healthy previous-release
listener using `<previous>\.venv\Scripts\python.exe`. REQ-12 had incorrectly
applied the future packaged-runtime interpreter expectation before the mutation
boundary. The pre-mutation and rollback contracts now require the governed
previous release interpreter; only the post-switch target listener requires
`<target>\runtime\python.exe`. Unknown, absent, ambiguous, wrong-address, and
wrong-release listeners remain fail-closed.

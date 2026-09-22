# Forwarder v1.10.0 Production operator tooling

This directory contains the laptop-qualified, operator-mediated Production
tooling for Forwarder v1.10.0. It does not authorize deployment. Codex does not
run these tools against Production; a human operator runs them locally on the
Windows Production server after the applicable gate and authorization.

The first server phase is read-only and uses
`Collect-ForwarderV110ProductionReadOnly.ps1`, its secret-safe Python database
bridge, the governed legacy Production witness, and the SQL files under `sql/`.
The collector emits one sanitized JSON result and performs no server mutation
other than creating that explicitly requested result file.

After a successful live read-only preflight, the backup/restore-proof stage uses
`New-ForwarderV110PreDeploymentBackup.ps1` on Production and
`Invoke-ForwarderV110ProductionRestoreProof.ps1` only on a controlled laptop.
The server tool supports the proven `postgresql+psycopg2://` connection shape,
requires the exact pre-migration revision, creates one timestamped custom dump,
and emits sanitized evidence. The laptop tool verifies the transferred bytes,
restores only to its generated disposable PostgreSQL 18 database, rehearses the
exact five migrations through the qualified package runtime, runs the governed
read-only assertions, and removes the disposable database.

Collector revision `r5` preserves the qualified `r3` live-topology discovery
and Scheduled Task projection authority. It additionally makes the two backup
gates explicit. Before validate-only, the newest governed dump must be fresh,
its backup evidence, size, SHA256, catalog, and sidecars must agree, and the
isolated restore/migration evidence must bind to those exact bytes and fixed
release identities. The collector then reports
`READY_FOR_SEPARATE_GO_REVIEW`; it does not claim that the future
deployment-window checkpoint already exists. During Execute, the deployer must
create and record a second, newer backup after writer containment and before
migration. Neither gate substitutes for the other.

Deployment-tooling revision `r5` retains the `r4` Windows PowerShell 5.1
`$listenerPid` correction and closes the observed asynchronous listener-teardown
defect. Writer containment disables and stops the exact governed task,
revalidates and terminates only the captured Waitress PID, then polls for at
most 15 seconds at 250 ms intervals and requires a continuous 2-second quiet
period. The task must remain disabled, the original listener must be gone or no
longer own the port, `127.0.0.1:5101` must be free, and no replacement PID may
appear. A replacement is reported and never killed. Backup and migration remain
behind this PASS gate. A staged target left by a failed attempt remains
preserved as evidence and is not a reusable release; the next validate-only
must use a newly generated, absent target path.

The collector
enumerates only plausible Forwarder Scheduled Tasks and proves one against the
active listener action; ambiguity remains BLOCKED. A missing current-format
manifest is not treated as proof of identity: the legacy release must instead
match all 323 governed backend/frontend witness files. Database access uses the
active release's Python, python-dotenv, and SQLAlchemy URL parser, so
`postgresql+psycopg2://` remains supported without putting a password in a
command line, output, or result file. Every SQL payload retains its explicit
read-only transaction envelope.

After exactly one Scheduled Task candidate is proven, `r5` projects the
candidate-derived action, runtime, working directory, arguments, and release
path before adding null-safe Task Scheduler state, result, principal, trigger,
and settings metadata. Listener ownership becomes true only when the listener
runtime/release, selected task runtime/release, and active release all agree.

Application bytes in the Production package are built only from
`e36ee7cee157657c97dc42a539eaf1909f510a33`. These tooling files are
stage-specific controls and are not Product runtime behavior.

Hard identities:

- Product version: `1.10.0`
- Application source: `e36ee7cee157657c97dc42a539eaf1909f510a33`
- Starting database revision: `20260921_shipment_evidence_ownership`
- Target database revision: `20260926_fixed_shipment_responsible_expert`
- Backend listener: live collector evidence must confirm the governed endpoint;
  the qualified historical contract is `127.0.0.1:5101`.
- Scheduled Task name hint: `Forwarder Backend Production`; the actual task is
  selected only through exact listener/release/runtime/action evidence.
- IIS site: `forwarder`
- External environment: `C:\1-webapp\forwarder-runtime\production.env`

`REFERENCE_IMPACT=NONE`

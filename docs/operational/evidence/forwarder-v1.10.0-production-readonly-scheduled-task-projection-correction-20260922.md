# Forwarder v1.10.0 Production Read-Only Scheduled Task Projection Correction — 2026-09-22

## Governance and scope

LPAF v2.2 and its Agent Entry Protocol govern this laptop-side Production tooling correction. The reviewed v2.3 reference-impact discipline is applied as a strong default. `REFERENCE_IMPACT=NONE`.

This slice changes only the read-only collector's final selected-Scheduled-Task projection and the r3 read-only bundle/handoff. It does not change Product runtime, tests accepted as Product behavior, migrations, database tooling, deployment semantics, the candidate-discovery authority model, or ambiguity gates. Codex did not access Production and did not deploy.

## Authoritative returned r2 facts

The human operator's sanitized r2 JSON proved:

- active release identity, with application commit `e97338661d7dfa40766a5a1dce1f0f2e1cdc9bc4`;
- PostgreSQL `18.1`, database revision `20260921_shipment_evidence_ownership`, zero schema-drift blockers, and all migration compatibility checks PASS;
- ADR-047 counts `already_valid=6`, `deterministic_repair=0`, `ambiguous=0`, `contradiction=0`, and `other_unresolved=0`;
- zero mandatory configuration failures, external document storage, healthy disk capacity, and healthy IIS/API/SPA/health/readiness.

The only collection error was `SCHEDULED_TASK_SELECTED_METADATA_FAILED`. Bounded discovery had already proven exactly one candidate named `Forwarder Backend Production`, reason `EXACT_LISTENER_ACTION_MATCH`, for release:

`C:\1-webapp\forwarder-production\release-20260914215708-20260921_shipment_evidence_ownership`

Its action executable was `C:\Windows\System32\cmd.exe`, its resolved runtime was the release-local `runtime\python.exe`, and its working directory was the same release. The final `scheduled_task` record nevertheless retained null action/runtime/arguments/working-directory fields, so listener ownership remained false.

## Correction

Revision r3 keeps candidate enumeration, proof, and ambiguity behavior unchanged. It retains the exact selected task object and exported XML from the bounded discovery pass, projects the already-proven candidate fields first, and then adds Task Scheduler state, enabled state, last result/times, principal summary, triggers, restart policy, and multiple-instance policy through null-safe reads. Optional principal or settings nodes can no longer erase authoritative candidate-derived fields.

Listener ownership now requires all of the following simultaneously:

- exactly one loopback Waitress listener;
- a PROVEN selected task with the exact listener relationship;
- listener executable equals selected task resolved runtime;
- listener release equals selected task release;
- active release equals selected task release.

Any zero-match, multi-match, cached-record inconsistency, or selected metadata query failure remains fail closed.

## Regression and qualification

- Sanitized r2-shaped fixture with the observed null final projection and one correct candidate: PASS.
- Group-principal and absent optional restart-policy projection: PASS.
- Candidate action/runtime/arguments/working-directory/release preservation: PASS.
- Listener/task/release ownership agreement: PASS.
- Multiple exact candidates: fail closed.
- Full Production tooling regression suite: `25 passed`.
- PowerShell parsing and read-only/secret-safety guards: PASS.
- Independent deterministic r3 rebuild: PASS.
- Bundle inventory/checksums and ZIP-to-expanded byte equality: PASS.
- Expanded bundle files: `9`; deployment material: absent.

Qualified r3 read-only bundle:

- Expanded: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157-r3\`
- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Read-Only-Preflight-Bundle-e36ee7cee157-r3.zip`
- Size: `41162` bytes
- SHA256: `46faccf3284ff8cb5cf545af6a2047094af3a497364c0858fd10cfefcbcc073d`

The Product package remains byte-identical at SHA256 `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`. The deployment bundle remains byte-identical at SHA256 `acf45576c82bc04fa3a3dd02b12500690d4efeeba32c9ffb1e47322227919dbb`. Neither was rebuilt or modified.

`REFERENCE_IMPACT_FINAL=NONE`

## Verdict

PASS — v1.10.0 PRODUCTION READ-ONLY COLLECTOR SCHEDULED TASK PROJECTION FIXED

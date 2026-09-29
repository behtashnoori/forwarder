# ADR-072 — Governed Historical Cargo Continuity Repair

## Status

Accepted for the bounded Product Owner mission dated 2026-09-29. This ADR does not authorize production, deployment, release, mass backfill, raw SQL, or any ordinary Product UI action.

## Context

The pre-fix Request→Shipment creation boundary could persist an accepted-quote Shipment, Shipment Cargo, active RoutePlan and Execution while omitting Request Cargo lineage, requested quantity and Cargo route participation. The current Product creation path is already fixed. Existing ordinary Cargo and route commands cannot safely complete the preserved historical record because active RoutePlans intentionally reject ordinary destination edits.

## Decision

Add one CLI-only maintenance capability with separate `plan` and confirmed `apply` operations for exactly one opaque Shipment identity. Both operations require an active persisted `PLATFORM_ADMIN` actor, one active tenant membership, an active tenant, and an exact named operator equal to that actor username. Possession of this offline command plus the explicit Product approval reference is the deliberately chosen command-specific maintenance capability; no ordinary tenant permission is inferred or granted. The command does not call ordinary tenant mutation APIs and is not exposed through HTTP or UI.

Every invocation is also bound to an operator-reviewed database name and exact Cargo, source Request Cargo, RoutePlan and terminal RouteLeg identities. This mission permits only an in-memory focused-test database, an owned local PostgreSQL database named `forwarder_cargo_continuity_repair_*`, or the preserved local UAT database `forwarder_human_walkthrough`; production, remote databases and development runtimes fail closed before domain reads.

The service recomputes all eligibility facts at apply time under database locks. It permits only the defect signature: exact Shipment-creation audit and idempotency evidence, exact operator-reviewed Cargo/source-Cargo identities, one accepted Quote/Request, one uniquely provable Request Cargo and Shipment Cargo, missing lineage and requested quantity, one exact operator-reviewed original active RoutePlan revision and terminal leg, no conflicting destination, and no contradictory actual/allocation/transfer/delivery/Cargo-report fact. Existing Execution is permitted only when it is on the same Shipment, plan and repaired path; orphan or mismatched execution/allocation identity refuses repair.

Apply adds the missing lineage/requested quantity and one `RouteCargoDestination` atomically, then writes one consolidated `OperationalAudit`, one internal outbox event and one idempotency ledger in the same transaction. Replay validates the complete required audit metadata, outbox payload, ledger hash/response and route mapping before returning unchanged; missing or altered repair provenance fails closed. The outbox is internal operational history and is not projected to Customer UI. The existing schema and audit store are sufficient, so no migration is authorized.

## Consequences

- Active-plan repair is explicitly distinguished from replanning: no RoutePlan, RouteLeg, topology, time, status or Execution field changes.
- System Admin gains no implicit tenant business access; only the named offline maintenance command is available.
- The path is intentionally narrow and may refuse records that require interpretation. A broader or bulk repair needs a separate Product and architecture decision.
- Requested Customer destination and operational planned destination remain separate, unchanged facts.
- `JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY`; the exact candidate must rerun the affected slice and integrated journeys plus the complete critical automated pack required by the mission.

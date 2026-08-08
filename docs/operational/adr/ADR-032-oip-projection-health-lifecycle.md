# OIP-D20 — Projection Health Lifecycle

- Status: Accepted and implemented
- Contract version: `oip-projection-health-v1`
- Projection: `oip-attention-v1`
- Freshness policy: `oip-health-watermark-v1`
- Owner: `OipProjectionState` at the OIP projection/reconciliation boundary

## Decision

Projection Health describes trust in derived OIP intelligence and never operational truth. Its exact states are `FRESH`, `STALE`, `REBUILDING`, and `DEGRADED`; no other state is supported.

- `FRESH`: the current authoritative-source fingerprint equals the last successfully processed fingerprint.
- `STALE`: the projection remains readable and structurally valid, but the fingerprints differ or no successful reconciliation has yet been recorded.
- `REBUILDING`: the real governed reconciliation/rebuild operation has committed its run identity and start time and is actively rebuilding.
- `DEGRADED`: a recognized reconciliation/rebuild operation failed. Only a stable code and sanitized reason cross the API boundary.

The freshness policy uses exact watermarks derived from the authoritative OIP input set. It has no time tolerance, hidden fallback, or developer-chosen default. A successful reconciliation or rebuild records the same source and processed watermarks and returns health to `FRESH`.

## Transition and concurrency contract

Explicit service logic permits `FRESH → STALE`, `STALE → FRESH|REBUILDING|DEGRADED`, `REBUILDING → FRESH|DEGRADED`, and `DEGRADED → FRESH|REBUILDING`. PostgreSQL transaction advisory locks and the single organization-owned row serialize health writers. A second operation is rejected while `REBUILDING`; run identity prevents superseded completion; row locks protect latest success/failure evidence.

Health transitions create compact durable `OipProjectionHealthHistory` evidence with state, code, run, projection/policy versions, watermarks, and time. They do not mutate operational facts, MDPM, document truth, readiness, or operational authorization.

## API and presentation

`GET /api/oip/projection/status` is the canonical status boundary. Queue responses and Situation detail/DecisionContext embed the same health contract. `POST /api/oip/projection/rebuild` drives the real rebuild. UI warnings explicitly distinguish intelligence health from operational status in RTL and LTR layouts.

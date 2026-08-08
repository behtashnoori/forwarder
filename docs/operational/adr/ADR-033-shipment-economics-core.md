# ADR-033: Shipment Economics Core

## Context

FE-0 found fragmented commercial amounts and no authoritative shipment economics. FE-1 defined a dedicated bounded context. The Architecture Owner authorized FE-2 as the first implementation slice.

## Decision

Add `EconomicLine` and append-oriented `EconomicObservation` facts scoped by organization and `OperationalShipment`. Observations use `ESTIMATE`, `COMMITMENT`, or `ACTUAL`; exact Money; authority/source/effective/recorded time; idempotency; and supersession/reversal history. Explicit contractual/manual-approved FX facts support traceable reporting conversion. Projections are rebuilt from facts, stage-separated, permission-filtered, and abstain when cost, revenue, or FX is missing. Accepted quotes enter only through preview/confirm.

## Scope and exclusions

Included: shipment lines/observations, evidence references, corrections, explicit FX, shipment/project projections, completeness, API/OpenAPI, bounded UI, audit/security. Deferred: cross-shipment allocation until a real source fact requires it; invoices/payments/settlement/ERP; tax; ExecutionUnit economics; OIP and AI.

## Invariants

Money is decimal plus governed currency. Unknown is not zero. Stages do not overwrite one another. Consequential history is not deleted. Margin is derived. Tenant scope and opaque API identities fail closed. Quote creation is never commitment. Exact evidence versions remain historical even after document supersession.

## Trade-offs and security

The slice uses existing governed ServiceType and operational membership capabilities, avoiding party/accounting masters. Counterparty is optional until a governed party reference exists for the charge. Cost and margin require separate permissions. Logs contain identities/classification, not monetary values. PostgreSQL locking and unique idempotency constraints prevent lost/duplicated truth.

## Evidence and migration policy

Migration `20260817_shipment_economics_core` is additive, has no backfill, and follows OIP head `20260816_oip_projection_health`. Downgrade fails closed because dropping durable economics would destroy consequential evidence. Recovery is backup restoration. Candidate evidence is indexed under `assurance/fe-2`.

## Status

Implemented as an FE-2 candidate; promotion depends on the FE-2 assurance report.

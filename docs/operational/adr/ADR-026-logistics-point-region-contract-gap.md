# ADR-026 — Logistics Point Region Contract

- **Status:** Accepted
- **Decision date:** 2026-08-03
- **Scope:** Release 1.7.0 Logistics Network Foundation
- **Approver roles:** Product, Architecture, Operations, Data
- **Consulted:** Security

## Context

The Release 1.7.0 slice originally allowed an optional free-text `region_name` when governed Province data was unavailable. The implemented model instead provides governed Country, optional governed Province and City, and a derived `geography_key` for normalized duplicate enforcement. Operational maturity does not currently justify exposing a generic administrative-region business concept.

## Decision

- Country remains required and governed.
- Province remains optional and governed.
- City remains optional and governed; a City requires its governed Province and must belong to it.
- `region_name` is explicitly deferred from Release 1.7.0. No free-text administrative-region field is introduced.
- Short address remains optional descriptive text and is not a reporting dimension.
- The existing `geography_key`, or an equivalent normalized implementation detail, may remain provided it does not expose a new business concept.
- No schema addition is required solely for `region_name`.
- Future region support requires a separate Product/Data/Architecture decision and an additive migration.

## Rationale

Controlled Country/Province/City supplies sufficient structure for the current operational scope. A free-text region would weaken standardization without a mature governed use case. Deferral avoids introducing an ambiguous reporting dimension, while a later additive field remains backward compatible.

## Consequences

The Release 1.7.0 contract and acceptance evidence use Country plus optional Province and City. Duplicate enforcement remains organization-scoped across the implemented governed geography. Maps, GIS, reporting, customer search, geography redesign, Production migration, and seed execution remain outside this decision.

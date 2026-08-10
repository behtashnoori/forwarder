# ADR-034: Optional Commercial Lineage and One OperationalShipment Aggregate

- **Status:** Accepted for Forwarder 1.9.1 implementation
- **Decision date:** 2026-08-10
- **Release:** 1.9.1 acceptance correction
- **Implementation status:** Contract only; not implemented, migrated, published, or deployed

## Context

Forwarder 1.9.0 creates an `OperationalShipment` only by converting an accepted `ExpertQuote`. Production acceptance confirmed that an authorized operator must also be able to create an operation directly, without manufacturing a `ShipmentRequest` or `ExpertQuote`. The correction must preserve the existing operational lifecycle and commercial history.

The repository already has a canonical CRM `Customer`. `ShipmentRequest.customer_id` is its governed commercial link, `Project.primary_customer_id` is its governed Project owner, and `OperationalShipment` currently has no direct customer reference. Customer names and telephone numbers on a request are descriptive input and are not canonical identity.

## Decision

There remains exactly one execution aggregate:

```text
Accepted Quote ----\
                    > OperationalShipment -> RoutePlan -> RouteLeg -> Milestones
Direct Operation --/
```

`OperationalShipment` gains immutable `source_type` with exactly two values:

- `accepted_quote`: `customer_id`, `shipment_request_id`, and `accepted_quote_id` are all required.
- `direct`: `customer_id` is required; `shipment_request_id` and `accepted_quote_id` are both null.

`OperationalShipment.customer_id` is the canonical customer relationship for execution. It is not derived dynamically from `Project`, names, phone numbers, or other free text. `project_id` remains optional for both sources. If present, the Project must be in the same operational organization and its `primary_customer_id` must equal the shipment customer. A future separately approved stakeholder policy may broaden that rule; 1.9.1 does not.

For a new accepted-quote conversion, `customer_id` is copied atomically from the accepted quote's `ShipmentRequest.customer_id`. Conversion fails closed when the request lacks a canonical customer link. The copy is an immutable creation snapshot of canonical identity: later CRM request relinking does not silently rewrite the operation.

Existing quote-derived operations remain valid. Migration may populate their `customer_id` only where `OperationalShipment.shipment_request_id -> ShipmentRequest.customer_id` is non-null and deterministic. Existing rows without that link are classified `legacy_incomplete`; they remain readable and operable under existing lifecycle authority, but cannot have a customer guessed or be used as precedent for new incomplete creation. Remediation requires an explicit governed command in a later authorized scope.

`source_type`, creation customer, and commercial lineage are immutable after creation. Half-linked states are prohibited by database and application invariants. No command changes a direct operation into a quote-derived operation or vice versa.

## Source and customer invariants

| `source_type` | Customer | Request | Accepted quote | Project | Result |
| --- | --- | --- | --- | --- | --- |
| `accepted_quote` | present | present | present and accepted for that request | absent | Valid |
| `accepted_quote` | present | present | present and accepted for that request | present, same organization and same primary customer | Valid |
| `accepted_quote` | absent | present | present | any | Invalid for new creation; legacy-incomplete only after migration |
| `accepted_quote` | present | absent | present | any | Invalid half-linked state |
| `accepted_quote` | present | present | absent | any | Invalid half-linked state |
| `accepted_quote` | present | request A | quote for request B | any | Invalid lineage mismatch |
| `direct` | present | absent | absent | absent | Valid |
| `direct` | present | absent | absent | present, same organization and same primary customer | Valid |
| `direct` | absent | absent | absent | any | Invalid |
| `direct` | present | present | absent | any | Invalid half-linked state |
| `direct` | present | absent | present | any | Invalid half-linked state |
| `direct` | present | present | present | any | Invalid; use accepted-quote source |
| either valid source | present | source-valid | source-valid | foreign organization | Invalid, non-disclosing tenant failure |
| either valid source | present | source-valid | source-valid | same organization, different primary customer | Invalid customer/Project mismatch |
| null or unknown | any | any | any | any | Invalid |

Database checks can enforce source/null shape. Quote acceptance, quote/request identity, organization ownership, customer identity, and Project/customer consistency are transaction-time service validations under lock.

## Consequences

- Quote conversion and direct creation use separate authorization and source validation, then one shared aggregate initializer.
- Direct operations receive the same route planning, milestones, work queue, audit, outbox, OIP, cargo, project, reporting, and ordinary economics/FX capabilities.
- Accepted-quote economics materialization remains source-specific and is not available to direct operations.
- Request-scoped documents and MDPM requirements remain supported for quote-derived operations and explicitly not applicable to direct operations in 1.9.1.
- A future `OperationalShipment -> DocumentAttachment/DocumentArtifact` capability may be added without creating a request or changing this source model. ADR-020 remains the governing extension seam; 1.9.1 adds no DMS.
- Additional creation sources require a later ADR and an expanded check constraint; arbitrary source strings are prohibited.

## Rejected alternatives

- A `DirectOperation` aggregate or parallel lifecycle.
- Requiring a fabricated request or quote.
- Deriving customer only through optional Project.
- Inferring customer from request names, phone numbers, email, or fuzzy CRM matching.
- Automatically granting direct-create authority to existing creators.
- Making request-scoped documents appear applicable to direct operations.

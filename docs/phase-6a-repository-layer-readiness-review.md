# Phase 6A: Repository Layer Readiness Review

## Decision

A global repository layer is not recommended yet.

Services still mix:

- payload construction
- transaction ownership
- route-specific validation
- DB queries

Introducing repositories everywhere now would add churn without enough isolation benefit.

## First Future Candidate

The strongest future candidate is shipment/request read access because repeated lookup patterns appear across:

- admin request list/detail
- expert request list/detail
- public tracking
- customer workflow

## Candidate Repositories

- `shipment_repository.py`: best later candidate for request lookup, filter, and location joins
- `expert_repository.py`: useful later for expert lookup and active checks
- `assignment_repository.py`: defer until assignment/manual statistics semantics are settled
- `user_repository.py`: defer; current user services remain cohesive
- `crm_repository.py`: defer; CRM services are already split and need a separate duplication review

## Risks of Premature Extraction

- large API churn
- duplicated abstractions
- unclear transaction boundaries
- weaker characterization coverage around query behavior
- services becoming thin wrappers around repositories without real simplification

## Recommended Phase 6B

Do a repository spike only after customer/admin read services stabilize. Start with shipment request read helpers, not write flows.

## Acceptance Criteria

Repository introduction should wait until:

- the first domain has repeated query patterns covered by tests
- transaction ownership is explicit
- payload building is separated enough that repositories do not return HTTP-shaped dictionaries

# Phase 1A API contract

Endpoints: create from accepted quote; shipment list/detail; milestone report/verify/correct; work-item list/resolve. Lists return `{data,meta:{page,per_page,has_more}}`; commands/details return `{data}` and create adds `meta.created`. Errors return `{error:{code,message,fields}}` without SQL or traceback.

Shipment filters: status, customer, request/quote, origin/destination, overdue, date range. Work filters: status, type, shipment (with pagination). Mutation requests use `Idempotency-Key`; reuse with a changed payload returns `409 IDEMPOTENCY_KEY_REUSED_WITH_DIFFERENT_PAYLOAD`. Stale versions and invalid transitions return 409; validation 422; permission 403; hidden tenant resources 404.

# Operational checkpoint catalog

Supported types: origin loading, export customs, border exit, transit border entry/exit, border entry, import customs, port entry/exit, terminal arrival, transshipment, destination arrival, unloading, and final delivery.

Checkpoints belong to a route plan and optionally a leg. They keep planned, projected, and actual arrival/departure independently. Final delivery must be unique and last.

Each checkpoint owns `checkpoint_arrival`, `checkpoint_processing_complete`, and `checkpoint_departure` milestones. A report appends a `reported` event; independent verification appends a `verified` event that references the report or correction it verifies. Correction appends a `corrected` event with a reason and provenance, invalidates the current actual immediately, and requires independent re-verification before the corrected time becomes actual.

`MilestoneEvent` is the immutable ledger. PostgreSQL rejects UPDATE and DELETE. Milestone and checkpoint actual fields are transactional summaries derived only from the currently verified report/correction; they are never accepted as independent command input.

Projected reconciliation follows dependency topological order. A checkpoint waits for the latest predecessor release, preserves its planned dwell interval, and uses verified actual arrival/departure ahead of projected/planned values. Arrival, processing-complete, and departure milestone projections synchronize to the checkpoint; route-leg projected departure/arrival summarize the earliest/latest effective checkpoint time.

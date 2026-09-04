# Clean Windows Release Qualification

`Forwarder Release Qualification` is manual-only and runs on GitHub-hosted
`windows-2025` runners. It checks out the fixed candidate source SHA rather
than the workflow commit, uses read-only permissions, and contains no
production credential, configuration, deployment, or release-freezing step.

Three independent fresh runners must complete `npm ci` before frontend,
backend, migration-graph, geography, Cargo, Logistics, authorization/tenant,
and release-engineering regressions run. The final job writes a compact
qualification decision artifact. `READY_FOR_RC_FREEZE` requires every job to
succeed; this workflow itself does not create an RC.

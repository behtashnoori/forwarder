# Forwarder v1.9.5.1 Production hotfix handoff

Baseline: accepted Production `v1.9.5` at `20260827_org_hostname`.

Target: application `v1.9.5.1`, database revision `20260828_referral_state_compat`.

Database migration is required. Before deployment, verify the artifact checksum, capture current server state, confirm v1.9.5, and complete database and document-storage backup checks. Extract the new immutable release, prepare its runtime, stop Production safely, migrate exactly one revision, validate WSGI, switch the release, and run core HTTP smoke tests.

Post-deployment, submit a shipment through `https://samand.logisticmarket.ir`. Verify there is no `referral_auto_assign_state` primary-key error, the request remains `TENANT` and Samand-owned, and referral either assigns an eligible Samand expert or leaves the request in Samand's unassigned queue. Confirm the legacy nullable state row and existing IDs remain unchanged, then capture post-deployment state and update the Forwarder Ops checkpoint.

Rollback to v1.9.5 does not reverse safe sequence advancement. No Production access, server database access, deployment, DNS/IIS/TLS change, or push is part of this preparation.

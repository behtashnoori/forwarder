# AUTH-RG-EXPERT-BASELINE

Status: active development regression control

Failure mode: a newly created active Expert received an empty operational
membership permission list and was denied normal operational APIs.

Rule: a newly provisioned active Expert in an active Organization receives the
authoritative normal Expert operational baseline, including Direct Operation.
Endpoint permission checks, active-user and active-membership checks,
organization resolution, and assigned-work/object authorization remain in
force.

The baseline keeps route-stage execution read/create/update coherent. An owning
Expert must be able to load the governed execution choices and current stage
executions before using the already-authorized create or revise commands.
`execution_unit.read` grants no Shipment scope by itself: persisted current
Shipment ownership, active membership, capability checks and tenant fencing
still apply independently at use time.

Evidence: `backend/tests/test_expert_membership_permissions.py` proves
provisioning, execution read/create/update completeness and idempotent additive
reconciliation.
`backend/tests/test_operational_vertical_slice.py` proves the baseline can use
Direct Operation while a deliberately capability-less membership remains
denied. `backend/tests/test_phase3_transport_execution.py` proves that the same
persisted owner identity shown by the Shipment read projection can load, create,
revise and reopen route-stage execution while existing non-owner, Admin,
inactive-member and foreign-tenant denials remain enforced.

Deferred domain gap: `CARGO_TO_TRANSPORT_UNIT_ALLOCATION=DEFERRED`. No cargo
to transport-unit allocation relationship is introduced by this control.

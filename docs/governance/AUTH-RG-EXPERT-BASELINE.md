# AUTH-RG-EXPERT-BASELINE

Status: active development regression control

Failure mode: a newly created active Expert received an empty operational
membership permission list and was denied normal operational APIs.

Rule: a newly provisioned active Expert in an active Organization receives the
authoritative normal Expert operational baseline, including Direct Operation.
Endpoint permission checks, active-user and active-membership checks,
organization resolution, and assigned-work/object authorization remain in
force.

Evidence: `backend/tests/test_expert_membership_permissions.py` proves
provisioning and idempotent additive reconciliation.  
`backend/tests/test_operational_vertical_slice.py` proves the baseline can use
Direct Operation while a deliberately capability-less membership remains
denied.

Deferred domain gap: `CARGO_TO_TRANSPORT_UNIT_ALLOCATION=DEFERRED`. No cargo
to transport-unit allocation relationship is introduced by this control.

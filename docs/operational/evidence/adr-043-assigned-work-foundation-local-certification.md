# ADR-043 assigned-work foundation — local certification

- Date: 2026-08-30
- Scope: local implementation foundation only; no production access, deployment, or push.
- Governing decisions: ADR-042, ADR-043, ADR-037.

## Implemented

- A fail-closed `authorize_work_action(actor, resource, action)` service resolves active identity, exactly one active tenant membership, canonical authority, resource tenant, request or direct-shipment root, current responsibility, intrinsic action class, and explicit Organization Admin capability.
- `PLATFORM_ADMIN` without tenant membership is denied tenant work. `role=admin` is not used to derive Platform authority.
- Direct OperationalShipment now has an additive `primary_responsible_expert_id` migration/model field. Creation validates an in-tenant responsible Expert and defaults only to the authenticated creation actor when no responsible Expert is supplied; this is creation-time root assignment, not creator-history authorization.
- Existing Direct Shipments with no responsibility remain denied to Basic Expert by the evaluator.

## Local certification

- `pytest backend/tests/test_assigned_work_authorization.py backend/tests/test_tenant_architecture_contract.py backend/tests/test_referral_tenant_fencing.py -q`: 20 passed, 1 expected xfail.
- Operational/CRM/admin/selector regression set: 35 passed.
- Python compilation and whitespace diff check passed.

## Deferred to later controlled implementation phases

Endpoint-wide evaluator integration, SQL collection-scope predicates, all certified child-resource enforcement, Organization Admin category migration, observational shadow telemetry, direct-shipment reassignment endpoint/audit stream, PostgreSQL migration upgrade/downgrade evidence, and browser E2E remain required before `IMPLEMENTATION_READY` can be YES. No permissive dual-evaluator composition has been added.

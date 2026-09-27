# Forwarder Reference Catalog V1 — installation runbook

This is source/runbook guidance for a future approved installation. It is not
deployment authority and must not be used against Production without a separate
approved change.

## Frozen inputs

- Catalog: `backend/reference_data/forwarder-reference-catalog-v1.json`
- Catalog name/version: `FORWARDER_REFERENCE_CATALOG_V1` / `1`
- Catalog checksum:
  `sha256:13a0f6361eca01286422b9ca8df165c2e616c2bc2e73919391056ec7647da45a`
- Organization profile:
  `backend/reference_data/forwarder-standard-org-profile-v1.json`
- Profile name/version: `FORWARDER_STANDARD_ORG_PROFILE_V1` / `1`
- Profile checksum:
  `sha256:38795e90a723eb25c1073a6a92278508e9d89c908105074ff767069d4a8bfce8`

## Required sequence

1. Install the exact approved application package and explicitly upgrade its
   schema through the normal migration command.
2. Run `python -m backend.reference_data_cli plan`. Review that checksum and
   counts match the approved package and that conflict/rejected counts are zero.
3. Run catalog apply only after review:

   `python -m backend.reference_data_cli apply --confirm --operator <named-operator> --approval-reference <approved-change> --expected-checksum sha256:13a0f6361eca01286422b9ca8df165c2e616c2bc2e73919391056ec7647da45a`

4. Run catalog plan again. Expected result is `created_count=0`, the approved
   definitions in `unchanged_count`, and zero conflict/rejected rows.
5. Ensure the target user is an active same-organization Organization Admin. A
   new self-hosted install may explicitly compose a dual admin with:

   `python -m backend.operational_cli bootstrap-self-hosted-admin --confirm --username <user> --organization-public-id <organization-uuid> --operator <named-operator> --approval-reference <approved-change>`

6. Run the organization profile plan:

   `python -m backend.reference_data_cli organization-profile-plan --organization-public-id <organization-uuid> --actor-username <organization-admin>`

7. Review the organization, profile checksum and counts. Intentionally inactive
   prior activations appear separately as `reactivation_count` and
   `reactivations`; they are never silently reactivated.
8. Apply the profile:

   `python -m backend.reference_data_cli organization-profile-apply --confirm --organization-public-id <organization-uuid> --actor-username <organization-admin> --operator <named-operator> --approval-reference <approved-change> --expected-checksum sha256:38795e90a723eb25c1073a6a92278508e9d89c908105074ff767069d4a8bfce8`

   When—and only when—the reviewed plan contains approved reactivation
   candidates, add `--confirm-reactivation`. Each reactivation increments the
   activation version and writes an audit record with the previous state.

9. Run profile plan again. Expected result is `created_count=0`,
   `reactivation_count=0`, `unchanged_count=60`, seven verified Request
   transport methods, and zero conflict/rejected rows.

The commands never run at normal application startup. They do not create
organization SKU items, private logistics points, operational reasons, SLA
durations, document requirements, route reference times or closure policies.

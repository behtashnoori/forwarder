# Forwarder 1.9.4 migration preflight

- Confirm annotated tag `v1.9.4`, verified package identity, backup completion, and separate Production authorization.
- Confirm current revision `20260825_admin_multitenant` and sole target head `20260826_org_document_policy`.
- Confirm the authorized database identity without printing credentials.
- Review the additive organization policy table and operational snapshot provenance changes.
- Do not seed, backfill, infer tenant ownership, or run against an unapproved database.

# Forwarder 1.9.5 migration preflight

- Confirm annotated tag `v1.9.5`, verified package identity, backups, and separate Production authorization.
- Confirm current revision `20260826_org_document_policy` and sole target head `20260827_org_hostname`.
- Confirm the authorized database identity without printing credentials.
- Review the additive `organization_hostname` table, exact normalized-host constraint, and active/primary partial unique indexes.
- Confirm the migration creates no hostname rows and performs no ownership inference, seed, or backfill.
- Do not create the Samand mapping until the separately authorized server phase.

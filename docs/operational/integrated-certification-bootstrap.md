# Integrated Certification Bootstrap Contract

Status: release-assurance infrastructure under PR-D03. It is not a product
capability and is forbidden in Production.

## Candidate binding

Every run records the repository commit and tree, the database migration head,
the SHA-256 of `docs/openapi/openapi.yaml`, and all migration-file hashes. Any
change to this bootstrap therefore creates a new derived candidate and requires
a new run. Evidence is written below
`docs/operational/evidence/integrated-certification/<run-id>/`; credentials and
the representative database backup are excluded from Git.

## Fixture boundary

| Category | Direct bootstrap writes | Required boundary |
|---|---|---|
| Reference/master data | Minimum synthetic Province, ServiceType, MilestoneType, DocumentDefinition, Project configuration, and OIP threshold policy | Existing governed model/configuration conventions; immutable codes are certification-prefixed |
| Test identities | One synthetic organization, disposable users, and memberships | Password supplied only through `FORWARDER_CERT_PASSWORD`; never written to evidence |
| Business transactions | Project only, because the certified product explicitly has no Project creation workflow; synthetic document binary metadata because the artifact is a disposable test input | Commercial Request, Quote, Customer Acceptance, OperationalShipment, MDPM association/assessment/transition, OIP reconciliation/lifecycle, and economics use existing application services |
| Derived state | None | MDPM readiness, OIP Situation/attention projection, and economic projections are calculated from authoritative source facts |

The Project exception is deliberately narrow: `Project` is a required
coordination aggregate, while its model states that the current slice exposes
no Project workflow. The bootstrap may attach the same-tenant accepted request
and shipment to that disposable Project; it must not introduce a product API.

## Safety and determinism

- Exactly one primary organization is created: `[CERTIFICATION] CERTIFICATION_ORG`.
- The target must be loopback PostgreSQL and its database name must begin with
  `forwarder_integrated_cert_`.
- `APP_ENV` must be `test` or `uat`; Production configuration is rejected.
- Synthetic identities use stable logical keys. The command is safe to rerun.
- No Production secret, shared credential, or credential value is accepted as
  evidence. Operators supply a temporary password in process scope.
- External trace fields contain opaque UUID/public identities only. Numeric
  database identities are retained solely inside the application boundary.
- The populated database is disposable and must not be reused as Production
  data.

## Operator command

After migrating a fresh disposable database to head:

```powershell
$env:APP_ENV = 'uat'
$env:DATABASE_URL = '<loopback URL whose database starts forwarder_integrated_cert_>'
$env:FORWARDER_CERT_PASSWORD = '<temporary process-only value>'
python scripts/integrated_certification_bootstrap.py --confirm
```

The JSON output is secret-safe and is the concise Golden Path trace.

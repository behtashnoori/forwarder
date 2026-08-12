# Forwarder 1.9.2 release notes

Forwarder 1.9.2 is the MT-1 tenant data integrity foundation patch release. It preserves the immutable 1.9.1 publication and adds canonical Organization ownership envelopes, same-tenant database constraints, application read/write enforcement, intake acceptance, re-parent protection, and certified quarantine for the human-confirmed synthetic legacy dataset.

The migration advances from `20260819_v191_acceptance_corrections` through five additive MT-1 revisions to sole head `20260824_mt1_graph`. No Organization ownership is backfilled into the 135 synthetic rows; they remain `KEEP_QUARANTINED_SYNTHETIC`. No cleanup or destructive contract phase is included.

Local certification: 709 passed, 79 skipped, one expected xfail, zero unexpected failures/errors; focused PostgreSQL MT-1 matrix 21 passed. Authorized disposable-server certification passed schema, constraints, census, reversibility, and read-only final-state gates. Production was not used for certification.

Deployment requires verified coordinated database/document backups, an application write-quiescence window, explicit Alembic migration, health and tenant-isolation smoke tests, and browser/UAT acceptance. MT-2 and later master-plan milestones remain separate from this patch release and remain required before onboarding a second real company.


# Forwarder v1.10.0 Backup / Restore-Proof Preparation Evidence — 2026-09-22

## Governance and mission classification

The active governing baseline is LPAF v2.2 with its mandatory Agent Entry Protocol. Applicable stages are M0/M1, M6, M7, and M9 at Level B Production rigor: current evidence first, exact artifact identity, recovery proof distinct from backup creation, human-reserved Production execution, and regression promotion for a consequential tooling defect. The reviewed v2.3 reference-impact discipline is applied as a strong default.

`REFERENCE_IMPACT=NONE`: this slice changes no Product behavior, architecture/reference truth, migration, read-only collector, or deployer semantics. It prepares bounded release-operations tooling and evidence only.

## Facts, assumptions, unknowns, and authority

FACT: the human-returned r3 result reports `PRODUCTION_READ_ONLY_COLLECTOR=PASS`, zero collection errors, no Production mutation, proven Scheduled Task/listener ownership, PostgreSQL 18.1 PRIMARY, one baseline revision `20260921_shipment_evidence_ownership`, zero schema-drift blockers, ADR-047 counts `6/0/0/0/0`, and all migration compatibility checks PASS.

FACT: the only remaining live prerequisite is a fresh custom-format Production backup plus isolated restore proof. The observed prior backup was approximately 531 hours old and had no restore evidence.

FACT: the existing backup tool used `[Uri]` directly and admitted only `postgres://` / `postgresql://`; the proven Production configuration uses `postgresql+psycopg2://`. It also did not query or record the current Alembic revision. Running it unchanged would objectively fail or omit a mandatory identity gate.

ASSUMPTION: the human operator has local authority to create a protected backup under `C:\1-webapp\forwarder-backups` and the local PostgreSQL administrator owns an isolated PostgreSQL 18 instance.

UNKNOWN: backup size/SHA256, exact fresh UTC, restore result, and Production-derived migration result remain unknown until human execution. No PASS is claimed for them.

DECISION NEEDED: before transferring the sensitive dump off Production, a named backup/restore owner must approve the protected operator channel, destination, retention, and access controls. No upload, repository commit, public/shared location, or chat transfer is authorized.

## Bounded correction and restore contract

`New-ForwarderV110PreDeploymentBackup.ps1` now supports the established SQLAlchemy URL form without exposing credentials, requires the exact Production host/PostgreSQL major/PRIMARY/baseline revision, and emits `Forwarder-v1.10.0-PreDeploymentBackup-<UTC>.json` with safe identity hashes, size, SHA256, catalog verification, retention/provenance, and explicit zero-mutation declarations.

`Invoke-ForwarderV110ProductionRestoreProof.ps1` is laptop-only. It verifies the transferred dump and frozen Product package, restores to one generated disposable PostgreSQL 18 database, runs baseline compatibility and ADR-047 checks, applies exactly the five migrations with the package runtime, runs governed post-migration assertions, emits sanitized restore evidence, and removes only its strictly named disposable database/work directory. It never connects to Production.

## Qualification

- PowerShell parsing: PASS.
- Backup SQLAlchemy URL self-test: PASS.
- Backup evidence contract self-test: PASS.
- Restore target disposable-only self-test: PASS.
- Exact five-migration sequence self-test: PASS.
- Production tooling regression suite: `27 passed`.
- Python lint for the toolkit builder: PASS.
- Deterministic independent toolkit rebuild: PASS.
- Bundle checksums/inventory: PASS.
- Product package SHA256 remains `2fdef076516273f82044c9b5aa1b2ad03bb8a97423de6c4f7bcb0adec2b0eacf`.
- Deployment bundle SHA256 remains `acf45576c82bc04fa3a3dd02b12500690d4efeeba32c9ffb1e47322227919dbb`.
- Production access: NO.
- Production deployment: NO.

Toolkit:

- Expanded: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Backup-Restore-Proof-Toolkit-e36ee7cee157-r1\`
- ZIP: `D:\1-webapp\forwarder-production-releases\Forwarder-v1.10.0-Backup-Restore-Proof-Toolkit-e36ee7cee157-r1.zip`
- Size: `20882` bytes
- SHA256: `942fd590cb4cc3981788c179bf77e6d0cf2e8e882da727ec2b7229d79263f1b1`
- Files: `10`

```text
LIVE_PRODUCTION_READ_ONLY_PREFLIGHT=PASS
FRESH_BACKUP_RESTORE_PROOF=PENDING
REFERENCE_IMPACT_FINAL=NONE
```

## Preparation verdict

PASS — FORWARDER v1.10.0 FRESH BACKUP / RESTORE-PROOF PROCEDURE READY

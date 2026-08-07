# GDR-FWD-1.9-S3-001 — Disposable S3 gate and framework delta

Decision UTC: 2026-08-07T16:46:00Z  
Authority: Architecture Owner execution brief  
Package consumed: `AEP-FWD-1.9-RC` v0.1.0  
Candidate: `CAND-FWD-1.9.0-NEXT-RC-001`

Decision: **S3 RESUME AUTHORIZED — DISPOSABLE ONLY**.

The package's weakest mandatory link is its explicitly local/disposable authority and confidence boundary. All mandatory links are sufficient inside that boundary. Production is prohibited.

## Project result

- Fresh candidate-scoped backup created outside Git and immediately hashed.
- Backup restored to a fresh allow-listed loopback PostgreSQL target.
- Restored revision and sampled counts matched the source.
- Candidate migration graph upgraded from `20260807_master_data` to the single `20260812_operational_execution` head.
- Migration check reported no pending revision; sampled pre-existing counts remained unchanged.
- Application constructed and served on loopback; authenticated browser read and Release 1.9 initialization write succeeded on a disposable target.
- Targeted migration/security/backend/frontend tests, build, and lint passed.

## Framework delta

| Finding | Delta |
| --- | --- |
| A successful preview was discarded when an unrelated parallel read failed. | CONFIRMS EAAF: gate-facing evidence must retain its own identity and failure boundary. |
| Historical UAT permissions omitted new Release 1.9 permission codes. | NEW FITNESS FUNCTION CANDIDATE: fixture role mappings should be checked against the accepted slice permission catalog. |
| Prior recoverability PASS lacked retrievable custody. | CONFIRMS EAAF: immediate identity, hash, path, and retention records are mandatory. |
| Visible internal IDs existed while opaque v2 execution identities were correct. | NEW REFERENCE EXAMPLE: presentation leakage can violate an identity boundary even when the new API is opaque. |
| S3 is sufficient locally but cannot authorize production. | CONFIRMS EAAF: evidence scope and permitted action must remain coupled. |

No EAAF philosophy change is proposed.


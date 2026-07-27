# Phase 1B persistent target inventory

## Scope and decision

This inventory is repository- and documentation-based. It does not authorize database access or migration application. No `.env` file, credential, raw DSN, customer row, or production repository was read. No database connection was attempted because no single target and no read-only access approval were established.

**Selection decision:** `BLOCKED`. The repository contains several deployment patterns and database references, but it does not identify one approved persistent database with all required ownership, access, backup, and maintenance controls.

## Candidate inventory

Fingerprints below are sanitized labels derived from non-secret repository descriptions; they are not connection values.

| ID | Environment class | Engine | Host class | Database fingerprint | Evidence source | Approved target |
|---|---|---|---|---|---|---|
| PT-01 | DEVELOPMENT_PERSISTENT | PostgreSQL | localhost | `fp-dev-local-template` | `.env.example`, `backend/env.docker.example` | NO; example only |
| PT-02 | DEVELOPMENT_PERSISTENT | PostgreSQL 16 image | private network | `fp-dev-compose-volume` | `docker-compose.yml` named volume and database service | NO; local compose pattern only |
| PT-03 | PRODUCTION | PostgreSQL 16 image | private network | `fp-prod-compose-volume` | `docker-compose.production.yml` named volume and production env file reference | NO; deployment template, not proof of the active target |
| PT-04 | UNKNOWN | PostgreSQL required by runtime | unknown | `fp-runtime-secret-unknown` | `backend/env.production.example`, `backend/config.py`; value must come from a deployment secret source | NO; actual host/database identity is absent |
| PT-05 | INTERNAL_UAT | PostgreSQL 18 disposable | localhost | `fp-uat-disposable-retired` | Phase 1B application register and UAT evidence | NO; disposable resources were removed |
| PT-06 | PRODUCTION | PostgreSQL expected | unknown | `fp-historical-prod-unknown` | Historical production reference: separate repository, service port 5001, old deploy branch/commit | NO; isolation reference only and not database identity |

SQLite local-development storage is explicitly excluded from persistent-target selection.

## Selection controls

| Control | Evidence | Result |
|---|---|---|
| Environment class | Multiple classes are documented | AMBIGUOUS |
| Environment owner | No named owner for a candidate target | MISSING |
| Database owner | No named database owner | MISSING |
| Connection source | Production template names a secret-store responsibility, but no approved source is identified | MISSING |
| PostgreSQL engine | Required by UAT/production runtime; templates use PostgreSQL | PASS at design level |
| Database identity | Template labels exist; active database identity is not proven | MISSING |
| Backup location | No approved target-specific location | MISSING |
| Migration authority | No named approver or change ticket | MISSING |
| Maintenance policy | No approved window or downtime budget | MISSING |
| Read-only inspection approval | Not provided | MISSING |

## Approval boundary

| Control | Required | Current state |
|---|---|---|
| Environment owner identified | YES | NO |
| Database owner identified | YES | NO |
| Read-only inspection approved | YES | NO |
| Production classification known | YES | NO for the actual target |
| Credential source approved | YES | NO |
| Backup responsibility known | YES | NO |

The human decision package must identify exactly one candidate or a new candidate, its environment classification, owner names, sanitized host/database fingerprint, approved credential source, backup destination, maintenance window, and Go/No-Go authority. Until then, public PostgreSQL 5432 and the historical production environment remain untouched.

## Isolation record

- Production repository touched: NO
- Production service or port 5001 touched: NO
- Public PostgreSQL touched: NO
- Persistent database applied: NO
- Deploy or merge performed: NO

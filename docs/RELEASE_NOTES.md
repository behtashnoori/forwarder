# Release Notes

## Unreleased

### Feature: Landing Page Value Proposition Enhancement

Release metadata:

| Field | Value |
| --- | --- |
| VERSION | `1.1.0` |
| RELEASE NAME | `Landing Page Value Proposition Enhancement` |
| CHANGE TYPE | `MINOR / Feature` |
| GIT COMMIT | `PENDING — to be recorded after commit creation` |
| DATABASE REVISION | `20260804_case_documents` — unchanged, no pending migration |
| DEPLOYMENT TYPE | `Frontend-only application deployment; no database migration` |

Version decision: the repository has no separate release-version policy document; the runtime application baseline is `1.0.0`, and this backward-compatible user-facing feature increments the SemVer minor component to `1.1.0`.

Business value:

- Positions Forwardert as a workflow-management platform rather than only an online request form.
- Makes process visibility, controlled document management, reporting, and stakeholder coordination easier for prospective users to understand.
- Reduces ambiguity between process visibility and unsupported GPS or live-location tracking.
- Improves Persian and English product discovery through clearer search and social metadata.

Changes:

- Updated product positioning from a request-form-focused message to international freight workflow management.
- Added a key capability section covering process visibility, authorized document access, operational reporting, and stakeholder coordination.
- Improved SEO metadata, Open Graph title and description, keywords, document language, and dynamic title fallback behavior.
- Updated bilingual Persian and English landing-page content.

Technical scope:

- Updated the public landing-page composition and responsive capability cards.
- Updated Persian and English translation resources.
- Updated static SEO/Open Graph metadata and runtime title fallback configuration.
- Added release documentation and refreshed desktop/mobile UI evidence.
- No backend, API, database, migration, dependency, or routing changes.
- No GPS, map, live-location, or automated carrier-integration capability is claimed.

Deployment impact:

- Rebuild and deploy the frontend application assets.
- Backend restart is not required for this feature.
- No Alembic upgrade, data backfill, environment-variable change, or service dependency change is required.
- Existing request submission, public status tracking, expert access, and admin/reporting routes remain compatible.
- Browser/CDN cache invalidation should follow the normal frontend deployment procedure so updated HTML metadata is served.

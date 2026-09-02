# Production verification plan (not executed)

Read-only checks: verify artifact SHA before extraction; release-directory, backend/source and frontend identity; root/SPA; API; Organization Admin, Platform Admin and Expert authority; canonical tenant resolution; document/readiness; reporting/export fencing; reference and operational networks; logs; DB head; and CORS/canonical-host behavior. HTTP 200 alone is insufficient.

Controlled mutating smoke requires separate authorization, synthetic identification and cleanup policy: bounded customer request → tenant → assignment → expert visibility only. Stop on any identity, authorization, tenant, CORS, migration or severe-error failure.

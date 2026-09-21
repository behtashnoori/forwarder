# New Forwarder UAT Version — Forwarder UAT v1.10.0

## Release identity

| Field | Value |
| --- | --- |
| Previous Product Version | `1.9.5.1` |
| New Product Version | `1.10.0` |
| Release ID | `Forwarder-UAT-v1.10.0` |
| Accepted Product Base SHA | `a742628293359379cb476b782a2fe27e61a8db1f` |
| Release Source SHA | `RESOLVED_AFTER_RELEASE_COMMIT` |
| Final Canonical SHA | `RESOLVED_AFTER_EVIDENCE_COMMIT` |
| Release Tag | `forwarder-uat-v1.10.0` |
| Tag Target SHA | `RESOLVED_AFTER_RELEASE_COMMIT` |
| Package | `RESOLVED_AFTER_PACKAGE_BUILD` |
| Package SHA-256 | `RESOLVED_AFTER_PACKAGE_BUILD` |
| Database head | `20260926_fixed_shipment_responsible_expert` |
| Runtime entrypoint | `START-UAT.ps1` |

## Owned UAT runtime

This package is restricted to a non-Production, loopback PostgreSQL database
whose name starts with `forwarder_uat_`. It refuses another database identity.
The default browser URL is `http://127.0.0.1:8110`; the internal backend listens
on `127.0.0.1:5110`.

1. Verify the package with `VERIFY-PACKAGE.ps1`.
2. Create an owned disposable database named `forwarder_uat_<session>` by using
   the repository's governed disposable-database helper.
3. Set `APP_ENV=uat`, point `DATABASE_URL` at that owned database, and run the
   packaged `runtime\python.exe -m backend.migration_cli upgrade
   20260926_fixed_shipment_responsible_expert --confirm`.
4. Run the approved UAT fixture runner. It generates a fresh password at runtime
   and provides persona names in its local fixture record. The secret is not
   written to Git or release evidence.
5. Start with:

   `./START-UAT.ps1 -DatabaseUrl <owned-loopback-url> -DocumentStorageRoot <owned-uat-storage>`

6. Stop with `./STOP-UAT.ps1`.

## Personas

- Customer — Request, Cargo, Quote response, Shipment, and public tracking.
- Transport Expert E1 — official Quote issuer and fixed Shipment owner.
- Transport Expert E2 — negative fixed-owner authorization persona.
- Admin/Manager — organization oversight and read-only governed Documents view.
- Public Tracking visitor — unauthenticated opaque-capability journey.

The approved fixture runner records the generated persona usernames and the
operator-only credential location. It never records the password in Git,
package metadata, screenshots, or evidence.

## Customer-session order

1. Open or create the Customer Request.
2. Show transport intent, an empty Cargo case, and a multiple-Cargo case.
3. Open the official Quote and choose Needs Discussion.
4. As Expert E1, read the message and issue a revised official Quote.
5. As Customer, accept the revision.
6. Open the resulting Shipment and show the fixed Expert owner.
7. Show Documents and version history.
8. Show tracking/event history.
9. Open Control Tower, search/filter, and drill into the Shipment.
10. Open the product-generated `SR2-` opaque Public Tracking link.
11. Point out Gregorian (Jalali) dates and the Persian/RTL mobile view.

## Reset and rehearsal

Stop the package, drop only the owned `forwarder_uat_<session>` database, delete
only its owned document-storage directory, recreate the disposable database,
run migrations, and rerun the approved fixture runner. Never edit rows manually.
The Customer journey is ready only when the complete storyboard can be repeated
without database surgery.

## Intentionally deferred

Notification delivery remains dormant. Mandatory Cargo, generalized Customer
Documents, exactly-once Document upload recovery, retention/purge/DMS,
personalized dashboards, extended public-tracking hardening, Production
migration adjudication, Modular Architecture Assessment, and Staged
Modularization are not part of this UAT release.

No Production database, environment, IIS site, Scheduled Task, or Production
configuration is used or changed by this handoff.

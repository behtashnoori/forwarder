# Phase 1A findings and deferred items

Fixed during recovery: invalid PostgreSQL verifier fixture role; detached ORM fixture references; nested API-error parsing; stable idempotency conflict code; queue pagination; correction replay ordering; required event idempotency keys; per-organization PostgreSQL reconcile serialization; missing list/detail/queue data and states; duplicate-submit guard; operational accessibility/testing configuration.

Closure blocker: the earlier Browser UAT record claimed a complete run and
screenshot evidence that the current finalization run did not verify. Those
claims were superseded by closure run `P1A-UAT-20260723125334`.

Defects fixed in the closure run:

- UAT provisioning granted every operational permission to reporter and
  verifier users. Permissions are now separated by role, while unauthorized and
  outsider users receive no operational permissions.
- The create form exposed a raw `Invalid time value` error in the real browser.
  Date-time input is now explicit and invalid values receive a localized
  validation message; a frontend regression test covers the failure.

The remaining blocker was closed in `P1A-MOBILE-CLOSURE-20260723132017`.
The earlier fixed 1280px width was confirmed as an in-app runner limitation.
Fresh temporary Playwright Chromium contexts proved exact 360, 390, and 768
widths through JavaScript, client dimensions, media queries, and PNG metadata;
interactive mobile UAT had no document overflow. UAT-20 also passed an
owned-backend stop, bounded error, restart, health, and in-page Retry cycle.

Final notes: twelve existing lint warnings and the deferred features below are
non-blocking. No production, deployment, merge, or Phase 1B action occurred.

Deferred: multiple active-plan history UI, complex multi-leg planning, documents, claims, exceptions, costs/invoice/settlement, GPS, external notification delivery, Excel import, and full control-tower dashboard. Phase 1B, merge, release, and deployment are out of scope. Production, production credentials, and servers were not touched.

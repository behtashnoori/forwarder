# Forwarder 1.9.4 post-deployment acceptance

1. Public root returns the production `index.html` and does not reference `/src/main.tsx`.
2. Hashed JavaScript and CSS under `/assets/` return HTTP 200.
3. Backend and public health return HTTP 200.
4. `python -m backend.migration_cli current` reports `20260826_org_document_policy`.
5. Platform Admin retains global Document Definition management.
6. Organization Admin sees only its Organization Document Policy and cannot submit another organization identifier.
7. Effective precedence is Project override, Organization policy, then compatibility fallback only with zero policy rows.
8. Representative case/readiness snapshots record provenance and existing snapshots remain unchanged.

Also verify visible/support release identity `1.9.4` and same-origin API routing. Do not create or onboard another Organization during acceptance.

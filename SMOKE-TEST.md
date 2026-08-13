# Forwarder 1.9.3.1 post-deployment acceptance

1. Public root returns the production `index.html` and does not reference `/src/main.tsx`.
2. Hashed JavaScript and CSS under `/assets/` return HTTP 200.
3. Backend and public health return HTTP 200.
4. `python -m backend.migration_cli current` remains `20260825_admin_multitenant`.
5. Existing Samand Tarabar Organization Admin can log in and open User Management without a render crash.
6. User-management API errors render as controlled messages.
7. Organization Admin remains unable to mutate Platform-only settings or global reference configuration.
8. Existing operational data remains accessible according to tenant policy.

Also verify visible/support release identity `1.9.3.1` and same-origin API routing. Do not create or onboard another Organization during acceptance.

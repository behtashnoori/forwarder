# Forwarder 1.9.3 post-deployment acceptance

1. IIS Forwarder site is Started.
2. Backend is listening on `127.0.0.1:5101`.
3. Backend HTTP health returns 200.
4. Public URL returns 200.
5. `python -m backend.migration_cli current` reports `20260825_admin_multitenant`.
6. Existing Samand Tarabar admin can log in.
7. That admin resolves exactly one active Organization.
8. Organization Admin cannot mutate Platform-only settings or global reference configuration.
9. Normal shipment and admin pages load without HTTP 500.
10. Existing Samand Tarabar operational data remains accessible according to tenant policy.

Also verify visible/support release identity `1.9.3`, same-origin API routing, and Platform Admin versus Organization Admin separation. Do not create or onboard Company B during acceptance.

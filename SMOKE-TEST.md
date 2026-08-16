# Forwarder 1.9.5 post-deployment acceptance

1. Public root returns production `index.html`; it does not reference `/src/main.tsx`.
2. Hashed JavaScript and CSS under `/assets/` return HTTP 200.
3. Backend and public health return HTTP 200.
4. `python -m backend.migration_cli current` reports `20260827_org_hostname`.
5. Unknown or unmapped hostnames create `INTAKE` requests with no Organization ownership.
6. The authorized Samand hostname resolves to the Samand Organization only after mapping/DNS/IIS/TLS setup.
7. A Samand-host submission creates a `TENANT` request owned by Samand.
8. Referral assignment selects only an active, uniquely membered Samand expert in an active Organization.
9. With no eligible Samand expert, the request remains tenant-owned and unassigned.
10. Samand Organization Admin sees the request; another Organization Admin does not.

Also verify visible/support release identity `1.9.5`, same-origin API routing, and post-deployment server-state evidence.

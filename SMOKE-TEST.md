# Forwarder 1.9.5.1 post-deployment acceptance

1. Public root returns production `index.html`; it does not reference `/src/main.tsx`.
2. Hashed JavaScript and CSS under `/assets/` return HTTP 200.
3. Backend and public health return HTTP 200.
4. `python -m backend.migration_cli current` reports `20260828_referral_state_compat`.
5. Submit a shipment through `https://samand.logisticmarket.ir`.
6. Confirm no `referral_auto_assign_state` primary-key error occurs.
7. Confirm the request remains `TENANT` and belongs to the Samand Organization.
8. Confirm an eligible Samand expert is assigned, or the request remains tenant-owned in the unassigned queue.
9. Confirm the nullable legacy referral state row and all existing IDs remain unchanged.

Also verify visible/support release identity `1.9.5.1` and same-origin API routing.

# Forwarder 1.9.5.1 migration preflight

- Confirm annotated tag `v1.9.5.1`, verified package identity, backup completion, and separate Production authorization.
- Confirm current revision `20260827_org_hostname` and sole target head `20260828_referral_state_compat`.
- Confirm the authorized database identity without printing credentials.
- Record `MAX(referral_auto_assign_state.id)` and the sequence state for evidence.
- Run the additive compatibility migration; do not change existing IDs or Organization ownership.
- Confirm the nullable legacy row remains unchanged and the sequence can allocate above every existing ID.

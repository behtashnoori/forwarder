# Forwarder 1.9.5.1 rollback and recovery

The application rollback target is immutable `v1.9.5`.

Stop v1.9.5.1 at `20260828_referral_state_compat` before rollback and downgrade the recorded Alembic revision to `20260827_org_hostname`. The downgrade intentionally does not reverse safe PostgreSQL sequence advancement because lowering the allocator could recreate duplicate primary-key failures. Existing referral state rows and IDs remain unchanged. Reactivate v1.9.5 only after database and application identity checks pass.

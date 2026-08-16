# Forwarder 1.9.5 rollback and recovery

The application rollback target is immutable `v1.9.4`.

Stop v1.9.5 at `20260827_org_hostname` before rollback. Record and remove hostname routing configuration under approved change control, downgrade to `20260826_org_document_policy`, then reactivate v1.9.4. Reverse DNS, IIS binding, and TLS changes through their owning server procedures. Never force a downgrade, delete tenant ownership, or fabricate replacement ownership.

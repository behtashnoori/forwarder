# Forwarder v1.9.5.1 hotfix release notes

Forwarder v1.9.5.1 repairs legacy-to-tenant referral auto-assignment state compatibility.

- An additive PostgreSQL migration safely aligns the state-table sequence with existing IDs without rewriting or deleting rows.
- The nullable legacy global state row is preserved as compatibility data and is never shared with tenant-specific state.
- Concurrent first use for one Organization converges on its unique state row through a savepoint-protected insert path.
- Different Organizations continue to receive isolated state rows.
- Hostname routing and runtime referral tenant fencing remain unchanged.

This hotfix does not access Production, modify hostname mappings, DNS, IIS, or TLS, deploy, seed, backfill ownership, or push Git refs.

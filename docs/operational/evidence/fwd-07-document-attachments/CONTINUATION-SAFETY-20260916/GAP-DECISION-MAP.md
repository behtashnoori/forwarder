# Previously undefined recovery gaps — proposed decisions only

| Previously NOT_DEFINED | Proposed choice now | ADR-049 section |
| --- | --- | --- |
| Operation/receipt owner | Dedicated document-owned operation persistence; receipt in same row | 2, 9 |
| Pre-send stable identity/scope | UI UUID v4, tenant uniqueness, fixed target/action/initiating actor | 3 |
| Payload/bytes binding | Versioned canonical effective manifest plus server-verified SHA256/length | 3 |
| Lifecycle/in-progress/unknown | RESERVED/RECEIVING/STAGED/SUCCEEDED/REJECTED/EXPIRED; UNKNOWN client-only | 4 |
| Reopen/client state | User/tenant IndexedDB manifests; no bytes/credentials; bounded actor discovery after state loss | 5 |
| Current authority/revoke | Reauthorize every seam; deny revoked/reassigned replay; no file reactivation | 6 |
| Storage/DB/crashes/races | Fenced claims, generation staging, one no-overwrite operation final key, atomic DB file/receipt/audit | 7 |
| Old clients/replacement | No legacy replay guarantee; exact replaced version; explicit N-1 disablement | 6, 8 |
| Retention/late retry | 90-day rich discovery; durable non-reuse/history tombstones; 410 without new attachment | 8 |
| Schema/history/migration/rollback | New owner table + nullable file link; actual FWD06 predecessor; no intent backfill; populated downgrade refuses | 9 |
| Concrete real validation | Real dropped committed response, native races/crash matrix, revoke and RTL file states | 11 |

All are PROPOSED. Owner acceptance and separate implementation authority are still required. No runtime implementation, migration or cleanup is authorized by this document.

# Evidence custody index — AEP-FWD-1.9-RC

Producer: Codex stabilization executor  
Indexed UTC: 2026-08-07T16:48:00Z  
Scope and candidate binding: Release 1.9 disposable S3; `CAND-FWD-1.9.0-NEXT-RC-001` at `fa2871e0717a6062e5cb362eaaf4f751893d2c5a`.

Retention: retain through the Release 1.9 human production decision and any authorized rollback window. Expire on candidate change, integrity failure, loss of retrievability, supersession, or a relevant environment/engine change.

## Governed Git records

| Path | Size | SHA-256 | Git blob |
| --- | ---: | --- | --- |
| `aep-manifest.yaml` | 3,782 | `8817fac3da435d633b9f61a54633e29ab384c0e2bae753d61d4b2baee3057db4` | `e1e53ce57a3c837de39e2bd3157a85bafa40506c` |
| `browser-validation.md` | 1,645 | `140e333c66207b430b3b9714b4b3530052535d16254bfff2834388fc7560a920` | `0ca4d293992540ebf8ad33499568048078c76136` |
| `candidate-manifest.yaml` | 3,161 | `7064ad5839fc142691c923f75c1fb6b44573e6eee7c4588625a48b24588670f1` | `49561cd55a8fee4c0736edc7b1cc601b43e65097` |
| `gate-and-framework-delta.md` | 2,081 | `63e0bd4f340406dd8317d65a3514aa127bfb1765c55b246af9c60d9f6b668562` | `969f737787cd5e02b80b02085ba943b3289c2c29` |
| `recoverability-evidence.yaml` | 2,734 | `465c1d6e912666a51a2e3298d2ef45216095c7489276d6b61daa7d9e65e2faff` | `a9693327abb4b71c1d4cf5d430d8bcb2920ead7b` |

## External evidence

Base path: `C:/Users/pc/AppData/Local/Forwarder/15-forwarder/evidence/AEP-FWD-1.9-RC/recoverability/`

| Evidence ID / file | Size | SHA-256 | Lifecycle |
| --- | ---: | --- | --- |
| `EVD-FWD-REC-003-next-rc-source.dump` | 367,958 | `1e6307834c54b3305d33480a9c19f0736f0e049d892366ddaa43579197998758` | ACTIVE |
| `EVD-FWD-S3-003-next-rc-upgrade.txt` | 3,540 | `d9e1b19c026edaa121ae961bc13c30644812a9a210a7f2f0a5259c0694061492` | CONSUMED |
| `EVD-FWD-S3-004-next-rc-check.txt` | 588 | `8d4fa2d09db59626fe1fb40fab331b5d5d0449275b60833494fd041b5c76ad35` | CONSUMED |
| `EVD-FWD-S3-005-next-rc-downgrade.txt` | 1,628 | `01746315ad3ee777050fea8f91f1e5ba9c06bb98666af84875bf48deb9ac199f` | CONSUMED |
| `EVD-FWD-S3-006-next-rc-reupgrade.txt` | 1,878 | `9fd4d6f179ebea3fdf9f6239af024dc3d720ee3e5c6a9777b448fe2e3ded9e03` | CONSUMED |
| `EVD-FWD-S3-007-next-rc-final-check.txt` | 588 | `8d4fa2d09db59626fe1fb40fab331b5d5d0449275b60833494fd041b5c76ad35` | CONSUMED |

`EVD-FWD-REC-001`, `EVD-FWD-REC-002`, `EVD-FWD-S3-001`, and `EVD-FWD-S3-002` are retained as superseded rehearsal history and do not authorize the frozen candidate.

The backup contains no exported credentials. Credentials were supplied only through process-scoped environment variables.


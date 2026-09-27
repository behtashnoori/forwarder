# P3-15 security matrix

Result: **PASS**. The focused backend set passed 165 tests with zero failures;
the browser and PostgreSQL evidence below adds normal-navigation and persisted
multi-session proof.

| Required boundary | Result | Evidence |
| --- | --- | --- |
| Tenant A versus Tenant B | PASS | Workspace Phase 1, reference/catalog/route PostgreSQL tests, `test_admin_multitenant_adversarial` |
| owner Expert | PASS | P3-01..14 browser set, IPJ-01, IPJ-04 |
| non-owner Expert | PASS | IPJ-01 fixed owner, P3-13/IPJ-04 old-owner denial |
| inactive membership | PASS | authorization/security backend tests and P3-01 catalog journey |
| Organization Admin | PASS | P3-14 normal navigation, P3-12 policy, P3-13 transfer, IPJ-04 closure policy |
| Platform Admin without tenant membership | PASS | admin multitenant and operational authorization tests |
| Customer A | PASS | P3-09 and IPJ-04 own-Cargo/document/location/delivery projection |
| Customer B | PASS | P3-09 and IPJ-04 independent private projection |
| unentitled Customer C | PASS | P3-09 empty list and direct 404 |
| revoked DN10 entitlement | PASS | P3-09 revoke, in-flight stale-response rejection and fresh list |
| Public Tracking | PASS | MT3 PostgreSQL + Chrome; opaque capability and fixed allowlist |
| guessed identifiers | PASS | MT3 numeric/opaque probes, Customer and internal 404 contracts |
| direct links | PASS | foreign Expert, unentitled Customer and old-owner direct route/API probes |
| count/search/page | PASS | admin multitenant, Customer entitlement and control-tower scope tests |
| document metadata/download | PASS | P3-06, P3-09, P3-13/IPJ-04 and shipment-document authorization tests |
| old/new owner after transfer | PASS | P3-13 and named IPJ-04 browser proof |
| stale browser/cache | PASS | P3-09 delayed authorized response after revoke; P3-14 obsolete list response protection |
| post-closure command boundary | PASS | P3-12 plus IPJ-04 new reported-fact command denied after reopen |
| recovery token/session | PASS | valid, expired, invalid/replay, single-use, old session revoked, old password denied, new login accepted |

Focused suites:

```text
test_admin_multitenant_adversarial
test_customer_entitlement
test_shipment_document_authorization
test_phase3_owner_transfer
test_phase3_closure
test_customer_portal_account
test_public_tracking_security
test_operational_workspace
test_control_tower_scope
```

All negative boundaries fail closed. No negative test treats an infrastructure
failure as an authorization PASS.

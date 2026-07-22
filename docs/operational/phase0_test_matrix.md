# Phase 0 Test Matrix

این ماتریس acceptance design برای Phase 1/vertical slice است؛ Phase 0 کدی برای اجرای تست اضافه نمی‌کند.

## Matrix

| ID | سطح | سناریو | انتظار | Gate |
|---|---|---|---|---|
| T01 | Domain | convert accepted quote | یک OperationalShipment با lineage | P1 |
| T02 | Domain | quote رد/منقضی | guard failure | P1 |
| T03 | Idempotency | replay همان key/payload | همان response، duplicate صفر | P1 |
| T04 | Idempotency | همان key/payload متفاوت | 409 | P1 |
| T05 | Concurrency | expected version قدیمی | 409، lost update صفر | P1 |
| T06 | State | transition نامعتبر | 409 stable code | P1 |
| T07 | Route | sequence/time نامعتبر | 422 | P1 |
| T08 | Route | publish revision | plan قبلی immutable | P1 |
| T09 | Location | master rename | snapshot تاریخی ثابت | P1 |
| T10 | Location | free text unverified | quarantine/verification required | P1 |
| T11 | Event | duplicate MilestoneEvent | effect یک‌بار | P1 |
| T12 | Event | out-of-order event | deterministic projection | P1 |
| T13 | Event | correction | supersedes، تاریخچه حفظ | P1 |
| T14 | Verify | submitter self-verify حساس | forbidden طبق policy | P1 |
| T15 | Completion | required milestone ناقص | completion blocked | P1 |
| T16 | Permission | cross-org read/write | 403/404-safe | P1 |
| T17 | Public | tracking response | internal fields صفر | P1 |
| T18 | Queue | overdue milestone | WorkItem یکتا | P2 |
| T19 | Queue | claim/resolve | owner/audit/state صحیح | P2 |
| T20 | Migration | empty DB upgrade | head صحیح | P1 |
| T21 | Migration | production-like upgrade | data/invariants سالم | P1 |
| T22 | Migration | backfill rerun/resume | idempotent/checkpoint | P1 |
| T23 | Compatibility | legacy Request/Quote | baseline بدون regression | هر release |
| T24 | Compatibility | legacy public tracking | contract/fallback سالم | P2 |
| T25 | Observability | correlation end-to-end | log/event/audit قابل ردیابی | P1 |
| T26 | Recovery | flags off/application rollback | legacy فعال، داده حفظ | P1 |
| T27 | Security | IDOR/mass assignment | blocked | P1 |
| T28 | Performance | queue/projection/API baseline | در SLO مصوب | P2 |

## Test suites اجباری

- unit invariant/state machine؛
- service/transaction integration؛
- PostgreSQL migration/constraint؛
- OpenAPI contract/client compatibility؛
- authorization matrix و organization scope؛
- idempotency/concurrency/property tests؛
- projection rebuild/out-of-order؛
- public allowlist snapshot؛
- regression Request/Assignment/Quote/CRM/Tracking/Auth؛
- backup/restore و rollback rehearsal.

## Regression scope موجود

ایجاد request داخلی/بین‌المللی، auto/manual assignment، expert list/detail/status، quote و customer accept/reject، CRM linking، admin report/XLSX، public tracking، auth session/revocation و location/reference endpoints.

## Test data

حداقل dataset: request با چند quote، quote accepted/rejected/expired، route یک و دو leg، دو timezone، چند unit، duplicate/out-of-order event، location rename، cross-organization principals و exception overdue. داده production باید anonymized و استفاده آن **نیازمند تأیید** باشد.

## Quality thresholds

- duplicate/orphan/public sensitive-field: صفر؛
- state/permission critical tests: 100٪ PASS؛
- migration rerun: اثر اضافی صفر؛
- projection rebuild: خروجی deterministic؛
- performance/SLO و shadow mismatch: عدد **نیازمند تأیید**؛
- flaky critical test: صفر.

## Traceability

هر acceptance criterion vertical slice حداقل یک T-ID دارد. هر transition از [State Matrix](phase0_state_transition_matrix.md) و هر permission از [Permission Matrix](phase0_permission_matrix.md) باید test case مثبت و منفی داشته باشد.

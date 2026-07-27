# گزارش PostgreSQL Startup Recovery و Operator Full UAT

## Final status note (2026-07-27)

Recovery was verified by the final runs. Browser/Mobile UAT is `YES`, all five viewports and 22/22 workflows passed, and P1B-UAT-001 through P1B-UAT-006 are `CLOSED_VERIFIED`. Persistent applied is `NO`; production/public PostgreSQL was untouched. Earlier NO/pending states below are historical chronology only.

## PostgreSQL Root Cause

- Status: `RECOVERED`
- Root cause: Harness، سرور را مستقیماً با `postgres.exe` اجرا می‌کرد. PostgreSQL 18 در این محیط
  اجرای مستقیم سرور با سطح دسترسی administrative را با exit code برابر `1` رد کرد.
- Classification: `RC-D — PG_CTL_LAUNCH_ARGUMENT_DEFECT`
- Previous exit stage: `postgres child process`، پیش از listener و connection acceptance
- PostgreSQL log finding: Runtime قبلی طبق cleanup حذف شده بود و log آن باقی نمانده بود. بازتولید
  دقیق direct-launch پیام `Execution of PostgreSQL by a user with administrative permissions is not
  permitted.` را ثبت کرد.
- Harness defect: `YES`
- Environment defect: `NO`؛ PostgreSQL 18.0 و تمام binaryهای لازم سالم‌اند.
- Files changed: `scripts/uat/phase1b_full_uat_runner.py`,
  `backend/tests/test_phase1b_full_uat_runner.py` و همین گزارش

اصلاح محدود Harness، startup را به argument vector بدون shell زیر منتقل کرد:

`pg_ctl.exe start -D <data> -l <server-log> -o "-h 127.0.0.1 -p <token-port>" -w`

Readiness با `pg_isready` بررسی و cleanup فقط با `pg_ctl stop -D <owned-data-dir> -m fast -w`
انجام می‌شود. Failure diagnostics شامل exit code و tail پاک‌سازی‌شده log است.

## Live PostgreSQL Probe

| Control | Result |
|---|---|
| initdb | PASS؛ exit `0`، مدت `5.122s` |
| PostgreSQL start | PASS؛ یک attempt |
| Listener loopback | PASS؛ فقط `127.0.0.1` روی port موقت `52987` |
| pg_isready | PASS؛ exit `0`، `86ms` |
| SQL connection | PASS؛ exit `0`، `77ms` |
| Version | PostgreSQL `18.0` |
| UTF8 | PASS |
| Cleanup | PASS؛ listener صفر و runtime حذف شد |

Probe مستقیم contract قبلی نیز با cluster تازه انجام شد: `initdb=0`، سپس
`postgres.exe=1` پیش از readiness، با پیام administrative-permission فوق. بنابراین timeout،
port collision، config، authentication و dependency علت نبودند.

## Harness Validation

| Control | Result |
|---|---|
| Compile | PASS |
| Unit tests | PASS؛ `10 passed` |
| Validate-only | PASS؛ `processes_started=false` |
| Dry-run | PASS؛ `processes_started=false` |
| Secret scan | PASS؛ `findings=0` |
| git diff --check | PASS |

## Full UAT

- Status: `BLOCKED_AFTER_BROWSER_RUNNER_START`
- Browser Runner: اجرا شد و exit code برابر `1` برگرداند؛ retry انجام نشد.
- PostgreSQL: PASS
- Backend: PASS (readiness عبور کرد)
- Vite: PASS (readiness عبور کرد)
- Viewports: نتیجه نهایی قابل تأیید نیست.
- Workflows: نتیجه نهایی قابل تأیید نیست.
- Browser/Mobile UAT: `NO`
- Persistent applied: `NO`

Runtime همان run طبق قرارداد پاک شد. Browser runner خروجی console نداشت و evidence داخل runtime
بود؛ بنابراین علت داخلی exit code `1` پس از cleanup قابل بازیابی نبود. Harness برای runهای بعدی
اصلاح شد تا `phase1b_browser_result.json` را پیش از cleanup در failure detail حفظ کند. طبق ممنوعیت
retry و product remediation، run دیگری انجام نشد.

## Defects

| ID | Final status |
|---|---|
| P1B-UAT-001 | FIXED_PENDING_FULL_UAT |
| P1B-UAT-002 | RESOLVED_HARNESS_ALIGNMENT_PENDING_FULL_UAT |
| P1B-UAT-003 | FIXED_PENDING_FULL_UAT |
| P1B-UAT-004 | FIXED_PENDING_FULL_UAT |
| P1B-UAT-005 | FIXED_PENDING_FULL_UAT |
| P1B-UAT-006 | RESOLVED_TEST_FIXTURE_ALIGNMENT_PENDING_FULL_UAT |

`NOT EXECUTED` یا run ناقص، defect status را تغییر نمی‌دهد.

## Reports

- JSON: `C:\Users\pc\AppData\Local\Temp\forwarder-phase1b-uat-reports\P1B-UAT-20260726185010908193.json`
- Markdown: `C:\Users\pc\AppData\Local\Temp\forwarder-phase1b-uat-reports\P1B-UAT-20260726185010908193.md`
- PostgreSQL recovery report: `docs/operational/phase1b_postgresql_startup_recovery.md`

Credential موقت Browser که ابتدا در report تولیدی آشکار شده بود فوراً redact شد و
`PHASE1B_UAT_PASSWORD` به secret-key set Harness افزوده شد.

## Cleanup

- Token processes: صفر
- Token listeners: `55432`, `57066`, `5174` همگی صفر
- Disposable databases: حذف‌شده همراه cluster disposable
- Runtime directory: حذف‌شده
- Public PostgreSQL: listener موجود روی `5432` متوقف یا تغییر داده نشد
- Production repository: دست‌نخورده
- Tracked databases: در Git تغییر نکردند و باز یا query نشدند
- `.backend-port`: `57065`
- Commit/Stage/Push/Deploy: صفر

## خط پایانی

PHASE_1B_BROWSER_MOBILE_UAT_BLOCKED

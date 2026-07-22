# Phase 0.1 Backend Restart and Rollback Runbook

> این Runbook دستور عملیاتی آینده است. اجرای آن در این مأموریت انجام نشده است.

## Preconditions

1. branch/commit release و artifact digest ثبت شود.
2. backup و restore point طبق سیاست سازمان تأیید شود.
3. target با خروجی پاک‌سازی‌شده `migration_cli current` بازبینی شود.
4. `AUTO_MIGRATE_ON_STARTUP=false` باشد.
5. `DB_CONNECT_TIMEOUT_SECONDS` مقدار محدود و تأییدشده داشته باشد.
6. maintenance window، owner و rollback commander مشخص باشند.
7. secretها فقط از secret manager/environment و هرگز در command/log قرار نگیرند.

## Pre-deploy read-only gate

```powershell
python -m backend.migration_cli current
python -m backend.migration_cli check
```

exit 0 از check یعنی current=head. exit 2 یعنی migration معوق و start production باید مسدود بماند. خطای اتصال نیز NO-GO است.

## Explicit migration step

تنها پس از backup، review target و approval:

```powershell
python -m backend.migration_cli upgrade --confirm
python -m backend.migration_cli check
```

این مرحله باید به‌عنوان release job تک‌نمونه اجرا شود، نه در Gunicorn worker، container startup یا health probe.
اجرای هم‌زمان دو migration job ممنوع است؛ orchestrator/deployment pipeline باید single-runner بودن این step را تضمین کند.

## Start/restart sequence

1. old instanceها drain شوند؛
2. artifact جدید با `backend.wsgi:app` و env false شروع شود؛
3. `/api/health/ping` برای liveness؛
4. `/api/health/ready` باید 200 دهد؛
5. smoke read-only endpointها؛
6. traffic تدریجی؛
7. error/latency/readiness monitor؛
8. old instance فقط پس از soak period متوقف شود.

restart command وابسته به platform است و **نیازمند تأیید**؛ این سند عمداً systemctl/docker/cloud command مخرب تجویز نمی‌کند.

## Fail-fast outcomes

| حالت | رفتار | اقدام |
|---|---|---|
| DB unavailable | production start blocked | شبکه/credential را بدون چاپ secret بررسی کنید |
| migration pending | production start blocked | release migration explicit |
| critical table missing | production start blocked | migration history/restore بررسی شود |
| auto-migrate=true | startup rejected | env را false کنید؛ migration explicit |
| readiness 503 | no traffic | log/correlation و migration check |

## Application rollback

اگر schema additive و backward-compatible است:

1. traffic از instance جدید خارج شود؛
2. artifact قبلی deploy شود؛
3. migration خودکار اجرا نشود؛
4. readiness و smoke بررسی شود؛
5. داده‌های additive حفظ شوند؛ drop/delete فوری ممنوع.

## Database rollback

downgrade خودکار پیش‌فرض نیست. برای failure پس از migration:

- ابتدا application rollback و feature disable؛
- داده و audit حفظ؛
- تصمیم restore/downgrade فقط با DBA، rehearsal و بررسی data loss؛
- FK duplicate cleanup downgrade عمداً no-op است؛
- هر repair SQL باید reviewed، idempotent و ثبت‌شده باشد.

## Verification and evidence

commit/digest، زمان‌ها، exit codeهای current/check، readiness responses بدون secret، migration revision before/after، approver و incident id ثبت شوند. URL کامل دیتابیس و environment dump ذخیره نشود.

## Emergency stop

در data corruption، secret exposure یا unexpected schema mutation: traffic قطع، writerها متوقف، evidence حفظ و DBA/security فراخوانده شود. force push، migration مجدد کور یا حذف constraint بدون inventory ممنوع است.

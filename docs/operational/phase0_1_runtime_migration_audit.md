# Phase 0.1 Backend Runtime and Migration Safety Audit

## Scope and outcome

این فاز startup، Alembic، entry point، FK cleanup، health/readiness و deployment commands را تثبیت می‌کند. هیچ `OperationalShipment`، `RouteLeg`، `Milestone` یا قابلیت عملیاتی ایجاد نشده است.

## Root cause analysis

### Migration ناخواسته

در base commit، `backend.__init__.create_app` پس از DB ping، در حالت non-test و `skip_startup=False` توابع `backend.startup.run_migrations`، `verify_critical_tables` و `run_startup_seed` را اجرا می‌کرد. `run_migrations` نیز `command.upgrade(..., "head")` و سپس fallback ساخت `expert_quote` را انجام می‌داد.

`backend/wsgi.py` در import، `app = create_app()` داشت. بنابراین import شدن WSGI توسط Gunicorn، ابزارها یا مسیر Alembic می‌توانست migration و seed اجرا کند. `backend/run.py` نیز با وجود `skip_startup=True` همان سه عملیات را دستی اجرا می‌کرد.

### چرا `alembic current` Upgrade اجرا کرد

`backend/migrations/env.py` برای گرفتن URL، `create_app(skip_startup=True)` را می‌ساخت و Flask-Migrate config نیز از extension داخل app استخراج می‌شد. در مسیرهای legacy مانند `run_upgrade.py` خود `create_app()` ابتدا upgrade خودکار را اجرا می‌کرد؛ پس فرمانی که ظاهراً برای current/config inspection بود، قبل از عملیات اصلی schema را upgrade می‌کرد. همچنین env پیشین پیش از هر command، `ensure_version_table_capacity` را اجرا می‌کرد که read-only نبود.

### خطاهای `EnvironmentContext`

ترکیب nested Alembic invocation، ساخت Flask app داخل `env.py` و استفاده از `current_app.extensions["migrate"]` lifecycle دو EnvironmentContext را درهم می‌کرد. پس از پایان/تعویض context داخلی، proxy یا config قبلی می‌توانست `None` باشد یا کلید `config`/section وجود نداشته باشد؛ منشأ محتمل `NoneType` و `KeyError: config` همین recursion و ownership مبهم config است. reproduction دقیق stack تاریخی **نیازمند تأیید** است، اما مسیر معیوب از کد base قابل اثبات بود.

## Entry point audit

- entry point tracked از ابتدا `backend/wsgi.py` بوده است؛ Git history ایجاد آن را در commit `4ae527a...` نشان می‌دهد.
- `wsgi.py` در root هرگز در هیچ branch/history tracked مشاهده نشد و در ignoreها نیز rule مرتبط وجود ندارد؛ بنابراین مدرکی برای untracked/generated بودن آن نیست.
- Docker backend با context `./backend` و `wsgi:app` به layoutی وابسته بود که import package `backend` را مبهم می‌کرد.
- Root Dockerfile نیز `wsgi:app` می‌خواست، در حالی که root file وجود نداشت.

Entry point canonical اکنون در هر deployment از repository root برابر است با:

```text
gunicorn -w 2 -b 0.0.0.0:5000 backend.wsgi:app
```

## رفتار تثبیت‌شده

- `create_app` فقط application object و routeها را می‌سازد؛ DB ping/migration/seed ندارد.
- `backend.runtime.create_runtime_app` readiness read-only را اجرا می‌کند.
- `AUTO_MIGRATE_ON_STARTUP=true` صریحاً رد می‌شود؛ default و examples برابر false است.
- production با migration معوق، DB unavailable یا critical table ناقص start نمی‌شود.
- development می‌تواند non-ready start شود، اما readiness برابر 503 است.
- Alembic env URL و metadata را بدون ساخت Flask app می‌گیرد.
- `script_location` و `prepend_sys_path` مستقل از current working directory هستند.
- probeهای PostgreSQL از `DB_CONNECT_TIMEOUT_SECONDS` با پیش‌فرض ۵ ثانیه استفاده می‌کنند.
- ظرفیت `alembic_version.version_num` فقط پیش از فرمان explicit upgrade بررسی/اصلاح می‌شود؛ current/check آن را تغییر نمی‌دهند.

## فرمان‌های رسمی

```powershell
python -m backend.migration_cli current
python -m backend.migration_cli check
python -m backend.migration_cli upgrade --confirm
```

`current` و `check` read-only هستند. `check` در صورت pending با exit code 2 خارج می‌شود. `upgrade` بدون `--confirm` اجرا نمی‌شود. خروجی فقط target پاک‌سازی‌شده و بدون password/token چاپ می‌کند.

## FK duplicate cleanup

migration `20260729_deduplicate_foreign_keys` constraintهای PostgreSQL را با signature ستون‌های مبدا، جدول/ستون مقصد و semantics کامل options مانند `ondelete`, `onupdate`, `deferrable` و `initially` گروه‌بندی می‌کند؛ نام صریح `fk_*` را نگه می‌دارد و فقط duplicateهای واقعاً هم‌معنا را حذف می‌کند. SQLite عمداً no-op است زیرا بازسازی امن جدول‌های legacy خارج این migration است. downgrade duplicate بی‌ارزش را بازنمی‌گرداند.

## محدودیت Alembic legacy

upgrade یک SQLite خالی در آزمایش isolated در revision `20240920_add_transport_method_to_shipment_request` به دلیل `ALTER COLUMN ... DROP DEFAULT` متوقف شد. این migration تاریخی PostgreSQL-oriented است. current/check مستقل و read-only موفق بودند. بازنویسی کامل زنجیره legacy برای SQLite خارج از Phase 0.1 است؛ migration rehearsal production-like باید روی PostgreSQL موقت و ایزوله انجام شود.

## PostgreSQL isolated rehearsal

چرخه کامل روی یک cluster موقت PostgreSQL 18 با data directory و port تصادفی در Temp اجرا شد؛ سرویس نصب‌شده restart یا تغییر نکرد. نتایج:

- empty database: `current=<base>` و `check` با exit code 2؛
- explicit `upgrade --confirm`: موفق تا `20260729_deduplicate_foreign_keys`؛
- check پس از upgrade: `pending=no`؛
- ظرفیت `alembic_version.version_num`: مقدار 255؛
- گروه FK تکراری پس از cleanup: صفر؛
- cluster موقت پس از آزمون متوقف شد؛ سرویس اصلی در وضعیت Running باقی ماند.

## Health model

- `/api/health/ping`: liveness، بدون DB؛
- `/api/health`: compatibility health و DB connectivity؛
- `/api/health/ready`: DB + Alembic head + critical tables؛ status 503 در عدم آمادگی.

هیچ exception دیتابیس یا connection string در response برگردانده نمی‌شود.

## Files and controls

تغییرات runtime/migration/deployment همراه با testهای isolated ثبت شده‌اند. هیچ اتصال production، restart سرویس موجود، deploy، seed واقعی یا migration production در این فاز انجام نشده است.

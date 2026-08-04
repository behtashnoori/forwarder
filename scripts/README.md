# Scripts Catalog

## Credential security closure

Scripts that embedded shared login credentials, directly created users, mutated passwords, or probed live hashes were removed on 2026-08-04. `setup-users.sh` and `setup-users.bat` now invoke only the interactive `python manage.py create-admin` path. Names listed later in this historical catalog may refer to retired files and are not current execution guidance. Do not restore removed helpers or add runtime credential defaults.

این پوشه شامل اسکریپت‌های عملیاتی و تستی پروژه است. برای کاهش پراکندگی، اسکریپت‌ها فعلاً با این دسته‌بندی منطقی مدیریت می‌شوند (تا در ریفکتور بعدی فیزیکی هم جدا شوند):

## 1) Diagnostics
- `check-backend-determinism.js`: بررسی اتصال backend و رفتار endpointها
- `check_expert.py` / `check_expert_details.py` / `check_expert_password.py`: بررسی وضعیت داده‌های کارشناس
- `test-health.js` / `test-backend-health-live.py`: health check

## 2) Tests (manual/integration-style)
- `test-api*.js`
- `test-shipment-requests.js`
- `test-expert-*.js`
- `test-request-*.py`
- `test-assignment-*.py`

> نکته: این‌ها جایگزین تست‌های واحد رسمی نیستند و باید به‌مرور به تست‌های استاندارد `backend/tests` و `src/tests` منتقل شوند.

## 3) Seed / Setup
- `setup-env.js`
- `setup-users.sh` / `setup-users.bat`
- `create-admin-in-db.js` / `create-admin-in-db.sql`
- `create_expert*.py` و `create-expert-user.js`

## 4) Legacy / OS-specific
- `*.ps1` بیشتر برای ویندوز
- اسکریپت‌هایی که خروجی summary markdown تولید می‌کنند و در CI استفاده نمی‌شوند

---

## قواعد استفاده
1. هر اسکریپت جدید باید نام واضح و دامنه مشخص داشته باشد.
2. اگر اسکریپت تستی است، در اولین فرصت به runner رسمی (pytest/vitest) منتقل شود.
3. اسکریپت‌های migration/ساختار باید idempotent باشند یا در توضیحات، non-idempotent بودنشان ذکر شود.
4. برای بررسی سلامت ساختار پروژه، از دستور زیر استفاده کنید:

```bash
npm run check:structure
```

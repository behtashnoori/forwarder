# برنامه آمادگی انتشار، استقرار، Migration و UAT بسته CRM Customer Link/Create

تاریخ: 2026-07-10

## 1. وضعیت این سند

این سند فقط برای برنامه‌ریزی انتشار و UAT است.

در این فاز هیچ deploy، migration production، تغییر backend، تغییر frontend، تغییر مدل، ساخت migration، تغییر تست، نصب package، commit یا push انجام نمی‌شود.

## 2. وضعیت Git و محدوده بسته

وضعیت تاییدشده در زمان تهیه سند:

| مورد | نتیجه |
| --- | --- |
| Branch | `forwarder-14050324-ver-13` |
| Upstream | `origin/forwarder-14050324-ver-13` |
| وضعیت sync | branch با origin هم‌تراز است |
| ahead set | خالی |
| working tree | بدون تغییر قابل مشاهده؛ فقط warning شناخته‌شده `.pytest_cache` ممکن است دیده شود |

آخرین commitهای مرتبط با بسته CRM:

- `9d0b3dd` - مستند سیاست لینک Customer CRM به ShipmentRequest
- `ce71214` - مستند طراحی فنی لینک دستی Customer
- `df0e64d` - پیاده‌سازی backend لینک دستی Customer
- `908f903` - پیاده‌سازی UI لینک دستی Customer
- `12e002f` - مستند hardening audit لینک CRM
- `da5719b` - پیاده‌سازی audit trail لینک CRM
- `6c90ec0` - مستند طراحی ساخت Customer از روی درخواست
- `c35da0c` - endpoint پیش‌نمایش ساخت Customer
- `006574c` - backend ساخت و لینک Customer
- `2bb534f` - UI ساخت Customer از صفحه جزئیات درخواست

## 3. هدف انتشار

هدف این بسته، فعال کردن یک workflow کنترل‌شده برای تیم مجاز CRM/عملیات است:

- مشاهده وضعیت لینک CRM روی صفحه جزئیات درخواست حمل.
- جستجوی Customer موجود و لینک/relink/unlink دستی.
- مشاهده پیش‌نمایش ساخت Customer جدید از روی `ShipmentRequest`.
- بررسی duplicate candidateها قبل از ساخت.
- ساخت Customer جدید با تایید صریح کاربر.
- در صورت انتخاب کاربر، لینک کردن Customer تازه‌ساخته‌شده به همان درخواست.
- ثبت audit ساختاریافته برای تغییرات لینک CRM.

این بسته نباید چرخه عملیاتی حمل را تغییر دهد. لینک CRM فقط رابطه مرجع بین `ShipmentRequest.customer_id` و `Customer` است و نباید status، assignment، quote، tracking، SLA یا داده خام درخواست را بازنویسی کند.

## 4. اجزای فنی در محدوده انتشار

### 4.1 Backend API

مسیرهای اصلی بسته:

| مسیر | رفتار |
| --- | --- |
| `GET /api/crm/customer-link/customers` | جستجوی Customerهای CRM برای لینک دستی |
| `GET /api/crm/shipment-requests/<request_id>/customer-link` | خواندن وضعیت لینک CRM درخواست |
| `PUT /api/crm/shipment-requests/<request_id>/customer-link` | لینک یا relink به Customer موجود |
| `DELETE /api/crm/shipment-requests/<request_id>/customer-link` | حذف لینک CRM بدون حذف Customer یا درخواست |
| `GET /api/crm/shipment-requests/<request_id>/customer-create-preview` | پیش‌نمایش ساخت Customer، بدون mutation |
| `POST /api/crm/shipment-requests/<request_id>/create-customer` | ساخت Customer و optionally لینک به درخواست |

### 4.2 Backend service و audit

اجزای کلیدی:

- `backend/services/crm_customer_create_from_request_service.py`
- `backend/routes/crm.py`
- `CRMCustomerLinkAudit`
- `ExpertConsoleLog` برای trace عملیاتی/timeline

قاعده audit:

- `CRMCustomerLinkAudit` منبع رسمی history لینک CRM است.
- `ExpertConsoleLog` فقط trace قابل مشاهده در timeline است.
- عملیات `link`, `relink`, `unlink`, و `create_and_link` باید قابل ردیابی باشند.
- preview نباید هیچ رکورد Customer، audit یا تغییر روی ShipmentRequest ایجاد کند.

### 4.3 Frontend UI

اجزای UI:

- `src/lib/api.ts`
- `src/pages/RequestDetail.tsx`

رفتار UI:

- نمایش وضعیت فعلی لینک CRM.
- محدود کردن UI به نقش‌های مجاز تعریف‌شده در frontend.
- جستجوی Customer موجود.
- نمایش هشدار relink وقتی درخواست از قبل Customer دارد.
- دریافت preview ساخت Customer.
- نمایش duplicate candidateها و شدت match.
- الزام تایید صریح قبل از create.
- الزام duplicate acknowledgement در صورت وجود duplicate قوی.
- امکان انتخاب اینکه Customer تازه‌ساخته‌شده به درخواست لینک شود یا فقط ساخته شود.

## 5. پیش‌نیازهای release readiness

انتشار فقط وقتی مجاز است که همه موارد زیر در محیط release candidate تایید شوند:

| Gate | وضعیت مورد انتظار |
| --- | --- |
| Git | branch production/release از `origin/forwarder-14050324-ver-13` یا commit تاییدشده ساخته شود |
| Working tree | clean باشد |
| Secrets | هیچ secret جدیدی لازم نیست و هیچ secret در log یا artifact چاپ نشود |
| Backend dependencies | Python runtime سالم باشد؛ مشکل `No module named 'encodings'` در محیط release وجود نداشته باشد |
| Frontend dependencies | از lockfile موجود استفاده شود؛ package جدید نصب نشود مگر در release process رسمی |
| Database access | فقط DBA/operator مجاز migration را اجرا کند |
| Backup | backup قابل بازیابی قبل از migration/deploy تهیه شود |
| Role access | نقش‌های مجاز برای CRM با سیاست محصول هماهنگ باشند |
| Monitoring | امکان مشاهده خطاهای 4xx/5xx مسیرهای `/api/crm/...` وجود داشته باشد |

## 6. برنامه Migration

### 6.1 اصل ایمنی

در این task هیچ migration اجرا نمی‌شود. این بخش فقط برنامه عملیاتی برای تیم deploy/DBA است.

### 6.2 بررسی قبل از migration

قبل از هر deploy روی staging یا production:

1. وضعیت migration فعلی DB خوانده شود.
2. head فعلی migration repository با head مورد انتظار release مقایسه شود.
3. وجود جدول‌ها و ستون‌های مورد نیاز CRM بررسی شود:
   - `customers`
   - `shipment_requests.customer_id`
   - `shipment_requests.gamification_customer_id`
   - جدول audit لینک CRM، یعنی `CRMCustomerLinkAudit` مطابق نام واقعی مدل/جدول در DB
4. اگر DB قبلا با migrationهای archive یا مسیرهای قدیمی stamp شده باشد، deploy متوقف و DBA review انجام شود.

### 6.3 اجرای migration در staging

ترتیب پیشنهادی:

1. backup staging تهیه شود.
2. app متوقف یا در حالت maintenance کوتاه قرار گیرد.
3. migration status خوانده و ثبت شود.
4. migration upgrade تا head release اجرا شود.
5. schema post-check انجام شود.
6. backend staging restart شود.
7. smoke API اجرا شود.
8. frontend staging build/deploy شود.

### 6.4 اجرای migration در production

Production فقط بعد از PASS کامل staging و امضای UAT مجاز است.

ترتیب پیشنهادی:

1. پنجره deploy و مالک rollback تعیین شود.
2. backup production و روش restore تایید شود.
3. migration current ثبت شود.
4. migration upgrade اجرا شود.
5. schema post-check ثبت شود.
6. backend deploy/restart انجام شود.
7. frontend artifact تاییدشده deploy شود.
8. smoke محدود production اجرا شود.

### 6.5 No-Goهای migration

در هرکدام از حالت‌های زیر migration/deploy متوقف شود:

- DB backup قابل بازیابی نیست.
- migration current با انتظار release سازگار نیست.
- جدول audit لینک CRM وجود ندارد یا schema آن با contract سازگار نیست.
- `shipment_requests.customer_id` یا مدل `Customer` با contract فعلی ناسازگار است.
- environment Python خراب است یا backend بالا نمی‌آید.
- smoke endpointهای CRM خطای 500 می‌دهد.

## 7. برنامه Deploy

### 7.1 ترتیب deploy پیشنهادی

1. تایید source commit و branch.
2. build frontend از source تاییدشده.
3. آماده‌سازی backend artifact/container از source تاییدشده.
4. migration staging.
5. deploy backend staging.
6. deploy frontend staging.
7. smoke staging.
8. UAT staging.
9. تایید business owner.
10. deploy production طبق پنجره رسمی.
11. smoke production.
12. مانیتورینگ خطا و audit.

### 7.2 Smoke testهای backend

با کاربر مجاز CRM:

- `GET /api/crm/customer-link/customers?search=<known>` باید 200 بدهد.
- `GET /api/crm/shipment-requests/<id>/customer-link` باید وضعیت لینک را بدهد.
- `GET /api/crm/shipment-requests/<id>/customer-create-preview` باید preview بدهد و DB را تغییر ندهد.
- `POST /api/crm/shipment-requests/<id>/create-customer` با payload ناقص باید 400 بدهد و هیچ write انجام ندهد.
- `POST /api/crm/shipment-requests/<id>/create-customer` با duplicate قوی و بدون acknowledgement باید reject شود.

با کاربر غیرمجاز:

- مسیرهای CRM link/create باید 401 یا 403 مناسب بدهند.

### 7.3 Smoke testهای frontend

در صفحه جزئیات درخواست:

- کارت CRM برای نقش مجاز دیده شود.
- کاربر غیرمجاز امکان عملیات link/create نداشته باشد.
- جستجوی Customer موجود کار کند.
- preview ساخت Customer نمایش داده شود.
- فرم create با نام/نام خانوادگی خالی submit نشود.
- duplicate قوی بدون acknowledgement submit نشود.
- success toast بعد از create/link درست نمایش داده شود.

## 8. برنامه UAT

### 8.1 نقش‌های UAT

حداقل نقش‌های لازم:

- `crm_manager`
- `business_expert`
- `admin` یا نقش مدیریتی تاییدشده محصول
- یک کاربر غیرمجاز برای تست denial

اگر `supervisor` در محصول مجاز تلقی شده است، باید جداگانه در UAT بررسی شود؛ چون سیاست اولیه CRM-3 درباره این نقش نیازمند احتیاط محصولی بود.

### 8.2 داده‌های UAT

داده‌های staging باید شامل این حالت‌ها باشد:

- درخواست بدون `customer_id`.
- درخواست با `customer_id` موجود.
- درخواست با `gamification_customer_id` برای اطمینان از جدا بودن portal customer و CRM customer.
- Customer موجود با شماره تماس مشابه.
- Customer موجود با نام مشابه اما شماره تماس متفاوت.
- درخواست با نام/نام خانوادگی ناقص.

### 8.3 سناریوهای UAT

| سناریو | انتظار |
| --- | --- |
| خواندن وضعیت لینک درخواست بدون Customer | UI وضعیت بدون لینک نشان دهد |
| لینک به Customer موجود | `ShipmentRequest.customer_id` تنظیم شود و audit ثبت شود |
| relink به Customer دیگر | old/new customer در audit قابل ردیابی باشد |
| unlink | فقط لینک حذف شود؛ Customer و ShipmentRequest حذف نشوند |
| preview create | هیچ write انجام نشود |
| create بدون link | Customer ساخته شود، اما `ShipmentRequest.customer_id` تغییر نکند و audit لینک ثبت نشود |
| create and link | Customer ساخته شود، درخواست لینک شود، audit `create_and_link` ثبت شود |
| duplicate قوی بدون تایید | عملیات reject شود و write انجام نشود |
| duplicate قوی با تایید | عملیات فقط بعد از تایید صریح کاربر انجام شود |
| payload ناقص | reject شود و write انجام نشود |
| کاربر غیرمجاز | عملیات قابل انجام نباشد |
| وضعیت عملیاتی درخواست | status، assignment، quote و tracking بدون تغییر بمانند |

### 8.4 معیار PASS برای UAT

UAT فقط وقتی PASS است که:

- همه سناریوهای بالا با evidence ثبت شوند.
- هیچ خطای 500 در مسیرهای CRM رخ ندهد.
- audit برای link/relink/unlink/create_and_link قابل خواندن و قابل توضیح باشد.
- preview بدون mutation باقی بماند.
- هیچ تغییر ناخواسته‌ای روی lifecycle عملیاتی حمل دیده نشود.
- کاربران غیرمجاز نتوانند mutation انجام دهند.

## 9. Rollback و توقف اضطراری

### 9.1 Rollback نرم

اگر مشکل فقط frontend باشد:

- frontend artifact قبلی restore شود.
- backend و DB دست‌نخورده باقی بمانند.
- مسیرهای backend می‌توانند تا deploy بعدی بدون exposure UI باقی بمانند.

اگر مشکل فقط workflow باشد:

- دسترسی نقش‌های CRM موقتا از UI/route policy محدود شود، طبق سازوکار موجود سیستم.
- عملیات جدید CRM متوقف شود.
- auditهای موجود حفظ شوند.

### 9.2 Rollback سخت

Rollback DB فقط با تصمیم DBA مجاز است.

قبل از هر rollback سخت:

- تعداد Customerهای ساخته‌شده از مسیر جدید استخراج شود.
- auditهای `create_and_link` استخراج و نگهداری شود.
- اثر روی `ShipmentRequest.customer_id` بررسی شود.
- مشخص شود rollback باید داده ساخته‌شده را حذف کند یا فقط deploy را عقب ببرد.

### 9.3 No-Goهای production

Production rollout باید متوقف شود اگر:

- UAT staging PASS نشده باشد.
- backup production تایید نشده باشد.
- migration current نامشخص باشد.
- smoke staging خطای 500 داشته باشد.
- audit ثبت نشود.
- preview mutation ایجاد کند.
- عملیات CRM باعث تغییر status یا assignment درخواست شود.

## 10. مانیتورینگ بعد از انتشار

در 24 ساعت اول بعد از production deploy، موارد زیر پایش شود:

- نرخ خطای مسیرهای `/api/crm/customer-link/...`
- نرخ خطای مسیرهای `/api/crm/shipment-requests/.../customer-create-preview`
- نرخ خطای مسیرهای `/api/crm/shipment-requests/.../create-customer`
- تعداد auditهای `link`, `relink`, `unlink`, `create_and_link`
- تعداد Customerهای ساخته‌شده با `source = shipment_request`
- موارد duplicate قوی که override شده‌اند
- شکایت کاربران درباره لینک اشتباه یا Customer تکراری

## 11. تصمیم readiness

وضعیت این سند: `RELEASE_PLAN_READY`

این به معنی مجوز deploy نیست. معنی آن این است که بسته CRM برای ورود به مرحله release candidate، staging migration، smoke و UAT دارای برنامه اجرایی روشن است.

مجوز production فقط بعد از این موارد صادر شود:

- تایید source commit.
- اجرای موفق migration در staging.
- PASS شدن smoke backend و frontend در staging.
- PASS شدن UAT با evidence.
- تایید rollback owner و backup.
- تایید business owner برای فعال‌سازی workflow ساخت و لینک Customer.

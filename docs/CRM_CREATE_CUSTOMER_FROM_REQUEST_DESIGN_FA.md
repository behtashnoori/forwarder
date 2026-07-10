# CRM-4: طراحی ساخت CRM Customer از روی ShipmentRequest

تاریخ: 2026-07-10

## 1. هدف سند

این سند طراحی CRM-4 را برای قابلیت «ساخت مشتری CRM از روی درخواست حمل» تعریف می‌کند.

CRM-4 باید به کاربر مجاز اجازه بدهد، بعد از مشاهده یک `ShipmentRequest` موجود، از داده‌های همان درخواست یک `Customer` جدید در CRM بسازد و سپس همان درخواست را به مشتری تازه‌ساخته‌شده لینک کند.

این سند فقط طراحی و مستندسازی است. در این فاز هیچ کد backend، کد frontend، مدل، migration، تست، route، package یا push انجام نمی‌شود.

## 2. وضعیت فعلی تاییدشده از کد

بر اساس وضعیت فعلی branch:

- `ShipmentRequest.customer_id` همچنان لینک فعال و nullable به `Customer` است.
- نبودن `customer_id` روی درخواست حمل یک وضعیت معتبر است.
- `ShipmentRequest.gamification_customer_id` جدا از `customer_id` است و به `CustomerGamification` مربوط می‌شود.
- مدل `Customer` برای CRM وجود دارد و فیلدهای اصلی آن شامل `first_name`, `last_name`, `company_name`, `email`, `phone`, `mobile`, `customer_type`, `status`, `source`, `notes`, `address`, `city`, `province`, `country` است.
- سرویس موجود `crm_write_service.create_customer` قابلیت ساخت مشتری CRM را دارد.
- سرویس موجود `crm_customer_link_service.link_customer_to_request` قابلیت لینک کردن یک درخواست حمل به مشتری CRM موجود را دارد.
- جدول ساختاریافته `CRMCustomerLinkAudit` برای ثبت `link`, `relink`, `unlink` وجود دارد.
- `ExpertConsoleLog` همچنان trace عملیاتی/timeline را نگه می‌دارد، اما audit رسمی لینک CRM در جدول اختصاصی ثبت می‌شود.

نتیجه طراحی: CRM-4 نباید schema جدیدی برای لینک بسازد. مسیر درست، ترکیب کنترل‌شده «ساخت Customer» و «لینک به ShipmentRequest» با transaction، validation و audit مناسب است.

## 3. دامنه CRM-4

داخل دامنه:

- طراحی workflow ساخت `Customer` از روی `ShipmentRequest`.
- طراحی mapping پیشنهادی داده‌های درخواست به فیلدهای `Customer`.
- طراحی رفتار create-and-link به صورت atomic.
- طراحی سیاست duplicate-check قبل از ساخت مشتری جدید.
- طراحی audit برای عملیات `create_and_link`.
- طراحی مجوز، خطاها، rollback و contract تست‌های آینده.
- طراحی UX آینده در صفحه جزئیات درخواست.

خارج از دامنه:

- ساخت خودکار Customer هنگام ثبت عمومی درخواست حمل.
- اجباری کردن `ShipmentRequest.customer_id`.
- تغییر lifecycle، status، assignment، quote، SLA یا tracking درخواست.
- ادغام `CustomerGamification` با `Customer`.
- ساخت یا لینک کردن `Opportunity` به `ShipmentRequest`.
- تغییر مدل‌ها یا migration جدید.
- تغییر routeهای موجود در این فاز.
- تغییر تست‌ها یا اجرای refactor.

## 4. تصمیم طراحی اصلی

CRM-4 باید یک اقدام دستی و صریح باشد.

قاعده اصلی:

`Customer` فقط وقتی از روی `ShipmentRequest` ساخته می‌شود که کاربر مجاز، بعد از مشاهده داده‌های درخواست و بررسی مشتری‌های مشابه، دکمه یا action مشخص «ساخت مشتری CRM از این درخواست» را اجرا کند.

پیامدها:

- ثبت عمومی درخواست حمل همچنان فقط `ShipmentRequest` می‌سازد.
- ساخت Customer نباید به صورت ضمنی در background انجام شود.
- لینک فعال بعد از عملیات همچنان فقط `ShipmentRequest.customer_id` است.
- اگر ساخت Customer موفق شود ولی لینک شکست بخورد، کل transaction باید rollback شود.
- اگر لینک موفق شود ولی audit شکست بخورد، کل transaction باید rollback شود.
- عملیات موفق نباید هیچ فیلد عملیاتی درخواست را تغییر دهد.

## 5. Workflow پیشنهادی

### 5.1 مشاهده درخواست

کاربر مجاز وارد صفحه جزئیات `ShipmentRequest` می‌شود.

UI باید وضعیت CRM link را نشان دهد:

- بدون مشتری CRM
- لینک‌شده به مشتری CRM
- نیازمند بررسی به دلیل وجود مشتری‌های مشابه

### 5.2 پیشنهاد داده‌های قابل انتقال

سیستم می‌تواند از روی درخواست، پیش‌نویس Customer بسازد، اما این پیش‌نویس هنوز در DB ذخیره نمی‌شود.

فیلدهای پیشنهادی:

| فیلد Customer | منبع پیشنهادی از ShipmentRequest | قاعده |
| --- | --- | --- |
| `first_name` | `customer_first_name` | اگر خالی بود، کاربر باید تکمیل کند. |
| `last_name` | `customer_last_name` | اگر خالی بود، کاربر باید تکمیل کند. |
| `phone` | `contact_phone` | منبع اصلی تماس از درخواست. |
| `mobile` | `contact_phone` یا خالی | فقط اگر محصول تصمیم بگیرد phone/mobile یکی باشند. |
| `company_name` | ورودی دستی | از داده درخواست فعلی منبع قطعی ندارد. |
| `email` | ورودی دستی | اگر در درخواست فعلی وجود ندارد، نباید حدس زده شود. |
| `source` | مقدار ثابت مثل `shipment_request` | برای گزارش‌گیری CRM. |
| `notes` | خلاصه کنترل‌شده از request id/tracking | بدون اطلاعات حساس و بدون کپی کامل درخواست. |
| `country`, `province`, `city` | داده مسیر، در صورت قابل اتکا بودن | فقط به عنوان پیش‌نویس قابل ویرایش. |
| `customer_type` | `prospect` | پیش‌فرض فعلی CRM. |
| `status` | `active` | پیش‌فرض فعلی CRM. |

قاعده مهم:

داده خام درخواست نباید با داده CRM یکی فرض شود. تغییر بعدی Customer نباید فیلدهای خام `ShipmentRequest.customer_first_name`, `customer_last_name` یا `contact_phone` را بازنویسی کند.

### 5.3 بررسی مشتری‌های مشابه

قبل از ساخت Customer جدید، سیستم باید مشتری‌های مشابه را نشان دهد.

معیارهای قوی:

- `phone` یا `mobile` برابر با `contact_phone`
- `email` برابر، اگر کاربر email وارد کرده باشد
- ترکیب `company_name` و شماره تماس

معیارهای ضعیف:

- نام و نام خانوادگی مشابه
- شرکت مشابه بدون شماره تماس
- شهر یا استان مشابه

رفتار پیشنهادی:

- اگر match قوی وجود دارد، UI باید کاربر را به لینک کردن مشتری موجود تشویق کند.
- اگر کاربر با وجود match قوی مشتری جدید می‌سازد، باید دلیل کوتاه وارد کند.
- سیستم نباید صرفا بر اساس match ضعیف، ساخت را مسدود کند.
- گزینه «لینک به مشتری موجود» باید کنار «ساخت مشتری جدید» باقی بماند.

## 6. Contract رفتاری create-and-link

ورودی منطقی:

- `shipment_request_id`
- داده‌های Customer قابل تایید/ویرایش توسط کاربر
- user فعلی
- optional `reason` یا `note`
- optional duplicate override flag، اگر match قوی وجود دارد

پیش‌شرط‌ها:

- درخواست حمل وجود داشته باشد.
- کاربر مجوز ساخت Customer و لینک CRM داشته باشد.
- داده‌های حداقلی Customer معتبر باشد.
- در صورت وجود مشتری مشابه قوی، کاربر تصمیم آگاهانه بگیرد.

رفتار موفق:

1. `ShipmentRequest` خوانده می‌شود.
2. داده‌های Customer validate و normalize می‌شود.
3. مشتری‌های مشابه بررسی می‌شوند.
4. یک `Customer` جدید ساخته می‌شود.
5. `ShipmentRequest.customer_id` برابر `Customer.id` تازه ساخته‌شده می‌شود.
6. یک رکورد `CRMCustomerLinkAudit` با `operation = create_and_link` ثبت می‌شود.
7. یک رکورد `ExpertConsoleLog` برای timeline عملیاتی ثبت می‌شود.
8. همه موارد در یک transaction commit می‌شوند.

خروجی منطقی:

- `operation = create_and_link`
- شناسه درخواست
- خلاصه مشتری تازه ساخته‌شده
- وضعیت لینک جدید
- هشدار duplicate، اگر کاربر override کرده باشد

## 7. رفتار در وضعیت‌های مرزی

### 7.1 درخواست از قبل لینک دارد

اگر `ShipmentRequest.customer_id` از قبل مقدار داشته باشد، CRM-4 نباید بی‌صدا مشتری جدید بسازد و relink کند.

رفتار پیشنهادی:

- پیش‌فرض: خطای conflict یا نیاز به confirmation صریح.
- اگر محصول اجازه بدهد، عملیات باید به عنوان `create_and_link` با `old_customer_id` قبلی و `new_customer_id` جدید ثبت شود، اما UI باید هشدار واضح relink نشان دهد.
- مسیر ساده‌تر و محافظه‌کارانه‌تر برای فاز اول: ساخت Customer از درخواست فقط برای درخواست بدون لینک مجاز باشد.

تصمیم پیشنهادی CRM-4:

فاز اول فقط وقتی مجاز باشد که درخواست هنوز CRM Customer ندارد. relink به مشتری تازه‌ساخته‌شده باید به فاز جداگانه موکول شود.

### 7.2 داده‌های نام کافی نیست

`Customer.first_name` و `Customer.last_name` در مدل فعلی nullable نیستند.

اگر درخواست نام کافی ندارد:

- UI باید کاربر را مجبور به تکمیل نام کند.
- backend آینده باید payload بدون `first_name` یا `last_name` معتبر را رد کند.
- سیستم نباید مقدارهای جعلی مثل `Unknown` بسازد، مگر اینکه محصول صریحا سیاست placeholder تصویب کند.

### 7.3 شماره تماس تکراری

اگر شماره تماس با Customer موجود match قوی دارد:

- ساخت مشتری جدید باید نیازمند تایید و دلیل باشد.
- audit باید reason را نگه دارد.
- این حالت نباید به صورت خودکار merge یا relink انجام دهد.

### 7.4 خطای commit

هر خطای DB هنگام ساخت Customer، لینک، audit یا console log باید rollback کامل ایجاد کند.

بعد از rollback:

- Customer جدید نباید باقی بماند.
- `ShipmentRequest.customer_id` نباید تغییر کند.
- audit ناقص نباید باقی بماند.

## 8. Audit و ردیابی

CRM-4 باید از جدول اختصاصی `CRMCustomerLinkAudit` استفاده کند.

برای عملیات موفق:

- `operation = create_and_link`
- `old_customer_id = null` در فاز اول محافظه‌کارانه
- `new_customer_id = Customer.id`
- `performed_by_user_id`
- `performed_by_role`
- `source = request_detail_ui` یا مقدار مشابه
- `reason`
- `request_status_at_time`
- `assigned_to_at_time`
- `gamification_customer_id_at_time`
- `ip_address`
- `created_at`

`ExpertConsoleLog` نیز می‌تواند برای timeline انسانی ثبت شود:

- `action = crm_customer_link`
- `old_status = shipment_request.status`
- `new_status = shipment_request.status`
- note کنترل‌شده شامل `operation=create_and_link` و id مشتری جدید

قاعده:

audit منبع رسمی history است. `ExpertConsoleLog` trace عملیاتی و قابل مشاهده در timeline است.

## 9. جای پیشنهادی منطق در معماری آینده

پیاده‌سازی آینده باید service-first باشد.

گزینه پیشنهادی:

- اضافه کردن تابع جدید در محدوده سرویس لینک CRM، مثلا `create_customer_from_request_and_link`.
- یا ساخت سرویس کوچک جدید مثل `crm_create_customer_from_request_service`.

مسئولیت route آینده:

- authentication
- authorization
- خواندن payload
- پاس دادن user و remote address
- mapping خطا به response

مسئولیت service آینده:

- validate request
- validate customer payload
- duplicate search
- create Customer
- set `ShipmentRequest.customer_id`
- create structured audit
- create console timeline log
- commit/rollback
- build response payload

نکته:

استفاده مستقیم از `crm_write_service.create_customer` در وضعیت فعلی برای composition atomic کافی نیست، چون آن تابع خودش commit می‌کند. در پیاده‌سازی آینده یا باید variant بدون commit طراحی شود یا منطق create-and-link در یک transaction واحد نوشته شود.

## 10. API پیشنهادی برای فاز آینده

این سند route دقیق را تصویب نمی‌کند، اما مسیر باید کوچک و واضح باشد.

گزینه محافظه‌کارانه:

`POST /api/crm/shipment-requests/<request_id>/customer-link/create-customer`

بدنه پیشنهادی:

```json
{
  "customer": {
    "first_name": "...",
    "last_name": "...",
    "company_name": "...",
    "email": "...",
    "phone": "...",
    "mobile": "...",
    "source": "shipment_request",
    "notes": "..."
  },
  "reason": "...",
  "duplicate_override": false
}
```

پاسخ موفق پیشنهادی:

```json
{
  "operation": "create_and_link",
  "shipment_request": {
    "id": 123,
    "customer_id": 456,
    "status": "new",
    "assigned_to": null,
    "gamification_customer_id": null
  },
  "customer": {
    "id": 456,
    "name": "...",
    "company_name": "...",
    "email": "...",
    "phone": "...",
    "mobile": "...",
    "customer_type": "prospect",
    "status": "active"
  }
}
```

کدهای خطای پیشنهادی:

- `400`: payload نامعتبر یا داده حداقلی Customer ناقص است.
- `401`: کاربر احراز هویت نشده است.
- `403`: کاربر مجوز ندارد.
- `404`: درخواست حمل پیدا نشد.
- `409`: درخواست از قبل لینک دارد، یا match قوی بدون override وجود دارد.
- `500`: خطای کنترل‌شده server/DB همراه با rollback.

## 11. Authorization پیشنهادی

مجوز باید با CRM-3 سازگار باشد.

نقش‌های کاندید:

- `business_expert`: مجاز، اگر به صفحه و داده درخواست دسترسی دارد.
- `crm_manager`: مجاز، اگر در سیستم route/role فعلی به CRM دسترسی دارد.
- `admin`: مجاز، اگر سیاست محصول اجازه عملیات CRM از admin را بدهد.

نقش‌هایی که پیش‌فرض نباید مجاز باشند:

- `expert` عادی، مگر تصمیم محصول جداگانه گرفته شود.
- کاربر عمومی/مشتری.

قاعده:

کاربری که Customer می‌سازد و لینک می‌کند باید مسئولیت تجاری تصمیم را داشته باشد، چون این عملیات هم داده CRM می‌سازد و هم رابطه رسمی با درخواست حمل ایجاد می‌کند.

## 12. UX پیشنهادی آینده

در صفحه جزئیات درخواست، بخش CRM باید این حالت‌ها را پوشش دهد:

1. درخواست بدون Customer:
   - نمایش وضعیت «بدون مشتری CRM»
   - جستجو و لینک به مشتری موجود
   - ساخت مشتری جدید از روی این درخواست

2. قبل از ساخت:
   - فرم پیش‌پرشده از داده‌های درخواست
   - امکان ویرایش فیلدها
   - نمایش مشتری‌های مشابه
   - امکان cancel

3. هنگام match قوی:
   - نمایش هشدار واضح
   - پیشنهاد لینک به مشتری موجود
   - نیاز به دلیل برای ادامه ساخت مشتری جدید

4. بعد از موفقیت:
   - نمایش Customer لینک‌شده
   - بدون تغییر status عملیاتی درخواست
   - refresh از backend، نه اتکا به state موقت frontend

5. کاربر غیرمجاز:
   - action ساخت یا لینک را نبیند، یا backend پاسخ `403` بدهد.

## 13. برنامه تست آینده

تست‌های backend/service پیشنهادی:

1. درخواست بدون لینک می‌تواند با Customer جدید لینک شود.
2. عملیات موفق فقط Customer جدید، `ShipmentRequest.customer_id`, audit و console log را تغییر می‌دهد.
3. عملیات موفق `status`, `assigned_to`, `priority`, `sla_due_at`, quote و tracking را تغییر نمی‌دهد.
4. عملیات موفق `gamification_customer_id` و `CustomerGamification` را تغییر نمی‌دهد.
5. payload بدون `first_name` یا `last_name` معتبر خطای `400` می‌دهد.
6. درخواست ناموجود خطای `404` می‌دهد و Customer نمی‌سازد.
7. کاربر غیرمجاز خطای `403` می‌دهد و Customer نمی‌سازد.
8. درخواست از قبل لینک‌شده در فاز اول خطای `409` می‌دهد.
9. match قوی بدون override خطای `409` یا response نیازمند تایید می‌دهد.
10. match قوی با override و reason معتبر عملیات را انجام می‌دهد.
11. خطای commit باعث rollback کامل Customer، link و audit می‌شود.
12. audit با `operation = create_and_link` و old/new صحیح ثبت می‌شود.
13. `ExpertConsoleLog` فقط trace timeline ایجاد می‌کند و status را تغییر نمی‌دهد.

تست‌های frontend/manual پیشنهادی:

1. فرم از داده‌های درخواست پیش‌پر می‌شود.
2. فیلدهای لازم قابل تکمیل و validate هستند.
3. مشتری‌های مشابه قبل از ساخت نمایش داده می‌شوند.
4. لینک به مشتری موجود از مسیر ساخت جدید جدا باقی می‌ماند.
5. بعد از ساخت موفق، صفحه Customer لینک‌شده را از backend نشان می‌دهد.
6. refresh صفحه وضعیت لینک را حفظ می‌کند.
7. کاربر غیرمجاز action را نمی‌بیند یا خطای قابل فهم دریافت می‌کند.

## 14. ریسک‌ها و کنترل‌ها

ریسک: ایجاد مشتری تکراری.

کنترل: duplicate-check، نمایش match قوی، نیاز به reason برای override.

ریسک: مخلوط شدن Customer CRM با CustomerGamification.

کنترل: عدم تغییر `gamification_customer_id` و ثبت snapshot آن در audit.

ریسک: ساخت Customer بدون لینک به دلیل commit زودهنگام.

کنترل: transaction واحد و پرهیز از استفاده از helperهایی که commit مستقل دارند.

ریسک: تغییر ناخواسته lifecycle درخواست.

کنترل: contract test روی فیلدهای عملیاتی و snapshot قبل/بعد.

ریسک: افشای داده حساس در notes یا audit.

کنترل: محدود کردن note/reason، عدم ذخیره token/secret، و استفاده از summary کنترل‌شده.

## 15. معیار پذیرش برای ورود به پیاده‌سازی

CRM-4 وقتی برای پیاده‌سازی آماده است که موارد زیر پذیرفته شده باشند:

- تصمیم محصول تایید کند ساخت Customer از درخواست فقط دستی و صریح است.
- تصمیم محصول تایید کند فاز اول فقط برای درخواست بدون لینک مجاز است.
- mapping فیلدهای Customer از درخواست تایید شود.
- سیاست duplicate-check و override تایید شود.
- route و authorization نهایی شوند.
- contract testهای create-and-link، duplicate، rollback و audit آماده تعریف باشند.
- UI آینده با مسیرهای «لینک به موجود» و «ساخت جدید» تداخل نداشته باشد.

## 16. جمع‌بندی تصمیم CRM-4

تصمیم CRM-4 این است:

- قابلیت ساخت `Customer` از روی `ShipmentRequest` مجاز است، اما فقط با اقدام دستی کاربر مجاز.
- عملیات باید در یک transaction، به صورت create-and-link انجام شود.
- لینک فعال همچنان `ShipmentRequest.customer_id` است.
- `CRMCustomerLinkAudit` منبع رسمی history برای `create_and_link` است.
- `ExpertConsoleLog` فقط trace/timeline عملیاتی باقی می‌ماند.
- نبودن Customer CRM برای درخواست همچنان معتبر است.
- ساخت خودکار Customer هنگام ثبت عمومی درخواست ممنوع است.
- `CustomerGamification`, `Opportunity`, status و lifecycle عملیاتی درخواست در CRM-4 تغییر نمی‌کنند.

این طراحی CRM-4 را به یک گام کوچک، قابل تست، قابل rollback و سازگار با CRM-3 تبدیل می‌کند، بدون اینکه CRM مالک چرخه عملیاتی حمل شود.

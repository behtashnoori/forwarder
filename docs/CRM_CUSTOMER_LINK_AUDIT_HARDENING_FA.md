# CRM-3A.3: بازبینی سخت‌سازی Audit برای لینک مشتری CRM

تاریخ: 2026-07-10

## 1. هدف سند

این سند یک بازبینی طراحی برای audit لینک دستی `Customer` در CRM به `ShipmentRequest` است.

این فاز فقط مستندسازی و تصمیم طراحی است. در این فاز هیچ کد backend، کد frontend، مدل، migration، تست، پکیج، push، refactor یا تغییر runtime انجام نمی‌شود.

پرسش اصلی این فاز:

آیا ثبت فعلی تغییرات لینک CRM در `ExpertConsoleLog` برای ادامه کافی است، یا باید برای فاز آینده یک مکانیزم audit اختصاصی طراحی شود؟

## 2. وضعیت فعلی تاییدشده

در CRM-3A.2، عملیات لینک مشتری CRM این رفتارها را دارد:

- از فیلد موجود `ShipmentRequest.customer_id` استفاده می‌کند.
- عملیات `link`, `relink`, `unlink` و `noop` را از هم تفکیک می‌کند.
- لینک به همان مشتری فعلی و unlink درخواست بدون لینک را idempotent نگه می‌دارد.
- فقط مقدار `ShipmentRequest.customer_id` را تغییر می‌دهد.
- وضعیت، تخصیص، اولویت، SLA، quote، timeline عملیاتی و `CustomerGamification` را تغییر نمی‌دهد.
- برای عملیات واقعی `link`, `relink`, `unlink` یک رکورد در `ExpertConsoleLog` ثبت می‌کند.

ثبت فعلی audit در `ExpertConsoleLog` به شکل زیر است:

- `shipment_request_id`: شناسه درخواست حمل
- `expert_user_id`: کاربر انجام‌دهنده
- `action`: مقدار ثابت `crm_customer_link`
- `old_status` و `new_status`: هر دو برابر وضعیت فعلی درخواست، برای حفظ سازگاری با ساختار log موجود
- `note`: متن آزاد شامل `operation`, `old_customer_id`, `new_customer_id` و note اختیاری کاربر
- `ip_address`
- `created_at`

## 3. ارزیابی کفایت وضعیت فعلی

تصمیم این بازبینی:

`ExpertConsoleLog` برای CRM-3A.2 به عنوان trace حداقلی قابل قبول است، اما برای audit رسمی و بلندمدت لینک مشتری CRM کافی نیست.

دلیل قابل قبول بودن در وضعیت فعلی:

- قابلیت کوچک، دستی و محدود است.
- مسیر write فعلی contract test دارد.
- رکورد log فعلی تغییر واقعی را قابل مشاهده می‌کند.
- با timeline و الگوی فعلی expert console سازگار است.
- بدون migration و بدون تغییر مدل، حداقل ردپا را ایجاد می‌کند.

دلیل ناکافی بودن برای آینده:

- داده‌های مهم audit در `note` متنی و غیرساخت‌یافته ذخیره می‌شوند.
- `old_customer_id` و `new_customer_id` ستون مستقل و قابل query ندارند.
- نوع عملیات به صورت ستون رسمی ذخیره نمی‌شود.
- نقش انجام‌دهنده در لحظه عملیات ذخیره نمی‌شود.
- رابطه اختصاصی با `Customer` قبلی و جدید وجود ندارد.
- گزارش‌گیری، فیلتر، export و بررسی تاریخی لینک‌ها سخت و شکننده می‌شود.
- `ExpertConsoleLog` ذاتا log فعالیت expert console است، نه ledger اختصاصی تغییر رابطه CRM.
- اگر در آینده logهای console پاکسازی یا archive شوند، audit لینک CRM ممکن است همراه آنها از بین برود.
- تغییر قالب متن `note` می‌تواند گزارش‌گیری یا parserهای آینده را بشکند.

## 4. تصمیم طراحی

برای ادامه محدود CRM-3A.2، ثبت فعلی در `ExpertConsoleLog` کافی است.

برای هر یک از موارد زیر، قبل از توسعه بیشتر باید audit اختصاصی طراحی و پیاده‌سازی شود:

- نمایش history رسمی لینک در CRM
- گزارش مدیریتی یا export از تغییرات لینک
- استفاده از لینک CRM در تصمیم‌های تجاری حساس
- ساخت مشتری از روی درخواست و لینک همزمان
- ابزار تطبیق پیشنهادی مشتری
- نیاز به بررسی اختلاف، کنترل داخلی، یا پیگیری مسئولیت تصمیم
- حذف، ادغام یا پاکسازی آینده logهای expert console

بنابراین تصمیم نهایی:

`ExpertConsoleLog` نقش trace عملیاتی موقت دارد. مکانیزم آینده باید یک audit table اختصاصی و append-only برای تغییرات لینک CRM داشته باشد.

## 5. طراحی پیشنهادی audit اختصاصی آینده

نام پیشنهادی جدول:

`crm_customer_link_audit`

ماهیت جدول:

- append-only
- بدون update برای رکوردهای ثبت‌شده
- بدون delete در مسیرهای عادی محصول
- مستقل از lifecycle عملیاتی حمل
- قابل گزارش و export

ستون‌های پیشنهادی:

| ستون | نوع منطقی | توضیح |
| --- | --- | --- |
| `id` | integer/bigint | شناسه audit |
| `shipment_request_id` | FK به `ShipmentRequest` | درخواست حمل هدف |
| `old_customer_id` | nullable FK به `Customer` | لینک قبلی، اگر وجود داشته باشد |
| `new_customer_id` | nullable FK به `Customer` | لینک جدید، اگر وجود داشته باشد |
| `operation` | string/enum | یکی از `link`, `relink`, `unlink`, `noop`, `create_and_link` |
| `performed_by_user_id` | nullable FK به `ExpertUser` | کاربر انجام‌دهنده |
| `performed_by_role` | string | نقش کاربر در زمان عملیات |
| `source` | string | مثلا `request_detail_ui`, `crm_api`, `admin_tool`, `system_migration` |
| `reason` | nullable text | دلیل یا یادداشت کاربر |
| `request_status_at_time` | string | وضعیت درخواست در لحظه عملیات، فقط برای زمینه |
| `assigned_to_at_time` | nullable integer | کارشناس تخصیص‌یافته در لحظه عملیات، فقط برای زمینه |
| `gamification_customer_id_at_time` | nullable integer | برای اثبات جدا بودن مشتری پورتال از مشتری CRM |
| `ip_address` | nullable string | IP درخواست |
| `created_at` | datetime | زمان ثبت audit |

نکته مهم:

این جدول نباید مالک وضعیت لینک فعلی باشد. وضعیت فعلی همچنان از `ShipmentRequest.customer_id` خوانده می‌شود. جدول audit فقط تاریخچه تصمیم‌ها را نگه می‌دارد.

## 6. سیاست ثبت عملیات‌ها

### 6.1 Link

وقتی درخواست قبلا بدون لینک بوده و به یک `Customer` وصل می‌شود:

- `operation = link`
- `old_customer_id = null`
- `new_customer_id = Customer.id`

### 6.2 Relink

وقتی درخواست از یک `Customer` به `Customer` دیگری منتقل می‌شود:

- `operation = relink`
- `old_customer_id = previous Customer.id`
- `new_customer_id = selected Customer.id`
- UI باید هشدار واضح بدهد.

### 6.3 Unlink

وقتی لینک فعلی حذف می‌شود:

- `operation = unlink`
- `old_customer_id = previous Customer.id`
- `new_customer_id = null`

### 6.4 Noop

برای عملیات idempotent، دو گزینه وجود دارد:

گزینه پیشنهادی برای محصول فعلی:

- `noop` در audit اختصاصی ثبت نشود، مگر اینکه نیاز محصولی برای ردیابی تلاش‌های بی‌اثر وجود داشته باشد.

گزینه سخت‌گیرانه‌تر آینده:

- `noop` با `operation = noop` و reason ثبت شود، اما در گزارش‌های عادی از تغییرات واقعی جدا نمایش داده شود.

تصمیم پیشنهادی:

برای کاهش noise، فقط تغییرات واقعی (`link`, `relink`, `unlink`, و در آینده `create_and_link`) در audit اختصاصی ثبت شوند. اگر compliance نیاز داشت، ثبت `noop` به صورت feature جداگانه فعال شود.

## 7. رابطه با `ExpertConsoleLog`

بعد از طراحی audit اختصاصی، دو مسیر قابل قبول وجود دارد:

1. نگه داشتن `ExpertConsoleLog` برای timeline انسانی و ثبت audit اختصاصی برای history رسمی.
2. حذف وابستگی CRM link به `ExpertConsoleLog` و نمایش history لینک از جدول اختصاصی.

پیشنهاد این سند:

در فاز اول hardening، هر دو ثبت انجام شود:

- `ExpertConsoleLog` برای سازگاری با timeline و مشاهده سریع در صفحه درخواست
- `crm_customer_link_audit` برای گزارش، export، بررسی تاریخی و trace رسمی

بعد از اینکه UI و گزارش‌ها به audit اختصاصی متکی شدند، می‌توان تصمیم گرفت آیا `ExpertConsoleLog` همچنان لازم است یا فقط برای timeline خلاصه بماند.

## 8. اصول امنیت و داده

Audit اختصاصی باید این اصول را رعایت کند:

- هیچ secret یا token در audit ذخیره نشود.
- note/reason کاربر طول محدود داشته باشد.
- IP به صورت اختیاری ذخیره شود و در UI عمومی نمایش داده نشود.
- تغییر نام یا اطلاعات `Customer` نباید history old/new id را از بین ببرد.
- اگر نمایش نام تاریخی لازم شد، باید snapshot کوچک و کنترل‌شده طراحی شود؛ در غیر این صورت idها منبع حقیقت باقی بمانند.
- audit نباید به مسیر عمومی ثبت درخواست حمل اضافه شود.
- audit نباید باعث ساخت خودکار Customer شود.
- audit نباید `CustomerGamification` را با `Customer` مخلوط کند.

## 9. Contract تست پیشنهادی آینده

در فاز پیاده‌سازی audit اختصاصی، تست‌ها باید این موارد را پوشش دهند:

1. `link` رکورد audit با old null و new customer ایجاد می‌کند.
2. `relink` رکورد audit با old و new صحیح ایجاد می‌کند.
3. `unlink` رکورد audit با old صحیح و new null ایجاد می‌کند.
4. `noop` طبق تصمیم محصولی یا audit ایجاد نمی‌کند یا با operation جدا ثبت می‌شود.
5. خطای customer ناموجود audit ایجاد نمی‌کند.
6. خطای request ناموجود audit ایجاد نمی‌کند.
7. خطای payload نامعتبر audit ایجاد نمی‌کند.
8. rollback روی commit، هم تغییر `customer_id` و هم audit را برمی‌گرداند.
9. audit شامل `performed_by_user_id`, `performed_by_role`, `created_at`, `source` و `ip_address` است.
10. audit تغییر وضعیت، تخصیص، quote، SLA یا `CustomerGamification` ایجاد نمی‌کند.
11. حذف یا تغییر اطلاعات Customer، رکورد audit را حذف نمی‌کند.
12. گزارش history بر اساس audit اختصاصی، ترتیب زمانی درست دارد.

## 10. Migration و rollback آینده

پیاده‌سازی آینده نیازمند migration جداگانه است.

قواعد migration:

- migration فقط جدول audit و indexهای لازم را اضافه کند.
- هیچ backfill اجباری روی `ShipmentRequest.customer_id` انجام نشود.
- هیچ تغییر اجباری روی nullable بودن `ShipmentRequest.customer_id` انجام نشود.
- هیچ تغییر روی `CustomerGamification` انجام نشود.

Indexهای پیشنهادی:

- `shipment_request_id, created_at`
- `old_customer_id`
- `new_customer_id`
- `performed_by_user_id`
- `operation`

Rollback فنی:

- حذف جدول audit باید مستقل از وضعیت لینک فعلی باشد.
- rollback نباید `ShipmentRequest.customer_id` را تغییر دهد.

## 11. معیار پذیرش برای فاز hardening

قبل از اینکه audit اختصاصی به عنوان آماده تولید پذیرفته شود، این معیارها باید اثبات شوند:

- جدول append-only برای عملیات واقعی لینک وجود دارد.
- contract test برای link, relink, unlink و خطاها وجود دارد.
- rollback کامل تغییر لینک و audit تست شده است.
- `ExpertConsoleLog` دیگر تنها منبع قابل استناد audit نیست.
- هیچ migration یا تغییر مدل، حالت معتبر درخواست بدون `customer_id` را حذف نمی‌کند.
- هیچ منطق frontend یا backend باعث تغییر lifecycle حمل از مسیر CRM link نمی‌شود.
- سند API یا گزارش history مشخص می‌کند منبع رسمی audit کدام جدول است.

## 12. تصمیم نهایی CRM-3A.3

وضعیت فعلی:

`ExpertConsoleLog` برای trace حداقلی CRM-3A.2 کافی است و نیازی به تغییر فوری کد ندارد.

تصمیم آینده:

برای hardening واقعی، گزارش‌گیری، history رسمی، export یا کنترل داخلی، باید جدول audit اختصاصی `crm_customer_link_audit` طراحی و در فاز جداگانه پیاده‌سازی شود.

مرز مهم:

این تصمیم فقط طراحی است. هیچ کد، مدل، migration، تست، frontend، backend یا package در CRM-3A.3 تغییر نمی‌کند.

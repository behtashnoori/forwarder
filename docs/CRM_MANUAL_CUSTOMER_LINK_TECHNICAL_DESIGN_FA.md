# CRM-3A: طراحی فنی و برنامه تست لینک دستی ShipmentRequest به Customer

تاریخ: 2026-07-09

## 1. هدف سند

این سند طراحی فنی و برنامه تست CRM-3A را برای لینک دستی بین `ShipmentRequest` و `Customer` در CRM تعریف می‌کند.

این فاز فقط طراحی و مستندسازی است. در این فاز هیچ کد backend، کد frontend، تغییر مدل، migration، تغییر مسیر API، نصب پکیج، اجرای migration، refactor یا push انجام نمی‌شود.

هدف CRM-3A این است که مسیر پیاده‌سازی آینده برای لینک کردن دستی یک درخواست حمل به یک مشتری CRM روشن، کوچک، قابل تست و قابل rollback باشد؛ بدون اینکه CRM مالک چرخه عملیاتی حمل شود.

## 2. وضعیت فعلی تاییدشده از کد

بر اساس بررسی فایل‌های فعلی:

- مدل `ShipmentRequest` در `backend/models.py` فیلد nullable زیر را دارد:
  - `customer_id = ForeignKey("customer.id"), nullable=True`
- همان مدل relationship زیر را دارد:
  - `customer = db.relationship("Customer", back_populates="requests")`
- مدل `Customer` relationship معکوس زیر را دارد:
  - `requests = db.relationship("ShipmentRequest", back_populates="customer", lazy=True)`
- `ShipmentRequest` فیلد جداگانه `gamification_customer_id` هم دارد که به `CustomerGamification` وصل است و نباید با `Customer` در CRM یکی فرض شود.
- سرویس ثبت درخواست عمومی در `backend/services/shipment_service.py` هنگام ساخت درخواست، `customer_id` را `None` قرار می‌دهد.
- مسیرهای فعلی CRM با prefix فعلی `/api/crm` و decorator فعلی `@require_role("business_expert")` کار می‌کنند.
- مسیرهای فعلی admin shipment request با prefix فعلی `/api/admin` و decorator فعلی `@require_role("admin")` کار می‌کنند.
- جزئیات فعلی admin shipment request در `backend/services/admin_shipment_request_service.py` اطلاعات خام مشتری ثبت‌شده روی درخواست را برمی‌گرداند، اما payload فعلی لینک CRM Customer را نمایش نمی‌دهد.

نتیجه: schema پایه برای لینک دستی وجود دارد، اما رفتار عملیاتی، contract تست، authorization، audit و نمایش payload هنوز باید در فاز پیاده‌سازی آینده تعریف و اضافه شود.

## 3. دامنه CRM-3A

داخل دامنه:

- طراحی رفتار لینک دستی درخواست حمل موجود به مشتری CRM موجود.
- طراحی رفتار اصلاح لینک و حذف لینک.
- تعیین مرز authorization.
- تعیین نیازهای audit.
- تعیین contract تست‌های backend.
- تعیین تست‌های frontend/manual برای زمانی که UI در فاز بعدی ساخته شود.
- تعیین ریسک‌ها، rollback و معیار پذیرش.

خارج از دامنه:

- ساخت خودکار Customer از روی درخواست عمومی.
- یکی کردن `CustomerGamification` و `Customer`.
- اتصال `Opportunity` به `ShipmentRequest`.
- تغییر lifecycle، status، assignment، quote، tracking یا timeline درخواست.
- اجباری کردن `customer_id` برای درخواست‌ها.
- تغییر مسیرهای موجود API در این فاز.
- تغییر مدل یا migration در این فاز.
- طراحی کامل UI production-ready در این فاز.

## 4. تصمیم طراحی اصلی

لینک CRM باید یک عملیات دستی، صریح و قابل ردیابی باشد.

قاعده اصلی:

`ShipmentRequest.customer_id` فقط وقتی مقدار می‌گیرد که کاربر مجاز، بعد از مشاهده اطلاعات کافی، یک `Customer` موجود در CRM را برای یک `ShipmentRequest` موجود انتخاب کند.

پیامدها:

- درخواست بدون `customer_id` همچنان معتبر است.
- لینک کردن نباید `ShipmentRequest.status`، `assigned_to`، `priority`، `sla_due_at`، `last_customer_touch_at`، quote یا timeline را تغییر دهد.
- لینک کردن نباید `CustomerGamification` را تغییر دهد.
- لینک کردن نباید Customer جدید بسازد.
- لینک کردن فقط ارجاع CRM را روی درخواست تنظیم می‌کند.

## 5. محل پیشنهادی منطق در معماری آینده

پیاده‌سازی آینده باید کوچک و service-first باشد.

پیشنهاد:

- منطق write در یک سرویس کوچک جدید یا extension محدود داخل service مناسب قرار بگیرد؛ مثلا `crm_request_link_service`.
- route فقط authentication، authorization، خواندن payload و mapping پاسخ/خطا را انجام دهد.
- سرویس مسئول validation، lookup، conflict handling، audit و commit/rollback باشد.
- read payloadهای admin/CRM فقط بعد از تثبیت write contract گسترش پیدا کنند.

این طراحی عمدا از refactor بزرگ CRM یا admin panel جلوگیری می‌کند.

## 6. Contract رفتاری عملیات لینک

### 6.1 Link

ورودی منطقی:

- `shipment_request_id`
- `customer_id`
- user فعلی
- optional note/reason کوتاه برای audit

پیش‌شرط‌ها:

- درخواست حمل وجود داشته باشد.
- مشتری CRM وجود داشته باشد.
- کاربر مجوز لینک داشته باشد.
- درخواست می‌تواند بدون لینک یا دارای لینک قبلی باشد.

رفتار:

- اگر درخواست بدون لینک است، `ShipmentRequest.customer_id` برابر `Customer.id` می‌شود.
- اگر درخواست از قبل به همان customer لینک شده، پاسخ باید idempotent باشد و تغییر عملیاتی اضافه انجام ندهد.
- اگر درخواست به customer دیگری لینک شده، رفتار باید به عنوان relink کنترل‌شده ثبت شود.
- هیچ فیلد عملیاتی درخواست نباید تغییر کند.

خروجی منطقی:

- شناسه درخواست.
- وضعیت لینک جدید.
- خلاصه مشتری لینک‌شده.
- نوع عملیات: `link` یا `relink` یا `noop`.

### 6.2 Unlink

ورودی منطقی:

- `shipment_request_id`
- user فعلی
- optional note/reason کوتاه برای audit

رفتار:

- `ShipmentRequest.customer_id` به `None` برمی‌گردد.
- درخواست حذف نمی‌شود.
- Customer حذف نمی‌شود.
- Activity، Opportunity، quote، log و timeline حذف نمی‌شوند.
- اگر درخواست از قبل بدون لینک است، پاسخ باید idempotent باشد.

خروجی منطقی:

- شناسه درخواست.
- وضعیت لینک جدید: بدون لینک.
- نوع عملیات: `unlink` یا `noop`.

## 7. Authorization پیشنهادی

برای پیاده‌سازی آینده، مجوز باید با نقش‌های فعلی سازگار باشد و از دسترسی بیش از حد جلوگیری کند.

پیشنهاد محافظه‌کارانه:

- `admin`: مجاز به link، relink و unlink.
- `crm_manager`: کاندیدای مجاز، اگر route آینده واقعا در سطح CRM عملیاتی شود.
- `business_expert`: کاندیدای مجاز برای لینک در CRM، اما باید با دسترسی به درخواست حمل هم کنترل شود.
- `expert`: به صورت پیش‌فرض مجاز نباشد، مگر تصمیم محصولی جداگانه گرفته شود.

نکته مهم: چون مسیرهای فعلی admin shipment request فقط `admin` هستند و مسیرهای فعلی CRM از `business_expert` به بالا استفاده می‌کنند، انتخاب محل route آینده باید قبل از پیاده‌سازی نهایی شود. CRM-3A مسیر API جدید را تصویب نمی‌کند؛ فقط نیاز authorization را مشخص می‌کند.

## 8. Audit و ردیابی

هر تغییر لینک باید قابل ردیابی باشد.

حداقل داده audit پیشنهادی:

- `shipment_request_id`
- `old_customer_id`
- `new_customer_id`
- `operation`: `link`, `relink`, `unlink`, `noop`
- `performed_by_user_id`
- `performed_by_role`
- `created_at`
- `note` یا `reason` اختیاری

گزینه‌های پیاده‌سازی آینده:

- استفاده محدود از log موجود، اگر برای این نوع رویداد مناسب و قابل گزارش باشد.
- یا افزودن audit مستقل در فاز جداگانه، اگر محصول نیازمند history رسمی لینک‌ها باشد.

تا وقتی audit مناسب وجود ندارد، فعال کردن لینک در UI گسترده ریسک عملیاتی دارد.

## 9. خطاها و وضعیت‌های مرزی

پیاده‌سازی آینده باید این حالت‌ها را صریح تست کند:

- درخواست حمل پیدا نشود: `404`
- مشتری CRM پیدا نشود: `404`
- کاربر احراز هویت نشده باشد: `401`
- کاربر احراز هویت شده ولی مجاز نباشد: `403`
- payload نامعتبر باشد: `400`
- لینک به همان customer فعلی: موفق و idempotent
- unlink روی درخواست بدون لینک: موفق و idempotent
- خطای DB هنگام commit: rollback و پاسخ خطای کنترل‌شده

هیچ‌کدام از خطاها نباید باعث تغییر ناقص در وضعیت عملیاتی درخواست شوند.

## 10. Read Model و نمایش داده

بعد از تثبیت write contract، read payloadها می‌توانند به صورت محدود گسترش پیدا کنند.

پیشنهاد برای payload آینده:

- در جزئیات درخواست، یک object کوچک برای CRM link اضافه شود:
  - `customer_id`
  - `name`
  - `company_name`
  - `phone`
  - `email`
  - `status`
- در لیست درخواست‌ها، نمایش لینک باید سبک باشد و باعث join سنگین غیرضروری نشود.
- اگر لینک وجود ندارد، UI باید حالت معتبر «بدون مشتری CRM» را نشان دهد.

محدودیت:

- تغییر نام یا اطلاعات Customer نباید داده خام ثبت‌شده روی `ShipmentRequest.customer_first_name` و `customer_last_name` را بازنویسی کند.
- گزارش‌ها باید منبع داده را روشن نگه دارند: داده خام درخواست یا Customer لینک‌شده.

## 11. برنامه تست backend

تست‌های پیشنهادی contract/service:

1. درخواست بدون `customer_id` همچنان معتبر و قابل خواندن است.
2. کاربر غیرمجاز نمی‌تواند لینک ایجاد کند.
3. کاربر مجاز می‌تواند request موجود را به customer موجود لینک کند.
4. لینک موفق فقط `ShipmentRequest.customer_id` را تغییر می‌دهد.
5. لینک موفق `status`, `assigned_to`, `priority`, `sla_due_at`, `last_customer_touch_at` را تغییر نمی‌دهد.
6. لینک موفق `gamification_customer_id` و داده‌های `CustomerGamification` را تغییر نمی‌دهد.
7. لینک به customer ناموجود خطای `404` می‌دهد و commit انجام نمی‌شود.
8. لینک request ناموجود خطای `404` می‌دهد و commit انجام نمی‌شود.
9. لینک دوباره به همان customer idempotent است.
10. relink از customer قبلی به customer جدید مقدار قبلی و جدید را audit می‌کند.
11. unlink مقدار `customer_id` را `None` می‌کند.
12. unlink درخواست، Customer یا داده‌های عملیاتی را حذف نمی‌کند.
13. unlink روی درخواست بدون لینک idempotent است.
14. خطای commit باعث rollback می‌شود.
15. پاسخ read بعد از لینک، خلاصه Customer لینک‌شده را در صورت تصویب read payload برمی‌گرداند.

محل احتمالی تست:

- تست contract جداگانه برای لینک دستی، مثلا در خانواده تست‌های CRM یا admin shipment request.
- تست service مستقیم برای rollback و idempotency.
- تست route برای authorization و کدهای پاسخ.

## 12. برنامه تست frontend و دستی آینده

وقتی UI در فاز بعدی ساخته شود، تست دستی باید این سناریوها را پوشش دهد:

1. درخواست بدون لینک با برچسب «بدون مشتری CRM» نمایش داده شود.
2. کاربر مجاز بتواند مشتری را جستجو و انتخاب کند.
3. قبل از لینک، خلاصه customer انتخاب‌شده نمایش داده شود.
4. کاربر بتواند عملیات لینک را cancel کند.
5. بعد از لینک، صفحه بدون تغییر status عملیاتی، مشتری لینک‌شده را نشان دهد.
6. تغییر لینک موجود هشدار واضح داشته باشد.
7. حذف لینک، درخواست و Customer را حذف نکند.
8. کاربر غیرمجاز دکمه یا عملیات لینک را نبیند یا در backend پاسخ `403` بگیرد.
9. خطای customer ناموجود یا request ناموجود پیام قابل فهم بدهد.
10. صفحه بعد از refresh وضعیت لینک را از backend بخواند، نه از state موقت frontend.

## 13. ریسک‌ها

- مخلوط شدن Customer CRM با CustomerGamification.
- تغییر ناخواسته status یا assignment هنگام لینک.
- افزودن route در محل نامناسب و باز کردن دسترسی بیش از حد.
- نبود audit کافی برای relink و unlink.
- join سنگین در لیست درخواست‌ها.
- نمایش داده CRM به کاربرانی که فقط باید داده عملیاتی request را ببینند.
- ساخت خودکار Customer از درخواست عمومی بدون تصمیم محصولی.

## 14. معیار پذیرش فاز پیاده‌سازی آینده

CRM-3A وقتی برای ورود به پیاده‌سازی آماده است که این معیارها در فاز آینده قابل اثبات باشند:

- لینک دستی فقط با کاربر مجاز انجام شود.
- لینک، relink و unlink تست contract داشته باشند.
- درخواست بدون لینک همچنان حالت معتبر باشد.
- CustomerGamification تغییر نکند.
- فیلدهای عملیاتی ShipmentRequest تغییر نکنند.
- خطاهای `401`, `403`, `404`, `400` و rollback تست شوند.
- audit یا لاگ قابل قبول برای تغییر لینک وجود داشته باشد.
- read payload فقط داده لازم را برگرداند و مرز داده خام request با Customer CRM را مخلوط نکند.

## 15. جمع‌بندی

CRM-3A باید یک قابلیت کوچک، دستی و قابل کنترل برای اتصال `ShipmentRequest` به `Customer` موجود طراحی کند. schema فعلی امکان این اتصال را فراهم کرده، اما فعال‌سازی آن باید با contract تست، authorization روشن، audit مناسب و حفظ مرزهای عملیاتی انجام شود.

تصمیم نهایی این سند:

- `ShipmentRequest.customer_id` لینک اختیاری به CRM Customer است.
- نبود لینک معتبر است.
- لینک دستی نباید چرخه عملیاتی حمل را تغییر دهد.
- CustomerGamification جدا از Customer CRM باقی می‌ماند.
- در این فاز هیچ کد، مدل، migration، API path یا UI تغییر نمی‌کند.

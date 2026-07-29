# بسته کارگاه تصمیم‌گیری سیاست‌های زمان

> وضعیت سند: آماده برگزاری کارگاه — هیچ پیشنهاد این سند تصمیم نهایی یا قرارداد پیاده‌سازی نیست.
> مرجع اصول فنی: [ADR-016](../../operational/adr/ADR-016-time-and-timezone-architecture.md)؛
> مرجع وضعیت تصمیم‌ها: [Time Business Decision Register](time-business-decision-register.md)

## ۱. هدف و محدوده جلسه

این جلسه برای طراحی فنی یا بررسی Migration نیست؛ هدف آن تصویب، رد یا ارجاع برای
بررسی تکمیلیِ **معنای کسب‌وکاری زمان‌ها** است. خروجی ثبت‌شده جلسه، ورودی اصلاحات
فنی آینده خواهد بود و به‌تنهایی مجوز تغییر کد، داده یا Schema نیست.

## ۲. اصول فنی غیرقابل‌مذاکره

- رخداد واقعی یک UTC Instant است و در API offset صریح دارد.
- Date-only یک روز تقویمی است، نه Timestamp در نیمه‌شب.
- زمان محلی عملیاتی باید مالک و IANA timezone داشته باشد.
- Timezone مرورگر مرجع رخداد بین‌المللی نیست و تهران قرارداد عمومی عملیات نیست.
- Migration سراسری Timestampهای Legacy مجاز نیست.
- داده Mixed فقط با Rule اختصاصی و شواهد قابل تبدیل است.

این اصول Accepted هستند و در جلسه دوباره به رأی گذاشته نمی‌شوند؛ تغییرشان نیازمند
اصلاح رسمی ADR-016 است.

## ۳. نمای کلی تصمیم‌ها

| ID | گروه | تصمیم موردنیاز | مالک اصلی | اثر اصلی | اولویت | وضعیت |
| -- | -- | -- | -- | -- | -- | -- |
| TIME-BIZ-001 | SLA و Workflow | پیوسته یا ساعات کاری بودن SLA | مدیریت بازرگانی / مدیریت عملیات | تقویم، deadline، API/UI | P0 | Pending business approval |
| TIME-BIZ-002 | SLA و Workflow | رفتار SLA در Reassignment | مدیریت عملیات | history، reason و audit | P0 | Pending business approval |
| TIME-BIZ-003 | Quote و بازرگانی | Timezone پایان اعتبار Quote | مدیریت بازرگانی | snapshot و expiry | P0 | Pending business approval |
| TIME-BIZ-004 | Quote و بازرگانی | معنای `responded_at` | مدیریت بازرگانی | event model و audit | P1 | Pending business approval |
| TIME-BIZ-005 | CRM | تفکیک `due_date` و `due_at` | مالک فرایند CRM | model/API/UI/reminder | P0 | Pending business approval |
| TIME-BIZ-006 | CRM | مالک Timezone موعد دقیق | مالک فرایند CRM | ownership و reassignment | P0 | Pending business approval |
| TIME-BIZ-007 | Tracking و عملیات بین‌المللی | تقدم منبع Timezone رخداد | مدیریت عملیات / مالک Tracking | ingestion و provenance | P0 | Pending business approval |
| TIME-BIZ-011 | Tracking و عملیات بین‌المللی | fallback رخداد بدون Location/zone | مدیریت عملیات / حاکمیت داده | exception و reconciliation | P1 | Pending business approval |
| TIME-BIZ-008 | Route Planning | Timezone خروج برنامه‌ریزی‌شده | مدیریت عملیات | Route Leg و UI | P0 | Pending business approval |
| TIME-BIZ-009 | Route Planning | Timezone ورود برنامه‌ریزی‌شده | مدیریت عملیات | Route Leg و کنترل مدت | P0 | Pending business approval |
| TIME-BIZ-010 | Reporting | مبنای روز گزارش شرکت | مدیریت ارشد / مالی | query، cache و export | P0 | Pending business approval |
| TIME-BIZ-012 | Security و Session | Sliding یا absolute بودن Session | امنیت / مالک محصول | token/session و UX | P1 | Pending business approval |

## ۴. کارت‌های تصمیم

در جدول‌های گزینه، «پیشنهادی» فقط **پیشنهاد اولیه برای تصمیم‌گیری** است.

### TIME-BIZ-001 — سیاست محاسبه SLA

**سؤال تصمیم:** SLA پاسخ کارشناسی پیوسته است یا بر اساس ساعات کاری واحد مسئول؟

**مسئله و سناریو:** بدون این تصمیم، deadline و تأخیر در UI و گزارش یکسان نیست.
درخواست ساعت ۱۷:۵۵ جمعه به واحدی با تعطیلی شنبه می‌رسد؛ موعد دقیق باید قابل محاسبه باشد.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| تقویم‌محور | ساعات کاری، تعطیلات و IANA zone واحد مسئول | منطبق با ظرفیت واقعی | نیازمند تقویم versioned | calendar/deadline/API/UI | پیشنهادی |
| پیوسته 24/7 | Duration از زمان شروع | ساده و شفاف | بی‌توجه به تعطیلی | موتور ساده‌تر | ساده‌تر |
| ساعت مرورگر | محاسبه ضمنی با zone کاربر | ندارد | متغیر و غیرقابل Audit | قرارداد ناسازگار | رد شود |

**مالک:** مدیریت بازرگانی / مدیریت عملیات. **مشاوران:** محصول، پشتیبانی، معماری،
حقوقی. **مشاور فنی:** معماری. **تیم اجرا:** Backend، Frontend، داده.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-002 — SLA در Reassignment

**سؤال تصمیم:** آیا Reassignment باید SLA را reset کند؟

**مسئله و سناریو:** انتقال مکرر پرونده می‌تواند تأخیر را پنهان کند؛ پرونده پس از
۸۰٪ مهلت از عملیات به بازرگانی منتقل می‌شود.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| حفظ deadline | reset فقط با reason سازمانی و Audit | ضد دست‌کاری | نیازمند استثنا | history/reason/event | پیشنهادی |
| reset همیشگی | هر انتقال مهلت تازه | ساده | قابل سوءاستفاده | deadline جدید | ساده‌تر |
| reset پنهان | بدون history | ندارد | غیرقابل Audit | داده گمراه‌کننده | رد شود |

**مالک:** مدیریت عملیات. **مشاوران:** بازرگانی، محصول، Audit، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** Backend و محصول.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-003 — Timezone اعتبار Quote

**سؤال تصمیم:** `valid_until` تا پایان روز کدام Timezone معتبر است؟

**مسئله و سناریو:** مشتری استانبول و صادرکننده تهران، تاریخ ۱۴۰۵/۰۶/۱۰ را می‌بینند؛
لحظه انقضا باید بدون وابستگی به محل مشاهده روشن باشد.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| بازار/مشتری با snapshot | zone هنگام صدور تثبیت شود | منصفانه و پایدار | تعیین منبع لازم | snapshot/expiry/API/UI | پیشنهادی |
| Timezone ثابت شرکت | zone واحد و اعلام‌شده | ساده | نامتناسب با بازارها | تنظیم مرکزی | ساده‌تر |
| مرورگر بیننده | zone هر مشاهده | ندارد | انقضای متغیر | ناسازگار | رد شود |

**مالک:** مدیریت بازرگانی. **مشاوران:** فروش، حقوقی، مالی، محصول، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** Quote، Backend، Frontend.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-004 — معنای پاسخ Quote

**سؤال تصمیم:** `responded_at` زمان دریافت در سامانه است یا زمان اعلام‌شده مشتری؟

**مسئله و سناریو:** پاسخ تلفنی ساعت ۱۰ داده و ساعت ۱۳ دستی ثبت می‌شود؛ Audit باید
هر دو واقعیت را حفظ کند.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| تفکیک دو زمان | دریافت سیستمی و زمان ادعاشده جدا | دقیق و قابل Audit | UX بیشتر | naming/event/import | پیشنهادی |
| فقط دریافت سیستم | یک Instant معتبر | ساده | از دست‌رفتن ادعا | یک فیلد | ساده‌تر |
| معنای متغیر | یک فیلد برای هر دو | ندارد | گزارش نامعتبر | قرارداد مبهم | رد شود |

**مالک:** مدیریت بازرگانی. **مشاوران:** CRM، Audit، محصول، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** Quote/CRM و یکپارچه‌سازی.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-005 — نوع موعد CRM

**سؤال تصمیم:** آیا CRM باید `due_date` و `due_at` را جدا پشتیبانی کند؟

**مسئله و سناریو:** «تا سه‌شنبه تماس بگیر» با «سه‌شنبه ساعت ۱۰» یک معنا ندارد.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| دو نوع موعد | روزانه و ساعتی جدا | معنای درست | UI/validation بیشتر | model/API/reminder | پیشنهادی |
| فقط `due_at` | همه موعدها Instant | ساده | روزانه نیازمند ساعت ساختگی | یک مسیر | ساده‌تر |
| midnight خودکار | Date به Instant ضمنی | ندارد | جابه‌جایی روز | خطای timezone | رد شود |

**مالک:** مالک فرایند CRM. **مشاوران:** فروش، پشتیبانی، محصول، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** CRM، Backend، Frontend.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-006 — مالک Timezone موعد CRM

**سؤال تصمیم:** Timezone موعد دقیق متعلق به مسئول، مشتری یا Location فعالیت است؟

**مسئله و سناریو:** مسئول پرونده عوض می‌شود ولی تماس ساعت ۹ محلی مشتری باید ثابت بماند.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| مالک صریح برحسب فعالیت | همراه snapshot zone | پایدار و دقیق | Rule دامنه لازم | owner/snapshot/reassign | پیشنهادی |
| مسئول فعلی | zone کارشناس | ساده | موعد با انتقال تغییر می‌کند | وابستگی کاربر | ساده‌تر |
| مرورگر/تهران | پیش‌فرض عمومی | ندارد | جهانی نیست | رفتار ضمنی | رد شود |

**مالک:** مالک فرایند CRM. **مشاوران:** فروش، عملیات، محصول، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** CRM.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-007 — مرجع Timezone رخداد Tracking

**سؤال تصمیم:** تقدم Location، دستگاه، API خارجی یا ورود دستی چیست؟

**مسئله و سناریو:** دستگاه offset دارد، Location باکو است و API زمان دیگری می‌دهد؛
منبع منتخب و provenance باید روشن باشد.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| تقدم منبع معتبر | offset/zone منبع و Location؛ دستی با provenance | قابل Audit | validation پیچیده | ingestion/exception | پیشنهادی |
| فقط Location | zone مکان | ساده | Location غلط/غایب | lookup | ساده‌تر |
| zone ثبت‌کننده | مرورگر کاربر | ندارد | رخداد را تحریف می‌کند | ناسازگار | رد شود |

`occurred_at` (وقوع واقعی) از `recorded_at` (پذیرش سامانه) جدا می‌ماند.

**مالک:** مدیریت عملیات / مالک Tracking. **مشاوران:** یکپارچه‌سازی، داده، محصول،
معماری. **مشاور فنی:** معماری. **تیم اجرا:** Tracking و Integration.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-011 — Tracking بدون Location یا Zone

**سؤال تصمیم:** رخداد فاقد Location و zone/offset معتبر چه شود؟

**مسئله و سناریو:** فایل شریک فقط `2026-07-01 09:00` دارد؛ ساخت Instant حدسی ترتیب
محموله را مخدوش می‌کند.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| quarantine | نگهداری provenance تا تکمیل | بدون جعل | صف رسیدگی | quality/reconcile | پیشنهادی |
| zone منبع یکپارچه‌سازی | fallback قراردادی شریک | عملی‌تر | نیازمند اعتبارسنجی | source config | ساده‌تر |
| حدس از کاربر/سرور | تبدیل ضمنی | ندارد | داده جعلی | غیرقابل Audit | رد شود |

**مالک:** مدیریت عملیات / حاکمیت داده. **مشاوران:** یکپارچه‌سازی، پشتیبانی،
معماری. **مشاور فنی:** معماری. **تیم اجرا:** Tracking، Data Ops.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-008 — Timezone خروج برنامه‌ریزی‌شده

**سؤال تصمیم:** `planned_departure` بر مبنای Timezone مبدأ ثبت شود؟

**مسئله و سناریو:** برنامه‌ریز تهران خروج ۰۹:۰۰ شانگهای را وارد می‌کند؛ زمان دیواری
باید متعلق به مبدأ باشد.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| zone مبدأ + snapshot | IANA zone زمان برنامه‌ریزی | معنای عملیاتی | override لازم | Route/UI/resolution | پیشنهادی |
| ورود UTC | Instant مستقیم | ساده فنی | دشوار برای عملیات | UTC UI | ساده‌تر |
| zone مرورگر | zone برنامه‌ریز | ندارد | خروج غلط | ناسازگار | رد شود |

Override فقط با Reason و Audit قابل طرح است.

**مالک:** مدیریت عملیات. **مشاوران:** برنامه‌ریزی، محصول، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** Route Planning.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-009 — Timezone ورود برنامه‌ریزی‌شده

**سؤال تصمیم:** `planned_arrival` بر مبنای Timezone مقصد ثبت شود؟

**مسئله و سناریو:** حرکت از دبی و ورود به لندن در روز تغییر ساعت؛ نمایش و کنترل مدت
باید zone مقصد را لحاظ کند.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| zone مقصد + snapshot | هر checkpoint zone خودش | طبیعی برای عملیات | حل ambiguity | Route/duration/UI | پیشنهادی |
| ورود UTC | Instant مستقیم | ساده | UX دشوار | UTC UI | ساده‌تر |
| zone مرورگر | zone برنامه‌ریز | ندارد | ورود غلط | ناسازگار | رد شود |

Override فقط با Reason و Audit؛ checkpoint بر اساس Location خودش بررسی شود.

**مالک:** مدیریت عملیات. **مشاوران:** برنامه‌ریزی، محصول، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** Route Planning.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-010 — روز گزارش

**سؤال تصمیم:** روز شرکت، شعبه، مشتری و گزارش بین‌المللی با چه Timezone و مرزی است؟

**مسئله و سناریو:** فروش ساعت ۰۰:۳۰ تهران ممکن است برای شعبه استانبول روز قبل باشد؛
جمع گزارش بدون مبنای آشکار قابل مقایسه نیست.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| مبنای مصوب هر خانواده | شرکت/شعبه/مشتری؛ UTC برای بین‌المللی و نمایش `timezone_basis` | دقیق | governance بیشتر | query/cache/export | پیشنهادی |
| zone ثابت شرکت | همه گزارش‌های شرکتی | ساده | شعبه/مشتری نامتناسب | config واحد | ساده‌تر |
| zone مرورگر/سرور | ضمنی | ندارد | خروجی متغیر | غیرقابل بازتولید | رد شود |

همه بازه‌ها `[start, end)` هستند.

**مالک:** مدیریت ارشد / مالی. **مشاوران:** عملیات، BI، محصول، معماری.
**مشاور فنی:** معماری. **تیم اجرا:** BI، Reporting، Backend.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

### TIME-BIZ-012 — انقضای Session

**سؤال تصمیم:** lifetime به‌صورت sliding یا absolute است و سقف مطلق و clock skew چیست؟

**مسئله و سناریو:** کاربر فعال نباید Session بی‌نهایت داشته باشد؛ expiration ذخیره‌شده
در DB و JWT نیز نباید متفاوت باشد.

| گزینه | تعریف | مزیت | محدودیت | اثر فنی | پیشنهاد |
| -- | -- | -- | -- | -- | -- |
| سیاست تفکیکی | access کوتاه، refresh sliding با maximum absolute و skew مصوب | تعادل امنیت/UX | اجزای بیشتر | token/store/audit | پیشنهادی |
| absolute واحد | انقضای ثابت | ساده و قابل پیش‌بینی | خروج زودهنگام | یک expiry | ساده‌تر |
| ساعت محلی کاربر | وابسته به timezone | ندارد | امنیت ناپایدار | ناسازگار | رد شود |

**مالک:** امنیت / مالک محصول. **مشاوران:** Backend، عملیات، معماری.
**مشاور فنی:** امنیت و معماری. **تیم اجرا:** Backend/Auth.

**نتیجه جلسه:** `Decision:` … `Status:` … `Effective date:` … `Approved by:` …
`Conditions:` … `Follow-up actions:` …

## ۵. ماتریس مشارکت (RACI)

| تصمیم | عملیات | بازرگانی | CRM | فناوری اطلاعات | امنیت | مدیریت |
| -- | -- | -- | -- | -- | -- | -- |
| 001 SLA Policy | A | A/R | I | C | I | I |
| 002 SLA Reassignment | A/R | C | I | C | I | I |
| 003 Quote Validity | C | A/R | I | C | I | I |
| 004 Quote Response | I | A/R | C | C | I | I |
| 005 CRM Due Type | C | C | A/R | C | I | I |
| 006 CRM Due Ownership | C | C | A/R | C | I | I |
| 007 Tracking Zone | A/R | I | I | C | I | I |
| 011 Tracking fallback | A/R | I | I | C | C | I |
| 008 Departure Zone | A/R | I | I | C | I | I |
| 009 Arrival Zone | A/R | I | I | C | I | I |
| 010 Reporting Day | C | C | C | R | I | A |
| 012 Session expiry | I | I | I | R | A | C |

`A`: Approver، `R`: مسئول پیشنهاد، `C`: مشاور، `I`: مطلع. تیم توسعه Approver
تصمیم کسب‌وکاری نیست.

## ۶. دستورجلسه پیشنهادی

به‌دلیل ۱۲ تصمیم، دو نشست پیشنهاد می‌شود و بسته واحد می‌ماند:

| نشست | زمان | موضوع | خروجی |
| -- | --: | -- | -- |
| اول | ۱۰ دقیقه | اصول ADR و روش ثبت | درک مشترک |
| اول | ۲۵ دقیقه | TIME-BIZ-001 و 002 | سیاست SLA |
| اول | ۲۰ دقیقه | TIME-BIZ-003 و 004 | سیاست Quote |
| اول | ۲۵ دقیقه | TIME-BIZ-005 و 006 | سیاست CRM |
| اول | ۱۰ دقیقه | جمع‌بندی | وضعیت ۶ تصمیم |
| دوم | ۱۰ دقیقه | مرور مصوبات/ابهامات | هم‌ترازی |
| دوم | ۲۵ دقیقه | TIME-BIZ-007 و 011 | Tracking |
| دوم | ۲۰ دقیقه | TIME-BIZ-008 و 009 | Route Planning |
| دوم | ۱۵ دقیقه | TIME-BIZ-010 | Reporting |
| دوم | ۱۵ دقیقه | TIME-BIZ-012 | Session |
| دوم | ۵ دقیقه | جمع‌بندی | وضعیت همه تصمیم‌ها |

## ۷. شرایط تبدیل تصمیم به Accepted

تنها وقتی وضعیت Accepted ثبت می‌شود که مالک، گزینه صریح، Timezone/مبنای زمانی،
رفتار موارد مرزی، تاریخ اثر، اثر بر داده موجود و نبود ابهام اصلی ثبت شده باشد.
توافق شفاهی یا انتخاب کلی گزینه کافی نیست.

## ۸. Decision Log جلسه

| ID | تصمیم | وضعیت جدید | مصوبه | مالک اقدام | موعد | وابستگی |
| -- | -- | -- | -- | -- | -- | -- |
| TIME-BIZ-001 |  |  |  |  |  |  |
| TIME-BIZ-002 |  |  |  |  |  |  |
| TIME-BIZ-003 |  |  |  |  |  |  |
| TIME-BIZ-004 |  |  |  |  |  |  |
| TIME-BIZ-005 |  |  |  |  |  |  |
| TIME-BIZ-006 |  |  |  |  |  |  |
| TIME-BIZ-007 |  |  |  |  |  |  |
| TIME-BIZ-008 |  |  |  |  |  |  |
| TIME-BIZ-009 |  |  |  |  |  |  |
| TIME-BIZ-010 |  |  |  |  |  |  |
| TIME-BIZ-011 |  |  |  |  |  |  |
| TIME-BIZ-012 |  |  |  |  |  |  |

وضعیت‌های مجاز: `Accepted`، `Rejected`، `Deferred`،
`Pending technical validation`، `Pending business clarification`.

## ۹. خروجی فنی احتمالی پس از جلسه

فقط پس از پذیرش معتبر هر تصمیم ممکن است Update در Register، ADR تکمیلی، API
Contract، UI Specification، Data Migration Plan، Contract Test، Issue اجرایی یا
Rollout Plan لازم شود. هیچ‌یک در این مرحله ایجاد نشده‌اند.

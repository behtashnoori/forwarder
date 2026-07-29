# Time Data Type Guide

این راهنما برای انتخاب نوع زمانی در توسعه‌های بعدی است. سیاست‌های باز در
[Decision Register](time-business-decision-register.md) باید قبل از تثبیت قرارداد
دامنه مربوطه تصویب شوند.

## Decision flow

1. آیا مقدار یک لحظه واقعی و قابل ترتیب/Audit است؟ **Instant**
2. آیا فقط یک روز تقویمی را بدون ساعت نشان می‌دهد؟ **Local Date**
3. آیا کاربر ساعت محلی آینده را برای یک مکان/کسب‌وکار تعیین می‌کند؟
   **Business Local DateTime**
4. آیا مقدار فاصله یا مهلت است؟ **Duration**
5. آیا تکرار تقویمی است؟ **Recurrence Rule** به‌همراه IANA timezone و سیاست
   تقویم؛ نه فهرستی از Timestampهای حدسی.

## Contracts

| مفهوم | نمونه | Backend | Database هدف | API | UI |
| --- | --- | --- | --- | --- | --- |
| Instant | `created_at`, `occurred_at`, `recorded_at` | timezone-aware datetime در UTC | `timestamp with time zone` | RFC 3339 با `Z` یا offset صریح | نمایش در zone انتخاب‌شده و اعلام مبنا |
| Local Date | `pickup_date`, `valid_until` | date | `DATE` | `YYYY-MM-DD` | parse تقویمی؛ بدون `new Date(value)` |
| Business Local DateTime | departure ساعت 09:00 مبدأ | local date + local time + IANA zone + owner؛ Instant حل‌شده پس از validation | اجزای wall-clock/zone/owner و Instant حل‌شده طبق طراحی مصوب | local value، zone ID، owner/location و Instant در صورت حل | ورود در zone مالک؛ نمایش zone و رسیدگی به ambiguity |
| Duration | session lifetime، SLA duration | duration یا value + unit | interval یا value + unit طبق قرارداد | مقدار و واحد صریح / ISO 8601 duration در صورت تصویب | قالب انسانی، بدون تبدیل به تاریخ |
| Recurrence | ساعات کاری هفتگی | rule + calendar + IANA zone | ساختار rule/versioned calendar | rule، zone و calendar version | preview رخدادهای آینده با zone |

## Naming

- Instantها: پسوند `_at`، مانند `created_at`.
- Local Dateها: پسوند `_date` یا نام دامنه‌ای روشن، مانند `due_date`.
- Timezone: پسوند `_timezone` و مقدار IANA مانند `Europe/Istanbul`؛ abbreviation
  مبهمی مانند `CST` مجاز نیست.
- Offset به‌تنهایی timezone نیست؛ `+03:30` قواعد تاریخی/آینده یک منطقه را بیان
  نمی‌کند.
- برای رخداد تأخیری، `occurred_at` و `recorded_at` جدا هستند.
- نام‌هایی مانند `timestamp`, `date_time`, `time` یا `valid_until` بدون تعریف نوع
  معنایی در قرارداد ممنوع‌اند.

## Serialization and comparison

- Instant در مرز داخلی به UTC normalize و بر اساس Instant مقایسه می‌شود.
- API باید offset را صریح دریافت کند؛ datetime بدون offset برای Instant رد می‌شود.
- Date-only به midnight UTC/local تبدیل نمی‌شود و با قواعد تقویمی مقایسه می‌شود.
- بازه گزارش Instant به شکل نیمه‌باز `[start, end)` ساخته می‌شود؛ IANA timezone
  تولیدکننده مرزها جزو metadata گزارش است.
- تبدیل Business Local DateTime باید زمان ناموجود یا دوپهلو را آشکارا رد یا طبق
  سیاست مصوب resolve کند؛ انتخاب silent مجاز نیست.
- نمایش محلی، داده canonical را تغییر نمی‌دهد.

## Examples

| نیاز | نوع درست | نوع نادرست |
| --- | --- | --- |
| زمان ثبت رکورد | Instant | datetime naive سرور |
| روز تحویل وعده‌داده‌شده | Local Date | midnight Instant |
| پرواز ساعت 10:00 مبدأ | Business Local DateTime | 10:00 در zone مرورگر |
| مهلت 30 دقیقه | Duration | Timestamp با تاریخ ساختگی |
| زمان رخداد خارجی که دیر رسیده | `occurred_at` + `recorded_at` | یک `timestamp` مبهم |

## Review checklist

- معنای دامنه‌ای مقدار قبل از انتخاب type نوشته شده است.
- مالک Timezone و منبع آن مشخص است.
- قرارداد DB، Backend، API و UI یک معنا دارند.
- parsing به Timezone مرورگر یا سرور متکی نیست.
- نمونه‌های مرز روز، leap day، offset و تغییرات تقویمی پوشش داده شده‌اند.
- هر سیاست کسب‌وکاری لازم، `Approved` و دارای مرجع است.

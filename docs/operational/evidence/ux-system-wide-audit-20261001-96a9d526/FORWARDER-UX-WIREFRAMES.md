# Forwarder UX Target Wireframes

These are concise textual wireframes for the **Forwarder Guided Operational Workspace**. They define hierarchy and behavior, not visual styling or Product code.

## A. Expert Home / Operations Home

```text
HEADER
  عملیات امروز                                      [ایجاد محموله]
  آخرین به‌روزرسانی وضعیت: 10:42  •  ارزیابی Attention: تازه

STATUS STRIP
  فعال 12  |  نیازمند توجه 3  |  آماده اقدام 5  |  به‌روزرسانی‌نشده 2

PRIMARY WORK AREA — صف اقدام
  شدت  محموله       مسیر              مرحله فعلی     دلیل             اقدام
  بالا  FWD-1042     شانگهای ← تهران   در مسیر        گزارش مسیر قدیمی [ثبت پیشرفت]
  بالا  FWD-1037     بندرعباس ← کرج    رسیدن مقصد     تحویل نهایی ندارد [ثبت تحویل]
  ...

SECONDARY
  تغییرات مهم از آخرین مشاهده
  • محموله FWD-1031 به مرحله «در مسیر» رسید.
  • سند بارنامه FWD-1028 تأیید شد.

POSITIVE EMPTY STATE
  همه محموله‌های فعال به‌روز هستند؛ اقدام فوری وجود ندارد.
```

Rules:

- Queue, not KPI-card wall.
- Default order: blocker/urgency, then staleness, then recency.
- Row action opens the exact Shipment task, not generic Summary.
- Commercial Request work is a clear segment/peer queue, not a second unrelated “home.”
- Detailed reason evidence expands in place or a drawer.

## B. Shipment List

```text
HEADER
  محموله‌ها                            [محموله جدید]
  [جست‌وجو] [فیلتر: نیازمند توجه] [نمای ذخیره‌شده ▾]

PRIMARY WORK AREA
  محموله   مشتری       مسیر           مرحله      توجه             آخرین تغییر     اقدام بعدی
  FWD-1042 پارس تجارت  شانگهای→تهران  در مسیر    گزارش قدیمی       2 ساعت پیش       [ثبت پیشرفت]
  FWD-1037 آریا حمل    بندرعباس→کرج   مقصد       تحویل نهایی ندارد  دیروز            [ثبت تحویل]
  FWD-1028 سپهر کالا   دبی→قم          تخلیه      بدون هشدار         20 دقیقه پیش      [بستن پرونده]

SECONDARY COLUMNS / DENSITY CONTROL
  مالک، زمان برنامه‌ریزی‌شده، 7/9 وظیفه — selectable columns or compact secondary line

ON-DEMAND ROW DETAIL
  UUID، Project ID، Request/Quote source، full timestamps، provenance
```

Rules:

- Entire row opens Summary; action button deep-links to task.
- No card per Shipment on desktop.
- Mobile row order: human label + attention → stage/route → last change → CTA.

## C. Shipment Summary

```text
HEADER
  FWD-1042 • پارس تجارت                        وضعیت: فعال
  مالک: سارا احمدی  |  مسیر درخواستی: شانگهای→تهران
  مسیر عملیاتی: شانگهای→بندرعباس→تهران        [شناسه فنی ⧉]

PROCESS STATUS
  ✓ آماده‌سازی/بارگیری  ✓ خروج از مبدأ  ● در مسیر  ○ رسیدن مقصد  ○ تخلیه
  عملیات حمل: 2 از 5 مرحله تکمیل

CURRENT OPERATION
  آخرین موقعیت: نزدیک مرز                   45 دقیقه پیش
  ETA: در دسترس نیست — پیشرفت ساختاری مسیر نیاز به به‌روزرسانی دارد

NEXT ACTION
  اکنون: پیشرفت ساختاری مسیر را ثبت کنید. پس از آن ETA دوباره محاسبه می‌شود.
                                                        [ثبت پیشرفت مسیر]

ATTENTION
  ! یک مورد نیازمند توجه: گزارش ساختاری قدیمی است.        [مشاهده جزئیات]

TASK READINESS
  آمادگی عملیات: 6 از 9 مورد الزامی
  مسیر ✓  اجرا ✓  کالا ✓  تخصیص ✓  اسناد نیازمند توجه  پیگیری نیازمند توجه
  تحویل انجام نشده  بستن پرونده قفل

SECONDARY / ON-DEMAND
  آخرین رویداد، full task list، policy/provenance, raw IDs
```

Rules:

- All blocks above through Next Action fit initial desktop viewport.
- Ordered process and independent tasks are visibly different.
- Only current attention appears; resolved issues belong in History.

## D. Route & Execution

```text
HEADER
  مسیر و اجرای عملیاتی
  بخش فعال: بندرعباس → تهران • جاده‌ای • در حال اجرا

NEXT ACTION
  خروج از بندرعباس ثبت نشده است.                    [ثبت خروج از مبدأ]

PRIMARY WORK AREA — ROUTE TIMELINE
  ✓ شانگهای → بندرعباس      دریایی      رسید: 8 مهر
  ● بندرعباس → تهران        جاده‌ای      کامیون 24ع123 • در انتظار خروج
  ○ تهران                   مقصد نهایی

ATTENTION
  ! زمان مرجع این بخش 3 ساعت بیشتر از برنامه است.   [بررسی]

SECONDARY
  مسیر درخواستی در برابر مسیر عملیاتی
  planned / projected / actual timing summary

ON-DEMAND DETAIL
  [ویرایش برنامه مسیر] [جزئیات Execution و تجهیزات]
  [زمان/مسافت مرجع] [بازبینی و مغایرت] [نسخه‌ها و تاریخچه فنی]
```

Rules:

- Operate is default; Plan/Edit is a separate mode.
- Finance, project units, revisions, and raw IDs never precede the current leg/action.

## E. Cargo & Allocation

```text
HEADER
  کالا و تخصیص
  2 قلم کالا • 1 مورد نیازمند توجه

ATTENTION
  ! تخصیص واقعی «قطعات صنعتی» 5 تن کمتر از بار واقعی ثبت‌شده است. [اصلاح تخصیص]

PRIMARY WORK AREA — COMPARISON TABLE
  کالا           درخواستی  برنامه  بار واقعی  تخصیص برنامه  تخصیص واقعی  تحویل‌شده
  قطعات صنعتی    100 t      100 t   نامشخص     100 t          95 t          95 t
  مواد بسته‌بندی 20 pallet  20      20         20             20            20

NEXT ACTION
  بار واقعی هنوز نامشخص است؛ در صورت دریافت مدرک، مقدار واقعی را ثبت کنید.
                                                        [ثبت بار واقعی]

SECONDARY / ON-DEMAND
  destination, lineage, UOM detail
  [انتقال تخصیص] [اصلاح/بازگشایی] [تاریخچه تغییرات]
```

Rules:

- Unknown never becomes zero.
- Six concepts remain distinct but visually comparable.
- Forms open only after the user selects an action.

## F. Tracking & ETA

```text
HEADER
  پیگیری و زمان تقریبی رسیدن

CURRENT STATE
  موقعیت گزارش‌شده: نزدیک مرز                         45 دقیقه پیش
  پیشرفت ساختاری: بخش 2 از 3 • 62٪
  ETA: در دسترس نیست
  دلیل: پیشرفت ساختاری از آخرین رخداد مسیر قدیمی‌تر است.

NEXT ACTION
  پیشرفت بخش فعال را به‌روزرسانی کنید تا ETA قابل محاسبه شود.
                                                        [ثبت پیشرفت]

PRIMARY WORK AREA
  [ثبت گزارش موقعیت انسانی]   [ثبت پیشرفت ساختاری]
  Only the selected focused form opens.

SECONDARY
  آخرین 3 گزارش as concise timeline rows

ON-DEMAND DETAIL
  همه گزارش‌ها، ETA ruleset/provenance، correction/reopen، raw progress values
```

Rules:

- Human description and structured progress are never conflated.
- If the unavailable reason is not actionable, no false CTA is shown.

## G. Closure

```text
HEADER
  تکمیل و بستن پرونده

READINESS
  NOT READY — 4 از 6 معیار تکمیل شده
  [████████░░] 67%

BLOCKERS
  × تحویل نهایی ثبت نشده است.                         [رفتن به تحویل]
  × مرحله «تخلیه» تکمیل نشده است.                     [رفتن به مراحل]

WARNINGS
  ! تخصیص واقعی با مقدار تحویل 5 تن اختلاف دارد.       [بررسی]
    این هشدار مانع بستن پرونده نیست.

COMPLETED REQUIREMENTS (collapsed)
  ✓ مسیر کامل  ✓ Execution ثبت‌شده  ✓ اسناد الزامی کامل  [مشاهده همه]

NEXT ACTION
  ابتدا تحویل نهایی را ثبت کنید.                       [ثبت تحویل نهایی]

ON-DEMAND DETAIL
  policy/version, evaluation time, criterion evidence, exceptional close
```

Ready state:

```text
READY TO CLOSE — 6 از 6 معیار تکمیل شده
همه الزامات لازم تکمیل شده‌اند.                       [بستن پرونده]
```

Rules:

- Warnings never visually merge with blockers.
- Exceptional close is separated, permission-gated, and never equal in emphasis to normal close.
- Percentage is supportive; blocker text remains authoritative.

## Shared responsive behavior

- Desktop tables become structured rows, not miniature card walls.
- Current state and CTA stay before detail in DOM and visual order.
- Process stage becomes vertical on narrow screens.
- Section navigation becomes current-section selector plus overflow menu.
- Drawers become full-height sheets with focus trap and focus return.
- Long technical IDs are truncated, LTR-isolated, and copyable on demand.


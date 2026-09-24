# بسته بازبینی Product Owner — تجربه فاز ۳

وضعیت: `TARGET_PHASE3_UX`  
`UX_PRODUCT_OWNER_REVIEW=NOT_RUN`  
`HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN`

این سند اسکریپت بازبینی است، نه مدرک تأیید. ستون نتیجه عمداً `NOT_REVIEWED` است و فقط Product Owner انسانی می‌تواند آن را به `PASS`، `NEEDS_CHANGE` یا `DECISION_NEEDED` تغییر دهد.

## ۱. آماده‌سازی

از ریشه مخزن، یک static server روی پوشه Prototype اجرا کنید؛ برای نمونه:

```powershell
python -m http.server 4179 --directory docs/product/ux/phase3/prototype
```

سپس `http://127.0.0.1:4179/` را باز کنید. banner بالای صفحه باید `TARGET_PHASE3_UX` و «داده‌ها کاملاً ساختگی‌اند» را نشان دهد.

## ۲. چک‌پوینت‌های Expert

| # | صفحه/Context | سؤال Product | رفتار مورد انتظار | نتیجه reviewer | یادداشت |
|---:|---|---|---|---|---|
| 1 | نمای کلی S-100 | آیا وضعیت فعلی بدون جست‌وجو فهمیده می‌شود؟ | stage، reported location، time/source، ETA range، freshness و owner در بالای پرونده روشن‌اند | `NOT_REVIEWED` | — |
| 2 | قدم بعدی | آیا اقدام بعدی مفید و قابل توضیح است؟ | تخصیص ۱۰ کارتن به‌علت stage جاری پیشنهاد می‌شود و دلیل rule دیده می‌شود؛ AI ادعا نمی‌شود | `NOT_REVIEWED` | — |
| 3 | تصویر کاری | incomplete، Attention و problem قابل تفکیک‌اند؟ | HS/پلاک ناقص در ستون incomplete؛ تأخیر سند و allocation در Attention با معنای جدا | `NOT_REVIEWED` | — |
| 4 | مشتری‌ها و درخواست‌ها | آیا Request و Shipment یکی انگاشته نشده‌اند؟ | Requestهای لینک‌شده و Cargo حاصل نمایش داده می‌شوند؛ Customer از مالک Cargo است | `NOT_REVIEWED` | — |
| 5 | Cargo | آیا چند مشتری/چند Cargo و منبع هرکدام قابل فهم است؟ | owner، Request، مقصد و داده‌های Cargo در grouping روشن‌اند | `NOT_REVIEWED` | — |
| 6 | requested/planned/actual | آیا اختلاف مقادیر بدون مقایسه پنهان فهمیده می‌شود؟ | سه مقدار کنار هم و اختلاف آشکارند | `NOT_REVIEWED` | — |
| 7 | HS ناقص | آیا نقص با incident اشتباه نمی‌شود؟ | «HS Code هنوز تکمیل نشده» در سبک incomplete و بدون قرمز incident | `NOT_REVIEWED` | — |
| 8 | مسیر | آیا planned و actual جدا و مسیر تدریجی است؟ | tabها جدا؛ stageها و rangeهای مرجع روشن؛ stage ناقص مانع کل پرونده نیست | `NOT_REVIEWED` | — |
| 9 | شاخه مسیر | آیا divergence بدون network diagram شلوغ فهمیده می‌شود؟ | shared route تا hub و سپس شاخه Cargo A/B/C در فهرست ساده | `NOT_REVIEWED` | — |
| 10 | اجرای حمل | آیا means، unit/equipment و Carrier تفکیک شده‌اند؟ | زنجیره وسیله→واحد→Cargo و Carrier per execution واضح است | `NOT_REVIEWED` | — |
| 11 | چند execution | آیا چند کامیون/قطار در یک stage قابل مدیریت‌اند؟ | cardهای هم‌سطح با status و جزئیات ناقص مستقل | `NOT_REVIEWED` | — |
| 12 | تعریف پایه مفقود | آیا scope انسداد درست است؟ | فقط تعریف execution وابسته متوقف و Admin path نشان داده می‌شود؛ free-text bypass نیست | `NOT_REVIEWED` | — |
| 13 | تخصیص | آیا رابطه چندبه‌چند Cargo و unit قابل فهم است؟ | دو نمای Cargo-first و unit-first، Customer owner و مقدار دیده می‌شوند | `NOT_REVIEWED` | — |
| 14 | partial allocation | آیا ادامه مجاز ولی هشدار روشن است؟ | ۸۰/۹۰ و ۱۰ باقیمانده آشکار؛ CTA تکمیل دارد | `NOT_REVIEWED` | — |
| 15 | over-allocation | آیا خطا واقعاً مسدود است؟ | در modal مقدار ۱۱ وارد شود؛ خطای inline نشان داده و state تغییر نمی‌کند | `NOT_REVIEWED` | — |
| 16 | انتقال Cargo | آیا تغییر به‌جای ویرایش گذشته مدل شده؟ | from/to/quantity/point/time/reason گرفته و history قبلی قابل دستیابی است | `NOT_REVIEWED` | — |
| 17 | اسناد | آیا contextual و all documents هر دو قابل فهم‌اند؟ | scope Cargo/unit/stage/delivery و visibility جدا؛ filter و نمای all موجود است | `NOT_REVIEWED` | — |
| 18 | Timeline | آیا روایت عملیات خوانا و غیرخام است؟ | رخدادهای معنادار، outcome و grouping؛ raw event dump نیست | `NOT_REVIEWED` | — |
| 19 | reported location | آیا ادعای GPS/LIVE حذف شده؟ | location، occurrence/update time و source با «گزارش عملیاتی» دیده می‌شود | `NOT_REVIEWED` | — |
| 20 | correction | آیا تاریخچه بدون حذف حفظ شده؟ | گزارش قدیمی «بعداً اصلاح شد» و گزارش معتبر فعلی مشخص‌اند | `NOT_REVIEWED` | — |
| 21 | مشکل/پیگیری | آیا Problem، Action و Attention معناهای جدا دارند؟ | impact، متن داخلی، پیام امن و follow-up/SLA از هم جدا هستند | `NOT_REVIEWED` | — |
| 22 | تحویل | آیا partial delivery و evidence روشن‌اند؟ | ۶۰ تهران + ۴۰ قزوین و evidence مستقل؛ remaining قابل فهم است | `NOT_REVIEWED` | — |
| 23 | چندمشتری | آیا تکمیل A Shipment را نمی‌بندد؟ | A تحویل‌شده، B در حمل، C در گمرک و Shipment هنوز باز | `NOT_REVIEWED` | — |
| 24 | Closure | آیا کنترل پایان پرونده واضح و سخت‌گیرانه است؟ | دو requirement باز، نتیجه BLOCKED و راه رفع؛ Expert bypass ندارد | `NOT_REVIEWED` | — |

## ۳. چک‌پوینت‌های Customer A

در role switch، «مشتری A» را انتخاب و سپس viewport را روی حدود ۳۹۰ پیکسل نیز مرور کنید.

| # | صفحه/Context | سؤال Product | رفتار مورد انتظار | نتیجه reviewer | یادداشت |
|---:|---|---|---|---|---|
| 25 | خلاصه مشترک | آیا اشتراک حمل شفاف اما آرام است؟ | پیام shared Shipment روشن و بدون نمایش identity دیگران | `NOT_REVIEWED` | — |
| 26 | location و ETA | آیا Customer اطلاعات صادقانه می‌گیرد؟ | reported location، source، time و ETA range؛ بدون GPS/LIVE | `NOT_REVIEWED` | — |
| 27 | privacy | آیا هیچ fact خصوصی B/C دیده می‌شود؟ | نام، Cargo، quantity، document، علت خصوصی و delivery دیگران غایب‌اند | `NOT_REVIEWED` | — |
| 28 | issue message | اگر متن Expert خالی باشد، آیا Customer بی‌اطلاع نمی‌ماند؟ | safe default notice بدون توضیح داخلی نمایش داده می‌شود | `NOT_REVIEWED` | — |
| 29 | Cargo/Documents/Delivery | آیا projection فقط دارایی A است؟ | Cargo A، اسناد مجاز A و deliveryهای A | `NOT_REVIEWED` | — |
| 30 | Timeline | آیا timeline مشتری ساده، صادقانه و privacy-safe است؟ | milestone، correction و outcome مجاز؛ بدون raw/internal data | `NOT_REVIEWED` | — |
| 31 | موبایل 390px | آیا UI صرفاً desktop کوچک‌شده نیست؟ | stacking اولویت‌دار، bottom nav، بدون horizontal overflow | `NOT_REVIEWED` | — |

## ۴. چک‌پوینت‌های Organization Admin

| # | صفحه/Context | سؤال Product | رفتار مورد انتظار | نتیجه reviewer | یادداشت |
|---:|---|---|---|---|---|
| 32 | Reference Definitions | آیا central catalog و activation سازمان قابل فهم است؟ | تعریف مرکزی/سازمانی، state فعال و history concept؛ Expert bypass ندارد | `NOT_REVIEWED` | — |
| 33 | Route Time References | آیا movement و stop جدا و versioned هستند؟ | route stage + mode، current version، تاریخ اثر و history جدا | `NOT_REVIEWED` | — |
| 34 | Actual comparison | آیا comparison فقط پیشنهاد است؟ | actual ۹–۱۱ در برابر reference ۶–۸، CTA بازبینی؛ تغییر خودکار ندارد | `NOT_REVIEWED` | — |
| 35 | Closure Requirements | آیا general و mode-specific ترکیب می‌شوند؟ | دو گروه جدا با version/effective date؛ مثال‌ها universal اعلام نشده‌اند | `NOT_REVIEWED` | — |
| 36 | Closure Exception | آیا مسیر واقعاً استثنایی و audit‌شده است؟ | missing requirement، reason، approver، time، رد/تصویب؛ requirement PASS کاذب نمی‌شود | `NOT_REVIEWED` | — |

## ۵. مرور state و کیفیت طراحی

دکمه «حالت‌های رابط» را باز کنید و Normal، Loading، Empty، Error، Denied و Stale را ببینید.

| # | سؤال کیفیت | معیار تصمیم | نتیجه reviewer | یادداشت |
|---:|---|---|---|---|
| 37 | آیا Expert overwhelmed است؟ | کار فعلی و next action غالب‌اند؛ جزئیات عمیق عندالنیاز | `NOT_REVIEWED` | — |
| 38 | آیا incomplete از problem جداست؟ | واژه، رنگ، icon و اثر هرکدام مستقل است | `NOT_REVIEWED` | — |
| 39 | آیا history پیدا می‌شود ولی صفحه را اشغال نمی‌کند؟ | summary در primary view، detail/history قابل بازشدن | `NOT_REVIEWED` | — |
| 40 | آیا state فقط با رنگ بیان نشده؟ | هر state متن/marker دارد | `NOT_REVIEWED` | — |
| 41 | آیا stale نبود هشدار را سالم جلوه نمی‌دهد؟ | timestamp و هشدار صریح کاهش اطمینان | `NOT_REVIEWED` | — |
| 42 | آیا design فراتر از سناریو scale می‌کند؟ | grouping، filter و hierarchy به‌جای card بی‌قاعده | `NOT_REVIEWED` | — |
| 43 | آیا terminology طبیعی و عملیاتی است؟ | فعل‌های کاربرمحور، نه نام‌های دیتابیسی | `NOT_REVIEWED` | — |

## ۶. تصمیم‌های لازم در پایان جلسه

برای هر مورد DN-01 تا DN-09 در Blueprint یکی از حالت‌های «تصمیم گرفته شد»، «نیازمند گزینه‌های بیشتر» یا «خارج از نسخه» ثبت شود. موافقت کلی با Prototype مجوز پیاده‌سازی این موارد نیست؛ approval باید proposal مشخص، scope و owner را نام ببرد.

## ۷. ثبت نتیجه انسانی

تا زمان اجرای واقعی جلسه:

`UX_PRODUCT_OWNER_REVIEW=NOT_RUN`  
`HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN`

بازبینی browser خودکار و تصویری فقط سلامت Prototype و presentation را پشتیبانی می‌کند؛ جای Product Owner approval را نمی‌گیرد.


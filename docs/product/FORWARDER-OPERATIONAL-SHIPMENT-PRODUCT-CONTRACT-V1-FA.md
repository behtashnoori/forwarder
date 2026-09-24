# قرارداد محصول پرونده حمل عملیاتی Forwarder — نسخه ۱

## ۱. شناسنامه و وضعیت

| فیلد | مقدار |
| --- | --- |
| شناسه مرجع | `FORWARDER-OPERATIONAL-SHIPMENT-PRODUCT-CONTRACT-V1-FA` |
| وضعیت مرجع | `ACTIVE / CANONICAL PRODUCT REFERENCE` |
| خط مبنای حاکم | `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL` |
| مرجع تصویب | مأموریت صریح Product Owner برای «Operational Shipment Product Contract v1» |
| مبنای مخزن پیش از مأموریت | `48833131073d4b5c0a5229550e4391abe44e5704` روی `integration/golden-controlled` |
| نوع تغییر | تعریف و تثبیت Product target؛ فقط مستندات و مراجع |
| وضعیت رفتارهای این قرارداد | `APPROVED TARGET_PHASE3 / NOT_IMPLEMENTED` مگر آنکه در بخش ۲۲ صریحاً خلاف آن ثبت شده باشد |
| وضعیت Product validation | `EVIDENCE_PENDING` |
| وضعیت Release | `RELEASE_READY=NO` |
| اثر بر Journey | `JOURNEY_IMPACT=NEW_JOURNEY_REQUIRED`؛ `NEW_JOURNEY=FWD-J09` |

این سند معنای مصوب محصول برای پرونده حمل عملیاتی را پیش از طراحی UX فاز ۳ تثبیت می‌کند. ایجاد این سند به معنی پیاده‌سازی، آزمون، پذیرش انسانی، Release یا تغییر Production نیست. هرجا از عبارت «سیستم باید» استفاده می‌شود، منظور **رفتار هدف مصوب فاز ۳** است، نه ادعای وجود آن در محصول فعلی.

## ۲. هدف، دامنه و مرز مأموریت

هدف این قرارداد آن است که کارشناس حمل، مشتری و مدیر سازمان درباره یک پرونده حمل پیچیده، یک معنای مشترک داشته باشند؛ به‌ویژه وقتی چند درخواست، چند مشتری، چند کالا، چند مرحله مسیر، چند وسیله و ظرف حمل و چند شرکت حمل‌کننده درگیرند.

در دامنه این قرارداد:

- معنای محصولی پرونده حمل، کالا، مسیر، تخصیص، اسناد، حریم خصوصی، Timeline، موقعیت گزارش‌شده، ETA، تحویل و بستن پرونده تعریف می‌شود؛
- رفتار هدف فاز ۳ از محصول فعلی جدا می‌شود؛
- سفر حیاتی جدید `FWD-J09` تعریف می‌شود؛
- تصمیم‌های Product Owner به مرجع قابل ردیابی تبدیل می‌شوند.

خارج از دامنه:

- کد backend یا frontend؛
- طراحی schema، ORM، API یا migration؛
- طراحی صفحه، Wireframe یا Prototype؛
- تغییر Runtime، داده، Permission یا رفتار Production؛
- Release، Deployment یا دسترسی Production؛
- تصمیم‌های باز بخش ۲۵.

مرحله این مأموریت `M0/M1/M2` و سطح سخت‌گیری آن `Level B` است. مسیر قابلیت `Astra` انتخاب شده، چون مأموریت چند مرجع متعارض، تصمیم‌های وابسته و بار آشتی مرجع بالایی دارد. این انتخاب اختیار محصولی تازه ایجاد نمی‌کند.

## ۳. اصول مصوب محصول

1. **درخواست حمل با پرونده حمل یکی نیست.** Request نیاز تجاری مشتری است؛ Shipment پرونده اجرای واقعی عملیات است.
2. **چندمشتری‌بودن از کالاها به دست می‌آید.** خود Shipment به فهرست عضویت اصلی مشتریان تبدیل نمی‌شود؛ هر Cargo مالک مشتری خود را دارد.
3. **حقیقت جاری و تاریخچه معنادار با هم حفظ می‌شوند.** اصلاح نباید گذشته را بی‌صدا بازنویسی کند.
4. **اطلاعات می‌تواند تدریجی کامل شود.** ناقص‌بودن اطلاعات به‌تنهایی مشکل عملیاتی نیست.
5. **برنامه و واقعیت جدا هستند.** مقدار، مسیر، زمان و ETA برنامه‌ریزی‌شده با واقعیت جایگزین یا پاک نمی‌شوند.
6. **حقیقت عملیاتی می‌تواند مشترک باشد؛ دید مشتری محدود به همان مشتری است.**
7. **دامنه یک سند با مجوز دیدن آن یکی نیست.**
8. **پیچیدگی باید در مدل سیستم باشد، نه در ذهن کاربر.**
9. **شروع انعطاف‌پذیر، اجرای هدایت‌شده و بستن کنترل‌شده است.**
10. **رفتار هدف این سند تا زمان Build و Qualification، پیاده‌شده تلقی نمی‌شود.**

## ۴. واژه‌های محصولی

| مفهوم | واژه ساده در این سند | معنی |
| --- | --- | --- |
| Shipment | پرونده / عملیات حمل | پرونده اجرای واقعی حمل از برنامه‌ریزی تا تحویل و بستن |
| Cargo | کالا / بار داخل پرونده حمل | یک قلم یا مقدار معنادار که به یک مشتری مشخص تعلق دارد |
| Route Leg | مرحله مسیر | یک بخش از مسیر یا عملیات میان دو نقطه یا دو وضعیت مهم |
| Transport Means | وسیله حمل | چیزی که حرکت را انجام می‌دهد؛ مانند کامیون، قطار، کشتی یا هواپیما |
| Transport Equipment / Load Unit | واحد / ظرف حمل | چیزی که کالا داخل یا روی آن نگهداری یا سازمان‌دهی می‌شود؛ مانند کانتینر، تریلر، واگن یا تانک |
| Carrier | شرکت حمل‌کننده | مجری حمل یک وسیله در یک مرحله مسیر؛ نه مالک پرونده |
| Operational Exception | مشکل عملیاتی | وضعیت غیرعادی دارای اثر معنادار که نیاز به رسیدگی دارد |
| Action | پیگیری عملیاتی | کار مشخص برای رسیدگی به موضوع عملیاتی |
| Attention | مورد نیازمند توجه / هشدار عملیاتی | نشانه مشتق‌شده برای کمک به اولویت‌بندی |

این سند Product Contract است؛ نام جدول، رابطه ORM یا شکل graph پایگاه داده تعیین نمی‌کند.

## ۵. بازیگران و اختیار

| بازیگر | اختیار هدف در این قرارداد | مرز |
| --- | --- | --- |
| Transport Expert | ایجاد و ساختاربندی پرونده، تکمیل تدریجی اطلاعات، برنامه‌ریزی و اجرای عملیات، ثبت گزارش، مشکل، پیگیری، تحویل و آماده‌سازی برای بستن | نمی‌تواند الزام بستن را خودسرانه دور بزند یا داده پایه تعریف‌نشده را با free text جایگزین کند |
| Organization Admin | فعال‌سازی/تعریف مراجع سازمانی، تعیین مرجع زمان مسیر و checklist بستن، انتقال استثنایی مالک پرونده و تصویب استثنای بستن | اختیار فقط در سازمان خود و همراه دلیل، زمان و history؛ مجری روزانه همه پرونده‌ها نیست |
| Platform Admin | اداره catalog مرکزی و بررسی امکان تبدیل تعریف سازمانی به تعریف قابل استفاده سراسری | promotion خودکار نیست و اختیار عملیاتی Tenant ایجاد نمی‌کند |
| Customer | دیدن وضعیت، کالا، سند، Timeline، تحویل و اثرهای مجاز مربوط به خود | هویت، کالا، سند، علت خصوصی، ارتباط داخلی یا تحویل مشتری دیگر را نمی‌بیند |
| Carrier | اجرای حمل مربوط به وسیله و مرحله مسیر خود | مالک Shipment یا اطلاعات سایر مشتریان نیست |
| Driver | ارائه اطلاعات سبک در صورت نیاز | مدیریت تفصیلی راننده و Driver Portal خارج از فاز ۳ است |

## ۶. ساختار Shipment، Cargo، Customer و Request

ساختار مصوب:

```text
پرونده حمل
├── کالا A1 ← مشتری A ← درخواست A (در صورت وجود)
├── کالا A2 ← مشتری A ← درخواست A (در صورت وجود)
├── کالا B1 ← مشتری B ← درخواست B (در صورت وجود)
└── کالا C1 ← مشتری C ← درخواست C (در صورت وجود)
```

قواعد:

- یک Shipment می‌تواند Cargo ناشی از چند Request و چند Customer داشته باشد.
- هر Cargo دقیقاً Customer attribution خود را حفظ می‌کند.
- Cargo باید Request منبع خود را، هرجا وجود دارد، حفظ کند.
- Cargo هویت و history عملیاتی خود را دارد.
- چندمشتری‌بودن Shipment از مجموعه Customerهای Cargoهای آن مشتق می‌شود؛ یک فهرست مستقل و اصلی «اعضای مشتری Shipment» مبنای معنا نیست.
- lineage تجاری حذف نمی‌شود و `Request ≠ Shipment` برقرار می‌ماند.
- Shipment مستقیمِ مجاز می‌تواند بدون Request ساختگی وجود داشته باشد؛ این قاعده، attribution مشتری Cargo را حذف نمی‌کند.

## ۷. اطلاعات استاندارد Cargo

Cargo فقط شرح آزاد نیست. مدل هدف باید در سطح محصول از این اطلاعات پشتیبانی کند:

- مالک مشتری؛
- شرح کالا؛
- دسته/نوع کنترل‌شده کالا؛
- HS Code؛
- مقدار و واحد اندازه‌گیری کنترل‌شده؛
- نوع بسته‌بندی؛
- وزن و حجم، هرجا معلوم است؛
- مبدا مرتبط، هرجا لازم است؛
- مقصد؛
- اطلاعات اختیاری تکمیلی.

HS Code و داده‌های استاندارد مهم‌اند، اما ممکن است هنگام ایجاد اولیه معلوم نباشند. نبود آن‌ها باید به‌عنوان اطلاعات ناقص دیده شود، نه دلیلی برای توقف بی‌مورد کار اولیه. این داده می‌تواند در نقطه‌ای که عملیات، گمرک یا سند واقعاً آن را لازم دارد اجباری شود. نقطه دقیق الزام، catalog seed و دامنه عمیق Customs در این سند تعیین نمی‌شود. اصلاح واقعیت Cargo باید history داشته باشد.

## ۸. مقدار Cargo: درخواستی، برنامه‌ریزی‌شده و واقعی

سه حقیقت جدا حفظ می‌شوند:

| نوع | پرسش |
| --- | --- |
| `REQUESTED` | مشتری در ابتدا چه مقدار درخواست کرده است؟ |
| `PLANNED` | عملیات چه مقدار را برای جابه‌جایی برنامه‌ریزی کرده است؟ |
| `ACTUAL` | در عمل چه مقدار جابه‌جا یا تحویل شده است؟ |

برای نمونه، `Requested=100`، `Planned=90` و `Actual=87` سه واقعیت معتبرند. هیچ‌کدام دیگری را overwrite نمی‌کند. lifecycle فنی و جزئیات رابطه allocation برنامه‌ای با allocation واقعی، تصمیم طراحی بعدی است.

## ۹. تخصیص Cargo

- یک Cargo می‌تواند میان چند وسیله یا واحد/ظرف حمل تقسیم شود.
- یک وسیله یا واحد حمل می‌تواند Cargo چند Customer را حمل کند.
- تخصیص بیش از مقدار قابل استفاده مربوطه باید مسدود شود.
- تخصیص ناقص در دوره آماده‌سازی مجاز است.
- باقی‌مانده تخصیص‌نیافته باید آشکار باشد؛ برای نمونه «۲۰ کارتن هنوز تخصیص نیافته است».
- تغییر یا انتقال تخصیص، عملیات معنادار است و نباید با ویرایش خام history نمایش داده شود.
- UOM ناسازگار بدون قاعده مصوب تبدیل با هم جمع نمی‌شود.

این بخش معنی محصول را تصویب می‌کند؛ روش transaction، locking، precision یا schema را تعیین نمی‌کند.

## ۱۰. مسیر برنامه‌ریزی‌شده و مسیر واقعی

- Shipment می‌تواند با اطلاعات مسیر ناقص شروع شود.
- Transport Expert مسیر را تدریجی کامل می‌کند.
- Planned Route بیان انتظار عملیات است.
- Actual Route بیان اتفاق واقعی است.
- Actual Route، Planned Route را پاک نمی‌کند.
- اصلاح رسمی برنامه نیز باید نسخه/دلیل قابل بازیابی داشته باشد.
- تغییر مسیر به‌خودی‌خود مشکل عملیاتی نیست: `ROUTE_DEVIATION ≠ EXCEPTION`.
- انحراف وقتی مشکل عملیاتی می‌شود یا مشکل ایجاد می‌کند که اثر معناداری مانند تأخیر، ریسک یا نیاز به پیگیری داشته باشد.

## ۱۱. مسیر شاخه‌دار و مقصدهای متفاوت

Cargoهای یک Shipment مشترک می‌توانند بخشی از مسیر را با هم طی کنند و مقصدهای نهایی متفاوت داشته باشند:

```text
مسیر مشترک ← ایران
              ├── Cargo A ← تهران
              ├── Cargo B ← قزوین
              └── Cargo C ← کرج
```

محصول هدف نباید برای همه Cargoها یک مقصد نهایی خطی و واحد فرض کند. شکل graph یا schema مسیر در این مأموریت تصمیم‌گیری نمی‌شود.

## ۱۲. وسیله حمل، واحد/ظرف حمل و شرکت حمل‌کننده

**وسیله حمل** حرکت را انجام می‌دهد: کامیون، قطار، کشتی یا هواپیما.

**واحد/ظرف حمل** Cargo را نگه می‌دارد یا سازمان‌دهی می‌کند: کانتینر، تریلر/نیمه‌تریلر، واگن، تانک یا Load Unit کنترل‌شده.

نمونه:

```text
قطار ← واگن ← کانتینر ← Cargo
```

یک کانتینر می‌تواند ابتدا با کامیون، سپس با ریل و بعد با کامیون دیگری حرکت کند. بنابراین Means و Equipment در یک مفهوم `Vehicle` ادغام نمی‌شوند.

اجرای حمل به Route Leg تعلق دارد، نه به یک فیلد وسیله روی کل Shipment. یک مرحله مسیر می‌تواند هم‌زمان چند وسیله داشته باشد و Cargo میان آن‌ها توزیع شود. هر وسیله در همان مرحله می‌تواند Carrier خود را داشته باشد. یک مرحله ممکن است چند Carrier داشته باشد. Carrier مجری است، نه مالک Shipment.

## ۱۳. تکمیل تدریجی اطلاعات

اطلاعات ممکن است به‌تدریج برسد: شناسه وسیله، Carrier، مسیر میانی، HS Code یا سند. سیستم هدف نباید آغاز کار را فقط به دلیل نبود داده‌ای که در آن نقطه اختیاری یا آینده است مسدود کند.

```text
INCOMPLETE_INFORMATION ≠ OPERATIONAL_PROBLEM
```

UX باید این دو را متفاوت نشان دهد. «پلاک هنوز دریافت نشده» با «تأخیر سه‌روزه در مرز» یک وضعیت نیست.

## ۱۴. اسناد: زمینه، visibility و privacy

سند می‌تواند به کل Shipment، یک Cargo، یک وسیله/ظرف حمل، یک Route Leg، یک Delivery یا زمینه عملیاتی مصوب دیگری مربوط باشد.

دو پرسش جدا هستند:

1. این سند درباره چیست؟
2. چه کسی اجازه دیدن آن را دارد؟

ارتباط سند با کامیون یا کانتینر مشترک، آن را خودکار برای همه Customerهای حاضر در آن وسیله قابل مشاهده نمی‌کند.

مشتری فقط این موارد را می‌بیند:

- سند متعلق به Cargo/Customer خودش؛
- سند مشترکی که صریحاً برای Customer visibility مجاز شده است؛
- مدرک Delivery مربوط به Cargo خودش.

Invoice، Packing List، Cargo document، ارتباط خصوصی یا سند محافظت‌شده Customer دیگر و هر سند Internal-only نباید افشا شود. نسخه، اصلاح، جایگزینی و history معنادار سند حفظ می‌شود. جزئیات action matrix مدیریت فایل که با انتقال استثنایی مالک Shipment تغییر می‌کند، برای طراحی بعدی باز است و از این قرارداد استنباط نمی‌شود.

## ۱۵. اصل حریم خصوصی چندمشتری

اصل اصلی:

> حقیقت عملیاتی ممکن است مشترک باشد؛ دید Customer باید customer-scoped بماند.

Customer می‌تواند به زبان ساده بداند که «این حمل با بار سایر مشتریان به‌صورت مشترک انجام می‌شود». اما نباید هویت، شرح یا مقدار Cargo، اسناد، علت خصوصی مشکل، ارتباط داخلی یا اطلاعات Delivery مشتری دیگر را ببیند.

اگر مشکل Customer B بر وسیله مشترک اثر گذاشته و Customer A نیز متأثر است، Customer A فقط اثر امن را می‌بیند؛ برای نمونه «تأخیر عملیاتی ثبت شده است»، نه علت خصوصی «مدارک Customer B ناقص است».

یک مشکل می‌تواند توضیح داخلی و توضیح customer-facing جدا داشته باشد. اگر اثر بر Customer وجود دارد اما توضیح customer-facing هنوز نوشته نشده است، هدف محصول این است که پیام عمومی امن و deterministic مانند «یک مشکل عملیاتی در حمل ثبت شده و در حال پیگیری است» نمایش داده شود. catalog دقیق پیام و localization در طراحی بعدی تعیین می‌شود.

Customer نتیجه‌محور می‌بیند؛ مانند «در حال پیگیری»، «مدرک موردنیاز دریافت شد» یا «حمل ادامه پیدا کرد». تماس‌ها، یادداشت‌های کارکنان و گفت‌وگوی داخلی کامل به Customer داده نمی‌شود.

## ۱۶. Public Tracking و Customer Account

هدف Product فاز ۳:

- Public Tracking می‌تواند Shipment مشترک را با یک قابلیت/کد مشترک در سطح Shipment نمایش دهد، مشروط به qualification امنیتی؛
- Public Tracking فقط واقعیت مشترک، کم‌ریسک و غیرخصوصی را نشان می‌دهد؛
- نمونه داده مجاز بالقوه شامل وضعیت کلی مجاز، مسیر اصلی ساده، آخرین موقعیت عملیاتی گزارش‌شده و حالت کلی تأخیر است؛
- داده Cargo، سند یا علت خصوصی Customer در Public Tracking قرار نمی‌گیرد؛
- Customer Account همان حقیقت عملیاتی را با projection احرازشده و مخصوص همان Customer نشان می‌دهد.

این تصمیم، Public Tracking فعلی را تغییر نمی‌دهد و پیاده‌سازی امنیتی، capability format یا allowlist جدید را مجاز نمی‌کند.

## ۱۷. Timeline مشتری و گزارش موقعیت

Customer Timeline باید ساده، کم‌حجم، باکیفیت و privacy-safe باشد؛ یک روایت محصولی است، نه log فنی خام. رخدادهای مجاز می‌تواند شامل بارگیری، شروع حرکت، موقعیت گزارش‌شده، تأخیر، پیشرفت پیگیری، رفع مشکل، milestone مرزی/گمرکی و تحویل باشد.

موقعیت جاری در مدل فعلی Product **GPS truth نیست**. منبع می‌تواند گزارش Carrier، راننده، تماس، email یا عملیات باشد. عبارت درست نمونه:

- آخرین موقعیت گزارش‌شده: نزدیک مرز؛
- آخرین به‌روزرسانی: ۱۴:۳۰؛
- منبع: گزارش شرکت حمل؛
- وضعیت: گزارش عملیاتی.

منبع برای Customer به شکل عمومی نشان داده می‌شود؛ جزئیات داخلی فرد یا تماس افشا نمی‌شود.

گزارش اشتباه حذف نمی‌شود. گزارش اصلاحی، گزارش قبلی را با reason/history نگه می‌دارد. اگر گزارش قبلی قبلاً به Customer نشان داده شده، Timeline به‌صورت صادقانه نشان می‌دهد که اصلاح شده است، بدون افشای blame داخلی.

GPS، provider، SLA/accuracy و live map خارج از این مأموریت‌اند. مدل هدف فقط نباید راه integration آینده GPS را ببندد.

## ۱۸. نمای مسیر Customer

Customer مسیر ساده و قابل فهم را می‌بیند: مبدا، نقاط میانی مهم، مرز/گمرک مهم، تغییر اصلی نوع حمل، مقصد و آخرین موقعیت گزارش‌شده. جزئیات داخلی غیرضروری مسیر نمایش داده نمی‌شود. تغییر مهم وسیله، mode یا equipment می‌تواند با زبان ساده در Timeline دیده شود؛ برای نمونه «محموله از حمل جاده‌ای به حمل ریلی منتقل شد».

## ۱۹. فاصله، زمان مرجع و ETA

### فاصله

- Planned Route Distance یک واقعیت مهم محصول است.
- Actual Travelled Distance فقط با evidence معتبر مسیر واقعی یا GPS قابل ادعاست.
- در نبود evidence، محصول نباید مسافت دقیق واقعی جعل کند.
- provider یا engine محاسبه فاصله تصمیم implementation آینده است.

### زمان مرجع مسیر

Organization Admin مالک reference travel timeهای سازمان است؛ این reference با SLA یکی نیست. زمان مرجع:

- برای Route Leg تعریف می‌شود؛
- می‌تواند بازه باشد؛
- versioned، effective-dated، historical و organization-scoped است؛
- زمان Movement را از Stop/Operation/Waiting جدا می‌کند؛
- می‌تواند بر اساس mode متفاوت باشد؛
- با performance واقعی مقایسه می‌شود، اما خودکار تغییر نمی‌کند.

سیستم آینده می‌تواند پیشنهاد کند «مرجع این مسیر نیاز به بازبینی دارد»، ولی فقط Organization Admin مرجع رسمی را تغییر می‌دهد. هیچ مقدار پیش‌فرضی در این سند ساخته نمی‌شود.

### ETA

Shipment هدف باید ETA پویا برای مقصد نهایی و، هرجا داده کافی است، نقطه مهم بعدی داشته باشد. وقتی کیفیت داده اجازه دقت کاذب نمی‌دهد، بازه استفاده می‌شود. ETA قبلی history می‌ماند. Customer زمان آخرین به‌روزرسانی و مبنای قابل فهم برآورد را می‌بیند. الگوریتم دقیق و predictive AI خارج از دامنه است.

## ۲۰. Catalog مرکزی و تنظیمات سازمان

مدل مصوب:

```text
Central System Catalog
        ↓ انتخاب/فعال‌سازی
Organization Admin
        ↓ استفاده
Transport Expert
```

catalogهای قابل حاکمیت می‌تواند mode، نوع وسیله، نوع equipment/load unit، نوع کانتینر، UOM، packaging، Cargo category، document type، geography/logistics location و HS reference را پوشش دهد.

قواعد:

- از استانداردهای شناخته‌شده مانند HS، UN/LOCODE، UOM استاندارد و مفاهیم ISO container فقط پس از qualification استفاده می‌شود؛
- هیچ seed گسترده و تأییدنشده‌ای در این مأموریت ایجاد نمی‌شود؛
- Transport Expert در جریان عادی Shipment نوع پایه دلخواه با free text نمی‌سازد؛
- اگر تعریف لازم موجود یا فعال نیست، Expert منتظر اقدام Organization Admin می‌ماند؛
- Organization Admin می‌تواند تعریف مخصوص سازمان بسازد؛ این تعریف ابتدا فقط در همان سازمان قابل استفاده است؛
- Platform Admin می‌تواند پس از review، تعریف معادل مرکزی ایجاد یا promote کند؛ promotion خودکار نیست؛
- تغییر تعریف پایه history را بازنویسی نمی‌کند و Shipment قدیمی نباید تعریف آینده را مصرف‌شده نشان دهد.

Phase 3 محصول را به سامانه دائمی fleet asset management تبدیل نمی‌کند. Admin نوع/تعریف پایه را اداره می‌کند و Expert جزئیات واقعی همان اجرای Shipment را ثبت می‌کند.

## ۲۱. تحویل

- Cargoهای یک Shipment می‌توانند مقصدهای متفاوت داشته باشند.
- یک Cargo می‌تواند در چند Delivery تحویل شود.
- هر Delivery مقدار، زمان/تاریخ، مکان و evidence مرتبط خود را حفظ می‌کند.
- Customer فقط evidence مربوط به Cargo خودش را می‌بیند.
- تحویل Cargo یک Customer، Shipment مشترک را نمی‌بندد اگر Cargo دیگر هنوز در حال اجرا، گمرک یا تحویل باشد.

## ۲۲. مالک Shipment و انتقال استثنایی

Transport Expert که Shipment را ایجاد و از نظر عملیاتی ساختاربندی می‌کند، مالک اصلی Shipment است و در حالت عادی تا پایان مسئول می‌ماند. assignmentهای قبلی Request history هستند و چند مالک Shipment ایجاد نمی‌کنند.

تصمیم جدید و مصوب این قرارداد:

- انتقال مالکیت یک جریان عادی و آزاد نیست؛
- Organization Admin فقط برای ضرورت استثنایی مانند خروج کارمند، غیبت بلندمدت یا تداوم ضروری عملیات می‌تواند مسئولیت را منتقل کند؛
- انتقال باید مالک قبلی، مالک جدید، زمان، Admin تصویب‌کننده و دلیل را حفظ کند؛
- history پاک یا بازنویسی نمی‌شود.

این تصمیم، قاعده «هیچ انتقالی مجاز نیست» در ADR-047 را **فقط در دامنه انتقال استثنایی هدف فاز ۳** supersede می‌کند. Runtime فعلی تغییر نکرده است. جزئیات permissionهای وابسته، دسترسی مالک قبلی و handoff اسناد در طراحی بعدی تعیین می‌شود و نباید از این بند حدس زده شود.

## ۲۳. تکمیل و بستن Shipment

`Delivery Complete ≠ Shipment Closed`.

پس از تحویل ممکن است اسناد، مشکل‌های عملیاتی، پیگیری‌ها، مقدار واقعی یا evidence تحویل هنوز کامل نباشند. یک مفهوم مانند «تحویل کامل / تکمیل پرونده در انتظار» ممکن است لازم باشد، اما نام status فنی در این مأموریت تعیین نمی‌شود.

Organization Admin قواعد closure checklist سازمان را تعریف می‌کند. نمونه‌های احتمالی فقط برای توضیح‌اند: تعیین تکلیف همه Cargoها، ثبت actual quantity، ثبت Delivery، وجود evidence لازم، کامل‌بودن اسناد و حل مشکلات/پیگیری‌های لازم. این سند هیچ موردی را universal mandatory نمی‌کند.

Admin می‌تواند الزام‌های جداگانه modeهای road، rail، sea یا combined/multimodal را تعریف کند. در حمل ترکیبی، checklist از الزامات عمومی سازمان و modeهای قابل اعمال مشتق می‌شود؛ Expert نباید checklist را حدس بزند.

Expert نمی‌تواند الزام mandatory را دور بزند. اگر بستن با کمبود mandatory لازم است، Organization Admin استثنا را صریح تصویب می‌کند و requirement مفقود، Admin، دلیل، زمان و وضعیت/history «بستن با استثنا» ثبت می‌شود.

## ۲۴. قرارداد UX فاز ۳

اصل UX:

> پیچیدگی باید در مدل سیستم باشد، نه در ذهن کاربر.

تجربه Shipment هدایت‌شده و مرحله‌محور است، ولی wizard سخت‌گیر و مسدودکننده اطلاعات اختیاری اولیه نیست:

```text
شروع: انعطاف‌پذیر
حین اجرا: هدایت‌شده
بستن: کنترل‌شده و سخت‌گیر در الزام‌های مصوب
```

حوزه‌های مفهومی Workspace:

1. اطلاعات پایه؛
2. مشتری‌ها و درخواست‌های مرتبط؛
3. کالاها؛
4. مسیر و مراحل مسیر؛
5. وسیله/ظرف حمل و تخصیص کالا؛
6. اسناد؛
7. اجرای حمل و Timeline؛
8. مشکلات و پیگیری‌ها؛
9. تحویل‌ها؛
10. تکمیل و بستن پرونده.

UX باید سه مفهوم را روشن کند:

```text
DEFINE / SELECT → چه چیزی برای Shipment وجود دارد؟
ASSIGN / ALLOCATE → این چیزها چگونه به هم مربوط‌اند؟
CHANGE / OPERATE → چه تغییر عملیاتی معناداری رخ می‌دهد؟
```

عملیات زمینه‌دار مانند افزودن Cargo، تخصیص یا انتقال Cargo، افزودن/تغییر اجرای حمل، گزارش موقعیت، ثبت مشکل، افزودن پیگیری و ثبت Delivery بر ویرایش raw storage ترجیح دارد.

Workspace باید به‌صورت deterministic و rules-based پاسخ این پرسش‌ها را بدهد: کجای Shipment هستم؟ چه چیزی ناقص است؟ چه چیزی توجه می‌خواهد؟ قدم مفید بعدی چیست؟ AI برای این هدف تصویب نشده است.

تجربه Customer در Shipment مشترک، در محدوده مجاز، شامل وضعیت کلی، آخرین موقعیت و زمان/منبع، Timeline امن، مسیر ساده، ETA جاری و نقطه بعدی، Cargo/quantity/document/delivery خود، اثر مشکلات و نشانه ساده اشتراکی‌بودن حمل است. داده Customer دیگر نمایش داده نمی‌شود.

این سند صفحه یا navigation دقیق را طراحی نمی‌کند. مأموریت بعدی باید Wireframe/Prototype را برای review مالک محصول آماده کند.

## ۲۵. وضعیت فعلی در برابر هدف فاز ۳

برچسب‌ها:

- `CURRENT_AND_PROVEN`: رفتار فعلی با evidence موجود پشتیبانی شده است؛
- `CURRENT_PARTIAL`: بخشی از پایه فعلی وجود دارد، اما قرارداد کامل حاضر را اثبات نمی‌کند؛
- `TARGET_PHASE3`: تصمیم هدف مصوب است و هنوز پیاده/qualified نشده است؛
- `EVIDENCE_GAP`: برای ادعای فعلی مدرک کافی نیست؛
- `DECISION_NEEDED`: تصمیم صریح دیگری لازم است.

| حوزه | وضعیت | مرز ادعا |
| --- | --- | --- |
| جدایی Request و Shipment | `CURRENT_AND_PROVEN` | Journey Pack v1 آن را در سفرهای فعلی نگاشت کرده است |
| Cargo item، catalog و shared execution foundations | `CURRENT_PARTIAL` | وجود foundation، مدل یک Shipment چندمشتری و Journey جدید را ثابت نمی‌کند |
| Shipment مشترک چندمشتری از طریق Cargo attribution | `TARGET_PHASE3` | تعریف شده؛ پیاده/qualified نشده |
| Requested/Planned/Actual و allocation کامل | `TARGET_PHASE3` | lifecycle فنی باز است |
| Planned/Actual route و تاریخچه عملیاتی | `CURRENT_PARTIAL + TARGET_PHASE3` | پایه‌های رویداد/مسیر موجودند؛ مدل شاخه‌دار کامل و UX هدف نشده |
| Means/Equipment/Carrier per Route Leg | `TARGET_PHASE3` | از مدل‌های فعلی یا نام‌های legacy به‌عنوان اثبات استفاده نمی‌شود |
| Document history | `CURRENT_PARTIAL` | customer-scoped multi-customer visibility هنوز هدف است |
| Public Tracking و Customer Account چندمشتری | `TARGET_PHASE3 + EVIDENCE_GAP` | امنیت و privacy باید بعداً qualified شوند |
| Timeline و location correction | `CURRENT_PARTIAL + TARGET_PHASE3` | رویداد/موقعیت foundation دارد؛ تجربه Customer هدف اجرا نشده |
| GPS/live map | `DECISION_NEEDED / OUT_OF_SCOPE` | هیچ پیاده‌سازی مجاز نیست |
| Route distance، route time reference و dynamic ETA | `TARGET_PHASE3` | provider/algorithm تعیین نشده |
| catalog مرکزی و adoption سازمانی | `CURRENT_PARTIAL + TARGET_PHASE3` | برخی catalogها وجود دارند؛ مدل یکپارچه این سند کامل نیست |
| partial delivery و مقصدهای Cargo | `TARGET_PHASE3` | پیاده/qualified نشده |
| مالک ثابت Shipment | `CURRENT_PARTIAL` | شواهد فعلی، انتقال استثنایی هدف را پوشش نمی‌دهد |
| انتقال استثنایی مالک | `TARGET_PHASE3` | فقط تصمیم Product؛ runtime تغییر نکرده |
| closure checklist و استثنای Admin | `TARGET_PHASE3` | status/schema/rule engine تعیین نشده |
| UX هدایت‌شده و Next Best Action | `TARGET_PHASE3` | Wireframe/Prototype هنوز ساخته نشده |

برچسب‌های «Phase» در مراجع قدیمی نقشه راه تاریخی خودشان را دارند. `TARGET_PHASE3` در این سند به مأموریت هدف و UX بعدی همین قرارداد اشاره می‌کند و نباید با شماره‌گذاری تاریخی اسناد قبلی یکی فرض شود.

## ۲۶. تصمیم‌های عمداً باز و خارج از دامنه

این موارد در این قرارداد حل نمی‌شوند:

- lifecycle تفصیلی Driver و Driver Portal؛
- fleet-management دائمی؛
- Carrier Portal؛
- Finance؛
- دامنه عمیق Customs؛
- AI و predictive AI ETA؛
- GPS provider/integration، accuracy/SLA و live map؛
- business-calendar SLA semantics؛
- external Action assignee model؛
- schema فیزیکی و microservice decomposition؛
- الگوریتم دقیق ETA یا distance provider؛
- seed dataset دقیق catalogهای استاندارد؛
- taxonomy دقیق confidence برای reported location؛
- lifecycle فنی دقیق planned در برابر actual allocation؛
- permission/handoff جزئی اسناد پس از انتقال استثنایی مالک؛
- نام نهایی statusهای delivery/closure.

هرکدام در صورت لازم‌شدن، `DECISION_NEEDED` است. این سند آن را با inference حل نمی‌کند.

## ۲۷. اثر بر Journey

```text
JOURNEY_IMPACT=NEW_JOURNEY_REQUIRED
NEW_JOURNEY=FWD-J09
FWD_J09=CRITICAL_TARGET_PHASE3
FWD_J09_STATUS=DEFINED_NOT_IMPLEMENTED
```

`FWD-J01` تا `FWD-J08` حفظ شده‌اند. رفتار هدف آینده آن‌ها همگی می‌تواند از این قرارداد اثر بگیرد: پیگیری عمومی و Customer Account، تبدیل Request به Shipment، Workspace، مشکل/پیگیری، تنظیمات Admin، Control Tower و privacy/authorization. چون runtime در این مأموریت تغییر نکرده، evidence فعلی آن سفرها صرفاً با افزودن این سند stale نمی‌شود.

ابعاد چندمشتری/چندکالا و حمل ترکیبی/چندوجهی یکی نیستند. `FWD-J09` سفر چندمشتری/چندکالا است. Combined/Multimodal به‌صورت پیشنهاد مستقل `FWD-PJ-04` باقی می‌ماند و بدون تصمیم جدا Critical نمی‌شود.

سفر یکپارچه `FWD-IPJ-04` برای جریان هدف مشترک از assembly کالا تا تحویل customer-scoped و closure تعریف می‌شود و وضعیت آن `DEFINED_TARGET_NOT_RUN` است.

## ۲۸. آشتی با مراجع قبلی

| مرجع قبلی | آشتی این قرارداد |
| --- | --- |
| مدل عملیاتی Forwarder v1 | جدایی Request/Shipment، history، مسیر، اسناد و مالکیت را حفظ می‌کند؛ جزئیات باز چندمشتری را در دامنه این قرارداد حل می‌کند |
| طراحی فضای کار عملیاتی v1 | اصول context/history/attention را حفظ می‌کند؛ ساختار UX هدف این سند ورودی مأموریت طراحی بعدی است |
| ADR-046 | foundation shared execution را حفظ می‌کند؛ وجود آن اثبات Shipment چندمشتری کامل نیست |
| ADR-047 | قاعده مالک اصلی را حفظ می‌کند؛ منع مطلق انتقال فقط برای انتقال استثنایی هدف فاز ۳ supersede می‌شود |
| ADR-050 | history و management مرجع را حفظ می‌کند؛ semantics اسناد پس از انتقال owner باز می‌ماند |
| ADR-019 و ADR-040 | history، occurred/recorded time و reported-location authority را حفظ می‌کنند؛ customer timeline هدف هنوز implementation نیست |
| ADR-021/022/028/041 | foundation catalog/snapshot/governance حفظ می‌شود؛ catalog مرکزی سراسری این قرارداد نیازمند طراحی و qualification بعدی است |
| ADR-020 و ADR-023 | وضعیت تاریخی Proposed بازنویسی نمی‌شود؛ این قرارداد Product intent حریم خصوصی/تخصیص را تصویب می‌کند، نه architecture/schema implementation را |
| PDR-019 | جدایی Request Cargo از operational Cargo و Combined intent را حفظ می‌کند؛ multi-customer و Combined Journey جدا می‌مانند |

هیچ ADR یا PDR تاریخی در این مأموریت بازنویسی نمی‌شود. این جدول فقط تقدم تصمیم جدید Product Owner را در scope صریح این قرارداد ثبت می‌کند.

## ۲۹. آشتی مراجع

| مرجع | نتیجه | اقدام |
| --- | --- | --- |
| LPAF v2.7 | `NONE` | baseline فقط اعمال شده و هیچ فایل LPAF تغییر نکرده است. |
| Product Contract v1 | `CURRENT` | در مسیر canonical محصول ایجاد و از indexها قابل کشف است. |
| Journey Pack | `CURRENT / v1.1` | v1 به v1.1 تکامل یافته و مسیر جدید در `AGENTS.md` و indexها ثبت شده است. |
| `AGENTS.md` | `ALIGNED` | هر دو مرجع canonical Product را معرفی می‌کند. |
| README ریشه | `ALIGNED` | Product Contract و Journey Pack v1.1 را معرفی می‌کند. |
| Architecture Handbook و Decision Index | `ALIGNED` | هر دو مرجع و مرز current/target و supersession محدود را ثبت می‌کنند. |
| ADR/PDR تاریخی | `PRESERVED` | متن هیچ ADR/PDR بازنویسی نشده است. |

مقادیر `REFERENCE_IMPACT=UPDATE_REQUIRED` داخل مأموریت‌های قدیمی‌تر، نتیجه همان مأموریت در زمان خود و provenance تاریخی‌اند؛ با بازنویسی آن‌ها بسته نمی‌شوند. وضعیت فعلی این مأموریت پس از پیونددهی بالا:

```text
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
```

## ۳۰. Product Authority Record و آشتی PDA-07

### ۳۰.۱ نگاشت تصمیم‌های مصوب

| دامنه قرارداد | بخش‌های صریح مأموریت Product Owner |
| --- | --- |
| اصطلاحات و ساختار Shipment/Cargo/Customer/Request | ۶ تا ۸ |
| quantity، allocation و اطلاعات استاندارد Cargo | ۹ تا ۱۲ |
| planned/actual route، branching و deviation | ۱۳ تا ۱۵ |
| Means، Equipment، Route Leg، Carrier و Driver | ۱۶ تا ۱۹ |
| تکمیل تدریجی اطلاعات | ۲۰ |
| document scope، visibility و privacy | ۲۱ تا ۲۳ |
| Public Tracking، Customer Account، problem effect و پیام امن | ۲۴ تا ۲۸ |
| Customer Timeline، reported location، correction، GPS readiness و route view | ۲۹ تا ۳۴ |
| distance، reference time و ETA | ۳۵ تا ۴۲ |
| catalog مرکزی و governance سازمان | ۴۳ تا ۴۸ |
| delivery و partial completion | ۴۹ تا ۵۱ |
| owner و exceptional transfer | ۵۲ تا ۵۳ |
| completion، checklist و closure exception | ۵۴ تا ۵۸ |
| UX، guided workflow، contextual actions، next action و Customer experience | ۵۹ تا ۶۶ |
| current/target status و scope باز | ۶۷ تا ۶۸ |
| Journey Pack، `FWD-J09`، integrated/human/reference impact | ۷۰ تا ۷۹ |

این نگاشت نشان می‌دهد Product behaviorهای این قرارداد از تصمیم‌های صریح مأموریت آمده‌اند. عبارت‌های توضیحی، نمونه‌ها و ساختار سند اختیار تازه‌ای ایجاد نمی‌کنند.

### ۳۰.۲ رکورد اختیار

| فیلد | مقدار |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | فقط تعریف هدف Product در بخش‌های ۳ تا ۲۴، ایجاد `FWD-J09` و `FWD-IPJ-04` و به‌روزرسانی مراجع؛ بدون تغییر runtime |
| `DELEGATED_TECHNICAL_CHOICES` | ساختار سند، نگارش فارسی ساده، نام‌گذاری بخش‌ها، پیوندها و شکل نگاشت تصمیم‌ها |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | تمام runtime/API/UI/schema/migration/data/permission فعلی؛ evidence تاریخی؛ وضعیت Journeyهای اجرا‌نشده؛ LPAF؛ Production؛ موضوعات بخش ۲۶ |
| `DECISIONS_NEEDED` | فقط موارد بخش ۲۶ و هر رفتار Product تازه خارج از متن صریح مأموریت |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner از طریق دستور صریح همین مأموریت؛ LPAF v2.7 برای حاکمیت |
| `APPROVAL_REFERENCE` | مأموریت «Forwarder — Operational Shipment Product Contract v1 + Product Acceptance Journey Pack v1.1 + Canonical Product Reference Integration» |

### ۳۰.۳ آشتی تفاوت‌های قابل مشاهده

| تفاوت قابل مشاهده | طبقه‌بندی | دلیل |
| --- | --- | --- |
| Product targetهای جدید این قرارداد | `AUTHORIZED` | در مأموریت Product Owner به‌صورت جزئی و صریح تصویب شده‌اند |
| runtime Product | `PRESERVED` | هیچ فایل runtime، schema، migration، API یا UI تغییر نمی‌کند |
| Journey PASS یا Human PASS | `PRESERVED_AS_NOT_RUN` | هیچ اجرا یا پذیرش انسانی انجام نشده است |
| رفتار خارج از بخش‌های مصوب | `PRESERVED / DECISION_NEEDED` | این قرارداد آن‌ها را تغییر نمی‌دهد |

`VIOLATION=NONE` و `UNKNOWN_PRODUCT_CHANGE=NONE` برای دامنه مستنداتی این مأموریت؛ این نتیجه، Product Complete یا Release Ready نیست.

## ۳۱. نتیجه مرجع

```text
OPERATIONAL_SHIPMENT_PRODUCT_CONTRACT_V1=DEFINED
IMPLEMENTATION_STATUS=TARGET_PHASE3_NOT_IMPLEMENTED
JOURNEY_IMPACT=NEW_JOURNEY_REQUIRED
NEW_JOURNEY=FWD-J09
REFERENCE_RECONCILIATION=PASS
REFERENCE_IMPACT=NONE
INTEGRATED_PRODUCT_JOURNEYS=DEFINED_NOT_RUN
HUMAN_PRODUCT_WALKTHROUGH=DEFINED_NOT_RUN
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
RELEASE_READY=NO
FORWARDER_PRODUCT_CODE_CHANGED=NO
DATABASE_CHANGED=NO
MIGRATION_CHANGED=NO
PHASE_3_IMPLEMENTATION_STARTED=NO
PHASE_3_UX_IMPLEMENTATION_STARTED=NO
PRODUCTION_ACCESSED=NO
```

قدم بعدیِ مجاز پس از canonical شدن این مرجع، مأموریت مستقل **Phase 3 UX / Wireframe / Prototype Design** است؛ نه implementation.

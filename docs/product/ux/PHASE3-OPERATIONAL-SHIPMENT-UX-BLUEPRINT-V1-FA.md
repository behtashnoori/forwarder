# طرح مرجع تجربه کاربری پرونده حمل عملیاتی — فاز ۳

وضعیت: `TARGET_PHASE3_UX`  
نسخه: `1.0`  
تاریخ: `۱۴۰۵-۰۷-۰۲ / 2026-09-24`  
مبنای حاکمیتی: `LPAF 2.7`  
مبنای مخزن: `integration/golden-controlled@6d7a757d84d64afe3fe8614986a9e6900fe22fad`  
اثر بر سفرهای جاری: `JOURNEY_IMPACT=NONE`  
اعتبارسنجی سراسری محصول: `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING`  
آمادگی انتشار: `RELEASE_READY=NO`

> این سند، رفتار موجود محصول را گزارش نمی‌کند. یک مرجع هدف برای طراحی تجربه فاز ۳ است و هیچ مجوزی برای پیاده‌سازی Product، تغییر API، مدل داده، نقش، دسترسی یا چرخه‌عمر ایجاد نمی‌کند.

## ۱. قرارداد مأموریت و مرز اعتبار

هدف این طرح آن است که یک پرونده حمل مشترک، با چند مشتری، چند Cargo، مسیر چندمرحله‌ای و منشعب، چند وسیله و واحد حمل، چند Carrier، اسناد، مشکلات، پیگیری‌ها، تحویل‌ها و الزامات بستن، برای استفاده روزانه قابل‌فهم بماند. اصل محوری چنین است:

**پیچیدگی باید در مدل سیستم باشد، نه در ذهن کاربر.**

این مأموریت `Level B` و با مسیریابی `Astra` انجام شده است؛ چون دامنه چندسطحی، چندنقشی و دارای مرزهای حساس Product و privacy است. خروجی فقط طراحی، مستندات و Prototype ایزوله است.

### خارج از محدوده قطعی

- پیاده‌سازی backend، frontend runtime، route زنده یا component محصول؛
- API، مدل دامنه، پایگاه داده، schema یا migration؛
- موتور تخصیص، ETA، catalog یا closure؛
- GPS، AI، مالی، گمرک، Carrier Portal یا Driver Portal؛
- production، deployment، release یا تغییر داده واقعی؛
- اعلام PASS برای Integrated Product Journey یا بازبینی انسانی.

## ۲. منابع مرجع

این طرح با خواندن کامل منابع زیر ساخته شده است:

1. `FORWARDER-OPERATIONAL-SHIPMENT-PRODUCT-CONTRACT-V1-FA.md`
2. `FORWARDER-PRODUCT-ACCEPTANCE-JOURNEYS-V1.1-FA.md`
3. `FORWARDER-OPERATIONAL-MODEL-V1-FA.md`
4. `FORWARDER-OPERATIONAL-WORKSPACE-PRODUCT-DESIGN-V1-FA.md`
5. شواهد و مراجع جاری Workspace فازهای ۱، ۲ و ۲.۵؛ Customer Account، Quote/Request، Public Tracking و Control Tower؛ و الگوهای فعلی ناوبری و componentهای frontend.

LPAF v2.7 مرجع حاکم است؛ نسخه‌های تاریخی یا v2.6 در این مأموریت normative نیستند.

## ۳. Product Authority Record

| فیلد الزامی | رکورد این مأموریت |
|---|---|
| `AUTHORIZED_PRODUCT_CHANGES` | فقط طراحی UX، interaction و presentation برای رفتارهای ازقبل‌تصویب‌شده؛ ایجاد Blueprint، inventory، state matrix، review pack و Prototype محلی با داده ساختگی. هیچ رفتار runtime تغییر نمی‌کند. |
| `DELEGATED_TECHNICAL_CHOICES` | سلسله‌مراتب صفحه، گروه‌بندی، side navigation، tabs، progressive disclosure، drawer/modal، تراکم، visual hierarchy، responsive presentation، empty/loading/error presentation، microcopy بدون تغییر معنا، و ناوبری Prototype. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | نقش‌ها، دسترسی و privacy؛ مالکیت Customer/Cargo؛ Request در برابر Shipment؛ requested/planned/actual؛ معنای lifecycle/status/SLA؛ document visibility؛ Carrier/Driver authority؛ tracking/ETA semantics؛ catalog authority؛ closure rules؛ و همه رفتارهای production باید بدون تغییر بمانند. |
| `DECISIONS_NEEDED` | موارد بخش ۱۸؛ Prototype در آن نقاط فقط امکان و پیام تصمیم را نشان می‌دهد و هیچ معنای Product جدیدی را تصویب نمی‌کند. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner برای رفتارهای owner-reserved؛ LPAF v2.7 برای حاکمیت delivery؛ مأموریت کاربر فقط UX واگذارشده را مجاز کرده است. |
| `APPROVAL_REFERENCE` | متن مأموریت «Forwarder — Phase 3 UX / Wireframe / Clickable Prototype Design» به‌همراه Product Contract v1 و Journey Pack v1.1. |

### آشتی اختیار محصول در Verify

| طبقه | نتیجه | شاهد |
|---|---|---|
| رفتارهای ازقبل‌تصویب‌شده | `PRESERVED` | نگاشت بخش ۴ و پوشش سفرها در بخش ۱۹ |
| انتخاب‌های ارائه و تعامل | `AUTHORIZED` | موارد واگذارشده در مأموریت و همین رکورد |
| Product semantics جدید | `NONE` | Prototype هیچ API/DB/runtime ندارد |
| ابهام‌های owner-reserved | `DECISION_NEEDED` | بخش ۱۸؛ وارد baseline یا رفتار Prototype نشده‌اند |
| نقض اختیار | `NONE_FOUND` | بازبینی مسیرهای تغییر و diff نهایی |

## ۴. واقعیت‌ها، فرض‌ها و مجهولات

### `FACT`

- Customerهای یک Shipment از مالکیت Cargo نتیجه می‌شوند؛ Shipment فهرست مستقل عضویت مشتری ندارد.
- Request همان Shipment نیست و چند Request می‌توانند به یک Shipment متصل شوند.
- مقادیر requested، planned و actual سه مفهوم جدا هستند.
- یک Cargo می‌تواند بین چند واحد حمل تقسیم شود و یک واحد حمل می‌تواند Cargo چند مشتری را داشته باشد.
- over-allocation مسدود و partial allocation مجاز ولی آشکار است.
- وسیله حمل، واحد/ظرف حمل و Carrier سه مفهوم جدا هستند؛ Carrier به اجرای واقعی Route Leg تعلق دارد.
- مسیر planned و actual جدا هستند و مسیر می‌تواند پس از بخش مشترک منشعب شود.
- incomplete information با operational problem یکی نیست.
- زمینه سند با visibility آن یکی نیست.
- موقعیت جاری، گزارش عملیاتی با منبع و زمان است؛ GPS یا LIVE نیست.
- اصلاح، گزارش قبلی را حذف نمی‌کند.
- delivery می‌تواند جزئی باشد؛ تکمیل delivery یک مشتری Shipment مشترک را خودکار نمی‌بندد.
- Expert الزام closure را bypass نمی‌کند؛ Organization Admin می‌تواند استثنای آشکار، دلیل‌دار و audit‌شده را تصویب کند.

### `ASSUMPTION` صرفاً نمایشی

- Shipment ساختگی `S-100`، نام‌ها، کدها، مقادیر، مسیر، زمان‌ها و statusهای سناریو فقط برای قابل‌نقد کردن UI انتخاب شده‌اند.
- ۱۱ مقصد ناوبری Expert، URL یا ماژول runtime نیستند؛ گروه‌بندی پیشنهادی تجربه‌اند.
- priority و ترتیب «قدم بعدی» در Prototype با قانون نمونه ثابت تعیین شده و موتور نهایی محسوب نمی‌شود.
- requirementهای closure نمایش‌داده‌شده مثال سناریو هستند، نه الزام عمومی همه سازمان‌ها.

### `UNKNOWN`

- جزئیات قرارداد runtime، permission matrix نهایی و lifecycle فاز ۳ تا مأموریت implementation planning تعیین نشده است.
- readiness فنی و انسانی سفرهای فاز ۳ سنجیده نشده است.
- Product Owner هنوز هیچ screen، microcopy یا interaction این طرح را تأیید نکرده است.

## ۵. پرسوناها و مدل ذهنی روزانه

### کارشناس حمل

کارشناس یک «پرونده زنده» را اداره می‌کند، نه مجموعه‌ای از رکوردهای دیتابیس. او می‌خواهد بداند پرونده کجاست، چه چیز واقعی رخ داده، چه چیزی ناقص است، چه موردی واقعاً مشکل دارد و اقدام بعدی چیست. جریان کار او:

`START: منعطف → EXECUTION: هدایت‌شده → CLOSURE: کنترل‌شده`

شروع با داده ناقص ممکن است؛ اجرای عملیات با guidance و context پیش می‌رود؛ بستن پرونده فقط پس از کنترل الزامات مجاز است.

### مشتری احراز هویت‌شده

مشتری به پاسخ ساده و قابل‌اعتماد نیاز دارد: بار خودش کجاست، ETA چیست، چه رخدادی روی او اثر دارد، اسناد و تحویل خودش کدام‌اند. او نباید ساختار داخلی یا داده مشتری دیگر را ببیند.

### مدیر سازمان

مدیر، catalogهای قابل استفاده سازمان، زمان مرجع نسخه‌دار مسیر، الزام‌های closure و استثناهای closure را کنترل می‌کند. او operator روزمره Shipment نیست.

## ۶. معماری اطلاعات

### تصمیم اصلی

یک Shipment Workspace واحد با context ثابت پرونده و ناوبری جانبی Expert طراحی شده است. اطلاعات حیاتی—مرحله فعلی، آخرین موقعیت گزارش‌شده، ETA، نقطه مهم بعدی و تازگی—در header پرونده هنگام جابه‌جایی بین بخش‌ها حفظ می‌شوند.

این الگو بر ده صفحه جدا یا wizard صلب ترجیح داده شد، زیرا:

- context switching و بن‌بست کم می‌شود؛
- بخش‌های ناقص مانع کار مستقل نمی‌شوند؛
- برنامه‌ریزی، اجرا و کنترل در یک پرونده قابل‌بازیابی‌اند؛
- هر سطح فقط اطلاعات مرتبط را نشان می‌دهد؛
- history با summary در صفحه و detail عندالنیاز در دسترس است.

### الگوهای تعامل

| الگو | کاربرد |
|---|---|
| Side navigation | جابه‌جایی Expert بین سطح‌های اصلی، همراه شمارنده و state |
| Header ثابت Shipment | حفظ context عملیاتی در تمام سطح‌ها |
| Tabs محدود | planned/actual، contextual/all documents و نماهای همان مفهوم |
| Inline panel | Attention، incomplete و blockerهایی که باید در همان context دیده شوند |
| Modal/Drawer | اقدام کوتاه و contextual مانند تخصیص، انتقال، ثبت موقعیت یا تحویل |
| Detail view | جدول‌های پرتراکم، history و evidence بدون شلوغ کردن نمای اصلی |
| Bottom navigation مشتری | دسترسی یک‌دستی موبایل به خلاصه، Cargo، اسناد، timeline و delivery |

### سطح‌های Expert

1. نمای کلی
2. مشتری‌ها و درخواست‌ها
3. Cargoها
4. مسیر
5. اجرای حمل
6. تخصیص Cargo
7. اسناد
8. اجرا و Timeline
9. مشکلات و پیگیری‌ها
10. تحویل‌ها
11. تکمیل و بستن

این فهرست screen model است؛ الزاماً یازده URL نیست.

## ۷. الگوی «تعریف → تخصیص → تغییر»

| لایه | سؤال کاربر | نمونه اقدام | قاعده ارائه |
|---|---|---|---|
| `DEFINE / SELECT` | چه چیزی وجود دارد؟ | اتصال Request، افزودن Cargo، تعریف planned route، انتخاب نوع approved | هویت، منبع و incomplete بودن روشن است |
| `ASSIGN / ALLOCATE` | چه چیز به چه چیز تعلق دارد؟ | انتساب Carrier به execution، تخصیص Cargo به واحد حمل | رابطه‌ها در هر دو جهت دیده می‌شوند؛ مجموع و باقیمانده آشکار است |
| `CHANGE / OPERATE` | در واقعیت چه تغییری رخ داد؟ | انتقال Cargo، ثبت موقعیت، مشکل، پیگیری، delivery | تغییر به‌صورت event/action ثبت می‌شود؛ مقدار قبلی پاک نمی‌شود |

دکمه‌ها به زبان عملیات نوشته شده‌اند—«افزودن کالا»، «تخصیص کالا»، «انتقال کالا»، «ثبت موقعیت»—نه «ویرایش رکورد».

## ۸. Shipment Overview و هدایت مرحله‌ای

نمای Overview در یک نگاه پاسخ می‌دهد:

- وضعیت کلی: در حال حمل؛
- مرحله فعلی: خورگوس ← آکتائو؛
- آخرین موقعیت گزارش‌شده، زمان و منبع؛
- ETA نهایی به‌صورت range، نه زمان دقیق کاذب؛
- نقطه مهم بعدی و range آن؛
- مسئول پرونده؛
- freshness؛
- Attention واقعی در برابر اطلاعات ناقص؛
- progress معنادار بخش‌ها؛
- فعالیت‌های اخیر؛
- deterministic Next Best Action.

### قاعده نمونه Next Best Action

ترتیب نمونه و قابل‌توضیح Prototype:

1. blocker مرتبط با مرحله جاری؛
2. allocation باقیمانده برای execution جاری؛
3. operational problem باز با اثر زمانی/کالا؛
4. اطلاعات ناقص لازم برای اقدام نزدیک؛
5. موعد milestone بعدی؛
6. در نبود موارد بالا، مرور freshness.

این طراحی AI نیست و الگوریتم نهایی Product را تعریف نمی‌کند. متن «چرا این اقدام؟» دلیل rule فعال را نشان می‌دهد.

### progress بدون درصد گمراه‌کننده

به‌جای درصد واحد، هر حوزه با یکی از stateهای «کامل»، «ناقص»، «در جریان»، «نیازمند توجه» یا «مسدود» دیده می‌شود. current execution stage جداگانه حفظ می‌شود.

## ۹. مشتری، Request و Cargo

- Requestهای متصل با Customer، Cargo حاصل و source attribution دیده می‌شوند.
- Customer membership از Cargo ownership خوانده می‌شود، نه list مستقل.
- هر Cargo description، category، owner Customer، Request منبع، packaging، quantity/unit، weight/volume در صورت وجود و destination دارد.
- «HS Code هنوز تکمیل نشده» در سبک incomplete نمایش می‌یابد، نه operational problem.
- requested/planned/actual کنار هم و با اختلاف آشکار دیده می‌شوند؛ کاربر مجبور به مقایسه fieldهای پنهان نیست.
- چند Cargo یک مشتری و Cargoهای چند مشتری در grouping آرام و پرتراکم قابل مرورند.

## ۱۰. تخصیص و انتقال Cargo

نمای تخصیص دو جهت هم‌زمان دارد:

- **بر اساس Cargo:** کل، تخصیص‌یافته، باقیمانده، مالک Customer، Route Stage و unitها؛
- **بر اساس واحد حمل:** Cargoهای داخل هر unit، Customer مربوط و مقدار.

ورودی بیش از باقیمانده با خطای inline مسدود می‌شود. تخصیص ناقص ذخیره‌پذیر است، اما badge و پیام واضح دارد. «انتقال کالا» مقدار، مبدأ، مقصد، نقطه عملیاتی، زمان و دلیل اختیاری را می‌گیرد و history قبلی را حفظ می‌کند.

## ۱۱. مسیر، execution، وسیله، واحد حمل و Carrier

- planned route و actual route دو tab جدا هستند.
- مسیر مرحله‌به‌مرحله تکمیل می‌شود و لازم نیست در آغاز کامل باشد.
- شاخه مقصد به‌صورت «shared route تا hub + فهرست شاخه‌های Cargo» نمایش می‌یابد؛ از network diagram شلوغ پرهیز شده است.
- هر Route Leg می‌تواند چند execution هم‌زمان داشته باشد.
- زنجیره هر execution روشن است: `وسیله حمل → واحد/ظرف حمل → Cargo`.
- Carrier روی execution دیده می‌شود، نه به‌صورت یک field کلی Shipment.
- نبود پلاک یا detail با state ناقص نمایش می‌یابد و سایر کارهای مستقل را متوقف نمی‌کند.
- نبود base definition فقط همان اقدام وابسته را متوقف می‌کند و کاربر را به مسیر مدیر سازمان هدایت می‌کند؛ free-text bypass وجود ندارد.

## ۱۲. اسناد و privacy

اسناد دو سطح دارند:

1. contextual documents در context Cargo، unit، stage یا delivery؛
2. نمای «همه اسناد» برای مدیریت و فیلتر.

هر سند scope و visibility مستقل دارد. برچسب‌های ارائه‌ای فقط معنای مصوب را آشکار می‌کنند: داخلی، مخصوص مشتری مربوط، یا مشترک و قابل نمایش طبق اختیار موجود. اشتراک وسیله حمل هرگز دلیل visibility به همه مشتریان نیست.

## ۱۳. اجرای زنده، موقعیت و Timeline

پس از شروع execution، صفحه از configuration-heavy به awareness-heavy تغییر می‌کند. current stage، reported location، freshness، source، next important point، ETA، Attention و recent meaningful activity برجسته می‌شوند.

موقعیت همیشه با عبارت «آخرین موقعیت گزارش‌شده» و «گزارش عملیاتی» نمایش می‌یابد. برچسب GPS یا LIVE استفاده نمی‌شود. Timeline رویدادهای معنادار را به‌ترتیب و با grouping روزانه نشان می‌دهد؛ raw log نیست.

در اصلاح موقعیت:

- گزارش قبلی با برچسب «بعداً اصلاح شد» حفظ می‌شود؛
- گزارش معتبر جدید مشخص است؛
- مشتری نسخه ساده و صادقانه را می‌بیند؛
- Expert به دلیل و تاریخچه داخلی دسترسی دارد.

## ۱۴. مشکل، Action و Attention

سه مفهوم در visual hierarchy جدا هستند:

- Problem: چه اتفاقی افتاده و اثر آن چیست؛
- Action/Follow-up: چه کاری، توسط چه کسی و تا چه زمانی لازم است؛
- Attention: چرا اکنون باید بررسی شود.

Internal explanation و customer-safe explanation در دو panel جدا قرار دارند. اگر مشکل روی مشتری اثر داشته باشد و متن کارشناس خالی باشد، پیام امن پیش‌فرض و deterministic نمایش داده می‌شود تا سکوت گمراه‌کننده ایجاد نشود. متن داخلی هرگز به Customer projection راه نمی‌یابد.

## ۱۵. Delivery و Closure

هر Delivery مقدار، مکان، زمان و evidence مستقل دارد. مجموع delivered و remaining در سطح Cargo دیده می‌شود. وضعیت چندمشتری نیز مستقل است: مشتری A تحویل‌شده، B در حمل، C در گمرک؛ Shipment همچنان باز می‌ماند.

Closure یک checklist policy-driven است، نه نتیجه خودکار تحویل. Expert می‌بیند کدام الزام پاس، ناقص یا blocker است و به context اصلاح هدایت می‌شود. Expert bypass ندارد. درخواست استثنا به Organization Admin می‌رود و در آن:

- requirement مفقود حذف یا PASS نشان داده نمی‌شود؛
- دلیل مدیر الزامی است؛
- approver، time و exception state ثبت و نمایان‌اند.

Requirementهای موجود در Prototype صرفاً مثال‌اند؛ تعریف universal/mode-specific نهایی در اختیار Product Owner و Organization policy است.

## ۱۶. تجربه مشتری shared-Shipment

Customer A یک projection مستقل و mobile-first می‌بیند:

- status مجاز، reported location با زمان و منبع، ETA range و next point؛
- Cargo، quantity، document و delivery خود؛
- Timeline privacy-safe و issue message امن؛
- پیام روشن «این حمل با بار سایر مشتریان به‌صورت مشترک انجام می‌شود».

Customer A نام، Cargo، quantity، document، private exception cause یا delivery مشتری B/C را نمی‌بیند. privacy با projection و safe microcopy طراحی شده است، نه با پنهان‌کردن اتفاقی componentها.

## ۱۷. تجربه مدیر سازمان

Admin چهار سطح دارد:

1. **تعاریف مرجع:** فعال‌سازی central catalog یا مفهوم تعریف سازمانی؛ بدون free-text Expert؛
2. **زمان مرجع مسیر:** organization-scoped، route-stage و mode-specific، با حرکت جدا از توقف/عملیات و history نسخه‌ها؛
3. **الزامات closure:** ترکیب requirementهای عمومی و mode-specific؛
4. **بررسی استثنای closure:** missing requirement، دلیل، approver، time و state صریح.

مقایسه «مرجع فعلی ۶–۸ روز» با «عملکرد واقعی اخیر ۹–۱۱ روز» فقط پیشنهاد بازبینی می‌دهد. سامانه در طرح، مرجع را خودکار تغییر نمی‌دهد و analytics پیاده‌سازی نشده است.

## ۱۸. `DECISION_NEEDED`

این موارد عمداً در UX حل یا تصویب نشده‌اند:

| شناسه | تصمیم لازم | آنچه ثابت می‌ماند | اثر احتمالی |
|---|---|---|---|
| DN-01 | lifecycle و نام stateهای نهایی Phase 3 و transitionهای مجاز چیست؟ | Prototype فقط stateهای ارائه‌ای را نشان می‌دهد | Shipment Overview، Timeline، Closure |
| DN-02 | permission matrix دقیق اسناد مشترک و انتقال مالکیت استثنایی Shipment چیست؟ | document scope مساوی visibility نیست؛ privacy حفظ می‌شود | Customer documents، Admin audit |
| DN-03 | checklist نهایی universal و mode-specific closure چیست؟ | Expert bypass ندارد؛ استثنا آشکار است | Closure و FWD-IPJ-04 |
| DN-04 | مبنا، confidence، freshness و روش محاسبه ETA چیست؟ | range و زمان آخرین به‌روزرسانی نمایش داده می‌شود؛ precision کاذب ممنوع است | Overview و Customer summary |
| DN-05 | نقطه‌ای که HS Code الزام‌آور می‌شود کدام است؟ | در شروع می‌تواند ناقص باشد و incident نیست | Cargo completeness و Closure |
| DN-06 | taxonomy نهایی reported-location source/confidence و eventها چیست؟ | GPS/LIVE ادعا نمی‌شود؛ correction حفظ می‌شود | Timeline و tracking |
| DN-07 | متن‌های رسمی و localization پیام امن پیش‌فرض Customer چیست؟ | Customer متأثر در سکوت نمی‌ماند و متن داخلی افشا نمی‌شود | Exception communication |
| DN-08 | فرآیند seed/promotion و authority جزئی تعاریف سازمانی چیست؟ | Expert free-text bypass ندارد | Admin catalog و execution setup |
| DN-09 | سطح دسترسی پس از exceptional Shipment ownership transfer چیست؟ | مالکیت Cargo و Customer privacy تغییر نمی‌کند | Expert access و document handoff |

هر تصمیم باید به‌صورت مستقل توسط Product Owner/authority مربوط تصویب و سپس به Product Authority Record مأموریت پیاده‌سازی افزوده شود.

## ۱۹. پوشش سفرهای Product

این پوشش «طراحی» است، نه اجرای سفر یا PASS محصول.

| سفر | پوشش UX | وضعیت اعتبارسنجی |
|---|---|---|
| FWD-J03 | ایجاد/تکمیل تدریجی پرونده، اتصال Request و تعریف Cargo/route | `DESIGN_COVERED / NOT_RUN` |
| FWD-J04 | اجرای چندمرحله‌ای، چندوسیله‌ای و Carrier per execution | `DESIGN_COVERED / NOT_RUN` |
| FWD-J05 | reported location، Timeline، correction و Attention | `DESIGN_COVERED / NOT_RUN` |
| FWD-J06 | Customer projection، privacy و safe communication | `DESIGN_COVERED / NOT_RUN` |
| FWD-J07 | partial delivery، evidence و remaining quantity | `DESIGN_COVERED / NOT_RUN` |
| FWD-J09 | closure checklist و Admin exception | `TARGET_DESIGN_COVERED / PRODUCT_NOT_IMPLEMENTED` |
| FWD-IPJ-01 | Request → Shipment linkage و source attribution | `DESIGN_COVERED / NOT_RUN` |
| FWD-IPJ-02 | cross-surface execution awareness | `DESIGN_COVERED / NOT_RUN` |
| FWD-IPJ-03 | Customer-safe shared Shipment projection | `DESIGN_COVERED / NOT_RUN` |
| FWD-IPJ-04 | end-to-end closure control | `TARGET_DESIGN_COVERED / PRODUCT_NOT_IMPLEMENTED` |

`JOURNEY_IMPACT=NONE` چون هیچ رفتار runtime تغییر نکرده است. هیچ Integrated Product Journey یا Human Product Walkthrough در این مأموریت PASS نشده است.

## ۲۰. رویکرد responsive و accessibility

### Desktop Expert

نمای اصلی پرتراکم، side navigation پایدار، header context ثابت، جدول‌های خوانا و modalهای contextual دارد. برنامه‌ریزی پیچیده desktop-oriented است.

### Expert در عرض کم

دسترسی مفید به summary، Timeline، Attention، ثبت موقعیت، اطلاعات فوری و اسناد کلیدی حفظ می‌شود؛ برنامه‌ریزی پرتراکم به صفحه کوچک تحمیل نمی‌شود.

### Customer Mobile

چیدمان واقعاً بازآرایی می‌شود: header سبک‌تر، cardهای اولویت‌دار، CTA محدود و bottom navigation ثابت. جدول desktop صرفاً کوچک نشده است.

### accessibility

- HTML معنایی و labelهای قابل‌فهم؛
- skip link، focus واضح و keyboard navigation عملی؛
- state با متن و نشانه علاوه بر رنگ؛
- کنتراست و فاصله مناسب؛
- wrapper برای جدول پرتراکم؛
- جهت RTL و آمیختگی واژه‌های لاتین کنترل‌شده؛
- modal با بستن Escape و انتقال focus اولیه.

## ۲۱. دامنه Prototype

Prototype با HTML/CSS/JS ساده در مسیر مستندات قرار دارد و:

- فقط داده ساختگی دارد؛
- با banner دائمی `TARGET_PHASE3_UX` مشخص است؛
- هیچ fetch، API، credential، production endpoint یا DB ندارد؛
- هیچ فایل آن از runtime import نمی‌شود؛
- state فقط در حافظه مرورگر و تا refresh معتبر است؛
- role switch برای Expert، Customer A و Organization Admin دارد؛
- stateهای normal، incomplete، empty، loading، denied، error و stale را قابل مشاهده می‌کند.

## ۲۲. راهنمای مرزی برای مأموریت پیاده‌سازی بعدی

این طرح نباید مستقیم به schema یا API تبدیل شود. پیش از implementation باید:

1. Product Owner review اجرا و checkpointها ثبت شود؛
2. همه `DECISION_NEEDED`های اثرگذار تعیین تکلیف شوند؛
3. مأموریت implementation planning مستقل با sliceهای محدود شکل گیرد؛
4. Product Authority Record جدید و Journey Impact واقعی ساخته شود؛
5. contracts، authorization، data ownership و acceptance evidence هر slice جداگانه تعریف شوند.

نباید از requirementهای ساختگی Prototype، statusها، نام fieldها یا داده‌های نمایش به‌عنوان contract runtime استفاده شود.

## ۲۳. وضعیت بازبینی و reference

`UX_PRODUCT_OWNER_REVIEW=NOT_RUN`  
`HUMAN_PRODUCT_WALKTHROUGH=NOT_RUN`  
`BROWSER_PROTOTYPE_REVIEW=PASS`  
`REFERENCE_RECONCILIATION=PASS`  
`REFERENCE_IMPACT=NONE`

در آغاز، این سند یک مرجع هدف جدید بود و `REFERENCE_IMPACT=UPDATE_REQUIRED` داشت. با افزودن pointer به نقشه‌های مرجع پروژه، اثر رفع و به `NONE` آشتی داده شد. هیچ تغییری در LPAF v2.7 انجام نشده است.


# مرجع پذیرش سفرهای محصول Forwarder — نسخه ۱.۱

## ۱. شناسنامه و وضعیت

| فیلد | مقدار |
| --- | --- |
| شناسه مرجع | `FORWARDER-PRODUCT-ACCEPTANCE-JOURNEYS-V1.1-FA` |
| وضعیت مرجع | `ACTIVE / CANONICAL PRODUCT REFERENCE` |
| خط مبنای حاکم | `LPAF v2.7 — ACTIVE / FROZEN / CANONICAL` |
| مرجع تصویب | مأموریت صریح Product Owner برای تکامل Journey Pack از v1 به v1.1 و افزودن سفر هدف `FWD-J09` |
| شعبه مبنا | `integration/golden-controlled` |
| HEAD مبنای مخزن | `48833131073d4b5c0a5229550e4391abe44e5704` |
| Product SHA آخرین بستهٔ رفتاری واجد شواهد | `1aea4bebdde7e240a903baea1b7b678993f3c505` |
| توضیح اختلاف دو SHA | تغییر بعدی تا HEAD مبنا فقط بستهٔ شواهد Phase 2.5 را افزوده و فایل Product/runtime را تغییر نداده است؛ این توضیح جای اجرای دقیق Candidate آینده را نمی‌گیرد. |
| Alembic head در زمان تدوین | `20260929_operational_monitoring_reliability`، یکتا |
| تعداد سفرهای حیاتی تعریف‌شده | ۹؛ هشت سفر فعلی و یک سفر هدف فاز ۳ |
| تعداد سفرهای یکپارچه | ۴؛ سه سفر فعلی و یک سفر هدف فاز ۳ |
| وضعیت Pack | `DEFINED` |
| وضعیت شواهد Slice | `MAPPED` |
| سفرهای یکپارچه | `DEFINED_NOT_RUN` |
| مجموعهٔ خودکار Release | `DEFINED_NOT_RUN_AS_RELEASE_SET` |
| مرور انسانی | `DEFINED_NOT_RUN` |
| اعتبارسنجی سراسری Product | `EVIDENCE_PENDING` |
| آمادگی Release | `NO` |

این سند مرجع دائمی سفرهای پذیرش Forwarder است. نسخه ۱.۱ تکامل مستقیم نسخه ۱ در commit `71131e672ee349773c09b124451fd0953c2e5c75` است و شناسه‌های `FWD-J01` تا `FWD-J08` را بدون renumber حفظ می‌کند. تعریف `FWD-J09` به معنای پیاده‌سازی آن، اجرای سفر، پذیرش انسانی یا اجازهٔ Release نیست. نتیجه‌های تاریخی و Slice فقط ورودی‌اند؛ هیچ‌کدام به‌تنهایی PASS یک سفر یکپارچه محسوب نمی‌شوند.

## ۲. روش استفاده

- **Critical Journey** سفر فعلی و الزامی محصول است که باید در Release مربوط، با شواهد معتبر پوشش داده شود.
- **Slice evidence** فقط یک بخش محدود از رفتار را ثابت می‌کند.
- **Integrated Product Journey** چند نقش و چند سطح محصول را با ناوبری واقعی به هم وصل می‌کند.
- **Human Product Walkthrough** اجرای انسانی ثبت‌شده توسط Product Owner یا نمایندهٔ انسانی صریحاً مجاز است. عامل نرم‌افزاری نمی‌تواند برای آن PASS صادر کند.
- در این سند، `NOT_RUN` یعنی سناریو تعریف شده اما اجرا نشده است؛ نه شکست و نه موفقیت.
- هر ادعای Release باید به Candidate دقیق، محیط، دادهٔ آزمون، زمان، نتیجه و مدارک قابل بازبینی متصل باشد.

طبقه‌بندی وضعیت نیت و واقعیت:

| وضعیت | معنی |
| --- | --- |
| `ALIGNED` | نیت مصوب و سطح فعلی محصول همسو هستند. |
| `IMPLEMENTATION_GAP` | رفتار یا ناوبری لازم در محصول فعلی کامل نیست. |
| `EVIDENCE_GAP` | سطح محصول وجود دارد، اما مدرک لازم برای ادعای جاری کافی نیست. |
| `DECISION_NEEDED` | تصمیم Product Owner لازم است. |
| `HISTORICAL_ONLY` | مدرک فقط برای شناخت گذشته قابل استفاده است. |
| `CURRENT_AND_PROVEN` | رفتار فعلی در محدوده مدرک موجود اثبات شده است. |
| `CURRENT_PARTIAL` | بخشی از foundation فعلی وجود دارد، اما قرارداد کامل هدف را ثابت نمی‌کند. |
| `TARGET_PHASE3` | رفتار هدف توسط Product Owner تصویب شده، اما هنوز پیاده یا qualified نشده است. |
| `EVIDENCE_GAP` | برای ادعای موردنظر مدرک کافی یا تازه وجود ندارد. |
| `DECISION_NEEDED` | تصمیم Product Owner یا مرجع دارای اختیار لازم است. |

طبقه‌بندی نگاشت شواهد:

| طبقه | معنی |
| --- | --- |
| `FULL_EXISTING_SLICE_EVIDENCE` | Sliceهای اصلی سفر در شواهد فعلی دیده شده‌اند؛ با این حال سفر یکپارچه و Release set هنوز باید اجرا شوند. |
| `PARTIAL_EXISTING_EVIDENCE` | فقط بخشی از سفر یا بخشی از نقش‌ها/ناوبری/منفی‌ها شواهد دارند. |
| `NO_INTEGRATED_EVIDENCE_YET` | هیچ PASS یکپارچهٔ معتبر برای این Pack ثبت نشده است. |

## ۳. مرز اختیار این مأموریت

| کنترل | ثبت |
| --- | --- |
| سطح مأموریت | `Level B`، تعریف Product target و مرجع Journey بدون تغییر runtime |
| مسیر قابلیت | `Astra` برای آشتی تصمیم‌های وابسته، مراجع متعدد و وضعیت current/target |
| Product Owner | مالک تصویب فهرست سفرهای حیاتی و تغییرات آیندهٔ آن |
| `AUTHORIZED_PRODUCT_CHANGES` | تعریف target Product طبق قرارداد Shipment عملیاتی v1؛ افزودن `FWD-J09` و `FWD-IPJ-04`؛ بدون تغییر runtime |
| تغییرات محافظت‌شده | رفتار، نقش، Tenant، DB/API/UI/runtime فعلی؛ وضعیت `NOT_RUN`؛ evidence تاریخی؛ موضوعات عمداً باز |
| محدودهٔ مجاز | تکامل v1 به v1.1، نگاشت اثرها، اسکریپت مرور هدف و پیوندهای مرجع |
| `JOURNEY_IMPACT` | `NEW_JOURNEY_REQUIRED` |
| `NEW_JOURNEY` | `FWD-J09` |
| `REFERENCE_IMPACT` | `NONE`؛ Product Contract، Pack v1.1، `AGENTS.md` و indexهای پروژه با هم آشتی داده شده‌اند. |

مرجع‌های اصلی Product برای این Pack:

- [قرارداد محصول پرونده حمل عملیاتی v1](./FORWARDER-OPERATIONAL-SHIPMENT-PRODUCT-CONTRACT-V1-FA.md)
- [مدل عملیاتی Forwarder](./FORWARDER-OPERATIONAL-MODEL-V1-FA.md)
- [طراحی Product فضای کاری عملیاتی](./FORWARDER-OPERATIONAL-WORKSPACE-PRODUCT-DESIGN-V1-FA.md)
- [مدل دسترسی CRM](./FORWARDER-CRM-ACCESS-MODEL.md)
- [معماری چندسازمانی](../architecture/multi-tenant-architecture-contract.md)
- [دسترسی تجاری Shipment](../architecture/shipment-business-access-v2.md)
- [Public Tracking](../operational/adr/ADR-052-public-tracking-opaque-capability-authority.md)
- [Customer Account](../operational/adr/ADR-053-optional-customer-account-private-quote-authority.md)
- [مالک ثابت Shipment](../operational/adr/ADR-047-fixed-operational-shipment-responsible-expert.md)
- [SLA، Action و Attention](../operational/adr/ADR-054-organization-sla-action-attention.md)
- [پایداری ارزیابی عملیاتی](../operational/adr/ADR-055-operational-monitoring-reliability.md)

## ۴. اصول مشترک پذیرش

۱. `Request` نیاز تجاری مشتری است؛ `Shipment` اجرای عملیاتی است. پذیرش Quote به‌تنهایی Shipment نمی‌سازد.

۲. همان Transport Expert می‌تواند جریان تجاری و عملیاتی را ادامه دهد، اما مالک Shipment دقیقاً یک Expert ثابت است. تغییر مسئول Request مالک Shipment را عوض نمی‌کند.

۳. Tenant و اختیار از نشست، عضویت معتبر، hostname معتبر یا والد از قبل مجاز به دست می‌آید؛ شناسهٔ ارسالی کاربر اختیار ایجاد نمی‌کند.

۴. مخفی‌کردن دکمه در UI جای کنترل backend را نمی‌گیرد. دسترسی مستقیم حدس‌زده‌شده نیز باید بدون نشت داده رد شود.

۵. `Status`، رخداد، Exception، Action، Attention و SLA حقیقت‌های جدا هستند. بستن Action نباید Exception، SLA یا Shipment را خودکار ببندد.

۶. Attention یک نمای مشتق‌شده است، نه منبع حقیقت. باز بودن مرورگر شرط تولید آن نیست. نبودن هشدار وقتی freshness معتبر نیست، نشانهٔ سلامت نیست.

۷. Public Tracking فقط با قابلیت opaque معتبر و allowlist محدود کار می‌کند. شناسه‌های داخلی، Tenant، اطلاعات تماس، Quote، اسناد و اطلاعات Expert عمومی نیستند.

۸. Customer Account اختیاری است؛ سفر ناشناس باید مستقل باقی بماند. Customer در CRM و حساب پرتال مشتری یک مفهوم خودکار مشترک نیستند.

۹. حالت خالی، عدم دسترسی، خطای موقت و دادهٔ stale باید واضح و از موفقیت قابل تشخیص باشند.

۱۰. هر سفر باید پس از refresh و بازگشایی، حقیقت ماندگار مورد انتظار را نشان دهد.

اصول افزوده‌شده در v1.1 برای هدف فاز ۳:

۱۱. یک Shipment می‌تواند Cargo چند Request و چند Customer را در خود داشته باشد، اما چندمشتری‌بودن از Customer attribution هر Cargo مشتق می‌شود؛ Shipment به فهرست مستقل عضویت مشتری تبدیل نمی‌شود.

۱۲. `REQUESTED`، `PLANNED` و `ACTUAL` سه حقیقت مقدارند و یکدیگر را بازنویسی نمی‌کنند.

۱۳. Cargo می‌تواند میان چند وسیله/ظرف حمل تخصیص یابد و یک وسیله می‌تواند Cargo چند Customer را حمل کند؛ over-allocation مسدود و باقی‌مانده تخصیص‌نیافته آشکار می‌شود.

۱۴. Planned Route و Actual Route، وسیله حمل و واحد/ظرف حمل، Document scope و visibility و اطلاعات ناقص و مشکل عملیاتی مفاهیم جدا هستند.

۱۵. Product truth هدف می‌تواند مشترک باشد، اما Customer projection همیشه privacy-safe و customer-scoped است.

۱۶. همه اصول ۱۱ تا ۱۵ `TARGET_PHASE3` هستند و صرف ثبت در این Pack، runtime یا evidence فعلی ایجاد نمی‌کند.

## ۵. فهرست سفرهای حیاتی فعلی

| شناسه | نام ساده | بازیگر اصلی | وضعیت نیت/پیاده‌سازی | شواهد Slice فعلی | سفر یکپارچه مرتبط |
| --- | --- | --- | --- | --- | --- |
| `FWD-J01` | مشتری ناشناس: ثبت نیاز و پیگیری عمومی | مشتری ناشناس | `ALIGNED + EVIDENCE_GAP` | `PARTIAL_EXISTING_EVIDENCE` | `FWD-IPJ-01` |
| `FWD-J02` | مشتری دارای حساب: درخواست خصوصی و پاسخ به قیمت | مشتری دارای حساب | `ALIGNED + EVIDENCE_GAP` | `PARTIAL_EXISTING_EVIDENCE` | `FWD-IPJ-01` |
| `FWD-J03` | کارشناس: تحویل تجاری به عملیات | کارشناس حمل | `ALIGNED + EVIDENCE_GAP` | `PARTIAL_EXISTING_EVIDENCE` | `FWD-IPJ-01` |
| `FWD-J04` | کارشناس: فضای کاری روزانه | کارشناس حمل | `ALIGNED + EVIDENCE_GAP` | `FULL_EXISTING_SLICE_EVIDENCE` | `FWD-IPJ-02` |
| `FWD-J05` | مشکل عملیاتی، اقدام و پیگیری | کارشناس حمل | `ALIGNED + EVIDENCE_GAP` | `FULL_EXISTING_SLICE_EVIDENCE` | `FWD-IPJ-02` |
| `FWD-J06` | ادارهٔ سازمان | مدیر سازمان | `IMPLEMENTATION_GAP + EVIDENCE_GAP` | `PARTIAL_EXISTING_EVIDENCE` | `FWD-IPJ-03` |
| `FWD-J07` | برج کنترل | کارشناس/ناظر مجاز | `ALIGNED + EVIDENCE_GAP` | `FULL_EXISTING_SLICE_EVIDENCE` | `FWD-IPJ-02` |
| `FWD-J08` | حفاظت Tenant و مجوز | چند نقش | `ALIGNED + EVIDENCE_GAP` | `PARTIAL_EXISTING_EVIDENCE` | `FWD-IPJ-03` |
| `FWD-J09` | پرونده حمل مشترک چندمشتری / چندکالا | کارشناس حمل و مشتری‌های مرتبط | `TARGET_PHASE3 + EVIDENCE_GAP` | `NO_IMPLEMENTATION_OR_QUALIFICATION_EVIDENCE` | `FWD-IPJ-04` |

برای هر نه سفر، `NO_INTEGRATED_EVIDENCE_YET` برقرار است. `FWD-J01` تا `FWD-J08` سفرهای فعلی‌اند؛ `FWD-J09` سفر حیاتی هدف است و وضعیت آن `CRITICAL_TARGET_PHASE3 / DEFINED_NOT_IMPLEMENTED` است.

## ۶. رکورد سفرهای حیاتی

### FWD-J01 — مشتری ناشناس: ثبت نیاز و پیگیری عمومی

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | مشتری بدون حساب بتواند نیاز حمل را ثبت کند، کد پیگیری امن بگیرد و فقط نمای عمومی مجاز را ببیند. |
| بازیگر | مشتری ناشناس |
| محدوده Tenant | سازمان فعالِ حل‌شده از hostname؛ کاربر Tenant را انتخاب یا ارسال نمی‌کند. |
| نقطه شروع | صفحهٔ اصلی `/` |
| پیش‌نیاز | hostname معتبر، سازمان فعال، فرم درخواست در دسترس؛ برای پیگیری یک قابلیت معتبر `SR2-...` |
| ناوبری عادی | صفحهٔ اصلی ← «درخواست جدید» ← انتخاب داخلی/بین‌المللی ← فرم ← تأیید ثبت ← لینک پیگیری عمومی |
| گام‌ها | نوع درخواست را انتخاب کند؛ مسیر، اطلاعات تماس و در صورت نیاز Cargo/روش حمل/تاریخ را وارد کند؛ ارسال کند؛ کد را کپی یا باز کند؛ صفحه را refresh و دوباره باز کند. |
| نتیجهٔ قابل مشاهده | تأیید روشن ثبت، کد opaque، وضعیت تجاری ساده، تاریخ، جغرافیای محدود مبدا/مقصد، قصد حمل و مراحل عمومی مجاز. |
| حقیقت ماندگار | `ShipmentRequest` متعلق به سازمان hostname، Cargo اختیاری، قابلیت عمومی غیرقابل حدس و projection محدود. |
| نتیجه نهایی | درخواست ثبت است؛ Shipment، Quote یا حساب مشتری خودکار ساخته نشده است. |
| refresh/reopen | همان قابلیت معتبر همان projection مجاز را نشان دهد؛ دادهٔ خصوصی اضافه نشود. |
| خروج/ادامه | بازگشت به خانه، ثبت درخواست تازه یا ورود کارکنان؛ پیگیری پروژه مسیر جدا دارد. |
| پذیرش مجوز | ثبت ناشناس مجاز؛ فقط bearer capability معتبر برای نمایش؛ numeric/UUID/legacy/ناشناخته و قابلیت Tenant دیگر پاسخ غیرآشکار بدهند. |
| نباید رخ دهد | نمایش ID داخلی، Tenant، تماس، آدرس دقیق، ارزش/دستور Cargo، Expert، Quote، بحث، سند یا تاریخچهٔ داخلی؛ ساخت خودکار Shipment؛ الزام حساب. |
| حالت خالی | نبود واحد یا رخداد مشتری‌پسند باید پیام خالی روشن بدهد، نه دادهٔ ساختگی. |
| حالت denied | پیام عمومی یکسان و بدون تأیید وجود رکورد؛ مسیر امن برای بازگشت/درخواست جدید. |
| حالت error | خطای قابل‌فهم و امکان تلاش مجدد؛ موفقیت یا کد ساختگی نمایش داده نشود. |
| freshness | برای projection عمومی `N/A` مگر دادهٔ freshness صریح افزوده شود؛ نباید تازگی حدس زده شود. |
| شواهد فعلی | Phase 1/2/2.5 پیگیری عمومی و ایجاد ناشناس را به‌صورت Slice پوشش داده‌اند؛ MT-3 امنیت قابلیت را پوشش داده است. ارسال کامل فرم UI تا انتهای همین سفر روی Candidate Release فعلی ثابت نشده است. |
| انتظار مرورگر | تمام گام‌های مثبت از UI؛ سپس نمونه‌های قابلیت نامعتبر/حدس‌زده و کنترل allowlist؛ صفر خطای غیرمنتظره. |
| انتظار انسانی | متن، اعتمادپذیری کد، سادگی مسیر و نبود دادهٔ حساس توسط انسان بررسی شود. |
| شکاف/تصمیم باز | `EVIDENCE_GAP`: اجرای end-to-end فرم UI روی Candidate دقیق؛ تصمیم Product تازه‌ای لازم نیست. |
| مالک | Product Owner؛ مالک حقیقت Request در پیاده‌سازی `ShipmentRequest`. |
| محرک تغییر | فرم intake، hostname binding، مدل Cargo، قالب قابلیت، allowlist عمومی، status projection یا مسیر `/customer/track`. |

### FWD-J02 — مشتری دارای حساب: درخواست خصوصی و پاسخ به قیمت

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | مشتری با حساب فعال بتواند درخواست‌های خودش را ببیند، Quote جاری و تاریخچه را بخواند و یک پاسخ معتبر ثبت کند. |
| بازیگر | مشتری دارای حساب فعال |
| محدوده Tenant | hostname معتبر و account/session همان سازمان؛ ownership درخواست از سرور، نه ورودی مشتری. |
| نقطه شروع | `/customer`؛ پس از ورود `/customer/requests` |
| پیش‌نیاز | حساب `ACTIVE` و enrolled، نشست معتبر، درخواست متعلق به همان حساب؛ برای پاسخ Quote جاری و پاسخ‌پذیر. |
| ناوبری عادی | پرتال مشتری ← ورود/ثبت‌نام ← درخواست‌های من ← جزئیات درخواست ← Quote جاری/تاریخچه ← پذیرش، گفتگو یا رد |
| گام‌ها | ورود کند؛ فهرست خودش را ببیند؛ یک درخواست را باز کند؛ Quote و نسخه‌های قبلی را بخواند؛ پاسخ مناسب بدهد؛ refresh/reopen کند؛ برای درخواست جدید از CTA به خانه برود و در نشست فعال فرم را تکمیل کند. |
| نتیجهٔ قابل مشاهده | فقط درخواست‌های خود مشتری، Quote جاری، مبلغ/ارز/اعتبار/یادداشت مجاز، تاریخچه و پاسخ ثبت‌شده. |
| حقیقت ماندگار | session امن، ownership سروری، پاسخ یکتای Quote جاری با حالت `accepted`/`discussion`/`declined` و پیام محدود برای discussion. |
| نتیجه نهایی | پاسخ ذخیره است؛ پذیرش Quote فقط اجازهٔ ایجاد Shipment را فراهم می‌کند و Shipment خودکار نمی‌سازد. |
| refresh/reopen | فهرست، جزئیات، تاریخچه و پاسخ بدون تغییر ناخواسته باقی بمانند؛ پاسخ متعارض دوباره پذیرفته نشود. |
| خروج/ادامه | بازگشت به فهرست، پروفایل فقط‌خواندنی، تغییر رمز، خروج، یا درخواست تازه. |
| پذیرش مجوز | فقط صاحب دقیق درخواست/Quote؛ حساب disabled و session قدیمی پس از disable/password/reset/enrollment نامعتبر؛ درخواست خارجی رد شود. |
| نباید رخ دهد | نمایش درخواست یا Quote مشتری دیگر؛ ویرایش مبلغ/ارز توسط مشتری؛ استنتاج مالکیت از CRM؛ انتقال خودکار مالکیت؛ ساخت خودکار Shipment. |
| حالت خالی | «هنوز درخواستی ندارید» با CTA درخواست تازه؛ نبود Quote به‌صورت روشن. |
| حالت denied | نشست نامعتبر به ورود هدایت شود؛ دسترسی مستقیم به درخواست خارجی بدون نشت رد شود. |
| حالت error | خطا با امکان refresh/retry؛ پاسخ ثبت‌نشده موفق نشان داده نشود. |
| freshness | تاریخ و نسخهٔ Quote جاری باید مشخص باشد؛ پاسخ باید مقابل همان نسخه ثبت شود. |
| شواهد فعلی | Phase 1 و تکرارهای Phase 2/2.5 ورود، فهرست/جزئیات خصوصی، Quote history/response، recovery و admin API را Slice-wise پوشش داده‌اند؛ داده‌ها synthetic بوده‌اند. |
| انتظار مرورگر | ورود از UI، فهرست/جزئیات، هر پاسخ مجاز، refresh/reopen، پاسخ متعارض، مالکیت خارجی و session باطل‌شده. |
| انتظار انسانی | وضوح Quote جاری در برابر تاریخچه، اثر هر پاسخ و اعتماد به حریم خصوصی ارزیابی شود. |
| شکاف/تصمیم باز | `EVIDENCE_GAP`: سفر کامل از ایجاد درخواست در نشست تا پاسخ Quote روی Candidate دقیق؛ تحویل واقعی ایمیل recovery در محیط Release هنوز باید ثابت شود. |
| مالک | Product Owner؛ حقیقت حساب در Customer Account و حقیقت تجاری در `ShipmentRequest`/Quote. |
| محرک تغییر | login/register/session، ownership، فهرست/جزئیات، Quote version/response، recovery، profile یا پیوند CRM. |

### FWD-J03 — کارشناس: تحویل تجاری به عملیات

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | کارشناس نیاز مشتری را از Request و Quote تا ایجاد صریح Shipment عملیاتی ادامه دهد، بدون مخلوط‌کردن دو حقیقت. |
| بازیگر | Transport Expert مجاز |
| محدوده Tenant | عضویت فعال همان سازمان و دسترسی تجاری/عملیاتی مجاز. |
| نقطه شروع | ورود کارکنان از `/` یا deep link؛ صفحهٔ درخواست‌ها `/expert` |
| پیش‌نیاز | Request همان سازمان، دسترسی کارشناس، اطلاعات لازم Quote؛ برای ایجاد Shipment یک Quote پذیرفته‌شده یا اختیار direct. |
| ناوبری عادی | ورود ← درخواست‌ها ← جزئیات Request ← تخصیص/پیگیری ← صدور Quote ← مشاهده پاسخ مشتری ← «ایجاد محموله از پیشنهاد پذیرفته‌شده» ← فرم عملیات جدید ← جزئیات Shipment |
| گام‌ها | Request را باز کند؛ در صورت مجاز مسئولیت را بگیرد؛ Quote صادر کند؛ پاسخ مشتری را ببیند؛ پس از `accepted` اقدام صریح ایجاد Shipment را انتخاب کند؛ اطلاعات عملیاتی را تأیید و ثبت کند؛ Shipment را باز و منبع را بررسی کند. |
| نتیجهٔ قابل مشاهده | Request و Quote در صفحهٔ تجاری؛ CTA فقط بعد از پذیرش؛ Shipment جدید با منبع Request/Quote و Expert مسئول ثابت. |
| حقیقت ماندگار | Request/Quote دست‌نخورده به‌عنوان lineage؛ `OperationalShipment` جدا با `source=accepted_quote` و یک مسئول ثابت. |
| نتیجه نهایی | Shipment عملیاتی ایجاد و قابل بازگشایی است؛ Request با Shipment یکی نشده است. |
| refresh/reopen | صفحهٔ Shipment منبع، Quote مرتبط، Request و مسئول ثابت را همان‌طور نشان دهد. |
| خروج/ادامه | برگشت به Request، Workspace یا فهرست Shipmentها. |
| پذیرش مجوز | Quote و ایجاد Shipment فقط برای نقش/مجوز مجاز؛ Tenant خارجی و Request غیرمجاز رد؛ client نمی‌تواند مالک یا Tenant را تحمیل کند. |
| نباید رخ دهد | ساخت Shipment با پذیرش Quote بدون اقدام Expert؛ انتقال مالک Shipment با reassignment Request؛ گم‌شدن Quote history؛ تبدیل Request به Shipment. |
| حالت خالی | Request بدون Quote یا Quote بدون پذیرش CTA عملیاتی نداشته باشد و وضعیت را واضح بگوید. |
| حالت denied | deep link غیرمجاز بدون افشای محتوای Request/Shipment رد شود. |
| حالت error | ثبت ناموفق Shipment موفق نشان داده نشود؛ retry باعث Shipment تکراری نشود یا تکرار آشکار و قابل رسیدگی باشد. |
| freshness | پاسخ و نسخهٔ Quote باید پیش از ساخت دوباره خوانده شوند؛ CTA روی پاسخ قدیمی معتبر فرض نشود. |
| شواهد فعلی | Sliceهای Quote communication، fixed owner، Request/Shipment separation و Phase 1 موجودند؛ زنجیرهٔ کامل چندنقشی روی Candidate Release اجرا نشده است. |
| انتظار مرورگر | ناوبری UI Request→Quote→پاسخ مشتری→Shipment، persistence/reopen و منفی‌های role/Tenant. |
| انتظار انسانی | جدایی روشن Request و Shipment، نقطهٔ تعهد مشتری و مسئولیت Expert تأیید شود. |
| شکاف/تصمیم باز | `EVIDENCE_GAP`: اجرای چندنقشی یکپارچه؛ سیاست retry ساخت Shipment باید در آزمون Candidate اثبات شود. |
| مالک | Product Owner؛ Request/Quote تجاری و `OperationalShipment` عملیاتی. |
| محرک تغییر | Request state، Quote issuance/response، CTA ساخت، source mapping، مالک Shipment یا reassignment. |

### FWD-J04 — کارشناس: فضای کاری روزانه

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | کارشناس با ورود به Workspace بفهمد امروز چه چیزی نیازمند توجه است و از همان‌جا به زمینهٔ کامل Shipment برسد. |
| بازیگر | Transport Expert مجاز |
| محدوده Tenant | همان سازمان؛ Shipmentهای متعلق به مسئول ثابت یا ProjectAccess صریح طبق قرارداد، بدون گسترش مالکیت. |
| نقطه شروع | ورود کارکنان؛ مقصد نقش Expert برابر `/operations` |
| پیش‌نیاز | عضویت فعال، مجوز خواندن عملیات، دادهٔ Workspace؛ freshness قابل مشاهده. |
| ناوبری عادی | ورود ← Workspace ← Attention/محموله‌های فعال/به‌روزرسانی اخیر ← جزئیات Shipment ← تاریخچه ← بازگشت با ناوبری عملیات |
| گام‌ها | کارت‌های امروز را بخواند؛ freshness را بررسی کند؛ یک Attention را باز کند؛ دلیل، زمان، اقدام بعدی و منبع را ببیند؛ Shipment را بررسی کند؛ تاریخچه را باز کند؛ برگردد. |
| نتیجهٔ قابل مشاهده | شمارش‌های روز، Attention توضیح‌پذیر، Shipment فعال با مالک/مسیر/آخرین رخداد/SLA و تاریخچهٔ یکپارچه. |
| حقیقت ماندگار | Shipment و رویدادها منابع حقیقت‌اند؛ Workspace projection مشتق‌شده و محدود به مجوز است. |
| نتیجه نهایی | کارشناس زمینهٔ لازم برای اقدام را یافته، بدون آنکه Workspace حقیقت تازه‌ای جعل کند. |
| refresh/reopen | وضعیت جاری از backend دوباره خوانده شود؛ مسیر بازگشت به Workspace سالم بماند. |
| خروج/ادامه | Shipment، Request منبع، فهرست Shipmentها، Work Queue یا Control Tower طبق مجوز. |
| پذیرش مجوز | Shipment خارجی/غیرمجاز در شمارش، لیست، search یا direct route دیده نشود؛ ProjectAccess مالکیت Action نمی‌سازد. |
| نباید رخ دهد | نمایش Attention سالم وقتی freshness stale/degraded است؛ انتقال مالکیت؛ درخواست eager غیرمجاز؛ اتکا به مرورگر برای تولید Attention. |
| حالت خالی | Workspace خالی با پیام روشن و مسیر Requestها؛ خالی‌بودن به معنای سلامت SLA در freshness نامعتبر نیست. |
| حالت denied | پیام مجوز و خروج امن؛ Platform Admin بدون Tenant به عملیات وارد نشود. |
| حالت error | خطای موقت با retry؛ دادهٔ قبلی بدون برچسب تازه نمایش داده نشود. |
| freshness | فقط `FRESH` اجازهٔ برداشت عادی از absence را می‌دهد؛ `STALE/REBUILDING/DEGRADED` هشدار مشترک و روشن. |
| شواهد فعلی | Phase 1، Phase 2 و Phase 2.5 مسیر Workspace، context/history، empty/error، fixed owner و freshness را Slice-wise پوشش داده‌اند. |
| انتظار مرورگر | ورود واقعی، ناوبری عادی، Attention→Shipment→history→return، empty/error/denied و freshness. |
| انتظار انسانی | اولویت‌بندی، توضیح «چرا»، اقدام بعدی و قابل‌فهم بودن وضعیت stale ارزیابی شود. |
| شکاف/تصمیم باز | `EVIDENCE_GAP`: بازاجرای release set روی Candidate دقیق؛ تصمیم Product تازه‌ای ثبت نشده است. |
| مالک | Product Owner؛ projection در Operational Workspace و حقیقت در Shipment/رویداد/SLA. |
| محرک تغییر | Workspace query/UI، Attention semantics، fixed owner، search/count، freshness یا مسیرهای ناوبری عملیات. |

### FWD-J05 — مشکل عملیاتی، اقدام و پیگیری

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | یک مشکل واقعی با دلیل، اثر و مدرک ثبت شود؛ Action قابل پیگیری ساخته شود؛ هر حقیقت مستقل و قابل بازبینی بماند. |
| بازیگر | Transport Expert مالک ثابت Shipment |
| محدوده Tenant | Shipment همان سازمان و در جمعیت مجاز کارشناس؛ مالک داخلی Action همان مسئول ثابت Shipment. |
| نقطه شروع | Attention در `/operations` یا جزئیات Shipment مجاز |
| پیش‌نیاز | Shipment فعال، دلیل عملیاتی مصوب، مجوز مدیریت Exception/Action؛ برای SLA قاعدهٔ فعال سازمان و ارزیابی معتبر. |
| ناوبری عادی | Workspace Attention ← Shipment ← «مسائل عملیاتی» ← Exception ← Action/پیگیری ← تاریخچه ← Workspace/Control Tower |
| گام‌ها | Exception را با زمان، دلیل، یادداشت، اثر و شواهد ثبت کند؛ Action مرتبط با Shipment/Exception/فرایند بسازد؛ پیگیری بنویسد؛ نتیجه Action را ثبت و ببندد؛ تأیید کند Exception هنوز باز است؛ Exception را جداگانه رفع کند؛ تاریخچه و نماهای مشتق‌شده را بازبینی کند. |
| نتیجهٔ قابل مشاهده | Exception فعال، Action با مسئول/موعد/زمینه، آخرین پیگیری، نتیجه و history؛ Attention/SLA مرتبط با توضیح روشن. |
| حقیقت ماندگار | Exception، Action، follow-up، resolution و audit رویدادهای جدا؛ SLA commitment جدا و قابل محاسبه. |
| نتیجه نهایی | Action و Exception فقط با فرمان‌های مستقل بسته شده‌اند و تاریخچه هر دو را نگه می‌دارد. |
| refresh/reopen | وضعیت، متن پیگیری، نتیجه، زمان‌ها و history پس از refresh و ورود دوباره باقی بماند. |
| خروج/ادامه | Workspace، Work Queue، Control Tower و جزئیات Shipment. |
| پذیرش مجوز | فقط مالک/نقش دارای مجوز؛ ProjectAccess صرف مجوز خواندن است و مالک Action نمی‌سازد؛ Tenant خارجی رد. |
| نباید رخ دهد | بستن Action نباید Exception/SLA/Shipment را ببندد؛ رفع Exception نباید Action را جعل یا حذف کند؛ نبود Attention در freshness نامعتبر سلامت نیست. |
| حالت خالی | «هنوز اقدامی ثبت نشده» یا نبود Exception صریح؛ بدون هشدار ساختگی. |
| حالت denied | بخش یا mutation غیرمجاز بدون دادهٔ محافظت‌شده رد؛ UI مخفی تنها کنترل نباشد. |
| حالت error | conflict نسخه پیام تازه‌سازی بدهد؛ validation عنوان/موعد/نتیجه را روشن کند؛ retry history تکراری نسازد. |
| freshness | ارزیابی بیرون از مرورگر انجام شود؛ Workspace و Control Tower یک truth مشترک برای `FRESH/STALE/REBUILDING/DEGRADED` نشان دهند. |
| شواهد فعلی | Phase 2 ثبت Exception، Action، follow-up، resolution مستقل و history را پوشش داده؛ Phase 2.5 ارزیابی پس‌زمینه و freshness مشترک را بازاعتبارسنجی کرده است. |
| انتظار مرورگر | تمام mutationهای UI و بازگشایی؛ سپس Workspace و Control Tower؛ evaluator خارج مرورگر؛ خطاهای نسخه/مجوز نماینده. |
| انتظار انسانی | کاربر بتواند تفاوت مشکل، کار لازم، وضعیت SLA و نتیجهٔ نهایی را بدون تفسیر فنی بفهمد. |
| شکاف/تصمیم باز | `EVIDENCE_GAP`: Sliceها PASS تاریخی دارند اما release set یکپارچهٔ Pack اجرا نشده است. |
| مالک | Product Owner؛ Exception/Action متعلق به زمینهٔ Shipment، سازمان مالک SLA. |
| محرک تغییر | reason catalog، Exception/Action lifecycle، owner، SLA boundary، evaluator، freshness یا unified history. |

### FWD-J06 — ادارهٔ سازمان

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | مدیر سازمان کاربران، پشتیبانی حساب مشتری و قواعد SLA همان سازمان را بدون اختیار پلتفرمی یا دسترسی Tenant دیگر اداره کند. |
| بازیگر | Organization Admin |
| محدوده Tenant | فقط سازمان عضویت فعال مدیر؛ Platform Admin به‌صورت ضمنی مدیر Tenant نیست. |
| نقطه شروع | ورود کارکنان؛ مقصد `/admin` |
| پیش‌نیاز | عضویت `ORGANIZATION_ADMIN`، سازمان فعال؛ دادهٔ کاربر/حساب/SLA متعلق به همان سازمان. |
| ناوبری عادی مصوب | پنل مدیریت ← «مدیریت کاربران»؛ پنل مدیریت ← «پشتیبانی حساب‌های پرتال مشتری»؛ پنل مدیریت ← «SLA سازمان». |
| سطح فعلی ناوبری | تب کاربران و تب SLA قابل مشاهده‌اند. route پشتیبانی حساب `/admin/customer-portal-accounts` پیاده‌سازی شده، اما از پنل مدیریت لینک قابل مشاهده ندارد؛ این `IMPLEMENTATION_GAP` است. |
| گام‌ها | کارشناس سازمان را ایجاد/ویرایش/فعال یا غیرفعال کند؛ حساب پرتال همان سازمان را جست‌وجو و فعال/غیرفعال کند یا enrollment/recovery مجاز صادر کند؛ دو نوع SLA سازمان را ایجاد، نسخه‌گذاری، فعال/غیرفعال و history را مشاهده کند. |
| نتیجهٔ قابل مشاهده | فهرست و وضعیت کاربران همان سازمان؛ حساب پرتال بدون رمز؛ لینک یک‌بارمصرف فقط یک بار؛ SLA با دقیقه/آستانه/فعال‌بودن/نسخه و تاریخچه. |
| حقیقت ماندگار | membership و وضعیت کاربر؛ account status/token digest/session invalidation؛ قواعد versioned سازمان برای `EXCEPTION_RESPONSE` و `ACTION_FOLLOW_UP`. |
| نتیجه نهایی | تغییر فقط در سازمان مدیر ثبت و audit/history قابل مشاهده است. |
| refresh/reopen | وضعیت کاربر/حساب و آخرین نسخهٔ SLA باقی بماند؛ لینک یک‌بارمصرف دوباره آشکار نشود. |
| خروج/ادامه | داشبورد مدیر، کاربران، SLA، درخواست‌های تخصیص‌نیافته؛ بازگشت امن/خروج. |
| پذیرش مجوز | Organization Admin فقط Expert سازمان خودش می‌سازد؛ حساب/SLA خارجی رد؛ Platform Admin بدون membership جایگزین مدیر سازمان نیست. |
| نباید رخ دهد | مشاهده/تنظیم رمز مشتری؛ استنتاج پیوند CRM؛ انتخاب client-side Tenant؛ ایجاد نقش Platform Admin؛ قاعدهٔ SLA پیش‌فرض؛ business calendar یا pause تأییدنشده. |
| حالت خالی | نبود کاربر/حساب/SLA روشن؛ «SLA تعریف نشده» مجاز و به معنی default پنهان نیست. |
| حالت denied | نقش دیگر صفحهٔ پشتیبانی را نمی‌بیند/استفاده نمی‌کند؛ direct foreign ID با 403/404 قراردادی و بدون نشت. |
| حالت error | خطا و retry روشن؛ در failure تحویل recovery هیچ لینک فعال باقی نماند؛ version conflict موفق نمایش داده نشود. |
| freshness | history و version قواعد باید جدیدترین ثبت سرور را نشان دهند؛ وضعیت تحویل email صریح باشد. |
| شواهد فعلی | Phase 2 SLA admin و foreign denial؛ Phase 1 account-admin API؛ backend tests برای lifecycle حساب و مدیریت کاربران. سفر UI ترکیبی و ناوبری حساب کامل نیست. |
| انتظار مرورگر | ناوبری visible برای هر سه بخش، تغییر و reopen، history، نقش منفی و foreign Tenant؛ تا رفع لینک مفقود، این معیار Release نمی‌تواند PASS شود. |
| انتظار انسانی | مدیر محدوده اختیار، اثر enable/disable، نبود default و محرمانه‌بودن لینک را بفهمد. |
| شکاف/تصمیم باز | `IMPLEMENTATION_GAP`: لینک visible به پشتیبانی حساب؛ `EVIDENCE_GAP`: سفر UI یکپارچه و تحویل ایمیل محیط Release. |
| مالک | Product Owner؛ داده‌های مدیریتی و SLA متعلق به سازمان. |
| محرک تغییر | admin navigation، membership/role، customer account support، token/session، SLA rule/version/history یا tenant scoping. |

### FWD-J07 — برج کنترل

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | کاربر مجاز بداند ریسک عملیاتی کجاست، آن را فیلتر کند و به حقیقت Shipment برسد. |
| بازیگر | Transport Expert یا ناظر دارای مجوز خواندن عملیاتی |
| محدوده Tenant | فقط Shipmentهای مجاز در همان سازمان/جمعیت دسترسی. |
| نقطه شروع | ورود ← `/operations` ← لینک «برج کنترل» ← `/operations/control-tower` |
| پیش‌نیاز | مجوز `operational_shipment.read` و دادهٔ Control Tower؛ freshness قابل مشاهده. |
| ناوبری عادی | Operations Nav ← برج کنترل ← search/filter/کارت ریسک ← جزئیات Shipment ← بازگشت |
| گام‌ها | خلاصه و freshness را بخواند؛ فیلتر/search کند؛ کارت Attention را با شدت، Shipment، مسئول، محل، قصد Request/مسیر واقعی، دلیل و زمان ببیند؛ Shipment را باز کند؛ بازگردد. |
| نتیجهٔ قابل مشاهده | فهرست ریسک توضیح‌پذیر و محدود به مجوز با CTA جزئیات. |
| حقیقت ماندگار | Shipment/Exception/Action/SLA منبع حقیقت؛ Control Tower projection مشتق‌شده است. |
| نتیجه نهایی | کاربر ریسک را به رکورد عملیاتی مربوط وصل کرده است؛ Tower حقیقت جدا نمی‌سازد. |
| refresh/reopen | همان فیلترهای پشتیبانی‌شده و تازه‌ترین projection؛ رکورد رفع‌شده مطابق ارزیابی بعدی تغییر کند. |
| خروج/ادامه | Shipment detail و Operations Nav. |
| پذیرش مجوز | شمارش، search، card و direct detail همگی یک scope مجاز؛ foreign item غایب و direct access رد. |
| نباید رخ دهد | نمایش مشتری/Shipment خارجی؛ مساوی دانستن ProjectAccess با ownership؛ ادعای سلامت از فهرست خالی stale؛ وضعیت متفاوت با Workspace. |
| حالت خالی | پیام خالی همراه freshness؛ اگر freshness معتبر نیست، خالی بودن سلامت را ثابت نکند. |
| حالت denied | صفحه/داده برای نقش فاقد مجوز رد؛ Platform Admin بدون Tenant دسترسی ضمنی ندارد. |
| حالت error | failure class روشن و retry؛ دادهٔ قدیمی بدون هشدار نشان داده نشود. |
| freshness | Workspace و Tower باید یک health/freshness truth داشته باشند. |
| شواهد فعلی | Phase 2 کارت‌های SLA/Action و drill-down را Slice-wise پوشش داده؛ Phase 2.5 stale مشترک Tower/Workspace را پوشش داده است. |
| انتظار مرورگر | normal nav، filter/search، drill-down/back، empty/error/denied، FRESH و STALE مشترک. |
| انتظار انسانی | کاربر بتواند «کجا ریسک داریم و چرا» را سریع پاسخ دهد و false healthy برداشت نکند. |
| شکاف/تصمیم باز | `EVIDENCE_GAP`: اجرای Release set روی Candidate دقیق؛ تصمیم Product تازه‌ای لازم نیست. |
| مالک | Product Owner؛ projection متعلق به Control Tower و facts متعلق به دامنه‌های عملیاتی. |
| محرک تغییر | tower query/UI، filter/search، attention semantics، SLA/freshness، shipment link یا authorization population. |

### FWD-J08 — حفاظت Tenant و مجوز

| فیلد | تعریف |
| --- | --- |
| وضعیت | `CRITICAL_CURRENT / DEFINED / NOT_RUN_AS_RELEASE_SET` |
| هدف | ثابت شود هر نقش ابتدا مسیر مجاز خود را دارد و سپس دسترسی مستقیم حدس‌زده یا cross-Tenant بدون نشت رد می‌شود. |
| بازیگر | مشتری ناشناس، مشتری دارای حساب، Transport Expert، Organization Admin و Platform Admin بدون Tenant |
| محدوده Tenant | Tenant A و Tenant B مستقل با شناسه‌های opaque و دادهٔ نماینده. |
| نقطه شروع | صفحهٔ واقعی هر نقش: `/`، `/customer/requests`، `/operations`، `/admin`. |
| پیش‌نیاز | دادهٔ مثبت و خارجی هم‌شکل، نقش‌ها/نشست‌های جدا، capability معتبر و نامعتبر. |
| ناوبری عادی | ابتدا positive journey هر نقش از منو؛ سپس direct guessed URL/API فقط به‌عنوان آزمون منفی کنترل‌شده. |
| گام‌ها | ناشناس capability خودش را باز و رشته‌های numeric/UUID/foreign را امتحان کند؛ مشتری درخواست خودش و سپس public ID خارجی را باز کند؛ Expert Shipment مجاز و سپس Shipment خارجی را مستقیم بخواند/تغییر دهد؛ Org Admin SLA/account خود و سپس foreign ID را هدف بگیرد؛ Platform Admin بدون membership عملیات Tenant را باز کند. |
| نتیجهٔ قابل مشاهده | positive مسیر عادی کار می‌کند؛ منفی‌ها با پاسخ قراردادی و بدون محتوای محافظت‌شده رد می‌شوند. |
| حقیقت ماندگار | هیچ خواندن، شمارش، mutation، assignment، token یا audit نامعتبر در Tenant دیگر ایجاد نمی‌شود. |
| نتیجه نهایی | reach و use هر دو کنترل شده‌اند؛ frontend و backend همسو و backend مرجع نهایی است. |
| refresh/reopen | نشست/نقش عوض‌شده scope تازه را اعمال کند؛ cache دادهٔ قبلی را به نقش بعدی نشت ندهد. |
| خروج/ادامه | بازگشت به سطح مجاز نقش یا خروج کامل. |
| پذیرش مجوز | 401 برای بی‌نشستی، 403/404 قراردادی برای عدم اختیار/عدم افشا؛ ID/body/query هرگز scope را گسترش ندهد. |
| نباید رخ دهد | تأیید وجود رکورد خارجی، تفاوت افشاگر در پیام، count/search leakage، mutation جزئی، استفاده از UI hiding به‌جای backend، اختیار ضمنی Platform Admin. |
| حالت خالی | empty Tenant A با دادهٔ Tenant B پر نشود و با denied اشتباه نشود. |
| حالت denied | پایدار، غیرآشکار و بدون payload حساس؛ انتظار دقیق status بر اساس قرارداد همان endpoint ثبت شود. |
| حالت error | خطای زیرساخت با denial اشتباه گزارش نشود؛ نتیجه UNKNOWN/FAIL بسته به شواهد، نه PASS. |
| freshness | تغییر نقش، disable account و تغییر رمز/reset باید session قدیمی را بی‌اعتبار کند؛ cacheهای مشتق‌شده scope صحیح داشته باشند. |
| شواهد فعلی | MT-1/MT-3، پوشش authorization و Phase 1/2 منفی‌های fixed-owner/tenant بخشی از این ماتریس را پوشش داده‌اند؛ یک اجرای release-wide چندنقشی وجود ندارد. |
| انتظار مرورگر | ابتدا مثبت عادی، سپس direct-route/API منفی نماینده برای هر مرز؛ بررسی body، شمارش، log مرورگر و نبود mutation. |
| انتظار انسانی | پیام‌های denied دادهٔ حساس را لو ندهند و کاربر مجاز بداند چگونه به مسیر درست برگردد. |
| شکاف/تصمیم باز | `EVIDENCE_GAP`: ماتریس چندنقشی exact-candidate؛ status دقیق هر endpoint از قرارداد همان endpoint گرفته شود. |
| مالک | Product Owner برای سیاست نقش؛ backend authorization و tenant authority برای enforcement. |
| محرک تغییر | نقش/permission، membership، hostname/session، public capability، query population، direct route، search/count/download یا admin support. |

### FWD-J09 — پرونده حمل مشترک چندمشتری / چندکالا

| فیلد | تعریف |
| --- | --- |
| طبقه‌بندی | `CRITICAL_TARGET_PHASE3` |
| وضعیت | `DEFINED_NOT_IMPLEMENTED / NOT_RUN` |
| هدف | کارشناس بتواند Cargo چند Request و چند Customer را با حفظ lineage و privacy در یک Shipment مشترک برنامه‌ریزی و اجرا کند و هر Customer فقط projection امن خود را ببیند. |
| بازیگران | Transport Expert مالک Shipment؛ Customerهای مرتبط؛ Organization Admin فقط در اختیارهای تنظیمات، انتقال استثنایی مالک و استثنای بستن |
| محدوده Tenant و داده | یک سازمان؛ Customer attribution برای هر Cargo؛ هیچ scope ورودی کاربر یا رابطه shared transport اختیار دیدن Customer دیگر ایجاد نمی‌کند. |
| نقطه شروع | Workspace کارشناس و عملیات معنادار ایجاد/بازکردن Shipment؛ برای Customer، Customer Account یا Public Tracking مجاز |
| پیش‌نیاز | چند Request/Customer/Cargo معتبر یا Shipment مستقیم مجاز؛ تعریف‌های پایه فعال سازمان؛ نقش‌ها و مجوزهای معتبر؛ هیچ فرضی درباره کامل‌بودن اولیه route، HS Code، Carrier یا سند وجود ندارد. |
| ناوبری هدف | Workspace ← Shipment ← مشتری‌ها/Requestها ← Cargo ← Route Legs ← Means/Equipment/Allocation ← Documents/Timeline/Problems ← Deliveries ← Completion/Closure؛ جزئیات navigation در مأموریت UX بعدی تعیین می‌شود. |
| گام ۱ — assembly | Cargoهای چند Request/Customer به Shipment افزوده می‌شوند؛ هر Cargo، Customer و Request منبع خود را حفظ می‌کند. |
| گام ۲ — مقدار | برای Cargoهای نماینده، `REQUESTED`، `PLANNED` و بعداً `ACTUAL` جدا ثبت/دیده می‌شوند؛ مقدار قبلی overwrite نمی‌شود. |
| گام ۳ — تخصیص | یک Cargo میان چند وسیله/ظرف حمل تقسیم می‌شود؛ یک وسیله Cargo چند Customer را می‌گیرد؛ over-allocation رد و unallocated remainder آشکار است. |
| گام ۴ — مسیر | Planned Route به Route Legها تکمیل می‌شود؛ Cargoها پس از مسیر مشترک مقصدهای متفاوت می‌گیرند؛ Actual Route و deviation بدون پاک‌کردن plan ثبت می‌شود. |
| گام ۵ — اجرا | برای هر Route Leg یک یا چند Transport Means، Equipment و Carrier واقعی مرتبط می‌شوند؛ Means و Equipment یکی نمی‌شوند. |
| گام ۶ — اسناد | سند در scope Shipment/Cargo/Equipment/Leg/Delivery ثبت می‌شود؛ visibility جدا تعیین می‌شود و Customer فقط سند خود یا سند مشترک صریحاً مجاز را می‌بیند. |
| گام ۷ — موقعیت و Timeline | reported location با زمان و منبع ساده ثبت می‌شود؛ گزارش نادرست با correction و history اصلاح می‌شود؛ Customer Timeline فقط رخداد مجاز را نشان می‌دهد. |
| گام ۸ — مشکل و اثر | مشکل داخلی و Customer-facing effect جدا ثبت می‌شوند؛ Customer متأثر پیام امن می‌بیند و Customer نامرتبط هیچ علت یا داده خصوصی نمی‌بیند. |
| گام ۹ — تحویل | Cargoها به مقصدهای متفاوت و در Deliveryهای جزئی تحویل می‌شوند؛ evidence هر Delivery به Cargo/Customer درست محدود می‌شود. |
| گام ۱۰ — تکمیل | تحویل یک Customer Shipment را نمی‌بندد؛ checklist سازمان و modeهای قابل اعمال ارزیابی می‌شود؛ bypass Expert ممنوع و استثنای Admin audit می‌شود. |
| نتیجه قابل مشاهده Expert | Customer/Request lineage، Cargo/quantity، allocation و remainder، Route Legs، Means/Equipment/Carrier، نقص اطلاعات، Attention، Timeline، Delivery و closure state بدون نیاز به فهم ساختار ذخیره‌سازی. |
| نتیجه قابل مشاهده Customer | وضعیت مجاز، نشانه shared transport، Cargo/quantity/document/delivery خود، route ساده، reported location، ETA و اثر امن مشکلات؛ بدون داده Customer دیگر. |
| حقیقت ماندگار هدف | current truth به‌همراه history معنادار Cargo، quantity، allocation، route، execution، document، report/correction، problem/action، ETA، delivery، ownership و closure. |
| نتیجه نهایی | همه Cargoها تعیین تکلیف و Deliveryهای لازم ثبت شده‌اند؛ requirementهای closure یا استثنای Admin روشن‌اند؛ Shipment فقط پس از کنترل formal بسته می‌شود. |
| refresh/reopen | Expert و هر Customer پس از خروج/ورود فقط scope خود و history مجاز را می‌بینند؛ allocation، correction، Delivery و checklist حفظ می‌شود. |
| خروج/ادامه | بازگشت به Workspace/Control Tower برای Expert؛ Customer Account/Public Tracking مجاز برای Customer؛ هیچ deep link خارجی اختیار تازه ایجاد نمی‌کند. |
| حالت ناقص | route/HS Code/vehicle/Carrier/document نامعلوم با برچسب `INCOMPLETE_INFORMATION` و next action مناسب؛ تا نقطه الزام، success جعلی یا block بی‌مورد ایجاد نمی‌شود. |
| حالت denied | Customer A یا actor خارجی به Cargo، سند، علت مشکل، delivery یا identity Customer B دسترسی ندارد؛ پاسخ بدون نشت است. |
| حالت error/conflict | over-allocation، UOM ناسازگار، stale update، تعریف پایه غیرفعال و conflict نسخه بدون mutation جزئی یا success جعلی رد می‌شوند. |
| must-not | حذف lineage؛ یک customer list اصلی روی Shipment؛ overwrite مقدار/route/report؛ Means=Equipment؛ یک Carrier روی کل Shipment؛ افشای داده Customer دیگر؛ GPS جعلی؛ بستن با Delivery اول؛ bypass checklist؛ ادعای AI. |
| قابلیت‌های مجاور | `FWD-J01` تا `FWD-J08`، Product Contract v1، Public Tracking، Customer Account، Documents، Timeline، Workspace، Control Tower و Admin references. |
| انتظار شواهد آینده | normal-navigation browser journey چندنقشی و چندCustomer روی Candidate دقیق؛ PostgreSQL disposable؛ persistence/reopen؛ privacy negatives؛ allocation limits؛ correction history؛ partial delivery؛ closure checklist؛ بدون Production. |
| انتظار انسانی | سادگی Workspace، فهم allocation/remaining، تمایز ناقص/مشکل، privacy، Timeline و کنترل closure توسط Product Owner بررسی شود. |
| شواهد فعلی | `NO_IMPLEMENTATION_OR_QUALIFICATION_EVIDENCE`؛ foundationهای پراکنده به معنی اجرای این journey نیستند. |
| شکاف/تصمیم باز | تمام جزئیات UI و schema، الگوریتم ETA، GPS، lifecycle فنی allocation، driver/carrier portals و موارد باز Product Contract؛ Journey با همین تصمیم‌های باز `DEFINED` است اما قابل PASS نیست. |
| مالک | Product Owner؛ SORهای فنی و commands در مأموریت‌های طراحی/معماری بعدی تعیین می‌شوند. |
| محرک بازاجرا | هر تغییر در مدل چندمشتری/Cargo، quantity/allocation، route/execution، document/privacy، tracking/timeline، delivery/closure یا owner transfer. |

## ۷. سفرهای یکپارچهٔ Product

چهار سفر زیر برای اجرای خودکار Release و مرور انسانی تعریف شده‌اند. سه سفر نخست قراردادهای فعلی v1 را حفظ می‌کنند. `FWD-IPJ-04` سفر هدف فاز ۳ است. وضعیت فعلی هر چهار سفر `NO_INTEGRATED_EVIDENCE_YET / NOT_RUN` است.

### FWD-IPJ-01 — از نیاز مشتری تا Shipment عملیاتی

| فیلد | تعریف |
| --- | --- |
| سفرهای پایه | `FWD-J01`، `FWD-J02`، `FWD-J03` و نقطهٔ ورود `FWD-J04` |
| هدف | اتصال مسیر واقعی مشتری، Quote و تصمیم صریح Expert برای ایجاد Shipment. |
| بازیگران | مشتری ناشناس یا دارای حساب؛ Transport Expert |
| شروع | صفحهٔ اصلی روی hostname سازمان |
| پیش‌نیاز | سازمان و Expert فعال؛ برای شاخه حساب، Customer Account فعال؛ دادهٔ route/Quote معتبر. |
| جریان عادی | مشتری درخواست را با UI ثبت می‌کند؛ Expert از `/expert` آن را باز و Quote صادر می‌کند؛ مشتری در پرتال Quote را می‌پذیرد؛ Expert از جزئیات Request به فرم ایجاد Shipment می‌رود؛ Shipment را ایجاد و در Workspace باز می‌کند. |
| نتیجهٔ قابل مشاهده | مشتری تأیید و Quote خود را می‌بیند؛ Expert منبع و پاسخ را می‌بیند؛ Shipment جدا با منبع پذیرفته‌شده و مسئول ثابت ظاهر می‌شود. |
| حقیقت ماندگار | Request + Quote/version/response + OperationalShipment/source/fixed owner، بدون تبدیل یا حذف lineage. |
| refresh/reopen | هر نقش پس از خروج/ورود یا refresh فقط حقیقت و محدودهٔ خودش را ببیند. |
| منفی اصلی | مشتری خارجی/Quote قدیمی/نقش غیرمجاز؛ پذیرش Quote بدون Shipment خودکار؛ direct URL خارجی بدون نشت. |
| must-not | یکی‌کردن Request و Shipment، مالکیت از client، نمایش Quote عمومی، ساخت خودکار Shipment، انتقال مالک با reassignment. |
| empty/error | نبود Quote/پذیرش CTA ساخت ندارد؛ failure در هر مرز success بعدی را جعل نمی‌کند. |
| شواهد Slice | موجود اما پراکنده: anonymous/public tracking، Customer Account/Quote، Expert/Shipment/fixed owner. |
| شواهد یکپارچه | `NOT_RUN` |
| نتیجهٔ خودکار Release | `NOT_RUN` |
| نتیجهٔ انسانی | `NOT_RUN` |
| وضعیت فعلی | `DEFINED_NOT_RUN` و Release blocker |
| محرک بازاجرا | هر تغییر در `FWD-J01/J02/J03`، auth/session، Quote یا ساخت Shipment. |
| اثر هدف v1.1 | تبدیل چند Request/Customer/Cargo به Shipment مشترک در `FWD-IPJ-04` آزموده می‌شود؛ تعریف فعلی این سفر و وضعیت `NOT_RUN` آن حفظ شده است. |

### FWD-IPJ-02 — از Shipment فعال تا حل عملیاتی

| فیلد | تعریف |
| --- | --- |
| سفرهای پایه | `FWD-J04`، `FWD-J05`، `FWD-J07` و منفی‌های `FWD-J08` |
| هدف | اتصال Attention روزانه، جزئیات Shipment، مشکل/Action/SLA، تاریخچه و Control Tower تا حل مستقل. |
| بازیگران | Transport Expert مالک ثابت؛ Organization Admin فقط برای پیش‌شرط SLA |
| شروع | ورود Expert و `/operations` |
| پیش‌نیاز | Shipment فعال، قواعد SLA معتبر یا حالت بدون قاعدهٔ صریح، reason مصوب و evaluator خارج مرورگر. |
| جریان عادی | Workspace را با freshness بررسی کند؛ Shipment را باز کند؛ Exception و Action مرتبط بسازد؛ evaluator مستقل اجرا شود؛ Attention در Workspace و Tower دیده شود؛ follow-up ثبت و Action بسته شود؛ Exception هنوز باز بماند؛ Exception جدا رفع شود؛ history و projection بعدی بازبینی شوند. |
| نتیجهٔ قابل مشاهده | علت توجه، مسئول ثابت، SLA، وضعیت مستقل Action/Exception، history و Tower همسو. |
| حقیقت ماندگار | Exception، Action/follow-up/result، SLA evaluation و audit جدا و versioned. |
| refresh/reopen | پس از هر mutation و ارزیابی، صفحه و ورود تازه همان حقیقت را نشان دهند. |
| منفی اصلی | peer/foreign expert، version conflict، stale evaluator، Platform Admin بدون Tenant. |
| must-not | ارزیابی وابسته به مرورگر، false healthy، بستن ضمنی حقیقت دیگر، اختلاف Workspace/Tower یا انتقال ownership. |
| empty/error | no-attention فقط با FRESH قابل تفسیر؛ degraded/stale با warning؛ failure بدون success جعلی. |
| شواهد Slice | Phase 1/2/2.5 برای Workspace، Exception/Action، Control Tower و reliability. |
| شواهد یکپارچه | `NOT_RUN` |
| نتیجهٔ خودکار Release | `NOT_RUN` |
| نتیجهٔ انسانی | `NOT_RUN` |
| وضعیت فعلی | `DEFINED_NOT_RUN` و Release blocker |
| محرک بازاجرا | هر تغییر در Workspace/Tower، Exception/Action/SLA، owner، evaluator/freshness یا history. |
| اثر هدف v1.1 | customer-safe effect، reported-location correction و Timeline چندمشتری در `FWD-IPJ-04` افزوده می‌شود؛ این سفر همچنان برای رفتار فعلی خود جدا می‌ماند. |

### FWD-IPJ-03 — ادارهٔ سازمان و جداسازی Tenant

| فیلد | تعریف |
| --- | --- |
| سفرهای پایه | `FWD-J06` و `FWD-J08`، با اثر قابل مشاهده در `FWD-J02/J04` |
| هدف | ثابت شود ادارهٔ نقش/حساب/SLA در Tenant A فقط همان Tenant را تغییر می‌دهد و مرز Tenant B در UI و direct access بسته است. |
| بازیگران | Organization Admin A، Expert A، Customer A، همتاهای Tenant B و Platform Admin بدون Tenant |
| شروع | ورود مدیر سازمان A و `/admin` |
| پیش‌نیاز | دو Tenant مستقل، کاربران/حساب‌ها/Shipment/SLAهای هم‌شکل، نشست‌های جدا. |
| جریان عادی | Admin A Expert را مدیریت می‌کند؛ از ناوبری visible به پشتیبانی حساب می‌رود و وضعیت Account A را تغییر می‌دهد؛ SLA A را ایجاد/نسخه‌گذاری می‌کند؛ Expert/Customer A اثر مجاز را می‌بینند؛ شناسه‌ها و routeهای B مستقیم آزموده و رد می‌شوند؛ Platform Admin بدون membership عملیات Tenant را نمی‌بیند. |
| نتیجهٔ قابل مشاهده | تغییرات A فقط در A؛ B ثابت؛ denial بدون نشت؛ sessionهای باطل‌شده کار نمی‌کنند. |
| حقیقت ماندگار | membership/account/SLA/audit فقط Tenant A؛ هیچ foreign mutation یا projection leakage. |
| refresh/reopen | هر نقش پس از نشست تازه scope درست را دارد؛ cache قبلی نشت نمی‌کند. |
| منفی اصلی | foreign account/SLA/user/request/shipment، body/query tenant override و Platform Admin implicit access. |
| must-not | پیوند CRM خودکار، مشاهده رمز، default SLA، role escalation، foreign count/search، reliance on hidden UI. |
| empty/error | empty A با داده B پر نشود؛ failure زیرساخت از denial جدا ثبت شود. |
| شواهد Slice | SLA admin، account admin API، membership/authorization و tenant isolation به‌صورت جدا. |
| شواهد یکپارچه | `NOT_RUN` |
| نتیجهٔ خودکار Release | `NOT_RUN` |
| نتیجهٔ انسانی | `NOT_RUN` |
| شکاف اجرای فعلی | لینک visible پشتیبانی حساب در پنل Admin وجود ندارد؛ تا رفع و بازآزمایی، این سفر نمی‌تواند PASS بگیرد. |
| وضعیت فعلی | `DEFINED_NOT_RUN` و Release blocker |
| محرک بازاجرا | هر تغییر در admin navigation، role/membership، account/session، SLA یا tenant authorization. |
| اثر هدف v1.1 | governance catalog، closure checklist و authority استثناهای Admin بر آینده این سفر اثر دارند؛ هیچ‌کدام در این مأموریت اجرا یا PASS نشده‌اند. |

### FWD-IPJ-04 — Shipment مشترک چندمشتری از assembly تا closure

| فیلد | تعریف |
| --- | --- |
| سفرهای پایه | `FWD-J09` با اثر هدف بر `FWD-J01` تا `FWD-J08` |
| طبقه‌بندی | `TARGET_PHASE3` |
| هدف | اتصال assembly چند Request/Customer/Cargo به planning، execution، privacy-safe customer views، deliveryهای جزئی و closure کنترل‌شده. |
| بازیگران | Transport Expert مالک Shipment، چند Customer، Organization Admin در نقاط اختیار مصوب |
| شروع | Workspace کارشناس؛ Customerها از surface مجاز خود وارد می‌شوند. |
| پیش‌نیاز | Contract v1، fixture چندTenant/چندCustomer، catalogهای لازم، داده نماینده و Candidate پیاده‌سازی‌شده آینده؛ وضعیت امروز این پیش‌نیازها را کامل نمی‌کند. |
| جریان عادی | Cargoهای چند Request/Customer assembly می‌شوند؛ quantityها جدا می‌مانند؛ Cargo تخصیص می‌یابد؛ Route Legs و Means/Equipment/Carrier اجرا می‌شوند؛ document/location/timeline/problem به projection امن تبدیل می‌شوند؛ Deliveryهای جزئی ثبت و checklist closure اعمال می‌شود. |
| نتیجه قابل مشاهده | Expert حقیقت کامل و next action را می‌بیند؛ هر Customer فقط حقیقت و اثر مجاز خود را می‌بیند؛ Public Tracking فقط allowlist مشترک امن دارد. |
| حقیقت ماندگار هدف | lineage، attribution، allocation، route/execution، history/correction، documents، problems/actions، deliveries، owner و closure بدون بازنویسی خام. |
| refresh/reopen | همه نقش‌ها پس از بازگشایی scope و history مجاز خود را می‌بینند. |
| منفی اصلی | over-allocation، Customer cross-scope، document leakage، علت خصوصی Exception، گزارش موقعیت اصلاح‌نشده، checklist bypass و owner transfer بی‌اختیار. |
| must-not | یکسان‌گرفتن Means/Equipment، Shipment/Request، scope/visibility، incomplete/problem یا Delivery/Closure؛ نمایش target به‌عنوان current. |
| empty/error | داده ناقص به‌صورت incomplete؛ خطا و conflict بدون partial-success جعلی؛ absence اطلاعات Customer دیگر به‌صورت leakage قابل استنتاج نیست. |
| شواهد Slice | foundationهای فعلی فقط `CURRENT_PARTIAL` هستند و qualification این journey نیستند. |
| شواهد یکپارچه | `NOT_RUN` |
| نتیجهٔ خودکار Release | `NOT_RUN` |
| نتیجهٔ انسانی | `NOT_RUN` |
| وضعیت فعلی | `DEFINED_TARGET_NOT_RUN`؛ implementation و qualification نشده است. |
| محرک بازاجرا | هر تغییر در Contract v1 یا هر capability پایه `FWD-J09`. |

## ۸. اسکریپت مرور انسانی

قواعد ثبت:

- فقط Product Owner یا نمایندهٔ انسانی صریحاً مجاز می‌تواند ستون Result را به `PASS` تغییر دهد.
- هر ردیف باید Candidate، محیط، زمان، مشاهده و مدرک خودش را داشته باشد.
- اگر یک ردیف `FAIL`، `BLOCKED`، `UNTESTED`، `STALE` یا `UNKNOWN` باشد، کل مرور همان سفر PASS نیست.
- مقدار فعلی همهٔ ردیف‌ها `NOT_RUN` است.

### مرور انسانی FWD-IPJ-01

| گام | بازیگر | شروع | اقدام | انتظار قابل مشاهده | نباید رخ دهد | مشاهده | نتیجه | مدرک |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ۱ | مشتری | `/` | درخواست تازه را از UI ثبت کند | تأیید و کد opaque | اجبار حساب یا ساخت Shipment | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۲ | مشتری | لینک موفقیت | پیگیری عمومی را باز کند | فقط projection عمومی | Quote/تماس/Expert/ID داخلی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۳ | Expert | ورود و `/expert` | Request را از فهرست و جزئیات باز کند | نیاز و Cargo مجاز | Tenant خارجی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۴ | Expert | جزئیات Request | Quote صادر کند | Quote جاری و waiting customer | Shipment خودکار | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۵ | مشتری حساب‌دار | `/customer/requests` | Quote را ببیند و بپذیرد | پاسخ و history ماندگار | ویرایش مبلغ/ارز | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۶ | Expert | جزئیات Request | CTA ایجاد Shipment را انتخاب و ثبت کند | Shipment جدا با source/fixed owner | تبدیل Request یا مالک client-side | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۷ | Expert | Shipment/Workspace | refresh، بازگشایی و منبع را بررسی کند | lineage و owner ثابت | انتقال با reassignment | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۸ | آزمون منفی | direct routes | Request/Quote/Shipment خارجی را هدف بگیرد | رد بدون نشت | تأیید وجود یا mutation | ثبت نشده | `NOT_RUN` | ثبت نشده |

نتیجهٔ کل مرور `FWD-IPJ-01`: `NOT_RUN`.

### مرور انسانی FWD-IPJ-02

| گام | بازیگر | شروع | اقدام | انتظار قابل مشاهده | نباید رخ دهد | مشاهده | نتیجه | مدرک |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ۱ | Expert | `/operations` | Workspace و freshness را بررسی کند | وضعیت FRESH یا warning صریح | false healthy | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۲ | Expert | Attention | Shipment را از source path باز کند | دلیل، زمان، next action، owner | زمینه نامرتبط/خارجی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۳ | Expert | مسائل عملیاتی | Exception با دلیل/اثر/مدرک بسازد | Exception فعال و ماندگار | مشکل بدون دلیل مصوب | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۴ | Expert | همان Shipment | Action مرتبط بسازد و پیگیری کند | owner ثابت، موعد، پیگیری | external assignee تأییدنشده | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۵ | اپراتور آزمون | بیرون مرورگر | evaluator مصوب را اجرا کند | Attention تازه در Workspace/Tower | وابستگی به صفحه باز | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۶ | Expert | Action | نتیجه را ثبت و Action را ببندد | Action resolved، Exception باز | بستن ضمنی Exception/SLA | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۷ | Expert | Exception | آن را جدا رفع و history را باز کند | دو resolution مستقل در history | حذف history | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۸ | Expert | Workspace/Tower | refresh و drill-down کند | truth/freshness مشترک | اختلاف دو نما | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۹ | آزمون منفی | نشست peer/foreign | Shipment را مستقیم بخواند/تغییر دهد | رد بدون نشت | count/mutation leakage | ثبت نشده | `NOT_RUN` | ثبت نشده |

نتیجهٔ کل مرور `FWD-IPJ-02`: `NOT_RUN`.

### مرور انسانی FWD-IPJ-03

| گام | بازیگر | شروع | اقدام | انتظار قابل مشاهده | نباید رخ دهد | مشاهده | نتیجه | مدرک |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ۱ | Admin A | `/admin` | کاربر Expert A را مدیریت کند | فقط کاربران A | ساخت Platform Admin یا B | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۲ | Admin A | پنل Admin | از لینک visible به پشتیبانی حساب برود | صفحهٔ حساب‌های A | نیاز به URL دستی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۳ | Admin A | پشتیبانی حساب | Account A را disable/enable یا recovery کند | وضعیت/تحویل روشن و session invalidation | مشاهده رمز/حساب B | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۴ | Admin A | تب SLA سازمان | rule بسازد، نسخه دهد و history را ببیند | نسخه و فعال‌بودن روشن | default یا business calendar پنهان | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۵ | Expert/Customer A | سطح عادی نقش | اثر مجاز تغییر را ببیند | فقط A و session معتبر | داده B یا session قدیمی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۶ | Admin A | direct ID/URL | account/SLA/user مربوط به B را هدف بگیرد | رد بدون نشت و mutation | تفاوت افشاگر | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۷ | Platform Admin | `/operations` | بدون membership عملیات Tenant را باز کند | منع «نیاز به سازمان» | اختیار ضمنی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۸ | همه نقش‌ها | خروج/ورود تازه | scope و cache را دوباره بررسی کنند | جداسازی پایدار | دادهٔ نشست قبلی | ثبت نشده | `NOT_RUN` | ثبت نشده |

نتیجهٔ کل مرور `FWD-IPJ-03`: `NOT_RUN`. گام ۲ با وضعیت فعلی محصول دارای شکاف پیاده‌سازی شناخته‌شده است.

### مرور انسانی FWD-IPJ-04 — هدف فاز ۳

| گام | بازیگر | شروع | اقدام | انتظار قابل مشاهده | نباید رخ دهد | مشاهده | نتیجه | مدرک |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ۱ | Expert | Workspace | Shipment هدف را با Cargo چند Request/Customer تشکیل دهد | attribution و lineage روشن | customer list مستقل یا حذف lineage | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۲ | Expert | Cargo | requested/planned/actual را ثبت و مقایسه کند | هر سه مقدار و history جدا | overwrite مقدار قبلی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۳ | Expert | Allocation | یک Cargo را تقسیم و یک وسیله را shared کند | remainder روشن و over-allocation مسدود | جمع ناسازگار یا success جعلی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۴ | Expert | Route/Execution | Route Legs، Means، Equipment و Carrierها را تنظیم کند | plan/actual و مفاهیم جدا | Means=Equipment یا Carrier روی کل Shipment | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۵ | Expert/Customerها | Documents | اسناد cargo/shared/internal را بررسی کنند | هر Customer فقط scope مجاز | invoice/packing list Customer دیگر | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۶ | Expert/Customerها | Timeline | موقعیت را گزارش و سپس اصلاح کند | time/source و correction صادقانه | ادعای live GPS یا حذف گزارش قبلی | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۷ | Expert/Customerها | Problems | مشکل Customer B با اثر مشترک ثبت کند | A فقط اثر امن را می‌بیند | علت خصوصی B یا سکوت کامل برای A متأثر | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۸ | Expert | Deliveries | Delivery جزئی در مقصدهای متفاوت ثبت کند | quantity/location/evidence هر Delivery | بسته‌شدن Shipment با Delivery اول | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۹ | Admin/Expert | Closure | checklist و استثنای مجاز را بررسی کند | closure کنترل‌شده و audit | bypass توسط Expert | ثبت نشده | `NOT_RUN` | ثبت نشده |
| ۱۰ | همه نقش‌ها | خروج/ورود تازه | Shipment را بازگشایی کنند | history، privacy و next action پایدار | نشت cache یا target-as-current | ثبت نشده | `NOT_RUN` | ثبت نشده |

نتیجهٔ کل مرور `FWD-IPJ-04`: `NOT_RUN`. این اسکریپت فقط برای Candidate پیاده‌سازی‌شده آینده قابل اجراست و تعریف آن به معنی شروع Phase 3 نیست.

## ۹. نگاشت شواهد موجود

### ۹.۱ نگاشت سفر به شواهد

| سفر | مدرک موجود و محدوده | طبقهٔ Slice | محدودیت استفاده | Integrated |
| --- | --- | --- | --- | --- |
| `FWD-J01` | [Phase 1](../operational/evidence/operational-workspace-phase-1-20260924/README.md)، تکرار Phase 2/2.5 و [MT-3](../operational/evidence/mt3-public-tracking-security-closure-20260921.md): ایجاد anonymous در API، بازکردن UI پیگیری و امنیت capability | `PARTIAL_EXISTING_EVIDENCE` | ارسال کامل فرم UI تا پایان، در release set فعلی ثابت نشده است. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J02` | Phase 1/2/2.5: login، private list/detail، Quote history/response، recovery و account-admin API | `PARTIAL_EXISTING_EVIDENCE` | کل زنجیرهٔ ایجاد Request در نشست تا Quote و دادهٔ غیرمصنوعی/تحویل واقعی email پوشش Release ندارد. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J03` | شواهد Quote communication، fixed owner و Phase 1 Request/Shipment separation | `PARTIAL_EXISTING_EVIDENCE` | یک اجرای چندنقشی normal-navigation از Request تا Shipment روی Candidate دقیق وجود ندارد. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J04` | Phase 1 و تکرارهای [Phase 2](../operational/evidence/operational-workspace-phase-2-20260924/README.md) و [Phase 2.5](../operational/evidence/operational-monitoring-reliability-phase-2-5-20260924/README.md) | `FULL_EXISTING_SLICE_EVIDENCE` | Slice PASS جای release set یا human walkthrough را نمی‌گیرد. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J05` | Phase 2: Exception/Action/follow-up/resolution/history؛ Phase 2.5: evaluator مستقل و freshness | `FULL_EXISTING_SLICE_EVIDENCE` | روی Product SHA قبلی و در بستهٔ Slice اجرا شده است. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J06` | Phase 2 SLA admin/foreign denial؛ Phase 1 account admin API؛ آزمون‌های کاربران | `PARTIAL_EXISTING_EVIDENCE` | سفر UI یکپارچه نیست و لینک visible پشتیبانی حساب مفقود است. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J07` | Phase 2 Control Tower/drill-down؛ Phase 2.5 shared stale truth | `FULL_EXISTING_SLICE_EVIDENCE` | release candidate exact و human هنوز اجرا نشده‌اند. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J08` | MT-1/MT-3، authorization ledger و منفی‌های Phase 1/2 | `PARTIAL_EXISTING_EVIDENCE` | یک ماتریس release-wide چندنقشیِ واحد روی Candidate دقیق وجود ندارد. | `NO_INTEGRATED_EVIDENCE_YET` |
| `FWD-J09` | Product Contract v1 و تصمیم صریح Product Owner؛ foundationهای پراکنده current | `TARGET_DEFINITION_ONLY` | هیچ implementation، Slice qualification یا journey execution برای قرارداد کامل وجود ندارد. | `NOT_RUN` |
| `FWD-IPJ-01` | فقط ورودی‌های Slice بالا | `PARTIAL_EXISTING_EVIDENCE` | جمع Sliceها PASS یکپارچه نمی‌سازد. | `NOT_RUN` |
| `FWD-IPJ-02` | فقط ورودی‌های Slice بالا | `FULL_EXISTING_SLICE_EVIDENCE` | زنجیرهٔ کامل Pack به‌عنوان یک Release journey اجرا نشده است. | `NOT_RUN` |
| `FWD-IPJ-03` | فقط ورودی‌های Slice بالا | `PARTIAL_EXISTING_EVIDENCE` | navigation gap و نبود اجرای ترکیبی. | `NOT_RUN` |
| `FWD-IPJ-04` | فقط تعریف هدف `FWD-J09` و Product Contract v1 | `TARGET_DEFINITION_ONLY` | implementation و Candidate واجد اجرا وجود ندارد. | `NOT_RUN` |

### ۹.۲ آشتی مواد Journey قدیمی

| مادهٔ موجود | طبقه | استفاده در Pack v1 |
| --- | --- | --- |
| [Phase 1 evidence](../operational/evidence/operational-workspace-phase-1-20260924/README.md) | `CURRENT_AND_REUSED_AS_SLICE_INPUT` | Workspace، fixed owner، tenant، Customer Account، Public Tracking و anonymous؛ متادیتای LPAF v2.6 آن تاریخی است و خط مبنای حاکم امروز نیست. |
| [Phase 2 evidence](../operational/evidence/operational-workspace-phase-2-20260924/README.md) | `CURRENT_AND_REUSED_AS_SLICE_INPUT` | SLA، Exception، Action، Workspace، Control Tower و تکرار Phase 1. |
| [Phase 2.5 evidence](../operational/evidence/operational-monitoring-reliability-phase-2-5-20260924/README.md) | `CURRENT_AND_REUSED_AS_SLICE_INPUT` | requalification زیر LPAF v2.7، evaluator مستقل و freshness؛ خودش صریحاً integrated/human را اجراشده نمی‌داند. |
| [S6 Golden Business Journeys](../governance/S6-GOLDEN-BUSINESS-JOURNEYS.md) | `HISTORICAL_REFERENCE_ONLY / PARTIALLY_REUSED` | واژگان و خطرها؛ PASSهای قدیمی یا قراردادهای هدف، PASS این Pack نیستند. |
| [Product Reality Walkthrough v1](../operational/evidence/product-reality-walkthrough-v1.md) | `HISTORICAL_REFERENCE_ONLY / PARTIALLY_REUSED` | نشانه‌های reachability و Product reality؛ Candidate و دامنهٔ آن متفاوت است. |
| [Final Product Acceptance after ADR-047](../operational/evidence/final-product-acceptance-after-adr047-20260921.md) | `HISTORICAL_REFERENCE_ONLY / SUPERSEDED_FOR_CURRENT_RELEASE_CLAIM` | پوشش گستردهٔ قبلی برای کشف خطرها؛ نه پذیرش یکپارچهٔ LPAF v2.7 و نه Candidate جاری. |
| اسناد readiness/UAT قدیمی در `docs/product` | `HISTORICAL_REFERENCE_ONLY` | برای ریشه‌یابی و فهم شکاف؛ وضعیت‌های قبلی را به امروز منتقل نمی‌کند. |
| Journey Pack v1 | `HISTORICAL_VERSION_IN_GIT` | نسخه پایه commit `71131e672ee349773c09b124451fd0953c2e5c75`؛ شناسه‌های `FWD-J01..J08` حفظ شده‌اند. |
| این سند v1.1 | `CURRENT_CANONICAL_REFERENCE` | فهرست فعال، `FWD-J09`، `FWD-IPJ-04`، نگاشت، Release gates، impact/staleness و human scripts. |

### ۹.۳ حقیقت Candidate و اعتبار مدرک

- Product SHA بستهٔ Phase 2.5 برابر `1aea4bebdde7e240a903baea1b7b678993f3c505` است.
- commit بعدی `48833131073d4b5c0a5229550e4391abe44e5704` فقط فایل‌های evidence همان بسته را افزوده است.
- این نسبت اجازه می‌دهد شواهد Phase 2.5 به‌عنوان Slice input نگاشت شوند، اما الزام LPAF برای اجرای integrated automated journey روی Candidate دقیق Release را حذف نمی‌کند.
- commitهای مستندسازی این مأموریت نیز Candidate آینده را جلو می‌برند؛ پیش از Release، هویت Candidate باید دوباره ثبت و مجموعهٔ لازم روی همان SHA اجرا شود.

## ۱۰. مجموعهٔ خودکار Release که باید ساخته/اجرا شود

| شناسه | دامنه | روش لازم | وضعیت فعلی |
| --- | --- | --- | --- |
| `FWD-AUTO-IPJ-01` | `FWD-IPJ-01` | مرورگر واقعی، چند نشست نقش، PostgreSQL disposable، normal navigation، persistence/reopen و منفی‌های مجوز | `DEFINED_NOT_RUN` |
| `FWD-AUTO-IPJ-02` | `FWD-IPJ-02` | مرورگر واقعی + evaluator بیرون مرورگر، Workspace/Tower مشترک، history و resolution مستقل | `DEFINED_NOT_RUN` |
| `FWD-AUTO-IPJ-03` | `FWD-IPJ-03` | دو Tenant و چند نقش، admin normal navigation، session invalidation و direct negative probes | `DEFINED_NOT_RUN` |
| `FWD-AUTO-IPJ-04` | `FWD-IPJ-04` | Candidate آینده؛ چند Request/Customer/Cargo، allocation، route/execution، privacy، correction، partial delivery و closure | `DEFINED_TARGET_NOT_RUN` |

حداقل ثبت هر اجرا:

- full Candidate SHA و dirty/clean state؛
- migration head یکتا و شناسهٔ DB disposable؛
- نسخهٔ مرورگر و runner؛
- fixture/actor/Tenant بدون secret؛
- شمارش سناریو و نتیجهٔ هر شناسه؛
- console/page/request error audit؛
- persistence/reopen و cleanup؛
- screenshot/log/result machine-readable؛
- فهرست انتظارهای منفی و پاسخ واقعی؛
- نتیجهٔ نهایی بدون تبدیل `NOT_RUN` یا `UNKNOWN` به PASS.

## ۱۱. ماتریس Release Gate

قاعدهٔ ثابت: وجود هر نتیجهٔ `FAIL`، `BLOCKED`، `UNTESTED`، `STALE`، `UNKNOWN` یا `NOT_RUN` در gate الزامی، `RELEASE_READY=NO` می‌دهد.

| Gate | انتظار برای Candidate Release | وضعیت فعلی | مانع Release؟ |
| --- | --- | --- | --- |
| Journey Pack v1.1 | نه Critical (هشت current + یک target) و چهار Integrated تعریف و نسخه‌بندی شده | `DEFINED` | خیر، خود تعریف کامل است |
| Product Authority | تغییرات مشاهده‌پذیر Candidate دارای approval و reconciliation | `UNTESTED_FOR_FUTURE_CANDIDATE` | بله |
| Candidate identity | branch/SHA/clean/ahead-behind و artifact دقیق ثبت شده | `UNTESTED_FOR_FUTURE_CANDIDATE` | بله |
| Migration/runtime identity | یک head، DB و runtime مطابق Candidate | `UNTESTED_FOR_FUTURE_CANDIDATE` | بله |
| Slice journeys | Sliceهای affected روی Candidate دقیق معتبرند | `MAPPED_NOT_RELEASE_RERUN` | بله |
| `FWD-AUTO-IPJ-01` | PASS روی Candidate دقیق | `NOT_RUN` | بله |
| `FWD-AUTO-IPJ-02` | PASS روی Candidate دقیق | `NOT_RUN` | بله |
| `FWD-AUTO-IPJ-03` | PASS روی Candidate دقیق | `NOT_RUN` | بله |
| `FWD-AUTO-IPJ-04` | PASS روی Candidate پیاده‌سازی‌شده آینده | `NOT_RUN` | بله برای Release شامل Phase 3 |
| Authorization/Tenant matrix | positive normal journeys و negative direct access PASS | `NOT_RUN_AS_RELEASE_SET` | بله |
| Freshness/reliability | evaluator و Workspace/Tower truth روی محیط Release معتبر | `NOT_RUN_AS_RELEASE_SET` | بله |
| Error/empty/denied | حالت‌های لازم بدون success جعلی PASS | `NOT_RUN_AS_RELEASE_SET` | بله |
| Human `FWD-IPJ-01` | PASS انسانی مجاز با مدرک | `NOT_RUN` | بله |
| Human `FWD-IPJ-02` | PASS انسانی مجاز با مدرک | `NOT_RUN` | بله |
| Human `FWD-IPJ-03` | PASS انسانی مجاز با مدرک | `NOT_RUN` | بله |
| Human `FWD-IPJ-04` | PASS انسانی مجاز با مدرک | `NOT_RUN` | بله برای Release شامل Phase 3 |
| Known gaps | همهٔ gapهای Release بسته یا صریحاً خارج scope با authority | `OPEN` | بله |
| Global Product validation | مدرک کامل زیر LPAF | `EVIDENCE_PENDING` | بله |

نتیجهٔ فعلی ماتریس: `RELEASE_READY=NO`.

## ۱۲. قانون Journey Impact برای مأموریت‌های آینده

هر مأموریت Forwarder پیش از Solution/Build/Verify باید یکی از این دو حالت را ثبت کند:

```text
JOURNEY_IMPACT=NONE
JOURNEY_IMPACT_RATIONALE=<مدرک اینکه رفتار، نقش، داده، ناوبری، مجوز و freshness هیچ سفر را تغییر نمی‌دهد>
```

یا:

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J..,FWD-IPJ-..
OBSERVABLE_CHANGE=<تغییر ساده و قابل فهم برای Product Owner>
REQUIRED_SLICE_RERUN=<شناسه‌ها>
REQUIRED_INTEGRATED_RERUN=<شناسه‌ها>
HUMAN_WALKTHROUGH_RERUN=YES|NO_WITH_AUTHORITY
```

تغییر در outcome، گام، نقش، Tenant، navigation/reachability، دادهٔ ماندگار، status، مجوز، empty/error/denied، freshness، owner/SOR یا must-not یک impact است. تغییر تست یا سند برای عادی‌سازی رفتار بدون authority ممنوع است. `NONE` بدون rationale قابل بازبینی پذیرفته نیست.

## ۱۳. قانون کهنگی شواهد

مدرک برای ادعای Release `STALE` است اگر پس از Candidate آن، هر بخش مرتبط زیر تغییر کرده باشد:

- runtime Product، API، schema/migration یا seed/fixture مؤثر؛
- نقش، permission، Tenant population، session/capability یا authorization contract؛
- navigation، route، UI outcome، copy معنادار، empty/error/denied؛
- owner/SOR، lifecycle، Quote/Request/Shipment semantics؛
- SLA/Attention/evaluator/freshness؛
- خود journey یا انتظار پذیرش آن؛
- test/harness به شکلی که معنا یا قدرت مدرک را تغییر دهد.

یک diff صرفاً مستنداتی می‌تواند برای «نگاشت Slice» با تحلیل مسیرها reuse شود، اما Integrated Release Journey باید روی SHA دقیق Candidate آینده اجرا شود. evidence بدون full SHA، محیط، نتیجهٔ سناریو، negative/error audit یا cleanup برای Release برابر `UNKNOWN` است. هر `STALE` یا `UNKNOWN` مانع Release است.

افزودن قرارداد هدف و `FWD-J09` در این مأموریت، چون هیچ runtime Product را تغییر نمی‌دهد، evidence رفتار فعلی `FWD-J01..J08` را صرفاً به دلیل تغییر مستندات stale نمی‌کند. در اولین Candidate که بخشی از target فاز ۳ را پیاده کند، Journey Impact باید دوباره ارزیابی و `FWD-J09/FWD-IPJ-04` و سفرهای فعلی متاثر روی همان Candidate اجرا شوند.

## ۱۴. شکاف‌های فعلی

| شناسه | نوع | شرح ساده | اثر |
| --- | --- | --- | --- |
| `FWD-GAP-01` | `IMPLEMENTATION_GAP` | صفحهٔ پشتیبانی حساب‌های پرتال مشتری پیاده‌سازی شده، اما از پنل مدیر سازمان لینک visible ندارد. | `FWD-J06` و `FWD-IPJ-03` با normal navigation نمی‌توانند PASS شوند. |
| `FWD-GAP-02` | `EVIDENCE_GAP` | هیچ‌یک از سه Integrated Journey به‌عنوان Release set روی Candidate دقیق اجرا نشده‌اند. | همهٔ Release gateهای یکپارچه بازند. |
| `FWD-GAP-03` | `EVIDENCE_GAP` | هیچ Human Product Walkthrough مجاز اجرا و ثبت نشده است. | Release Ready ممکن نیست. |
| `FWD-GAP-04` | `EVIDENCE_GAP` | سفر ناشناس در شواهد جدید، ایجاد API و مشاهده UI را دارد اما ارسال کامل فرم UI تا پایان یک Journey واحد نیست. | `FWD-J01` نیازمند اجرای کامل است. |
| `FWD-GAP-05` | `EVIDENCE_GAP` | Customer Account با دادهٔ synthetic آزموده شده و تحویل واقعی email recovery در محیط Release اثبات نشده است. | بخش محیطی `FWD-J02/J06` باز است. |
| `FWD-GAP-06` | `EVIDENCE_GAP` | ماتریس چندنقشی Tenant/Authorization به‌صورت یک Release journey واحد اجرا نشده است. | `FWD-J08/FWD-IPJ-03` بازند. |
| `FWD-GAP-07` | `EVIDENCE_GAP` | وضعیت جهانی Product زیر LPAF همچنان `EVIDENCE_PENDING` است. | ادعای Product validation سراسری ممنوع است. |
| `FWD-GAP-08` | `TARGET_PHASE3 / IMPLEMENTATION_GAP` | `FWD-J09` و `FWD-IPJ-04` تعریف شده‌اند، اما هیچ بخش از قرارداد کامل چندمشتری به‌عنوان Candidate فاز ۳ پیاده یا qualified نشده است. | هیچ PASS یا Release claim برای سفر جدید مجاز نیست. |

## ۱۵. Journeyهای پیشنهادی، نه Critical فعلی

این موارد در محصول یا شواهد آن دیده شده‌اند، اما این مأموریت آن‌ها را به فهرست حیاتی اضافه نمی‌کند. Product Owner می‌تواند هر مورد را جداگانه بپذیرد یا رد کند.

| شناسه پیشنهادی | چیست؟ | چرا ممکن است حیاتی شود؟ | خطر اگر پوشش نداشته باشد | وضعیت فعلی |
| --- | --- | --- | --- | --- |
| `FWD-PJ-01` | بازیابی رمز و enrollment حساب مشتری | راه بازگشت مشتری به حساب و امنیت session است. | قفل‌شدن مشتری، enumeration یا معتبرماندن نشست قدیمی. | پیاده‌سازی و Slice دارد؛ `PROPOSED_NOT_CRITICAL` |
| `FWD-PJ-02` | ساخت مستقیم Shipment بدون Request/Quote | عملیات واقعی همیشه از Quote شروع نمی‌شود. | جعل lineage، مالک نامعتبر یا اجبار Request ساختگی. | پیاده‌سازی شده؛ `PROPOSED_NOT_CRITICAL` |
| `FWD-PJ-03` | اسناد Shipment و آمادگی مدارک | سند برای اجرای حمل و اثبات تصمیم‌ها مهم است. | نشت فایل، نسخهٔ اشتباه، گم‌شدن history یا readiness نادرست. | پیاده‌سازی/شواهد تاریخی دارد؛ `PROPOSED_NOT_CRITICAL` |
| `FWD-PJ-04` | حمل ترکیبی / چندوجهی | یک Request intent می‌تواند combined باشد و اجرای واقعی چند mode داشته باشد. این بعد با چندمشتری/چندکالا یکی نیست. | مخلوط‌شدن intent تجاری با Route Legs واقعی یا از دست‌رفتن تغییر mode. | مستقل از `FWD-J09`؛ `PROPOSED_TARGET_NOT_CRITICAL` |
| `FWD-PJ-05` | نقاط لجستیکی خصوصی سازمان | شبکهٔ عملیاتی سازمان باید از مرجع پلتفرم جدا و Tenant-safe باشد. | استفادهٔ cross-Tenant، مکان ساختگی یا تغییر ناخواستهٔ snapshot. | سطح فعلی دارد؛ `PROPOSED_NOT_CRITICAL` |
| `FWD-PJ-06` | پیگیری عمومی Project در کنار Request tracking | محصول دو نوع public tracking جدا دارد. | اشتباه‌گرفتن capabilityها، هدایت غلط یا گسترش allowlist. | route جدا موجود است؛ `PROPOSED_NOT_CRITICAL` |

## ۱۶. حوزه‌های آینده و عمداً خارج از Pack v1

موارد زیر Critical Journey فعلی نیستند و تا تصویب Product Owner و وجود implementation scope نباید وارد Release requirements این Pack شوند:

- implementation و qualification رفتارهای `TARGET_PHASE3`؛
- AI؛
- Finance؛
- Carrier Portal؛
- Driver Portal؛
- گسترش حل‌نشدهٔ Customs؛
- business-calendar semantics تأییدنشده؛
- external assignee model تأییدنشده.

وجود UI یا دادهٔ مقدماتی در یک گوشه، این حوزه‌ها را به Product truth فعال تبدیل نمی‌کند.

## ۱۷. تصمیم‌های Product باز

| شناسه | تصمیم لازم | گزینه/اثر ساده |
| --- | --- | --- |
| `FWD-DEC-01` | آیا هر Journey پیشنهادی `FWD-PJ-01..06` به Critical تبدیل شود؟ | پذیرش، آن را وارد gates و rerunهای Release می‌کند؛ `FWD-PJ-04` فقط Combined/Multimodal است و با `FWD-J09` ادغام نمی‌شود. |
| `FWD-DEC-02` | اولویت رفع navigation پشتیبانی حساب چیست؟ | بدون لینک visible، `FWD-IPJ-03` normal-navigation PASS نمی‌شود. |
| `FWD-DEC-03` | معیار محیطی تحویل ایمیل recovery برای Release چیست؟ | باید محیط، provider و evidence لازم مشخص شود؛ این سند production را فعال نمی‌کند. |
| `FWD-DEC-04` | آیا Project Public Tracking باید سفر حیاتی مستقل باشد؟ | اگر بله، capability/allowlist و جدایی از Request tracking gate جدا می‌خواهد. |

موضوع‌هایی مانند business calendar، external assignee، Finance و Customs expansion در این نسخه «تصمیم Release جاری» نیستند؛ عمداً deferred هستند.

## ۱۸. چک‌لیست اجرای آینده

### پیش از اجرا

- Candidate exact SHA، branch، ahead/behind و clean state را ثبت کنید.
- یک Alembic head و DB disposableِ متعلق به runner را ثابت کنید.
- Product Authority Record و `JOURNEY_IMPACT` مأموریت را بخوانید.
- affected journeys و staleness شواهد قبلی را محاسبه کنید.
- fixtureهای دو Tenant و تمام نقش‌ها را بدون secret آماده کنید.
- مطمئن شوید navigation عادی وجود دارد؛ URL دستی فقط برای آزمون منفی مجاز است.

### پس از اجرا

- نتیجهٔ هر `FWD-AUTO-IPJ-*` و هر گام انسانی را جدا ثبت کنید.
- refresh/reopen، negative authorization، empty/error/denied و freshness را جا نیندازید.
- انتظار و مشاهده را کنار هم بنویسید؛ screenshot به‌تنهایی کافی نیست.
- cleanup مرورگر، process و DB را ثابت کنید.
- هر اختلاف را `AUTHORIZED`، `PRESERVED`، `VIOLATION` یا `UNKNOWN` reconcile کنید.
- فقط وقتی تمام gateهای الزامی PASS هستند، درخواست Release Ready مطرح کنید.

## ۱۹. مرور کوتاه Product Owner

### A. سفرهای حیاتی پذیرفته‌شده در این مأموریت

`FWD-J01` مشتری ناشناس، `FWD-J02` مشتری حساب‌دار، `FWD-J03` تحویل تجاری به عملیات، `FWD-J04` Workspace روزانه، `FWD-J05` مشکل/پیگیری، `FWD-J06` مدیر سازمان، `FWD-J07` برج کنترل و `FWD-J08` حفاظت Tenant/Authorization، همگی با هویت قبلی حفظ شده‌اند. `FWD-J09` پرونده حمل مشترک چندمشتری/چندکالا به‌عنوان `CRITICAL_TARGET_PHASE3` افزوده شده است.

چهار زنجیرهٔ پذیرش: `FWD-IPJ-01` نیاز تا Shipment، `FWD-IPJ-02` Shipment فعال تا حل عملیاتی، `FWD-IPJ-03` ادارهٔ سازمان/جداسازی Tenant و `FWD-IPJ-04` Shipment مشترک از assembly تا delivery/closure. هر چهار `NOT_RUN` هستند.

### B. پیشنهادهای نیازمند قبول یا رد

بازیابی رمز، Shipment مستقیم، اسناد Shipment، Combined/Multimodal، نقاط لجستیکی خصوصی و Project Public Tracking. چندمشتری/چندکالا دیگر proposal نیست و با شناسه `FWD-J09` هدف حیاتی مصوب است؛ Combined همچنان جدا و غیرحیاتی است.

### C. شکاف‌های مهم فعلی

لینک visible پشتیبانی حساب در Admin وجود ندارد؛ integrated release set و human walkthrough اجرا نشده‌اند؛ anonymous full-UI، email delivery و ماتریس چندنقشی release-wide مدرک جاری ندارند؛ `FWD-J09/FWD-IPJ-04` نیز فقط تعریف هدف‌اند و implementation/evidence ندارند.

### D. تصمیم‌های لازم پیش از پذیرش Release آینده

تصمیم دربارهٔ پیشنهادهای بالا، رفع navigation gap و معیار محیطی email recovery. بعد از هر تغییر Product، impact و rerun لازم باید طبق بخش‌های ۱۲ و ۱۳ ثبت شود.

### E. حوزه‌های عمداً آینده

پیاده‌سازی Phase 3، AI، Finance، Carrier Portal، Driver Portal، Customs توسعه‌نیافته، business calendar و external assignee. مأموریت بعدی فقط UX/Wireframe/Prototype فاز ۳ است.

## ۲۰. وضعیت نهایی همین مرجع

```text
JOURNEY_PACK_VERSION=1.1
JOURNEY_PACK=DEFINED
FWD_J01_TO_J08_PRESERVED=PASS
FWD_J09=CRITICAL_TARGET_PHASE3
FWD_J09_STATUS=DEFINED_NOT_IMPLEMENTED
FWD_IPJ_04=DEFINED_TARGET_NOT_RUN
SLICE_EVIDENCE=MAPPED
INTEGRATED_PRODUCT_JOURNEYS=DEFINED_NOT_RUN
AUTOMATED_PRODUCT_JOURNEYS=DEFINED_NOT_RUN_AS_RELEASE_SET
HUMAN_PRODUCT_WALKTHROUGH=DEFINED_NOT_RUN
JOURNEY_IMPACT=NEW_JOURNEY_REQUIRED
NEW_JOURNEY=FWD-J09
CURRENT_IMPLEMENTATION_DISTINGUISHED_FROM_TARGET=PASS
REFERENCE_IMPACT=NONE
GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING
RELEASE_READY=NO
```

این سند اجازهٔ merge، deploy، دسترسی production یا شروع Phase 3 نیست.

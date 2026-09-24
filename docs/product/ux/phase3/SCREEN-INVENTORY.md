# موجودی سطح‌های تجربه کاربری فاز ۳

وضعیت: `TARGET_PHASE3_UX`
مرجع اصلی: `../PHASE3-OPERATIONAL-SHIPMENT-UX-BLUEPRINT-V1-FA.md`

این inventory «سطح تجربه» را فهرست می‌کند، نه الزام URL یا component runtime. سطح‌ها می‌توانند در یک Workspace، tab، panel، drawer یا detail view ارائه شوند.

## ۱. Expert — Shipment Workspace

| شناسه | سطح | هدف و داده اصلی | اقدام‌های contextual | حالت‌های مهم | الگوی ارائه |
|---|---|---|---|---|---|
| EXP-01 | Shipment Overview | current stage، reported location، source، freshness، ETA، next point، owner، progress | بازکردن تخصیص، مرور Attention، رفتن به context | normal، incomplete، attention، problem، stale، blocked | Workspace landing + header ثابت |
| EXP-02 | Customers / Requests | Requestهای متصل، Customer و Cargo منبع؛ بدون membership مستقل | افزودن از Request، مشاهده منبع | empty، loading، denied، incomplete | جدول گروه‌بندی‌شده + detail |
| EXP-03 | Cargo | owner Customer، Request، category، HS، packaging، requested/planned/actual، مقصد | افزودن Cargo، تکمیل اطلاعات | incomplete، error، completed | card/table پرتراکم |
| EXP-04 | Route | planned در برابر actual، stageها، زمان مرجع و شاخه‌های Cargo | افزودن stage، تغییر planned view | incomplete، stale، historical | tab + stage rail + branch list |
| EXP-05 | Transport Execution | executionهای هم‌زمان هر leg؛ means، unit/equipment و Carrier جدا | تعریف execution، افزودن detail | incomplete، blocked-by-definition، current | stage context + execution cards |
| EXP-06 | Cargo Allocation | دو نمای Cargo→unit و unit→Customer/Cargo؛ مقدار و باقیمانده | ثبت allocation، انتقال Cargo | partial، over-allocation error، completed، historical | split view + action modal |
| EXP-07 | Documents | سندهای contextual و all documents؛ scope و visibility | افزودن، مشاهده، فیلتر | empty، missing required، denied، error | tabs + filters + rows |
| EXP-08 | Execution / Timeline | روایت عملیات، correction، mode/equipment changes، ETA و location | ثبت موقعیت، ثبت رخداد | current، corrected، historical، stale | awareness header + timeline |
| EXP-09 | Exceptions / Follow-ups | Problem، impact، internal explanation، customer-safe explanation، Action و SLA | ثبت مشکل، ثبت پیگیری | attention، problem، overdue، completed | issue focus + action panel |
| EXP-10 | Deliveries | delivered/remaining، مکان، زمان و evidence هر delivery | ثبت delivery، مشاهده evidence | partial، missing evidence، completed | summary + delivery table |
| EXP-11 | Closure | checklist عمومی و mode-specific، blocker و راه رفع | رفتن به context، درخواست استثنا | blocked، ready، exceptional، completed | control summary + checklist |

### محتوای ثابت Workspace

- هویت Shipment و برچسب `TARGET_PHASE3_UX`؛
- وضعیت کلی و مسئول پرونده؛
- مرحله فعلی؛
- reported location، time و source؛
- ETA range و next important point؛
- freshness؛
- شمارنده state برای هر مقصد ناوبری.

### responsive Expert

در موبایل، برنامه‌ریزی جدولی و تخصیص کامل در اولویت نیست. summary، Timeline، Attention، ثبت موقعیت/رخداد فوری و اسناد کلیدی باید قابل استفاده بمانند. سطح‌های پرتراکم می‌توانند پیام «برای برنامه‌ریزی کامل از دسکتاپ استفاده کنید» بدهند، بدون مسدودکردن خواندن وضعیت.

## ۲. Customer A — authenticated shared-Shipment projection

| شناسه | سطح | آنچه مجاز است | آنچه نباید دیده شود | الگوی ارائه |
|---|---|---|---|---|
| CUS-01 | Shipment Summary | status مجاز، shared indicator، reported location، source، freshness، ETA range و next point | owner داخلی، سایر Customerها، جزئیات private operation | mobile-first stacked summary |
| CUS-02 | Timeline | milestoneهای مجاز، correction ساده، customer-safe issue/outcome، delivery خود مشتری | raw log، internal explanation، private cause و event دیگران | timeline کوتاه و گروه‌بندی‌شده |
| CUS-03 | Cargo | Cargo، description، quantity و destination خود Customer A | Cargo/quantity/مالک B و C | card/detail |
| CUS-04 | Documents | سندهای مجاز Customer A با context واضح | سند داخلی یا مخصوص Customer دیگر | فهرست contextual |
| CUS-05 | Delivery | deliveryهای Customer A، مقدار، مکان، زمان و evidence مجاز | delivery دیگران | summary + history |

### مقایسه privacy مورد انتظار

| `VISIBLE_TO_CUSTOMER_A` | `INTERNAL_ONLY / OTHER_CUSTOMER` |
|---|---|
| نام و Cargo پارس موتور آریا | نام آرمان تجهیز شرق و راهکار پلیمر سپهر |
| وضعیت عملیاتی مجاز حمل مشترک | ظرفیت و allocation واحدهای مشترک |
| location گزارش‌شده، زمان و source ساده | تماس‌ها، یادداشت و confidence داخلی |
| ETA range و next important point مجاز | مبنای محاسباتی یا تحلیل داخلی ETA |
| سندهای scope/visibility مجاز A | Packing List یا رسید مخصوص B/C |
| deliveryهای A | quantity، destination و evidence تحویل B/C |
| پیام امن عمومی مشکل مؤثر | علت داخلی و follow-up خصوصی Carrier |

## ۳. Organization Admin

| شناسه | سطح | هدف | اقدام‌های نمونه | مرز اختیار |
|---|---|---|---|---|
| ADM-01 | Reference Definitions | central catalog → activation/configuration سازمان و مفهوم تعریف سازمانی | فعال‌سازی، درخواست تعریف سازمانی، دیدن history | Expert free-text bypass ندارد؛ Platform governance طراحی نشده |
| ADM-02 | Route Time References | مرجع organization-scoped، stage/mode-specific و versioned | افزودن نسخه، مقایسه current/actual | actual performance مرجع را خودکار تغییر نمی‌دهد |
| ADM-03 | Closure Requirements | requirementهای عمومی و mode-specific | افزودن/نسخه‌بندی/انتشار | مثال Prototype الزام universal ایجاد نمی‌کند |
| ADM-04 | Closure Exception Review | بررسی درخواست خاص با requirement، reason، approver و time | رد یا تصویب دلیل‌دار | requirement حذف یا PASS کاذب نمی‌شود |

## ۴. Overlayها و حالت‌های مشترک

| شناسه | سطح | کاربرد |
|---|---|---|
| OVL-01 | Allocation modal | انتخاب unit/stage و مقدار؛ خطای inline over-allocation |
| OVL-02 | Cargo transfer modal | Cargo، from، to، quantity، point، time و reason |
| OVL-03 | Reported location modal | location، occurrence time، source و note داخلی |
| OVL-04 | Problem / Follow-up modal | ثبت meaning-preserving داده‌های Phase 2 |
| OVL-05 | Delivery modal | Cargo، quantity، place، time و evidence |
| OVL-06 | Closure exception modal | missing requirement، دلیل الزامی و approver |
| OVL-07 | UI states gallery | normal، loading، empty، error، denied و stale برای نقد طراحی |

## ۵. مسیر کلیک ضروری Prototype

1. EXP-01 و خواندن current state؛
2. EXP-02 و EXP-03 برای Request، Customer، Cargo و HS ناقص؛
3. EXP-04 برای planned/actual و شاخه‌ها؛
4. EXP-05 برای چند execution و تفکیک means/unit/Carrier؛
5. EXP-06 برای partial allocation، block over-allocation و transfer history؛
6. EXP-08 برای reported location و correction؛
7. EXP-09 برای internal در برابر customer-safe message؛
8. EXP-10 برای partial delivery؛
9. EXP-11 برای closure blocker و مسیر Admin؛
10. CUS-01 تا CUS-05 برای projection مشتری؛
11. ADM-01 تا ADM-04 برای catalog، reference time، closure rules و exception.

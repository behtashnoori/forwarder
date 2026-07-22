# Phase 0 Domain Dictionary

## واژگان Canonical

| اصطلاح | تعریف | مالک | نام‌های ممنوع/مبهم |
|---|---|---|---|
| ShipmentRequest | بیان نیاز تجاری مشتری پیش از تعهد اجرا | Commercial | shipment اجرایی |
| Quote | پیشنهاد تجاری نسخه‌دار با پذیرش/رد | Pricing | actual cost |
| OperationalShipment | پرونده اجرای end-to-end یک حمل | Execution | ShipmentJob |
| ShipmentJob | alias منسوخ OperationalShipment | هیچ | class/table/API مستقل |
| RoutePlan | نسخه برنامه مسیر یک OperationalShipment | Execution | رخداد واقعی |
| RouteLeg | segment ترتیبی plan بین دو Canonical Location با mode/provider و زمان برنامه‌ای | Execution | TrackingEvent |
| Milestone | نقطه کنترل مورد انتظار روی shipment/leg با planned/actual projection | Execution | event خام |
| MilestoneEvent | شاهد append-only برای تحقق، لغو یا تصحیح Milestone | Visibility | Milestone row update مستقیم |
| TrackingEvent | واقعیت عمومی‌تر مکانی/وضعیتی؛ الزاماً milestone را محقق نمی‌کند | Visibility | RouteLeg |
| CanonicalLocation | هویت مرجع قابل استفاده مجدد یک مکان عملیاتی | Reference | snapshot تاریخی |
| LocationSnapshot | تصویر immutable نام/code/مختصات/timezone لازم در زمان plan/event | Execution/Visibility | master mutable |
| TransportUnit | واحد قابل رهگیری مانند container/truck/package group | Execution | shipment |
| LoadAllocation | تخصیص کمّی order/cargo به unit و leg | Execution | unit ownership |
| ExceptionCase | مسئله عملیاتی مالک‌پذیر با severity و resolution | Control Tower | delayed status |
| WorkItem | projection اقدام‌پذیر برای exception/SLA/data-quality | Control Tower | source event |
| OperationalTask | اقدام قابل واگذاری مرتبط با shipment/exception | Control Tower | CRM Task |
| TransportProject | ظرف چند shipment و dependency/budget مشترک | Projects | shipment |

## تعریف نهایی سه مفهوم اصلی

### RouteLeg

یک جزء ترتیبی و نسخه‌دار از `RoutePlan` است که حرکت یا خدمت بین `from_location` و `to_location` را با mode، provider اختیاری و planned departure/arrival تعریف می‌کند. RouteLeg **برنامه** است؛ ثبت حضور یا حرکت واقعی نیست.

### Milestone

تعهد/نقطه کنترل برنامه‌ریزی‌شده برای OperationalShipment یا RouteLeg است. milestone دارای type، required flag، planned time/window و projection وضعیت/actual است. actual آن فقط از MilestoneEvent معتبر یا override مجاز و ممیزی‌شده حاصل می‌شود.

### MilestoneEvent

رکورد append-only و زمان‌مند از یک ادعای تحقق، لغو یا تصحیح milestone است. شامل `event_id`, `milestone_id`, `event_type`, `occurred_at`, `recorded_at`, actor/source، location snapshot، evidence/reference، verification state و dedupe identity است. حذف/overwrite نمی‌شود؛ تصحیح با event جدید و `supersedes_event_id` انجام می‌شود.

## Canonical Location

تصمیم: از یک abstraction واحد `CanonicalLocation` استفاده می‌شود که می‌تواند رکوردهای موجود Country/Province/City/IranPort/CustomsOffice/TrackingLocationReference را از طریق type و source identity ارجاع دهد. Phase 1 نباید همه جداول مرجع موجود را ادغام کند.

قواعد:

- `canonical_location_id` هویت پایدار داخلی است؛
- `location_type` محدود و versioned؛
- source system/type/id و codeهای معتبر نگهداری می‌شوند؛
- plan و event علاوه بر FK، `LocationSnapshot` immutable دارند؛
- تغییر نام/master تاریخچه را تغییر نمی‌دهد؛
- free text فقط با source=`manual_unverified` و verification state مجاز است؛
- observed location می‌تواند confidence داشته باشد؛
- timezone/geocode/UNLOCODE coverage **نیازمند تأیید** است.

## Cardinality Freeze

| رابطه | Cardinality |
|---|---|
| ShipmentRequest → Quote | 1 به 0..n |
| ShipmentRequest → OperationalShipment | 1 به 0..n؛ سیاست business نیازمند تأیید |
| Accepted Quote → OperationalShipment | 1 به 0..n؛ conversion identity یکتا در revision |
| OperationalShipment → RoutePlan | 1 به 1..n؛ یک baseline فعال |
| RoutePlan → RouteLeg | 1 به 1..n |
| RouteLeg → Milestone | 1 به 0..n |
| Milestone → MilestoneEvent | 1 به 0..n |
| OperationalShipment → TransportUnit | 1 به 0..n |
| CanonicalLocation → Snapshot | 1 به 0..n |

## Invariantهای کلیدی

- sequence RouteLeg در هر plan یکتا و پیوسته است.
- زمان departure برنامه‌ای از arrival بعدتر نیست.
- فقط یک plan baseline فعال است.
- plan منتشرشده immutable است.
- required milestone بدون verified actual نمی‌تواند completion gate را پاس کند.
- `(source, external_event_id)` یا dedupe key رخداد یکتا است.
- `occurred_at` و `recorded_at` جدا هستند.
- status عملیاتی در ShipmentRequest ذخیره نمی‌شود.
- ShipmentJob در هیچ schema/API جدید ظاهر نمی‌شود، مگر توضیح deprecation.

## موارد نیازمند تأیید

CustomerOrder در Phase 1، taxonomy mode/service، source مکان خارجی، نوع evidence و verification authority، واحدهای اندازه‌گیری و قواعد consolidation.

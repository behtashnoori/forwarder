# قرارداد مأموریت P3-02 — انتساب Cargo، منشأ و سه مقدار

وضعیت: `ACTIVE_IMPLEMENTATION_MISSION`
مبنای حاکمیتی: `LPAF v2.7`
سطح سخت‌گیری: `Level B`
مسیر قابلیت: `Astra`
مبنای کد: `integration/golden-controlled@012d1fa1ae9afef902f0fada5ce4e5bf652edfad`
شاخهٔ نامزد: `codex/phase3-p3-02-cargo-lineage`

## نتیجه، دامنه و توقف

نتیجهٔ محصول این بخش آن است که یک Shipment بتواند Cargoهای چند Customer و چند Request را بدون ساخت Request جعلی نگه دارد. هر Cargo انتساب Customer مستقل، منشأ اختیاری Request/Request Cargo، مقدارهای جداگانهٔ درخواستی، برنامه‌ریزی‌شده و واقعی، واحد کنترل‌شده، نوع بسته‌بندی کنترل‌شده و اطلاعات تدریجی خود را حفظ می‌کند.

دامنه فقط `P3-02` است. مسیر شاخه‌ای و planned/actual route، وسیله/تجهیز/Carrier، تخصیص جدید، سند، location، Customer projection، ETA، delivery، closure و انتقال مالک خارج از دامنه‌اند. رفتارهای موجود این حوزه‌ها فقط regression می‌شوند. Production، deployment و release ممنوع‌اند.

شرایط توقف:

- نیاز به lifecycle/status/transition تازهٔ Product (`DN01`)؛
- اجباری‌کردن HS در هر نقطه (`DN05`)؛
- استنتاج Customer از نام، تماس، ایمیل، حساب پرتال یا Request؛
- ساخت Request جعلی برای Cargo مستقیم؛
- تبدیل ضمنی UOM یا تعبیر quantity تاریخی به requested/planned/actual؛
- grant تازهٔ Customer Portal یا تغییر رفتار خارج از `P3-02`.

## Product Authority Record

| فیلد | مقدار |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | انتساب عملیاتی Customer برای هر Cargo؛ منشأ اختیاری Request و Request Cargo؛ Cargo مستقیم بدون Request؛ سه مقدار مستقل requested/planned/actual با unknown صریح؛ مصرف Packaging Type فعال سازمان؛ اطلاعات تدریجی شامل HS، وزن، حجم و مقصد؛ نمایش اطلاعات ناقص؛ حفظ تاریخ تغییرهای معنادار. |
| `DELEGATED_TECHNICAL_CHOICES` | schema افزایشی، کلید و index، DTO و command، optimistic version، audit، compatibility adapter، migration و rollback، ساختار UI و روش آزمون تا وقتی معنای Product تغییر نکند. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | Request/Quote و ایجاد صریح Shipment؛ مسئول ثابت Shipment؛ Cargo Catalog و snapshotهای P3-01؛ Customer Account/Public Tracking؛ مسیر و milestone/event؛ allocation/execution؛ Workspace/Tower؛ همه lifecycleها و permissionهای خارج از این بخش؛ داده تاریخی بدون حدس. |
| `DECISIONS_NEEDED` | `DN01=OPEN` فقط اگر status/transition تازه لازم شود؛ `DN05=OPEN` و هیچ الزام HS اجرا نمی‌شود؛ `DN08=PARTIAL_DECISION_NEEDED` و تعریف/promotion سازمانی ساخته نمی‌شود؛ `DN10=OPEN` و projection خصوصی Customer ساخته نمی‌شود. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner با دستور صریح `START PHASE 3 IMPLEMENTATION — P3-02 AND P3-03 SEQUENTIALLY`؛ LPAF v2.7 برای حاکمیت. |
| `APPROVAL_REFERENCE` | درخواست جاری؛ Product Contract v1 §6–§8 و §13؛ Journey Pack v1.1؛ UX V2.1؛ رکورد P3-02 در Implementation Plan v1. |

## FACT / ASSUMPTION / UNKNOWN / DECISION NEEDED

### FACT

- canonical محلی و `github/integration/golden-controlled` هر دو روی SHA مبنا و ahead/behind برابر `0/0` بودند؛ worktree canonical پاک بود.
- Alembic پیش از تغییر دقیقاً یک head داشت: `20260930_phase3_reference_catalog`.
- P3-01 در ancestry است و CargoType/UOM/Packaging Type و activation سازمانی را فراهم می‌کند.
- `ShipmentCargoItem` اکنون Customer nullable، یک `quantity` بدون معنای سه‌گانه، UOM و snapshotهای catalog دارد؛ lineage هر Cargo به Request وجود ندارد.
- `RequestCargoItem` حقیقت تجاری Request و quantity/UOM اختیاری را جدا نگه می‌دارد.
- `OperationalAudit`، optimistic `version` و authorization مسئول ثابت Shipment موجودند.

### ASSUMPTION قابل آزمون

- کمینهٔ ایمن، توسعهٔ همان `ShipmentCargoItem` به‌عنوان SOR عملیاتی Cargo و استفاده از `OperationalAudit` برای سابقهٔ تغییر است؛ نه aggregate، فهرست Customer یا event store موازی.
- یک UOM کنترل‌شده برای سه quantity هر Cargo از تبدیل ضمنی جلوگیری می‌کند. وزن و حجم، در صورت ثبت، UOM کنترل‌شدهٔ هم‌بُعد خود را دارند.
- برای write سازگار قدیمی، ورودی legacy `quantity` قابل پذیرش می‌ماند اما هیچ‌یک از سه معنای جدید از آن استنتاج نمی‌شود. command جدید `planned_quantity` را صریح می‌نویسد و adapter همان مقدار را برای مصرف‌کنندگان قدیمی نگه می‌دارد.
- اگر Request Cargo مقدار و UOM واقعی داشته باشد، requested snapshot می‌تواند فقط از همان fact و بدون تبدیل ثبت شود؛ اختلاف رد می‌شود.

### UNKNOWN

- کیفیت و completeness داده‌های Cargo قدیمی معلوم نیست؛ migration هیچ Customer، lineage، quantity meaning، Packaging یا HS تازه‌ای برای آن‌ها نمی‌سازد.
- Product rule دقیق الزام HS معلوم نیست و `DN05=OPEN` باقی می‌ماند.

### DECISION NEEDED

- تصمیم تازه‌ای برای اجرای محدوده مجاز لازم نیست. اگر طراحی به status تازه یا الزام HS برسد، فقط همان بخش متوقف و `DN01` یا `DN05` ارائه می‌شود.

## مالکیت، SOR و زنجیره

`ShipmentCargoItem` SOR حقیقت عملیاتی Cargo است و از parent Shipment، tenant و مسئول ثابت را می‌گیرد. `Customer` هویت CRM عملیاتی است و Customer Portal Account نیست. `ShipmentRequest` و `RequestCargoItem` SOR حقیقت تجاری منبع باقی می‌مانند؛ linkage فقط ارجاع و snapshot quantity درخواست‌شده است و مالکیت Shipment را تغییر نمی‌دهد. `CargoType`، `UnitOfMeasure` و `PackagingType` مراجع platform هستند و availability سازمانی با activationهای P3-01 کنترل می‌شود. `OperationalAudit` سابقهٔ command و تغییر را نگه می‌دارد.

زنجیرهٔ command:

`owning Expert → authorized Shipment → same-tenant Customer → optional authorized same-tenant Request/Request Cargo → active organization references → ShipmentCargoItem + audit`

## Journey Impact و شواهد لازم

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J02,FWD-J03,FWD-J04,FWD-J08,FWD-J09,FWD-IPJ-01,FWD-IPJ-04
REQUIRED_SLICE_RERUN=P3-02-MULTI-CUSTOMER,P3-02-DIRECT,P3-02-THREE-QUANTITIES,P3-02-PROGRESSIVE,P3-02-REFERENCES,P3-02-TENANT,P3-02-LEGACY
REQUIRED_INTEGRATED_RERUN=FWD-IPJ-01,FWD-IPJ-04-BOUNDARY
HUMAN_WALKTHROUGH_RERUN=YES_BEFORE_RELEASE_READY
```

Qualification باید backend/frontend متمرکز، PostgreSQL 18، upgrade و downgrade/re-upgrade، tenant/authorization منفی، browser normal navigation و reopen، TypeScript، ESLint، build، architecture/structure/governance، diff check و regression کامل را به SHA دقیق Product bind کند. این مأموریت integrated journeyها را PASS اعلام نمی‌کند.

## وضعیت completion

`Engineering Complete`، `Product Complete`، `Release Ready` و `Release Complete` جدا گزارش می‌شوند. Human Product Walkthrough در این slice اجرا نمی‌شود؛ `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING` و `RELEASE_READY=NO` باقی می‌ماند.

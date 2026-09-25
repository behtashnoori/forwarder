# قرارداد مأموریت P3-01 — کاتالوگ مرجع و انتخاب سازمانی

وضعیت: `ACTIVE_IMPLEMENTATION_MISSION`
مبنای حاکمیتی: `LPAF v2.7`
سطح سخت‌گیری: `Level B`
مسیر قابلیت: `Sol/Astra`
مبنای کد: `integration/golden-controlled@5ebb8c3fb54b0a18898fe04db6ec4135bf41ef7e`
شاخهٔ نامزد: `codex/phase3-p3-01-reference-catalog`

## نتیجه، دامنه و توقف

نتیجهٔ محصول این بخش این است که مدیر سازمان تعیین کند کدام تعریف‌های مرکزیِ تأییدشده برای استفادهٔ جدید سازمان در دسترس‌اند و کارشناس حمل فقط همان گزینه‌ها را در کار عملیاتی انتخاب کند. غیرفعال‌سازی، انتخاب جدید را می‌بندد اما snapshot و خواندن سوابق قبلی را تغییر نمی‌دهد.

دامنه فقط `P3-01` است. Cargo چندمشتری، مسیر، اجرای حمل، تخصیص، سند، Customer projection، ETA، تحویل، closure، انتقال مالک، AI، GPS، مالی، ناوگان و Portalهای Carrier/Driver خارج از دامنه‌اند. Production، deployment و release ممنوع‌اند.

شرایط توقف:

- نیاز به workflow تازهٔ تعریف اختصاصی سازمان یا promotion آن به کاتالوگ مرکزی (`DN08`؛ فقط همان زیرقابلیت متوقف می‌شود)؛
- seed/import خارجی یا دادهٔ استاندارد بدون provenance و qualification؛
- free-text برای جایگزینی نوع پایهٔ کنترل‌شده؛
- بازنویسی snapshot یا معنای تاریخی؛
- تغییر رفتار خارج از `P3-01` یا تضاد حل‌نشده با مرجع Product.

## Product Authority Record

| فیلد | مقدار |
| --- | --- |
| `AUTHORIZED_PRODUCT_CHANGES` | تعریف‌های مرکزیِ کنترل‌شده؛ فعال/غیرفعال‌سازی availability سازمان برای استفادهٔ جدید؛ انتخاب فقط از گزینه‌های فعال سازمان؛ باقی‌ماندن سوابق قبلی پس از rename/update/deactivation؛ UI تدریجی مطابق V2.1؛ audit تغییر availability. |
| `DELEGATED_TECHNICAL_CHOICES` | مدل افزایشی و صریح، نام جدول و endpoint، adapterهای سازگاری، DTO، concurrency، audit، migration، ساختار component و روش آزمون، تا وقتی رفتار محصول را تغییر ندهند. |
| `PROTECTED_OUT_OF_SCOPE_BEHAVIOR` | Request/Cargo/Cargo Catalog/Documents/Logistics Points/Combined Transport/Customer Account/Public Tracking/Operational Workspace/Control Tower و تمام lifecycleها و permissionهای خارج از این بخش؛ نصب با catalog خالی؛ نبود seed خودکار؛ Platform Admin بدون اختیار ضمنی Tenant. |
| `DECISIONS_NEEDED` | `DN08`: semantics ایجاد تعریف اختصاصی سازمان، مرجع review و promotion. این تصمیم برای reuse/activation تعریف مرکزی لازم نیست. هر رفتار Product تازهٔ دیگر نیز `DECISION_NEEDED` است. |
| `APPROVING_OWNER_OR_AUTHORITY` | Product Owner با دستور صریح `START PHASE 3 IMPLEMENTATION — P3-01 ONLY`؛ LPAF v2.7 برای حاکمیت؛ ADRهای پذیرفته‌شده برای مرز فنی موجود. |
| `APPROVAL_REFERENCE` | درخواست جاری، `FORWARDER-PHASE3-IMPLEMENTATION-PLAN-V1-FA.md` رکورد P3-01، Product Contract v1 §5/§7/§20 و UX V2.1 approved. |

## FACT / ASSUMPTION / UNKNOWN / DECISION NEEDED

### FACT

- canonical محلی و `github/integration/golden-controlled` هر دو روی SHA مبنا و ahead/behind برابر صفر بودند؛ worktree مبنا پاک بود.
- Alembic پیش از تغییر یک head داشت: `20260929_operational_monitoring_reliability`.
- `CargoType`، `UnitOfMeasure` و `ServiceType` جدول‌های صریح platform-scoped با code پایدار، lifecycle و version دارند.
- `CargoCatalogItem` سازمانی و `ShipmentCargoItem` دارای snapshotهای CargoType/UOM است؛ snapshot معمولی بازتولید نمی‌شود.
- selector فعلی Cargo، همهٔ `CargoType/UOM`های globally active را نشان می‌دهد و approval سازمانی را اعمال نمی‌کند.
- `GlobalLogisticsPoint` و `OrganizationGlobalLogisticsPointAdoption` الگوی پذیرفته‌شدهٔ central→organization adoption را دارند؛ `DocumentDefinition` و policy سازمانی نیز ownerهای موجود خود را دارند.
- familyهای صریح packaging، transport means و transport equipment در foundation جاری کامل نیستند.

### ASSUMPTION قابل آزمون

- کمینهٔ ایمن P3-01، توسعهٔ owner فعلی master data با familyهای صریح لازم و association سازمانیِ tenant-owned است؛ نه ساخت subsystem موازی.
- availability قبلیِ globally-active CargoType/UOM برای سازمان‌های موجود، در migration فقط به‌عنوان mapping قطعیِ سازگاری حفظ می‌شود؛ این کار reference row تازه یا seed استاندارد تولید نمی‌کند.
- consumption عملیاتی همین بخش به CargoType/UOM موجود محدود می‌ماند؛ familyهای جدید foundation آینده‌اند و مصرف P3-02/P3-04 را در این بخش آغاز نمی‌کنند.

### UNKNOWN

- خانوادهٔ transport mode فعلی (`TransportMethod`) قرارداد identity/version یکسان با master-data جدید ندارد و در Request عمومی نیز مصرف می‌شود؛ تغییر مصرف آن تا اثبات adapter بدون تغییر Journey محفوظ می‌ماند.
- complete global HS catalog و منبع authoritative آن وجود ندارد؛ P3-01 آن را ایجاد یا اجباری نمی‌کند.

### DECISION NEEDED

- `DN08` فقط برای create/promotion تعریف اختصاصی سازمان باز است. هیچ UI/API برای آن در این نامزد ساخته نمی‌شود.

## مالکیت، SOR و زنجیره

تعریف مرکزی `PLATFORM_SCOPED` و SOR آن همان master-data صریح است. availability یک `TENANT_OWNED_DIRECT` متعلق به `OperationalOrganization` است. مدیر سازمان producer تغییر availability، کارشناس consumer گزینهٔ selectable و snapshot عملیاتی منبع نمایش تاریخی است. UI فقط نمایش می‌دهد؛ authorization و tenant scope در backend اعمال می‌شود.

## Journey Impact و شواهد لازم

```text
JOURNEY_IMPACT=AFFECTS_EXISTING_JOURNEY
AFFECTED_JOURNEYS=FWD-J06,FWD-J08,FWD-J09,FWD-IPJ-03,FWD-IPJ-04
REQUIRED_SLICE_RERUN=P3-01-ADMIN,P3-01-EXPERT,P3-01-INACTIVE-HISTORY,P3-01-MISSING,P3-01-TENANT
REQUIRED_INTEGRATED_RERUN=FWD-IPJ-03,FWD-IPJ-04-BOUNDARY
HUMAN_WALKTHROUGH_RERUN=YES_BEFORE_RELEASE_READY
```

مدرک باید به SHA دقیق Product، migration head، PostgreSQL 18، نسخه مرورگر، actor/tenantهای مصنوعی و نتیجهٔ منفی‌ها bind شود. عامل می‌تواند walkthrough را آماده کند اما `HUMAN_PRODUCT_WALKTHROUGH=PASS` را اعلام نمی‌کند.

## وضعیت completion

`Engineering Complete`، `Product Complete`، `Release Ready` و `Release Complete` جدا گزارش می‌شوند. این مأموریت deployment/release ندارد و `GLOBAL_PRODUCT_VALIDATION=EVIDENCE_PENDING` باقی می‌ماند.
